from datetime import timedelta
from uuid import uuid4

import pytest
from langgraph.types import Command

from aquaclean.domain.errors import DomainError
from aquaclean.graphs.main import build_graph
from aquaclean.infrastructure.persistence.checkpointer import checkpointer
from aquaclean.infrastructure.persistence.history_seed import seed_history
from aquaclean.workers.main import process_run
from tests.helpers import approve, fields, registered, stage
from tests.integration.test_graphs import start


async def test_A13_approved_proposal_invalidated_by_new_evidence(rt, case):
    a = await stage(rt, case["id"], {"action": "register", "fields": fields(rt)})
    await approve(rt, case["id"], a)
    await rt.repo.operator_event(
        rt.actor,
        str(case["id"]),
        str(uuid4()),
        "observation",
        "Dato sintético corregido después de aprobar",
        None,
    )
    with pytest.raises(DomainError, match="aprobación vigente"):
        await rt.executor.execute(rt.actor, str(case["id"]), str(uuid4()), str(a["id"]), {})


async def test_proposal_cannot_bind_new_evidence_it_did_not_analyze(rt, case):
    version = case["version"]
    await rt.repo.operator_event(
        rt.actor,
        str(case["id"]),
        str(uuid4()),
        "observation",
        "Nueva evidencia sintética durante la llamada LLM",
        None,
    )
    with pytest.raises(DomainError, match="durante el análisis"):
        await rt.repo.stage_proposal(
            rt.actor,
            str(case["id"]),
            str(uuid4()),
            "P1",
            {"action": "register", "fields": fields(rt)},
            "attention",
            "confirmation",
            expected_case_version=version,
        )


async def test_A07_expired_procedure_revalidated_at_commit(rt, case):
    await registered(rt, case["id"])
    for kind in ["inspection", "conformity"]:
        await rt.repo.operator_event(
            rt.actor,
            str(case["id"]),
            str(uuid4()),
            kind,
            "Evidencia sintética suficiente del operador",
            None,
        )
    # Isolated approved document, then expiration after proposal generation.
    did = "expire-" + str(uuid4())
    chunk = did + ":1"
    await rt.repo.db.execute(
        "INSERT INTO app.documents(id,organization_id,roles,title,version,hash,approved,valid_from) VALUES(%s,%s,ARRAY['quality'],'Procedimiento test','test','hash',true,%s)",
        (did, rt.actor.organization_id, rt.clock.now() - timedelta(days=1)),
    )
    vector = (await rt.knowledge.embeddings.embed(["calidad"], "RETRIEVAL_DOCUMENT"))[0]
    await rt.repo.db.execute(
        "INSERT INTO app.chunks(id,document_id,collection_id,section,content,hash,embedding) VALUES(%s,%s,%s,'1','calidad','hash',%s::vector)",
        (chunk, did, rt.knowledge.collection, str(vector)),
    )
    a = await stage(
        rt,
        case["id"],
        {"action": "release", "sources": [{"chunk_id": chunk, "hash": "hash"}]},
        "P3",
        "human",
        "quality",
    )
    await approve(rt, case["id"], a)
    await rt.repo.db.execute(
        "UPDATE app.documents SET valid_until=%s WHERE id=%s",
        (rt.clock.now() - timedelta(hours=1), did),
    )
    with pytest.raises(DomainError, match="procedimiento aprobado"):
        await rt.executor.execute(rt.actor, str(case["id"]), str(uuid4()), str(a["id"]), {})


async def test_A10_restart_after_command_before_response(rt, case):
    snapshot = await start(rt, case["id"])
    a = snapshot["approvals"][-1]
    rid, _ = await approve(rt, case["id"], a)
    run = await rt.repo.enqueue(
        rt.actor, str(case["id"]), rid, {"resume": True, "approval_id": str(a["id"])}
    )
    rt.current_run_id = rid
    config = {"configurable": {"thread_id": f"org:{rt.actor.organization_id}:case:{case['id']}"}}
    async with checkpointer(rt.settings) as saver:
        graph = build_graph(rt, saver)
        await graph.ainvoke(
            Command(resume={"approval_id": str(a["id"])}), config, interrupt_after=["execute"]
        )
    assert (await rt.repo.snapshot(rt.actor, str(case["id"])))["orders"]
    # Simulate a worker restart after the committed command and before response/terminal job status.
    await process_run(rt, run)
    value = await rt.repo.snapshot(rt.actor, str(case["id"]))
    assert len(value["orders"]) == 1
    assert value["runs"][-1]["status"] == "completed"
    assert (
        await rt.repo.db.one(
            "SELECT count(*) n FROM app.command_ledger WHERE case_id=%s", (case["id"],)
        )
    )["n"] == 1


