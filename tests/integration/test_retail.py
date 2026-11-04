from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from aquaclean.domain.errors import DomainError
from aquaclean.domain.retail import RetailOperation
from aquaclean.infrastructure.persistence.retail_operations import operate
from aquaclean.workers.outbox import processing_alerts
from tests.helpers import approve, stage
from tests.integration.test_graphs import resume


def reception(rt, existing_id=None):
    return {
        "customer": {"existing_id": existing_id}
        if existing_id
        else {"name": "Lucía Muestra (sintética)", "contact": "Contacto sintético en mostrador"},
        "received": True,
        "receipt_evidence": "Operador contó y recibió prendas sintéticas en mostrador",
        "channel": "counter",
        "items": [
            {
                "garment": "Camisa sintética",
                "quantity": 2,
                "service_code": "wash_piece",
                "observations": "Botón flojo declarado",
                "evidence_refs": [],
            }
        ],
        "advance": "5.00",
        "payment_evidence": "Operador declara adelanto sintético recibido",
    }


async def receive(rt, cid, data=None):
    data = data or reception(rt)
    case = await rt.repo.case(rt.actor, str(cid))
    proposal = await rt.retail.prepare(
        rt.actor,
        case,
        {
            "action": "receive",
            "reception": data,
            "response": "Confirmar recepción",
            "rationale_summary": "Declaración sintética",
            "source_ids": [],
            "sources": [],
        },
    )
    approval = await stage(rt, cid, proposal)
    await approve(rt, cid, approval)
    return await rt.executor.execute(rt.actor, str(cid), str(uuid4()), str(approval["id"]), {})


async def op(rt, cid, action, **extra):
    snapshot = await rt.repo.snapshot(rt.actor, str(cid))
    version = (
        snapshot["orders"][0]["version"]
        if snapshot["orders"]
        else snapshot["retail"]["pickup_request"]["version"]
    )
    return await operate(
        rt.repo,
        rt.actor,
        str(cid),
        RetailOperation(
            command_id=uuid4(),
            expected_version=version,
            action=action,
            evidence="Hito humano sintético observado y declarado",
            **extra,
        ),
    )


@pytest.mark.parametrize("existing", [False, True])
async def test_reception_without_any_prior_order_or_pickup(rt, existing):
    case = await rt.repo.create_case(
        rt.actor, "Recepción sintética nueva", "CLI-0001" if existing else None
    )
    result = await receive(rt, case["id"], reception(rt, "CLI-0001" if existing else None))
    snapshot = await rt.repo.snapshot(rt.actor, str(case["id"]))
    assert result["number"].startswith("DET-")
    assert snapshot["orders"][0]["status"] == "RECEIVED"
    assert snapshot["orders"][0]["pickup_request_id"] is None
    assert snapshot["retail"]["balance"] == "7.00"
    assert len(snapshot["retail"]["items"]) == len(snapshot["retail"]["payments"]) == 1
    assert snapshot["orders"][0]["total"] == Decimal("12.00")
    customer = await rt.repo.customer(rt.actor, result["customer_id"])
    if not existing:
        assert customer["email"] is None


async def test_reception_from_application_pauses_before_customer_and_payment(rt):
    from aquaclean.workers.main import process_run

    case = await rt.repo.create_case(rt.actor, "Recepción aplicación sintética")
    cid = str(case["id"])
    run = await rt.repo.enqueue(
        rt.actor,
        cid,
        str(uuid4()),
        {
            "text": "Recepción mostrador",
            "retail_draft": {"action": "receive", "reception": reception(rt)},
        },
    )
    await process_run(rt, run)
    before = await rt.repo.snapshot(rt.actor, cid)
    assert before["runs"][-1]["status"] == "paused"
    assert not before["orders"] and not before["retail"]["payments"] and not before["inbox"]
    assert before["case"]["client_id"] is None
    approval = before["approvals"][-1]
    after = await resume(rt, cid, approval)
    assert after["orders"][0]["status"] == "RECEIVED"
    assert after["retail"]["balance"] == "7.00"
    # A reconstructed graph/new PostgreSQL saver was used for resume; ledger covers retry.
    from uuid import UUID, uuid5

    result = await rt.executor.execute(
        rt.actor, cid, str(uuid5(UUID(str(approval["id"])), "execute")), str(approval["id"]), {}
    )
    assert result["order_id"] == str(after["orders"][0]["id"])
    assert len((await rt.repo.snapshot(rt.actor, cid))["retail"]["payments"]) == 1


