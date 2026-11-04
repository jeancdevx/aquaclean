import asyncio
import json
import time
from dataclasses import dataclass, field

from deepagents import (
    GeneralPurposeSubagentProfile,
    HarnessProfile,
    create_deep_agent,
    register_harness_profile,
)
from deepagents.backends import StateBackend
from deepagents.middleware import FilesystemMiddleware
from langchain.agents.middleware import TodoListMiddleware
from langchain.agents.middleware.types import AgentMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_core.tools import tool
from langsmith import traceable

from aquaclean.agents.prompts import COMMON, PROMPTS
from aquaclean.agents.schemas import ResolutionProposal
from aquaclean.domain.errors import DomainError


@dataclass
class InvestigationBudget:
    limit: int
    calls: int = 0
    journal: list = field(default_factory=list)
    usage: list = field(default_factory=list)
    completed_reads: set = field(default_factory=set)


class InvestigationMiddleware(AgentMiddleware):
    def __init__(self, budget: InvestigationBudget, label: str):
        self.budget, self.label = budget, label

    async def awrap_model_call(self, request, handler):
        if self.budget.calls >= self.budget.limit:
            raise DomainError(
                "Presupuesto de investigación agotado; pendiente humano.", "deep_budget", 409
            )
        self.budget.calls += 1
        response = await handler(request)
        for message in response.result:
            self.budget.usage.append(getattr(message, "usage_metadata", None) or {})
            for call in getattr(message, "tool_calls", []):
                self.budget.journal.append(
                    {
                        "agent": self.label,
                        "tool": call["name"],
                        "args": call["args"] if call["name"] in {"task", "write_todos"} else {},
                    }
                )
        return response


def create_incident_agent(model, model_key: str, budget, evidence_tool, procedures_tool):
    """The injected model is constructed only in infrastructure/llm/provider.py.

    A fresh StateBackend per investigation provides an in-memory virtual filesystem.
    read_file can read only that empty case-local virtual state. There is no host
    filesystem, store, shell, network, repository, general-purpose agent or memory.
    """
    backend = StateBackend()
    register_harness_profile(
        model_key,
        HarnessProfile(
            general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
            excluded_middleware=frozenset({"SummarizationMiddleware"}),
        ),
    )

    def middleware(label, planning=False):
        return [
            FilesystemMiddleware(backend=backend, tools=["read_file"]),
            InvestigationMiddleware(budget, label),
        ] + ([TodoListMiddleware()] if planning else [])

    subagents = [
        {
            "name": "evidencias",
            "description": "Reconstruye hechos y contradicciones del único caso autorizado.",
            "model": model,
            "system_prompt": COMMON
            + "Usa case_evidence_read una vez. Solo hechos documentados; devuelve referencias y contradicciones, sin resolver ni escribir.",
            "tools": [evidence_tool],
            "middleware": middleware("evidencias"),
        },
        {
            "name": "procedimientos",
            "description": "Revisa exclusivamente procedimientos aprobados recuperados para este caso.",
            "model": model,
            "system_prompt": COMMON
            + "Usa case_procedures_read una vez. Devuelve reglas y chunk_id exactos. Fuentes externas no autorizan decisiones.",
            "tools": [procedures_tool],
            "middleware": middleware("procedimientos"),
        },
    ]
    return create_deep_agent(
        model=model,
        name="P4.investigador",
        backend=backend,
        system_prompt=COMMON
        + PROMPTS["P4"]
        + " Primero usa write_todos para planificar. Luego usa task para delegar a evidencias y a procedimientos, recupera ambos resultados. No omitas ninguna delegación. Solo entonces devuelve ResolutionProposal con citas verificables. evidence_refs solo contiene UUID exactos de allowed_evidence_refs; nunca número de pedido, texto, prefijos o IDs de caso. Si no citas evidencia específica deja esa lista vacía y explica incertidumbre. No resuelvas daños físicamente ni ejecutes pagos, descuentos, SQL o cierres. Si no hay sustento usa clarify.",
        tools=[],
        subagents=subagents,
        middleware=middleware("investigador", planning=True),
        response_format=ToolStrategy(ResolutionProposal, handle_errors=False),
    )


