import asyncio
import time
from uuid import UUID, uuid5

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from aquaclean.agents.prompts import PROMPT_VERSION
from aquaclean.agents.supervisor import route
from aquaclean.application.presentation import describe_result
from aquaclean.domain.entities import digest
from aquaclean.domain.errors import DomainError
from aquaclean.domain.policies import ROLES, validate_action, validate_request
from aquaclean.graphs.specialist_flow import specialist_graph
from aquaclean.graphs.state import CaseState


class GraphRuntime:
    def __init__(self, settings, actor, clock, repo, provider, knowledge, media, executor):
        from aquaclean.infrastructure.persistence.retail import RetailRepository

        self.retail = RetailRepository(repo.db, clock, settings.retail_tariff_path)
        self.settings, self.actor, self.clock = settings, actor, clock
        self.repo, self.provider, self.knowledge, self.media, self.executor = (
            repo,
            provider,
            knowledge,
            media,
            executor,
        )

    def budget(self, state):
        if state.get("model_calls", 0) >= self.settings.max_model_calls:
            raise DomainError(
                "Límite piloto de llamadas al modelo alcanzado; caso pendiente.", "budget", 409
            )
        self.provider.remaining_calls = self.settings.max_model_calls - state.get("model_calls", 0)

    async def emit(self, state, kind, payload):
        run_id = getattr(self, "current_run_id", state["run_id"])
        run = await self.repo.db.one("SELECT cancelled FROM app.runs WHERE id=%s", (run_id,))
        if run and run["cancelled"]:
            raise DomainError(
                "Respuesta detenida; consulte el estado persistido. Un efecto ya confirmado permanece registrado.",
                "cancelled",
                409,
            )
        await self.repo.event(run_id, state["case_id"], kind, payload)


