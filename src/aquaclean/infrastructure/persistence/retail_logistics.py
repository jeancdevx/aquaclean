from datetime import datetime

from aquaclean.domain.errors import DomainError


async def cancel_delivery(conn, actor, case, order, proposal):
    actor.require("logistics")
    if proposal.get("operation") != "delivery" or order["status"] not in {
        "READY",
        "DELIVERY_PENDING",
    }:
        raise DomainError(
            "Solo se cancela la coordinación de entrega liberada, sin cancelar el servicio.",
            "invalid_phase",
            409,
        )
    reservations = await (
        await conn.execute(
            "DELETE FROM app.retail_reservations WHERE target_id=%s AND operation='delivery' RETURNING slot_id",
            (order["id"],),
        )
    ).fetchall()
    for reservation in reservations:
        await conn.execute(
            "UPDATE app.slots SET reserved=reserved-1,version=version+1 WHERE id=%s",
            (reservation["slot_id"],),
        )
    await conn.execute(
        "UPDATE app.orders SET status='READY',version=version+1 WHERE id=%s", (order["id"],)
    )
    await conn.execute(
        "UPDATE app.cases SET order_version=%s WHERE id=%s", (order["version"] + 1, case["id"])
    )
    return {
        "status": "delivery_coordination_cancelled",
        "service_status": "READY",
        "order_id": str(order["id"]),
        "released_slots": len(reservations),
    }


async def options(repo, actor, case_id):
    actor.require("logistics")
    case = await repo.case(actor, case_id)
    if case["order_id"]:
        target = await repo.order(actor, str(case["order_id"]))
        if target["kind"] == "legacy_v1":
            return await repo.slots(actor, str(target["id"]))
        if target["status"] not in {"READY", "DELIVERY_PENDING"}:
            return []
        day = target["promised_at"].date()
    elif case["pickup_request_id"]:
        target = await repo.db.one(
            "SELECT * FROM app.pickup_requests WHERE id=%s", (case["pickup_request_id"],)
        )
        actor.scope(target["organization_id"], target["client_id"])
        if target["status"] not in {"REQUESTED", "SCHEDULED"}:
            return []
        day = target["fields"]["day"]
    else:
        return []
    now = repo.clock.now()
    rows = await repo.db.all(
        "SELECT *, (day>%s::date+2) outside_policy FROM app.slots WHERE organization_id=%s AND day>=%s AND reserved<capacity ORDER BY day,shift LIMIT 16",
        (day, actor.organization_id, now.date()),
    )
    return [
        r
        for r in rows
        if datetime.combine(r["day"], repo.shift_times[r["shift"]], tzinfo=now.tzinfo) > now
    ][:8]


async def reserve(conn, actor, case, order, proposal, approval, selection, clock, shift_times):
    pickup = None
    if not order:
        pickup = await (
            await conn.execute(
                "SELECT * FROM app.pickup_requests WHERE id=%s FOR UPDATE",
                (case["pickup_request_id"],),
            )
        ).fetchone()
        if (
            not pickup
            or pickup["version"] != approval["pickup_version"]
            or pickup["status"] not in {"REQUESTED", "SCHEDULED"}
        ):
            raise DomainError("Solicitud cambió o no admite reserva.", "stale_pickup", 409)
        actor.scope(pickup["organization_id"], pickup["client_id"])
    if order and (
        order["kind"] != "retail_v2" or order["status"] not in {"READY", "DELIVERY_PENDING"}
    ):
        raise DomainError("Entrega exige liberación de calidad.", "invalid_phase", 409)
    operation = "delivery" if order else "pickup"
    if proposal.get("operation") != operation:
        raise DomainError("Operación incompatible con el objetivo logístico.", "invalid_phase", 409)
    option = next((o for o in proposal["options"] if o["id"] == selection.get("option_id")), None)
    if not option or (option["outside_policy"] and approval["kind"] != "human"):
        raise DomainError("Opción o autorización inválida.", "invalid_option", 409)
    slot = await (
        await conn.execute(
            "SELECT * FROM app.slots WHERE id=%s AND organization_id=%s FOR UPDATE",
            (option["id"], actor.organization_id),
        )
    ).fetchone()
    if (
        not slot
        or slot["version"] != option["version"]
        or slot["reserved"] >= slot["capacity"]
        or datetime.combine(slot["day"], shift_times[slot["shift"]], tzinfo=clock.now().tzinfo)
        <= clock.now()
    ):
        raise DomainError("Capacidad o ventana cambió.", "capacity_conflict", 409)
    target = order or pickup
    prior = await (
        await conn.execute(
            "SELECT slot_id FROM app.retail_reservations WHERE target_id=%s AND operation=%s",
            (target["id"], operation),
        )
    ).fetchone()
    if prior:
        await conn.execute(
            "UPDATE app.slots SET reserved=reserved-1,version=version+1 WHERE id=%s",
            (prior["slot_id"],),
        )
    await conn.execute(
        "UPDATE app.slots SET reserved=reserved+1,version=version+1 WHERE id=%s", (slot["id"],)
    )
    await conn.execute(
        "INSERT INTO app.retail_reservations VALUES(%s,%s,%s) ON CONFLICT(target_id,operation) DO UPDATE SET slot_id=excluded.slot_id",
        (target["id"], operation, slot["id"]),
    )
    if order:
        await conn.execute(
            "UPDATE app.orders SET status='DELIVERY_PENDING',version=version+1 WHERE id=%s",
            (order["id"],),
        )
        await conn.execute(
            "UPDATE app.cases SET order_version=%s WHERE id=%s", (order["version"] + 1, case["id"])
        )
    else:
        await conn.execute(
            "UPDATE app.pickup_requests SET status='SCHEDULED',version=version+1 WHERE id=%s",
            (pickup["id"],),
        )
        await conn.execute(
            "UPDATE app.cases SET pickup_version=%s WHERE id=%s",
            (pickup["version"] + 1, case["id"]),
        )
    return {
        "status": "scheduled",
        "operation": operation,
        "target_id": str(target["id"]),
        "slot_id": slot["id"],
        "day": str(slot["day"]),
        "shift": slot["shift"],
    }