async def test_processing_and_closure_preconditions_and_idempotent_payment(rt):
    case = await rt.repo.create_case(rt.actor, "Ciclo sintético")
    cid = str(case["id"])
    await receive(rt, cid)
    with pytest.raises(DomainError, match="no procede"):
        await op(rt, cid, "deliver", receiver="Receptor sintético", conformity=True)
    with pytest.raises(DomainError, match="fase"):
        await rt.repo.operator_event(
            rt.actor,
            cid,
            str(uuid4()),
            "conformity",
            "No hay todavía inspección final de calidad",
            None,
        )
    await op(rt, cid, "start_processing")
    assert (await rt.repo.snapshot(rt.actor, cid))["orders"][0]["status"] == "IN_PROCESSING"
    await op(rt, cid, "finish_processing")
    # Quality release is separately protected by HITL; simulate neither physical work nor release.
    with pytest.raises(DomainError, match="no procede"):
        await op(rt, cid, "close")
    snapshot = await rt.repo.snapshot(rt.actor, cid)
    command = RetailOperation(
        command_id=uuid4(),
        expected_version=snapshot["orders"][0]["version"],
        action="payment",
        amount="7.00",
        evidence="Cobro declarado por operador sintético",
    )
    first = await operate(rt.repo, rt.actor, cid, command)
    assert await operate(rt.repo, rt.actor, cid, command) == first
    assert first["balance"] == "0.00"
    with pytest.raises(DomainError, match="reutilizado"):
        await operate(
            rt.repo,
            rt.actor,
            cid,
            command.model_copy(update={"evidence": "Otra evidencia diferente"}),
        )
    with pytest.raises(DomainError):
        await op(rt, cid, "payment", amount="0.01")


async def release(rt, cid, action="release"):
    for kind in ["inspection", "conformity"]:
        await rt.repo.operator_event(
            rt.actor,
            str(cid),
            str(uuid4()),
            kind,
            "Evidencia física sintética verificada por operador",
            None,
        )
    sources = await rt.knowledge.search(
        rt.actor, "liberación calidad", (await rt.repo.case(rt.actor, str(cid)))["client_id"]
    )
    proposal = {
        "action": action,
        "response": "Disposición sintética",
        "rationale_summary": "Calidad",
        "sources": sources[:1],
        "source_ids": [sources[0]["chunk_id"]],
    }
    approval = await stage(rt, cid, proposal, "P3", "human", "quality")
    await approve(rt, cid, approval)
    return await rt.executor.execute(rt.actor, str(cid), str(uuid4()), str(approval["id"]), {})


async def test_full_retail_cycle_unique_ready_notice_and_commercial_closure(rt):
    case = await rt.repo.create_case(rt.actor, "Ciclo completo sintético")
    cid = str(case["id"])
    result = await receive(rt, cid)
    await op(rt, cid, "start_processing")
    await op(rt, cid, "finish_processing")
    released = await release(rt, cid)
    assert released["service_status"] == "READY"
    notices = await rt.repo.db.all(
        "SELECT id FROM app.outbox WHERE payload->>'type'='order_ready' AND payload->>'order_id'=%s",
        (result["order_id"],),
    )
    assert len(notices) == 1
    from aquaclean.infrastructure.persistence.retail_logistics import options

    await rt.repo.db.execute(
        "INSERT INTO app.slots(id,organization_id,day,shift,capacity) VALUES(%s,%s,%s,'manana',8)",
        (
            "DELIVERY-" + str(uuid4()),
            rt.actor.organization_id,
            rt.clock.now().date() + timedelta(days=1),
        ),
    )
    calculated = await options(rt.repo, rt.actor, cid)
    chosen = calculated[0]
    approval = await stage(
        rt,
        cid,
        {"action": "reserve", "operation": "delivery", "options": calculated},
        "P2",
        "human",
        "logistics",
    )
    selection = {"option_id": chosen["id"]}
    await approve(rt, cid, approval, selection)
    await rt.executor.execute(rt.actor, cid, str(uuid4()), str(approval["id"]), selection)
    assert (await rt.repo.snapshot(rt.actor, cid))["orders"][0]["status"] == "DELIVERY_PENDING"
    approval = await stage(
        rt, cid, {"action": "cancel", "operation": "delivery"}, "P2", "confirmation", "logistics"
    )
    await approve(rt, cid, approval)
    await rt.executor.execute(rt.actor, cid, str(uuid4()), str(approval["id"]), {})
    assert (await rt.repo.snapshot(rt.actor, cid))["orders"][0]["status"] == "READY"
    slot = await rt.repo.db.one("SELECT reserved FROM app.slots WHERE id=%s", (chosen["id"],))
    assert slot["reserved"] == chosen["reserved"]
    await op(rt, cid, "deliver", receiver="Lucía sintética", conformity=False)
    with pytest.raises(DomainError, match="Cierre exige"):
        await op(rt, cid, "close")
    await op(rt, cid, "payment", amount="7.00")
    with pytest.raises(DomainError, match="Cierre exige"):
        await op(rt, cid, "close")
    await op(rt, cid, "confirm_delivery", conformity=True)
    assert (await op(rt, cid, "close"))["status"] == "CLOSED"
    snapshot = await rt.repo.snapshot(rt.actor, cid)
    assert len(snapshot["retail"]["receipts"]) == 2
    assert "SIN VALIDEZ FISCAL" in snapshot["retail"]["receipts"][-1]["payload"]["label"]