def build_graph(runtime: GraphRuntime, checkpointer):
    repo, actor = runtime.repo, runtime.actor

    async def perceive(state: CaseState):
        observations = []
        for aid in state.get("attachment_ids", []):
            attachment = await runtime.media.get(actor, state["case_id"], aid)
            if attachment["perception_status"] != "completed":
                started = time.monotonic()
                runtime.budget(state)
                await runtime.emit(
                    state,
                    "tool.started",
                    {"name": "media_perception", "status": "running", "attachment_id": aid},
                )
                text = await runtime.provider.perceive(
                    await asyncio.to_thread(runtime.media.path(attachment).read_bytes),
                    attachment["mime"],
                )
                await repo.db.execute(
                    "UPDATE app.attachments SET observation=%s,perception_status='completed',observation_version=observation_version+1 WHERE id=%s",
                    (text, aid),
                )
                await runtime.emit(
                    state,
                    "tool.completed",
                    {
                        "name": "media_perception",
                        "status": "completed",
                        "attachment_id": aid,
                        "summary": "Observación editable guardada; requiere confirmación.",
                        "duration_ms": round((time.monotonic() - started) * 1000),
                    },
                )
                state["model_calls"] = state.get("model_calls", 0) + 1
            observations.append(
                {"attachment_id": aid, "source": "Gemini; observación sin confirmar"}
            )
        return {"observations": observations, "model_calls": state.get("model_calls", 0)}

    async def supervisor(state: CaseState):
        started = time.monotonic()
        runtime.budget(state)
        case = await repo.case(actor, state["case_id"])
        await runtime.emit(state, "agent.started", {"agent": "supervisor", "status": "routing"})
        decision = await route(
            runtime.provider,
            {
                "case": case,
                "messages": (await repo.messages(actor, state["case_id"]))[-20:],
                "text": state["text"],
            },
        )
        proposed_process = decision.process
        if decision.process == "P2" and not (case["order_id"] or case["pickup_request_id"]):
            # A new pickup starts in attention. Missing an order is a conversational
            # prerequisite, not an integration failure; no logistics tools/effects run.
            decision = decision.model_copy(
                update={
                    "process": "P1",
                    "needs_clarification": False,
                    "rationale_summary": (
                        "El caso aún no tiene un pedido registrado o vinculado. Atención "
                        "recoge los datos de una nueva solicitud o pide vincular el pedido "
                        "existente antes de coordinar su agenda."
                    ),
                }
            )
        if state.get("retail_draft"):
            decision = decision.model_copy(update={"process": "P1", "needs_clarification": False})
        if decision.process in {"P3", "P4"} and not case["order_id"]:
            decision = decision.model_copy(update={"needs_clarification": True})
        if decision.process == "P4" and case["order_id"] and case["process"] != "P4":
            order = await repo.order(actor, str(case["order_id"]))
            if order["kind"] == "retail_v2":
                if order["status"] == "QUALITY_PENDING":
                    decision = decision.model_copy(
                        update={"process": "P3", "needs_clarification": False}
                    )
                else:
                    decision = decision.model_copy(update={"needs_clarification": True})
        if decision.process == "P3" and case["order_id"]:
            order = await repo.order(actor, str(case["order_id"]))
            if order["kind"] == "retail_v2" and order["status"] != "QUALITY_PENDING":
                decision = decision.model_copy(update={"needs_clarification": True})
        actor.require(ROLES[decision.process])
        await runtime.emit(
            state,
            "agent.completed",
            {
                "agent": "supervisor",
                "selected_agent": decision.process,
                "proposed_agent": proposed_process,
                "duration_ms": round((time.monotonic() - started) * 1000),
                "rationale_summary": decision.rationale_summary,
                "model": runtime.settings.gemini_chat_model,
                "prompt_version": PROMPT_VERSION,
                "usage": getattr(runtime.provider, "last_usage", {}),
            },
        )
        return {
            "process": decision.process,
            "needs_clarification": decision.needs_clarification,
            "model_calls": state.get("model_calls", 0)
            + getattr(runtime.provider, "last_call_count", 1),
            "result": {},
            "human_approval": {},
            "review_decision": {},
            "skip_review": False,
        }

    async def clarify_route(state: CaseState):
        proposal = {
            "action": "clarify",
            "response": "Aclara la operación y su fase: recepción efectiva en mostrador, solicitud previa de recojo, agenda, calidad tras producción o incidencia. Vincula la orden para calidad; para reclamo abre un expediente P4 separado con el formulario de incidencias.",
            "rationale_summary": "Intención ambigua o fase incompatible; no se preparan escrituras.",
            "missing_fields": ["intención/fase"],
            "source_ids": [],
        }
        case = await repo.case(actor, state["case_id"])
        await repo.save_clarification(
            state["case_id"],
            state["process"],
            proposal,
            case["clarification_count"] >= runtime.settings.max_clarifications,
        )
        return {"proposal": proposal, "response": proposal["response"], "skip_review": True}

    async def stage(state: CaseState):
        proposal = state["proposal"]
        process = state["process"]
        validate_action(process, proposal["action"])
        case = await repo.case(actor, state["case_id"])
        if (
            process == "P2"
            and proposal["action"] == "reserve"
            and not proposal.get("options")
            and state["context"].get("schedule_options")
        ):
            # Display the calculator's verified options; an LLM omission cannot create a fake slot.
            proposal["options"] = state["context"]["schedule_options"]
            proposal["option_ids"] = [option["id"] for option in proposal["options"]]
        if (
            process == "P2"
            and proposal["action"] == "clarify"
            and not proposal.get("missing_fields")
            and state["context"].get("schedule_options")
        ):
            proposal["action"] = "reserve"
            if not proposal.get("options"):
                proposal["options"] = state["context"]["schedule_options"]
                proposal["option_ids"] = [option["id"] for option in proposal["options"]]
            proposal["response"] = (
                "Estas son las alternativas calculadas. Elige una opción y confirma; todavía no hay una reserva."
            )
        if (
            process == "P1"
            and proposal["action"] == "clarify"
            and not proposal.get("missing_fields")
        ):
            try:
                validate_request(
                    proposal.get("fields", {}),
                    runtime.clock,
                    runtime.settings.max_bags,
                    runtime.settings.max_pickup_days,
                )
            except DomainError:
                pass
            else:
                proposal["action"] = "register"
                proposal["rationale_summary"] += (
                    " Los siete campos están completos; se presenta una tarjeta sin ejecutar el registro."
                )
                await runtime.emit(
                    state,
                    "decision.summary",
                    {
                        "rationale_summary": proposal["rationale_summary"],
                        "sources": proposal.get("sources", []),
                    },
                )
        if process == "P1" and proposal["action"] in {"receive", "request_pickup"}:
            proposal = await runtime.retail.prepare(actor, case, proposal)
            proposal["response"] = (
                "Revisa la recepción y el importe calculado antes de confirmar."
                if proposal["action"] == "receive"
                else "Revisa la solicitud previa de recojo. No se creará una orden de servicio."
            )
        if proposal["action"] == "register" and case["order_id"]:
            raise DomainError(
                "Ya existe un pedido para este caso. Use logística para coordinarlo.",
                "existing_order",
                409,
            )
        if (
            process in {"P3", "P4"}
            and proposal["action"] not in {"answer", "clarify"}
            and not case["order_id"]
        ):
            raise DomainError(
                "Vincule un pedido verificado antes de disponer un lote o resolver una incidencia.",
                "order_required",
                409,
            )
        if proposal["action"] in {"clarify", "answer"} or proposal.get("missing_fields"):
            if process == "P1" and state["context"].get("customer", {}).get("blocked"):
                proposal["response"] = (
                    f"El cliente {case['client_id']} está bloqueado. El texto del chat no autoriza "
                    "una excepción; se requiere una revisión administrativa explícita antes de registrar. "
                    + proposal["response"]
                )
            if proposal["action"] == "clarify":
                limit = (
                    runtime.settings.max_clarifications
                    if process in {"P1", "P2"}
                    else runtime.settings.max_quality_evidence_requests
                    if process == "P3"
                    else runtime.settings.max_incident_clarifications
                )
                exhausted = (
                    case["clarification_count"] if case["process"] == process else 0
                ) >= limit
                await repo.save_clarification(state["case_id"], process, proposal, exhausted)
                if exhausted:
                    return {
                        "skip_review": True,
                        "response": "Límite piloto de aclaraciones alcanzado. El caso queda pendiente del operador: "
                        + proposal["response"],
                    }
            return {"skip_review": True, "proposal": proposal, "response": proposal["response"]}
        if process == "P1" and proposal["action"] == "register":
            proposal["response"] = (
                "Preparé el borrador de recojo. Revisa los campos de la tarjeta y confirma para registrar."
            )
            proposal["fields"] = validate_request(
                proposal["fields"],
                runtime.clock,
                runtime.settings.max_bags,
                runtime.settings.max_pickup_days,
            )
            customer = await repo.customer(actor, proposal["fields"]["cliente_id"])
            if case["client_id"] and case["client_id"] != customer["id"]:
                raise DomainError("Cliente del borrador distinto del caso.", "forbidden", 403)
            if not proposal["fields"].get("direccion_recojo"):
                proposal["fields"]["direccion_recojo"] = customer["address"]
                proposal["field_sources"]["direccion_recojo"] = "padrón sintético"
            if customer["blocked"]:
                proposal["commercial_exception_required"] = True
                proposal["response"] = (
                    f"El cliente {customer['id']} está bloqueado. No puedo ignorar el bloqueo ni "
                    "aceptar una autorización escrita en el chat. El pedido no está registrado: "
                    "necesita una excepción administrativa explícita y, después, confirmar los siete campos."
                )
                approval = await repo.stage_proposal(
                    actor,
                    state["case_id"],
                    state["run_id"],
                    process,
                    proposal,
                    "admin",
                    "human",
                    expected_case_version=state["context"]["case"]["version"],
                    observed_order_version=state["context"]["orders"][0]["version"]
                    if state["context"]["orders"]
                    else None,
                )
                await runtime.emit(
                    state,
                    "approval.requested",
                    {
                        "approval_id": str(approval["id"]),
                        "kind": "human",
                        "reason": "Excepción comercial; reconfirmar datos después.",
                    },
                )
                return {"proposal": proposal, "approval": approval, "skip_review": False}
        if process == "P2" and proposal["action"] == "reserve" and not proposal.get("options"):
            raise DomainError("No hay alternativas válidas; caso pendiente.", "no_capacity", 409)
        if process in {"P3", "P4"} and not proposal.get("sources"):
            raise DomainError(
                "Se requiere procedimiento vigente recuperado para proponer una disposición.",
                "insufficient_evidence",
                409,
            )
        kind = (
            "human"
            if process in {"P3", "P4"}
            or (process == "P2" and any(o["outside_policy"] for o in proposal.get("options", [])))
            else "confirmation"
        )
        approval = await repo.stage_proposal(
            actor,
            state["case_id"],
            state["run_id"],
            process,
            proposal,
            ROLES[process],
            kind,
            expected_case_version=state["context"]["case"]["version"],
            observed_order_version=state["context"]["orders"][0]["version"]
            if state["context"]["orders"]
            else None,
        )
        await runtime.emit(
            state, "approval.requested", {"approval_id": str(approval["id"]), "kind": kind}
        )
        return {"proposal": proposal, "approval": approval, "skip_review": False}

    async def review(state: CaseState):
        # This node deliberately has no effects before interrupt(). It restarts on resume.
        answer = interrupt(
            {
                "approval_id": str(state["approval"]["id"]),
                "proposal_hash": digest(state["proposal"]),
                "kind": state["approval"]["kind"],
                "rationale_summary": state["proposal"]["rationale_summary"],
            }
        )
        approval = await repo.db.one(
            "SELECT * FROM app.approvals WHERE id=%s AND case_id=%s",
            (answer["approval_id"], state["case_id"]),
        )
        if not approval or str(approval["id"]) != str(state["approval"]["id"]):
            raise DomainError("Revisión ajena al checkpoint.", "forbidden", 403)
        if approval["status"] not in {"approved", "rejected", "stale", "expired"}:
            raise DomainError("La revisión aún no fue validada por la API.", "forbidden", 403)
        return {
            "review_decision": approval.get("decision") or {"action": "reject"},
            "approval": approval,
            "execution_run_id": getattr(runtime, "current_run_id", state["run_id"]),
        }

    async def execute(state: CaseState):
        if (
            state["review_decision"]["action"] != "approve"
            or state["approval"]["status"] != "approved"
        ):
            await repo.db.execute(
                "UPDATE app.cases SET status='pending_operator',deadline=NULL WHERE id=%s",
                (state["case_id"],),
            )
            return {
                "response": "Propuesta rechazada, vencida o enviada a corrección. No se ejecutó el comando; el caso queda pendiente.",
                "result": {},
            }
        if (
            state["process"] == "P1"
            and state["approval"]["kind"] == "human"
            and state["proposal"]["action"] == "register"
        ):
            confirmation = await repo.stage_proposal(
                actor,
                state["case_id"],
                state["run_id"],
                "P1",
                state["proposal"],
                "attention",
                "confirmation",
                expected_case_version=state["approval"]["case_version"],
            )
            await runtime.emit(
                state,
                "approval.requested",
                {"approval_id": str(confirmation["id"]), "kind": "confirmation"},
            )
            return {
                "human_approval": state["approval"],
                "approval": confirmation,
                "review_decision": {},
            }
        command_id = str(uuid5(UUID(str(state["approval"]["id"])), "execute"))
        started = time.monotonic()
        await runtime.emit(state, "tool.started", {"name": "execute_command", "status": "running"})
        result = await runtime.executor.execute(
            actor,
            state["case_id"],
            command_id,
            str(state["approval"]["id"]),
            state["review_decision"].get("selection", {}),
        )
        await runtime.emit(
            state,
            "tool.completed",
            {
                "name": "execute_command",
                "status": "completed",
                "summary": result["status"],
                "result": result,
                "duration_ms": round((time.monotonic() - started) * 1000),
            },
        )
        return {"result": result, "response": describe_result(result)}

    async def respond(state: CaseState):
        # Stream the exact validated public answer. A second LLM must not reinterpret consent.
        response = state.get("response", "")
        await runtime.emit(state, "message.started", {"status": "responding"})
        for offset in range(0, len(response), 96):
            await runtime.emit(state, "message.delta", {"text": response[offset : offset + 96]})
        mid = str(
            uuid5(
                UUID(state["run_id"]),
                "assistant:" + str(state.get("approval", {}).get("id", "response")),
            )
        )
        await repo.message(
            state["case_id"],
            mid,
            "assistant",
            response,
            {
                "rationale_summary": state.get("proposal", {}).get("rationale_summary", ""),
                "sources": state.get("proposal", {}).get("sources", []),
                "result": state.get("result", {}),
            },
        )
        return {"response": response}

    graph = StateGraph(CaseState)
    graph.add_node("perceive", perceive)
    graph.add_node("supervisor", supervisor)
    for process in ROLES:
        graph.add_node(process, specialist_graph(process, runtime))
        graph.add_edge(process, "stage")
    graph.add_node("clarify", clarify_route)
    graph.add_edge("clarify", "respond")
    graph.add_node("stage", stage)
    graph.add_node("review", review)
    graph.add_node("execute", execute)
    graph.add_node("respond", respond)
    graph.add_edge(START, "perceive")
    graph.add_edge("perceive", "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lambda s: "clarify" if s["needs_clarification"] else s["process"],
        {**{p: p for p in ROLES}, "clarify": "clarify"},
    )
    graph.add_conditional_edges(
        "stage",
        lambda s: "respond" if s["skip_review"] else "review",
        {"respond": "respond", "review": "review"},
    )
    graph.add_edge("review", "execute")
    graph.add_conditional_edges(
        "execute",
        lambda s: (
            "review" if s.get("human_approval") and not s.get("review_decision") else "respond"
        ),
        {"review": "review", "respond": "respond"},
    )
    graph.add_edge("respond", END)
    return graph.compile(checkpointer=checkpointer)
