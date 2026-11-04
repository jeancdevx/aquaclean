import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest

from aquaclean.domain.entities import ORG, Actor
from aquaclean.domain.errors import DomainError
from aquaclean.infrastructure.persistence.database import jsonb
from aquaclean.workers.outbox import deliver, expire
from tests.helpers import approve, fields, registered, stage


async def test_A03_concurrent_idempotency_and_uncertain_commit(rt, case):
    cid = str(case["id"])
    proposal = {"action": "register", "fields": fields(rt)}
    approval = await stage(rt, cid, proposal)
    await approve(rt, cid, approval)
    command_id = str(uuid4())
    calls = [
        rt.executor.execute(rt.actor, cid, command_id, str(approval["id"]), {}) for _ in range(6)
    ]
    results = await asyncio.gather(*calls)
    assert all(result == results[0] for result in results)
    assert (await rt.repo.db.one("SELECT count(*) n FROM app.orders WHERE request_id=%s", (cid,)))[
        "n"
    ] == 1
    # Lost acknowledgement: replaying the same committed command recovers its result.
    assert (
        await rt.executor.execute(rt.actor, cid, command_id, str(approval["id"]), {}) == results[0]
    )
    with pytest.raises(DomainError, match="otro contenido"):
        await rt.executor.execute(
            rt.actor, cid, command_id, str(approval["id"]), {"unexpected": "change"}
        )


async def test_A04_outbox_failure_keeps_order(rt, case):
    # The dedicated _test database can retain >20 notifications from prior runs.
    # Drain that backlog so this test actually fails/retries its own notification.
    await rt.repo.db.execute("UPDATE app.outbox SET next_attempt_at=now() WHERE status='pending'")
    while await deliver(rt.repo.db):
        pass
    result = await registered(rt, case["id"])
    await deliver(rt.repo.db, fail=True)
    assert await rt.repo.db.one("SELECT id FROM app.orders WHERE id=%s", (result["order_id"],))
    failed = await rt.repo.db.one(
        "SELECT status,attempts FROM app.outbox WHERE case_id=%s", (case["id"],)
    )
    assert failed == {"status": "pending", "attempts": 1}
    await rt.repo.db.execute(
        "UPDATE app.outbox SET next_attempt_at=now() WHERE case_id=%s", (case["id"],)
    )
    await deliver(rt.repo.db)
    await deliver(rt.repo.db)
    assert (
        await rt.repo.db.one("SELECT count(*) n FROM app.inbox WHERE case_id=%s", (case["id"],))
    )["n"] == 1


async def test_A05_blocked_customer_cannot_ignore_policy(rt):
    case = await rt.repo.create_case(rt.actor, "Bloqueado sintético", "CLI-0002")
    approval = await stage(rt, case["id"], {"action": "register", "fields": fields(rt, "CLI-0002")})
    await approve(rt, case["id"], approval)
    with pytest.raises(DomainError, match="bloqueado"):
        await rt.executor.execute(rt.actor, str(case["id"]), str(uuid4()), str(approval["id"]), {})


async def test_A06_atomic_last_slot_and_cancel(rt):
    cases = [await rt.repo.create_case(rt.actor, "Cupo sintético", "CLI-0001") for _ in range(2)]
    for case in cases:
        await registered(rt, case["id"])
    slot_id = "TEST-" + str(uuid4())
    await rt.repo.db.execute(
        "INSERT INTO app.slots(id,organization_id,day,shift,capacity) VALUES(%s,%s,%s,%s,1)",
        (slot_id, ORG, rt.clock.now().date() + timedelta(days=1), "manana"),
    )
    option = await rt.repo.db.one(
        "SELECT *,false AS outside_policy FROM app.slots WHERE id=%s", (slot_id,)
    )
    approvals = []
    for case in cases:
        approval = await stage(
            rt,
            case["id"],
            {"action": "reserve", "options": [option], "operation": "pickup"},
            "P2",
            "confirmation",
            "logistics",
        )
        await approve(rt, case["id"], approval, {"option_id": slot_id})
        approvals.append(approval)
    results = await asyncio.gather(
        *[
            rt.executor.execute(
                rt.actor, str(c["id"]), str(uuid4()), str(a["id"]), {"option_id": slot_id}
            )
            for c, a in zip(cases, approvals, strict=True)
        ],
        return_exceptions=True,
    )
    assert sum(isinstance(r, dict) for r in results) == 1
    assert sum(isinstance(r, DomainError) for r in results) == 1
    assert (await rt.repo.db.one("SELECT reserved FROM app.slots WHERE id=%s", (slot_id,)))[
        "reserved"
    ] == 1
    winner = cases[next(i for i, r in enumerate(results) if isinstance(r, dict))]
    cancel = await stage(rt, winner["id"], {"action": "cancel"}, "P2", "confirmation", "logistics")
    await approve(rt, winner["id"], cancel)
    await rt.executor.execute(rt.actor, str(winner["id"]), str(uuid4()), str(cancel["id"]), {})
    assert (await rt.repo.db.one("SELECT reserved FROM app.slots WHERE id=%s", (slot_id,)))[
        "reserved"
    ] == 0