async def test_processing_alert_non_interrupting_and_unique(rt):
    case = await rt.repo.create_case(rt.actor, "Alerta sintética")
    cid = str(case["id"])
    result = await receive(rt, cid)
    await op(rt, cid, "start_processing")
    await rt.repo.db.execute(
        "UPDATE app.orders SET processing_started_at=%s WHERE id=%s",
        (rt.clock.now() - timedelta(hours=25), result["order_id"]),
    )
    assert await processing_alerts(rt.repo.db, rt.clock, 24) >= 1
    assert await processing_alerts(rt.repo.db, rt.clock, 24) == 0
    snapshot = await rt.repo.snapshot(rt.actor, cid)
    assert snapshot["orders"][0]["status"] == "IN_PROCESSING"


async def test_p3_opens_separate_p4_and_preserves_service_state(rt):
    case = await rt.repo.create_case(rt.actor, "Calidad sintética")
    cid = str(case["id"])
    await receive(rt, cid)
    await op(rt, cid, "start_processing")
    await op(rt, cid, "finish_processing")
    result = await release(rt, cid, "open_incident")
    incident = await rt.repo.case(rt.actor, result["incident_case_id"])
    parent = await rt.repo.snapshot(rt.actor, cid)
    assert incident["id"] != case["id"] and incident["parent_case_id"] == case["id"]
    assert parent["case"]["process"] == "P3"
    assert parent["orders"][0]["status"] == "QUALITY_PENDING"


async def test_pickup_request_can_schedule_without_order_and_receive_after_pickup(rt):
    from aquaclean.infrastructure.persistence.retail_logistics import options

    case = await rt.repo.create_case(rt.actor, "Recojo sin orden sintético", "CLI-0001")
    cid = str(case["id"])
    pickup = {
        "customer": {"existing_id": "CLI-0001"},
        "address": "Calle ficticia 123 sintética",
        "day": str(rt.clock.now().date() + timedelta(days=1)),
        "shift": "manana",
        "declared_volume": "Dos bolsas declaradas",
        "contact": "Contacto sintético",
    }
    proposal = await rt.retail.prepare(
        rt.actor, case, {"action": "request_pickup", "pickup": pickup}
    )
    approval = await stage(rt, cid, proposal)
    await approve(rt, cid, approval)
    result = await rt.executor.execute(rt.actor, cid, str(uuid4()), str(approval["id"]), {})
    assert not (await rt.repo.snapshot(rt.actor, cid))["orders"]
    await rt.repo.db.execute(
        "INSERT INTO app.slots(id,organization_id,day,shift,capacity) VALUES(%s,%s,%s,'manana',8)",
        ("RETAIL-" + str(uuid4()), rt.actor.organization_id, pickup["day"]),
    )
    calculated = await options(rt.repo, rt.actor, cid)
    approval = await stage(
        rt,
        cid,
        {"action": "reserve", "operation": "pickup", "options": calculated},
        "P2",
        "human",
        "logistics",
    )
    selection = {"option_id": calculated[0]["id"]}
    await approve(rt, cid, approval, selection)
    await rt.executor.execute(rt.actor, cid, str(uuid4()), str(approval["id"]), selection)
    await op(rt, cid, "pickup_completed")
    data = reception(rt, "CLI-0001")
    data.update(channel="pickup", pickup_request_id=result["pickup_request_id"])
    order = await receive(rt, cid, data)
    assert order["status"] == "RECEIVED"
    assert (await rt.repo.snapshot(rt.actor, cid))["orders"][0]["pickup_request_id"] is not None


