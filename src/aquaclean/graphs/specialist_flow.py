import time

from langgraph.graph import END, START, StateGraph

from aquaclean.agents.prompts import PROMPT_VERSION
from aquaclean.agents.specialists import interpret
from aquaclean.agents.tools import specialist_tools
from aquaclean.domain.errors import DomainError
from aquaclean.graphs.state import CaseState


def specialist_graph(process: str, runtime):
    async def load_tools(state: CaseState):
        actor = runtime.actor
        tools = specialist_tools(process, actor, state["case_id"], runtime.repo, runtime.knowledge)
        results = {}

        async def invoke(name, args):
            start = time.monotonic()
            await runtime.emit(state, "tool.started", {"name": name, "status": "running"})
            try:
                value = await tools[name].ainvoke(args)
                await runtime.emit(
                    state,
                    "tool.completed",
                    {
                        "name": name,
                        "status": "completed",
                        "duration_ms": round((time.monotonic() - start) * 1000),
                        "summary": f"{len(value)} elementos recuperados",
                    },
                )
                return value
            except DomainError as exc:
                await runtime.emit(
                    state,
                    "tool.completed",
                    {
                        "name": name,
                        "status": "unavailable",
                        "duration_ms": round((time.monotonic() - start) * 1000),
                        "summary": str(exc),
                    },
                )
                if name == "approved_knowledge":
                    results["knowledge_status"] = str(exc)
                    return []
                raise

        results.update(await invoke("case_evidence", {}))
        if process == "P1" and results["case"]["client_id"]:
            results["customer"] = await invoke(
                "customer_registry", {"client_id": results["case"]["client_id"]}
            )
        if process == "P2" and (
            results["case"]["order_id"] or results["case"]["pickup_request_id"]
        ):
            results["schedule_options"] = await invoke("schedule_options", {})
        runtime.budget(state)
        results["sources"] = await invoke(
            "approved_knowledge", {"query": state["text"] or f"Procedimiento {process}"}
        )
        results["sources"] += await invoke("historical_references", {"query": state["text"]})
        results["today_lima"] = str(runtime.clock.now().date())
        results["latest_user_message"] = state["text"]
        results["retail_draft"] = state.get("retail_draft", {})
        results["tariff"] = runtime.retail.tariff() if process == "P1" else {}
        results["pilot_limits"] = {"max_clarifications": runtime.settings.max_clarifications}
        # Limit provider context; original messages remain in PostgreSQL.
        results["messages"] = results["messages"][-30:]
        return {
            "context": results,
            "model_calls": state.get("model_calls", 0)
            + (0 if results.get("knowledge_status") else 1),
        }

    async def propose(state: CaseState):
        runtime.budget(state)
        started = time.monotonic()
        await runtime.emit(state, "agent.started", {"agent": process, "status": "interpreting"})
        if process == "P4":
            from aquaclean.agents.deep_incidents.factory import investigate

            proposal = await investigate(runtime, state)
        else:
            proposal = await interpret(runtime.provider, process, state["context"])
        if process == "P1" and state.get("retail_draft"):
            draft = state["retail_draft"]
            proposal.update(
                action=draft["action"],
                missing_fields=[],
                **{k: v for k, v in draft.items() if k != "action"},
            )
        retrieved = {s["chunk_id"]: s for s in state["context"]["sources"]}
        if not set(proposal.get("source_ids", [])) <= retrieved.keys():
            raise DomainError(
                "El proveedor citó una fuente que no fue recuperada.", "invalid_citation", 409
            )
        proposal["sources"] = [retrieved[sid] for sid in proposal.get("source_ids", [])]
        if process == "P2":
            options = {o["id"]: o for o in state["context"].get("schedule_options", [])}
            if not set(proposal.get("option_ids", [])) <= options.keys():
                raise DomainError(
                    "El modelo propuso una opción de agenda inexistente.", "invalid_option", 409
                )
            proposal["options"] = [options[oid] for oid in proposal.get("option_ids", [])]
        await runtime.emit(
            state,
            "agent.completed",
            {
                "agent": process,
                "duration_ms": round((time.monotonic() - started) * 1000),
                "status": "proposed",
                "model": runtime.settings.gemini_chat_model,
                "prompt_version": PROMPT_VERSION,
                "usage": getattr(runtime.provider, "last_usage", {}),
            },
        )
        await runtime.emit(
            state,
            "decision.summary",
            {"rationale_summary": proposal["rationale_summary"], "sources": proposal["sources"]},
        )
        return {
            "proposal": proposal,
            "response": proposal["response"],
            "model_calls": state.get("model_calls", 0)
            + getattr(runtime.provider, "last_call_count", 1),
        }

    graph = StateGraph(CaseState)
    graph.add_node("tools", load_tools)
    graph.add_node("propose", propose)
    graph.add_edge(START, "tools")
    graph.add_edge("tools", "propose")
    graph.add_edge("propose", END)
    return graph.compile()
