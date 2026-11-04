"""Human-declared milestones, payments and commercial closure, with ledger/outbox."""

from decimal import Decimal
from uuid import UUID, uuid5

from aquaclean.domain.entities import digest
from aquaclean.domain.errors import DomainError
from aquaclean.domain.retail import RetailOperation, next_status
from aquaclean.infrastructure.persistence.database import jsonb


async def operate(repo, actor, case_id: str, operation: RetailOperation):
    payload = operation.model_dump(mode="json")
    command_id = str(operation.command_id)
    async with repo.db.pool.connection() as conn, conn.transaction():
        await conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
            (actor.organization_id + command_id,),
        )
        case = await (
            await conn.execute(
                "SELECT * FROM app.cases WHERE id=%s AND organization_id=%s FOR UPDATE",
                (case_id, actor.organization_id),
            )
        ).fetchone()
        if not case:
            raise DomainError("Caso no disponible.", "not_found", 404)
        actor.scope(case["organization_id"], case["client_id"])
        action = operation.action
        actor.require(
            "logistics"
            if action in {"deliver", "delivery_pending", "pickup_completed"}
            else "attention"
        )
        prior = await (
            await conn.execute(
                "SELECT * FROM app.command_ledger WHERE organization_id=%s AND command_id=%s",
                (actor.organization_id, command_id),
            )
        ).fetchone()
        if prior:
            if prior["payload_hash"] != digest({"case_id": case_id, **payload}):
                raise DomainError(
                    "Comando reutilizado con otros datos.", "idempotency_conflict", 409
                )
            return prior["result"]
        if action == "pickup_completed":
            target = await (
                await conn.execute(
                    "SELECT * FROM app.pickup_requests WHERE id=%s FOR UPDATE",
                    (case["pickup_request_id"],),
                )
            ).fetchone()
            if (
                not target
                or target["version"] != operation.expected_version
                or target["status"] != "SCHEDULED"
            ):
                raise DomainError("Recojo requiere reserva vigente.", "invalid_phase", 409)
            await conn.execute(
                "UPDATE app.pickup_requests SET status='PICKED_UP',version=version+1 WHERE id=%s",
                (target["id"],),
            )
            await conn.execute(
                "UPDATE app.cases SET pickup_version=%s WHERE pickup_request_id=%s",
                (target["version"] + 1, target["id"]),
            )
            result = {"status": "PICKED_UP", "pickup_request_id": str(target["id"])}
            oid, pid = None, target["id"]
        else:
            order = await (
                await conn.execute(
                    "SELECT * FROM app.orders WHERE id=%s FOR UPDATE", (case["order_id"],)
                )
            ).fetchone()
            if not order or order["kind"] != "retail_v2":
                raise DomainError(
                    "Se requiere orden al detalle, no un antecedente V1.", "order_required", 409
                )
            actor.scope(order["organization_id"], order["client_id"])
            if order["version"] != operation.expected_version:
                raise DomainError(
                    "El pedido cambió; recargue antes de confirmar.", "stale_order", 409
                )
            if order["status"] == "CLOSED":
                raise DomainError("Orden cerrada.", "invalid_phase", 409)
            paid = await (
                await conn.execute(
                    "SELECT coalesce(sum(amount),0) total FROM app.payment_records WHERE order_id=%s",
                    (order["id"],),
                )
            ).fetchone()
            balance = order["total"] - paid["total"]
            status = order["status"]
            if action == "payment":
                if operation.amount is None or operation.amount > balance:
                    raise DomainError("Cobro declarado requiere importe positivo hasta el saldo.")
                await conn.execute(
                    "INSERT INTO app.payment_records VALUES(%s,%s,%s,'declared_payment',%s,%s,%s)",
                    (
                        command_id,
                        order["id"],
                        operation.amount,
                        operation.evidence,
                        actor.id,
                        repo.clock.now(),
                    ),
                )
                balance -= operation.amount
            elif action == "confirm_delivery":
                if status != "DELIVERED" or not operation.conformity:
                    raise DomainError(
                        "Conformidad explícita solo después de entrega.", "invalid_phase", 409
                    )
                await conn.execute(
                    "UPDATE app.delivery_evidence SET conformity=true,evidence=evidence || %s WHERE order_id=%s",
                    ("; conformidad: " + operation.evidence, order["id"]),
                )
            else:
                status = next_status(status, action)
                if action == "deliver":
                    if not operation.receiver:
                        raise DomainError("Entrega requiere receptor declarado.")
                    await conn.execute(
                        "INSERT INTO app.delivery_evidence VALUES(%s,%s,%s,%s,%s,%s,%s)",
                        (
                            command_id,
                            order["id"],
                            operation.receiver,
                            operation.evidence,
                            operation.conformity,
                            repo.clock.now(),
                            actor.id,
                        ),
                    )
                if action == "close":
                    delivery = await (
                        await conn.execute(
                            "SELECT * FROM app.delivery_evidence WHERE order_id=%s", (order["id"],)
                        )
                    ).fetchone()
                    incident = await (
                        await conn.execute(
                            "SELECT id FROM app.cases WHERE order_id=%s AND process='P4' AND status<>'closed' LIMIT 1",
                            (order["id"],),
                        )
                    ).fetchone()
                    if (
                        balance != Decimal("0.00")
                        or not delivery
                        or not delivery["conformity"]
                        or incident
                    ):
                        raise DomainError(
                            "Cierre exige saldo cero, entrega, conformidad e incidencias resueltas.",
                            "closure_blocked",
                            409,
                        )
                    receipt = {
                        "label": "COMPROBANTE DE DEMOSTRACIÓN · SIN VALIDEZ FISCAL",
                        "number": order["number"],
                        "currency": "PEN",
                        "total": str(order["total"]),
                        "paid": str(paid["total"]),
                        "balance": "0.00",
                        "bank_payment_executed": False,
                    }
                    await conn.execute(
                        "INSERT INTO app.demo_receipts(id,order_id,kind,payload) VALUES(%s,%s,'final',%s)",
                        (
                            str(uuid5(UUID(str(order["id"])), "receipt-final")),
                            order["id"],
                            jsonb(receipt),
                        ),
                    )
                if action == "start_processing":
                    await conn.execute(
                        "UPDATE app.orders SET processing_started_at=%s WHERE id=%s",
                        (repo.clock.now(), order["id"]),
                    )
            await conn.execute(
                "UPDATE app.orders SET status=%s,version=version+1 WHERE id=%s",
                (status, order["id"]),
            )
            await conn.execute(
                "UPDATE app.cases SET order_version=%s WHERE order_id=%s",
                (order["version"] + 1, order["id"]),
            )
            result = {
                "status": status,
                "order_id": str(order["id"]),
                "version": order["version"] + 1,
                "balance": str(balance),
                "declared_only": True,
            }
            oid, pid = order["id"], None
        await conn.execute(
            "INSERT INTO app.retail_events VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
            (command_id, oid, pid, case_id, action, jsonb(payload), actor.id, repo.clock.now()),
        )
        await conn.execute(
            "UPDATE app.cases SET version=version+1,updated_at=now() WHERE id=%s", (case_id,)
        )
        await conn.execute(
            "UPDATE app.approvals SET status='stale' WHERE case_id IN (SELECT id FROM app.cases WHERE order_id=%s OR pickup_request_id=%s OR id=%s) AND status='pending'",
            (oid, pid, case_id),
        )
        await conn.execute(
            "INSERT INTO app.command_ledger(organization_id,command_id,case_id,payload_hash,result) VALUES(%s,%s,%s,%s,%s)",
            (
                actor.organization_id,
                command_id,
                case_id,
                digest({"case_id": case_id, **payload}),
                jsonb(result),
            ),
        )
        await conn.execute(
            "INSERT INTO app.outbox(id,case_id,payload) VALUES(%s,%s,%s)",
            (str(uuid5(UUID(command_id), "human-milestone")), case_id, jsonb(result)),
        )
        return result


