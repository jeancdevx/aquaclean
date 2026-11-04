from uuid import uuid4

import pytest

from aquaclean.agents.deep_incidents.factory import investigate
from tests.helpers import registered


async def test_sdk_plans_delegates_and_recovers_results(rt, case):
    await registered(rt, case["id"])
    cid = str(case["id"])
    run = await rt.repo.enqueue(
        rt.actor, cid, str(uuid4()), {"text": "Investigar incidencia sintética"}
    )
    context = await rt.repo.snapshot(rt.actor, cid)
    context["sources"] = await rt.knowledge.search(rt.actor, "incidencia", case["client_id"])
    state = {
        "case_id": cid,
        "run_id": str(run["id"]),
        "text": "Investigar incidencia sintética",
        "context": context,
        "model_calls": 2,
    }
    proposal = await investigate(rt, state)
    assert proposal["action"] == "resolve_incident"
    assert proposal["source_ids"]
    saved = await rt.repo.db.one(
        "SELECT result FROM app.deep_investigations WHERE app_run_id=%s", (run["id"],)
    )
    journal = saved["result"]["journal"]
    assert {j["args"]["subagent_type"] for j in journal if j["tool"] == "task"} == {
        "evidencias",
        "procedimientos",
    }
    assert any(j["tool"] == "write_todos" for j in journal)
    assert saved["result"]["model_calls"] == 7
    assert all(
        not {"execute", "write_file", "edit_file", "ls", "glob", "grep", "delete"} & set(names)
        for names in rt.provider.model.observed_tools
    )
    assert (
        len((await rt.repo.snapshot(rt.actor, cid))["command_history"]) == 1
    )  # only prior reception


async def test_sdk_shared_budget_failure_never_executes_business_command(rt, case):
    from aquaclean.domain.errors import DomainError

    await registered(rt, case["id"])
    cid = str(case["id"])
    run = await rt.repo.enqueue(rt.actor, cid, str(uuid4()), {"text": "Investigar sintético"})
    context = await rt.repo.snapshot(rt.actor, cid)
    context["sources"] = await rt.knowledge.search(rt.actor, "incidencia", case["client_id"])
    rt.settings = rt.settings.model_copy(update={"deep_max_model_calls": 1})
    with pytest.raises(DomainError, match="Presupuesto"):
        await investigate(
            rt,
            {
                "case_id": cid,
                "run_id": str(run["id"]),
                "text": "Investigar",
                "context": context,
                "model_calls": 2,
            },
        )
    assert len((await rt.repo.snapshot(rt.actor, cid))["command_history"]) == 1


async def test_incident_evidence_is_bounded_to_single_order(rt):
    from aquaclean.infrastructure.persistence.incident_research import incident_evidence
    from tests.integration.test_retail import receive

    one = await rt.repo.create_case(rt.actor, "Orden A sintética")
    two = await rt.repo.create_case(rt.actor, "Orden B sintética")
    await receive(rt, one["id"])
    await receive(rt, two["id"])
    await rt.repo.operator_event(
        rt.actor, str(one["id"]), str(uuid4()), "observation", "Observación propia sintética", None
    )
    alien = str(uuid4())
    await rt.repo.operator_event(
        rt.actor, str(two["id"]), alien, "observation", "Observación de otro pedido sintético", None
    )
    evidence = await incident_evidence(rt.repo, rt.actor, str(one["id"]), 60000)
    assert alien not in evidence["allowed_evidence_refs"]
    assert len(evidence["events"]) == 1