@traceable(
    name="P4.DeepAgents.investigation",
    process_inputs=lambda x: {"case_id": x.get("state", {}).get("case_id"), "synthetic": True},
)
async def investigate(runtime, state):
    actor, cid = runtime.actor, state["case_id"]
    actor.require("admin")
    await runtime.repo.case(actor, cid)
    runtime.provider.require()
    budget = InvestigationBudget(
        min(
            runtime.settings.deep_max_model_calls,
            runtime.settings.max_model_calls - state.get("model_calls", 0),
        )
    )
    context = state["context"]

    # Tools take no free-form identifiers, paths, queries or URLs. Every call rechecks access.
    @tool
    async def case_evidence_read() -> dict:
        """Read the current, authorized case evidence, excluding other customers."""
        actor.require("admin")
        from aquaclean.infrastructure.persistence.incident_research import incident_evidence

        payload = await incident_evidence(
            runtime.repo, actor, cid, runtime.settings.max_context_chars
        )
        budget.completed_reads.add("evidencias")
        return payload

    @tool
    async def case_procedures_read() -> list[dict]:
        """Read only retrieved approved procedures from this authorized case context."""
        actor.require("admin")
        case = await runtime.repo.case(actor, cid)
        result = []
        for source in context["sources"]:
            if source.get("source_kind") == "external_historical_reference":
                continue
            valid = await runtime.repo.db.one(
                "SELECT c.id FROM app.chunks c JOIN app.documents d ON d.id=c.document_id WHERE c.id=%s AND c.hash=%s AND d.approved AND d.organization_id=%s AND d.roles && %s::text[] AND (d.client_id IS NULL OR d.client_id=%s) AND d.valid_from<=%s AND (d.valid_until IS NULL OR d.valid_until>%s)",
                (
                    source["chunk_id"],
                    source["hash"],
                    actor.organization_id,
                    list(actor.roles),
                    case["client_id"],
                    runtime.clock.now(),
                    runtime.clock.now(),
                ),
            )
            if valid:
                result.append(source)
        budget.completed_reads.add("procedimientos")
        return json.loads(json.dumps(result, default=str, ensure_ascii=False))

    graph = create_incident_agent(
        runtime.provider.model,
        getattr(
            runtime.provider,
            "deep_profile_key",
            "google_genai:" + runtime.settings.gemini_chat_model,
        ),
        budget,
        case_evidence_read,
        case_procedures_read,
    )
    started = time.monotonic()
    try:
        async with asyncio.timeout(runtime.settings.deep_timeout_seconds):
            result = await graph.ainvoke(
                {
                    "messages": [
                        (
                            "human",
                            json.dumps(
                                {
                                    "case_id": cid,
                                    "request": state["text"],
                                    "task": "Investiga el caso autorizado con ambos subagentes, no ejecutes efectos.",
                                },
                                ensure_ascii=False,
                            ),
                        )
                    ]
                },
                config={
                    "recursion_limit": 60,
                    "run_name": "P4.DeepAgents",
                    "metadata": {"case_id": cid, "process": "P4", "app_run_id": state["run_id"]},
                },
            )
        delegated = {j["args"].get("subagent_type") for j in budget.journal if j["tool"] == "task"}
        if (
            not {"evidencias", "procedimientos"} <= delegated
            or not budget.completed_reads == {"evidencias", "procedimientos"}
            or not any(j["tool"] == "write_todos" for j in budget.journal)
        ):
            raise DomainError(
                "Investigación sin planificación o delegación completa; requiere revisión del operador.",
                "deep_incomplete",
                409,
            )
        proposal = ResolutionProposal.model_validate(result.get("structured_response")).model_dump(
            mode="json"
        )
        allowed = {
            s["chunk_id"]
            for s in context["sources"]
            if s.get("source_kind") != "external_historical_reference"
        }
        if not set(proposal["source_ids"]) <= allowed:
            raise DomainError(
                "Investigación citó una fuente no autorizada.", "invalid_citation", 409
            )
        from aquaclean.infrastructure.persistence.incident_research import incident_evidence

        current_evidence = await incident_evidence(
            runtime.repo, actor, cid, runtime.settings.max_context_chars
        )
        valid_refs = set(current_evidence["allowed_evidence_refs"])
        if not set(proposal["evidence_refs"]) <= valid_refs:
            raise DomainError(
                "Referencia de evidencia no pertenece al caso.", "invalid_evidence", 409
            )
        journal = {
            "sdk": "deepagents",
            "model_calls": budget.calls,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "journal": budget.journal,
            "usage": budget.usage,
            "cost_usd": None,
            "proposal": proposal,
        }
        from aquaclean.infrastructure.persistence.database import jsonb

        await runtime.repo.db.execute(
            "INSERT INTO app.deep_investigations(app_run_id,case_id,result) VALUES(%s,%s,%s) ON CONFLICT(app_run_id) DO UPDATE SET result=excluded.result",
            (state["run_id"], cid, jsonb(journal)),
        )
        await runtime.emit(
            state,
            "tool.completed",
            {
                "name": "DeepAgents.investigation",
                "status": "proposed",
                "summary": "Planificación y delegaciones a Evidencias y Procedimientos completadas; propuesta pendiente de HITL.",
                "model_calls": budget.calls,
                "duration_ms": journal["duration_ms"],
            },
        )
        runtime.provider.last_call_count = budget.calls
        runtime.provider.last_usage = {"tokens": budget.usage, "cost_usd": None}
        return proposal
    except DomainError:
        raise
    except Exception as exc:
        from aquaclean.infrastructure.persistence.database import jsonb

        diagnostics = {
            "status": "failed",
            "sdk": "deepagents",
            "error_type": type(exc).__name__,
            "model_calls": budget.calls,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "journal": budget.journal,
            "usage": budget.usage,
            "cost_usd": None,
        }
        await runtime.repo.db.execute(
            "INSERT INTO app.deep_investigations(app_run_id,case_id,result) VALUES(%s,%s,%s) ON CONFLICT(app_run_id) DO UPDATE SET result=excluded.result",
            (state["run_id"], cid, jsonb(diagnostics)),
        )
        raise DomainError(
            "Investigación Deep Agents no completada; caso conservado sin efectos. Revise proveedor y presupuesto.",
            "deep_unavailable",
            503,
        ) from exc