async def test_p4_intent_in_quality_routes_to_p3_and_opens_separate_case(rt):
    from aquaclean.workers.main import process_run

    case = await rt.repo.create_case(rt.actor, "Incidencia desde Calidad sintética")
    cid = str(case["id"])
    await receive(rt, cid)
    await op(rt, cid, "start_processing")
    await op(rt, cid, "finish_processing")
    await rt.repo.operator_event(
        rt.actor,
        cid,
        str(uuid4()),
        "inspection",
        "Hallazgo físico sintético documentado por calidad",
        None,
    )
    rt.provider.process, rt.provider.action = "P4", "open_incident"
    run = await rt.repo.enqueue(
        rt.actor, cid, str(uuid4()), {"text": "Calidad solicita abrir incidencia"}
    )
    await process_run(rt, run)
    before = await rt.repo.snapshot(rt.actor, cid)
    assert before["case"]["process"] == "P3"
    assert before["approvals"][-1]["status"] == "pending"
    assert not before["retail"]["incidents"]
    after = await resume(rt, cid, before["approvals"][-1])
    assert after["retail"]["incidents"][0]["parent_case_id"] == case["id"]


async def test_human_new_incident_is_separate_idempotent_and_blocks_closure(rt):
    from aquaclean.infrastructure.persistence.incident_cases import open_incident

    case = await rt.repo.create_case(rt.actor, "Reclamo posterior sintético")
    cid = str(case["id"])
    await receive(rt, cid)
    s = await rt.repo.snapshot(rt.actor, cid)
    command = str(uuid4())
    first = await open_incident(
        rt.repo,
        rt.actor,
        cid,
        command,
        s["orders"][0]["version"],
        "Observación sintética del operador",
    )
    assert (
        await open_incident(
            rt.repo,
            rt.actor,
            cid,
            command,
            s["orders"][0]["version"],
            "Observación sintética del operador",
        )
        == first
    )
    assert first["incident_case_id"] != cid
    assert (await rt.repo.case(rt.actor, first["incident_case_id"]))["process"] == "P4"
    assert (await rt.repo.case(rt.actor, cid))["process"] == "P1"


async def test_tariff_change_invalidates_confirmation_without_partial_customer_order_payment(
    rt, tmp_path
):
    import json
    from pathlib import Path

    path = tmp_path / "tariffs.json"
    tariff = json.loads(Path("config/retail-tariffs-v2.json").read_text())
    path.write_text(json.dumps(tariff))
    rt.retail.tariff_path = path
    rt.executor.repository.tariff_path = path
    case = await rt.repo.create_case(rt.actor, "Cambio de tarifa sintético")
    proposal = await rt.retail.prepare(
        rt.actor, case, {"action": "receive", "reception": reception(rt)}
    )
    approval = await stage(rt, case["id"], proposal)
    await approve(rt, case["id"], approval)
    tariff["services"]["wash_piece"]["price"] = "6.50"
    tariff["version"] = "synthetic-test-changed"
    path.write_text(json.dumps(tariff))
    with pytest.raises(DomainError, match="Cotización"):
        await rt.executor.execute(rt.actor, str(case["id"]), str(uuid4()), str(approval["id"]), {})
    s = await rt.repo.snapshot(rt.actor, str(case["id"]))
    assert not s["orders"] and not s["retail"]["payments"] and s["case"]["client_id"] is None


async def test_retail_reprocess_needs_new_physical_verification_and_limit_is_per_order(rt):
    case = await rt.repo.create_case(rt.actor, "Reproceso al detalle sintético")
    cid = str(case["id"])
    result = await receive(rt, cid)
    await op(rt, cid, "start_processing")
    await op(rt, cid, "finish_processing")
    await release(rt, cid, "reprocess")
    assert (await rt.repo.snapshot(rt.actor, cid))["orders"][0]["status"] == "REPROCESS_PENDING"
    await rt.repo.operator_event(
        rt.actor,
        cid,
        str(uuid4()),
        "reprocess",
        "Operador ejecutó reproceso físico autorizado sintético",
        None,
    )
    assert (await rt.repo.snapshot(rt.actor, cid))["orders"][0]["status"] == "QUALITY_PENDING"
    sources = await rt.knowledge.search(rt.actor, "calidad reproceso", result["customer_id"])
    proposal = {"action": "release", "sources": sources[:1]}
    approval = await stage(rt, cid, proposal, "P3", "human", "quality")
    await approve(rt, cid, approval)
    with pytest.raises(DomainError, match="Falta evidencia humana"):
        await rt.executor.execute(rt.actor, cid, str(uuid4()), str(approval["id"]), {})
    other = await rt.repo.create_case(
        rt.actor, "Otro caso calidad misma orden", result["customer_id"]
    )
    order = await rt.repo.order(rt.actor, result["order_id"])
    await rt.repo.db.execute(
        "UPDATE app.cases SET order_id=%s,order_version=%s WHERE id=%s",
        (order["id"], order["version"], other["id"]),
    )
    with pytest.raises(DomainError, match="Límite piloto"):
        await release(rt, str(other["id"]), "reprocess")
    await release(rt, cid)
    assert (await rt.repo.snapshot(rt.actor, cid))["orders"][0]["status"] == "READY"