async def test_resume_after_review_row_before_dynamic_interrupt(rt, case):
    rid = str(uuid4())
    run = await rt.repo.enqueue(
        rt.actor, str(case["id"]), rid, {"text": "Fixture con pausa estática antes de interrupt"}
    )
    rt.current_run_id = rid
    config = {"configurable": {"thread_id": f"org:{rt.actor.organization_id}:case:{case['id']}"}}
    async with checkpointer(rt.settings) as saver:
        graph = build_graph(rt, saver)
        await graph.ainvoke(
            {
                "case_id": str(case["id"]),
                "run_id": rid,
                "execution_run_id": rid,
                "text": "Solicitud de fixture",
                "attachment_ids": [],
                "model_calls": 0,
            },
            config,
            interrupt_after=["stage"],
        )
    await rt.repo.db.execute("UPDATE app.runs SET status='paused' WHERE id=%s", (run["id"],))
    value = await rt.repo.snapshot(rt.actor, str(case["id"]))
    a = value["approvals"][-1]
    decision, _ = await approve(rt, case["id"], a)
    resumed = await rt.repo.enqueue(
        rt.actor, str(case["id"]), decision, {"resume": True, "approval_id": str(a["id"])}
    )
    await process_run(rt, resumed)
    value = await rt.repo.snapshot(rt.actor, str(case["id"]))
    assert len(value["orders"]) == 1
    assert value["runs"][-1]["status"] == "completed"


async def test_no_key_is_explicit_and_no_runtime_fake(rt, case):
    from aquaclean.infrastructure.llm.provider import GeminiProvider

    rt.provider = GeminiProvider(rt.settings)  # settings fixture explicitly clears the key
    value = await start(rt, case["id"])
    assert value["runs"][-1]["status"] == "failed"
    assert "GEMINI_API_KEY" in value["messages"][-1]["content"]
    assert not value["orders"]


async def test_historical_seed_idempotent_and_chronological(rt):
    first = await seed_history(rt, orders=12)
    second = await seed_history(rt, orders=12)
    assert second["inserted"] == {"orders": 0, "cases": 0, "operator_events": 0, "customers": 0}
    assert first["period"] == second["period"]
    invalid = await rt.repo.db.one(
        "SELECT count(*) n FROM app.operator_events e JOIN app.cases c ON c.id=e.case_id WHERE c.data_origin='synthetic_history_v1' AND (e.created_at<c.created_at OR e.created_at>c.updated_at OR NOT c.synthetic)"
    )
    assert invalid["n"] == 0


async def test_reprocess_requires_authorization_and_new_conformity(rt, case):
    await registered(rt, case["id"])
    await rt.repo.db.execute("UPDATE app.cases SET process='P3' WHERE id=%s", (case["id"],))
    await rt.repo.operator_event(
        rt.actor,
        str(case["id"]),
        str(uuid4()),
        "inspection",
        "Material y mancha documentados en guía sintética",
        None,
    )
    with pytest.raises(DomainError):
        await rt.repo.operator_event(
            rt.actor,
            str(case["id"]),
            str(uuid4()),
            "reprocess",
            "Intento sin autorización sintética",
            None,
        )
    sources = await rt.knowledge.search(rt.actor, "calidad", "CLI-0001")
    a = await stage(
        rt, case["id"], {"action": "reprocess", "sources": sources}, "P3", "human", "quality"
    )
    await approve(rt, case["id"], a)
    result = await rt.executor.execute(rt.actor, str(case["id"]), str(uuid4()), str(a["id"]), {})
    assert result["status"] == "awaiting_physical_reprocess"
    await rt.repo.operator_event(
        rt.actor,
        str(case["id"]),
        str(uuid4()),
        "reprocess",
        "Reproceso físico sintético autorizado realizado",
        None,
    )
    with pytest.raises(DomainError):
        await rt.repo.operator_event(
            rt.actor,
            str(case["id"]),
            str(uuid4()),
            "reprocess",
            "Segundo ciclo fuera del límite piloto",
            None,
        )
    release = await stage(
        rt, case["id"], {"action": "release", "sources": sources}, "P3", "human", "quality"
    )
    await approve(rt, case["id"], release)
    with pytest.raises(DomainError, match="conformity"):
        await rt.executor.execute(rt.actor, str(case["id"]), str(uuid4()), str(release["id"]), {})