async def quality_effect(conn, case, order, action, result, clock):
    """Called after schema, human approval and source/evidence checks in CommandRepository."""
    if action == "open_incident":
        incident_id = str(uuid5(UUID(str(case["id"])), "incident:" + str(case["version"])))
        await conn.execute(
            "INSERT INTO app.cases(id,organization_id,client_id,title,process,order_id,order_version,parent_case_id) VALUES(%s,%s,%s,'Incidencia vinculada · sintética','P4',%s,%s,%s)",
            (
                incident_id,
                case["organization_id"],
                case["client_id"],
                order["id"],
                order["version"],
                case["id"],
            ),
        )
        result["incident_case_id"] = incident_id
    if order["kind"] != "retail_v2":
        return
    if action in {"release", "reprocess", "open_incident"} and order["status"] != "QUALITY_PENDING":
        raise DomainError(
            "Calidad requiere procesamiento terminado e inspección.", "invalid_phase", 409
        )
    if action == "release":
        blocking = await (
            await conn.execute(
                "SELECT id FROM app.cases WHERE order_id=%s AND process='P4' AND status<>'closed' LIMIT 1",
                (order["id"],),
            )
        ).fetchone()
        if blocking:
            raise DomainError("Incidencia abierta impide liberación.", "incident_blocked", 409)
    if action in {"release", "reprocess"}:
        status = "READY" if action == "release" else "REPROCESS_PENDING"
        await conn.execute(
            "UPDATE app.orders SET status=%s,version=version+1 WHERE id=%s", (status, order["id"])
        )
        await conn.execute(
            "UPDATE app.cases SET order_version=%s WHERE id=%s", (order["version"] + 1, case["id"])
        )
        if action == "release":
            result["service_status"] = "READY"
            await conn.execute(
                "INSERT INTO app.outbox(id,case_id,payload) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
                (
                    str(uuid5(UUID(str(order["id"])), "READY")),
                    case["id"],
                    jsonb(
                        {
                            "type": "order_ready",
                            "order_id": str(order["id"]),
                            "number": order["number"],
                            "channel": "local_inbox",
                        }
                    ),
                ),
            )