async def test_A06_nonexistent_option_rejected(rt, case):
    await registered(rt, case["id"])
    a = await stage(
        rt, case["id"], {"action": "reserve", "options": []}, "P2", "confirmation", "logistics"
    )
    await approve(rt, case["id"], a, {"option_id": "inventada"})
    with pytest.raises(DomainError, match="calculada"):
        await rt.executor.execute(
            rt.actor, str(case["id"]), str(uuid4()), str(a["id"]), {"option_id": "inventada"}
        )


async def test_A07_quality_requires_human_evidence(rt, case):
    await registered(rt, case["id"])
    sources = await rt.knowledge.search(rt.actor, "calidad", "CLI-0001")
    a = await stage(
        rt, case["id"], {"action": "release", "sources": sources}, "P3", "human", "quality"
    )
    await approve(rt, case["id"], a)
    with pytest.raises(DomainError, match="evidencia humana"):
        await rt.executor.execute(rt.actor, str(case["id"]), str(uuid4()), str(a["id"]), {})


async def test_A08_A09_incident_approval_and_fulfillment(rt, case):
    await registered(rt, case["id"])
    sources = await rt.knowledge.search(rt.actor, "incidencia", "CLI-0001")
    a = await stage(
        rt,
        case["id"],
        {
            "action": "resolve_incident",
            "sources": sources,
            "facts": ["Guía y relato difieren"],
            "plan": ["Verificación física"],
        },
        "P4",
        "human",
        "admin",
    )
    # A proposal alone has no effect.
    with pytest.raises(DomainError, match="aprobación vigente"):
        await rt.executor.execute(rt.actor, str(case["id"]), str(uuid4()), str(a["id"]), {})
    await approve(rt, case["id"], a)
    result = await rt.executor.execute(rt.actor, str(case["id"]), str(uuid4()), str(a["id"]), {})
    assert result["status"] == "awaiting_customer_acceptance_and_fulfillment"
    closing = await stage(
        rt, case["id"], {"action": "close_incident", "sources": sources}, "P4", "human", "admin"
    )
    await approve(rt, case["id"], closing)
    with pytest.raises(DomainError, match="evidencia humana"):
        await rt.executor.execute(rt.actor, str(case["id"]), str(uuid4()), str(closing["id"]), {})
    for kind in ["customer_acceptance", "fulfillment", "conformity"]:
        await rt.repo.operator_event(
            rt.actor,
            str(case["id"]),
            str(uuid4()),
            kind,
            "Evidencia humana sintética de cumplimiento",
            None,
        )
    closing = await stage(
        rt, case["id"], {"action": "close_incident", "sources": sources}, "P4", "human", "admin"
    )
    await approve(rt, case["id"], closing)
    result = await rt.executor.execute(
        rt.actor, str(case["id"]), str(uuid4()), str(closing["id"]), {}
    )
    assert result["status"] == "closed"


async def test_A11_A13_foreign_and_stale_approvals(rt, case):
    a = await stage(rt, case["id"], {"action": "register", "fields": fields(rt)})
    for actor in [
        Actor("other", "other-org", frozenset({"admin", "attention"})),
        Actor("client", ORG, frozenset({"client"}), "CLI-0002"),
        Actor("wrong-role", ORG, frozenset({"quality"})),
    ]:
        with pytest.raises(DomainError):
            await rt.repo.resolve_approval(
                actor,
                str(case["id"]),
                str(a["id"]),
                str(uuid4()),
                {
                    "action": "approve",
                    "proposal_hash": a["proposal_hash"],
                    "case_version": a["case_version"],
                },
            )
    await rt.repo.db.execute(
        "UPDATE app.cases SET version=version+1,proposal=%s WHERE id=%s",
        (jsonb({"action": "cancel"}), case["id"]),
    )
    with pytest.raises(DomainError, match="cambió"):
        await approve(rt, case["id"], a)


async def test_A14_timeout_never_closes(rt, case):
    a = await stage(rt, case["id"], {"action": "register", "fields": fields(rt)})
    await rt.repo.db.execute(
        "UPDATE app.cases SET process='P4',deadline=now()-interval '1 minute' WHERE id=%s",
        (case["id"],),
    )
    await expire(rt.repo.db)
    assert (await rt.repo.case(rt.actor, str(case["id"])))["status"] == "pending_timeout"
    assert (await rt.repo.db.one("SELECT status FROM app.approvals WHERE id=%s", (a["id"],)))[
        "status"
    ] == "expired"


async def test_A12_executor_rejects_compromised_cross_role_proposal(rt, case):
    await registered(rt, case["id"])
    a = await stage(rt, case["id"], {"action": "cancel"}, "P3", "human", "quality")
    await approve(rt, case["id"], a)
    with pytest.raises(DomainError, match="fuera del contrato"):
        await rt.executor.execute(rt.actor, str(case["id"]), str(uuid4()), str(a["id"]), {})
