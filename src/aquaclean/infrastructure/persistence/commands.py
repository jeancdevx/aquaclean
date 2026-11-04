from uuid import UUID, uuid5

from langsmith import traceable

from aquaclean.domain.entities import POLICY, Actor, Clock, digest
from aquaclean.domain.errors import DomainError
from aquaclean.domain.policies import (
    ROLES,
    validate_action,
    validate_commercial_exception,
    validate_fulfillment,
)
from aquaclean.infrastructure.integrations.n8n import legacy_request
from aquaclean.infrastructure.persistence.database import Database, jsonb


class CommandRepository:
    """One transaction: ledger, aggregate/version, authorization and outbox.

    A lost commit acknowledgement is resolved by replaying the SAME command_id.
    Transaction advisory locks cover absent ledger rows as well as existing aggregates.
    """

    def __init__(
        self,
        db: Database,
        clock: Clock,
        policy_version: str = POLICY,
        max_bags: int = 40,
        max_pickup_days: int = 30,
        max_reprocesses: int = 1,
        shift_times: dict | None = None,
        tariff_path=None,
    ):
        from pathlib import Path

        self.tariff_path = tariff_path or Path("config/retail-tariffs-v2.json")
        self.db, self.clock = db, clock
        self.policy_version = policy_version
        self.max_bags, self.max_pickup_days, self.max_reprocesses = (
            max_bags,
            max_pickup_days,
            max_reprocesses,
        )
        from datetime import time

        self.shift_times = shift_times or {"manana": time(10, 30), "tarde": time(16, 0)}

    @traceable(
        name="AquaClean.deterministic_executor",
        run_type="tool",
        process_inputs=lambda x: {k: x.get(k) for k in ["case_id", "command_id", "approval_id"]},
    )
    async def execute(
        self, actor: Actor, case_id: str, command_id: str, approval_id: str, selection: dict
    ) -> dict:
        payload = {"case_id": case_id, "approval_id": approval_id, "selection": selection}
        async with self.db.pool.connection() as conn, conn.transaction():
            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                (actor.organization_id + command_id,),
            )
            prior = await (
                await conn.execute(
                    "SELECT * FROM app.command_ledger WHERE organization_id=%s AND command_id=%s",
                    (actor.organization_id, command_id),
                )
            ).fetchone()
            if prior:
                if prior["payload_hash"] != digest(payload):
                    raise DomainError(
                        "El comando ya existe con otro contenido.", "idempotency_conflict", 409
                    )
                # Replays still require current case access.
                case = await (
                    await conn.execute("SELECT * FROM app.cases WHERE id=%s", (case_id,))
                ).fetchone()
                actor.scope(case["organization_id"], case["client_id"])
                actor.require(ROLES[prior["result"].get("process", case["process"])])
                return prior["result"]
            case = await (
                await conn.execute(
                    "SELECT * FROM app.cases WHERE id=%s AND organization_id=%s FOR UPDATE",
                    (case_id, actor.organization_id),
                )
            ).fetchone()
            if not case:
                raise DomainError("Caso no disponible.", "not_found", 404)
            actor.scope(case["organization_id"], case["client_id"])
            actor.require(ROLES[case["process"]])
            approval = await (
                await conn.execute(
                    "SELECT * FROM app.approvals WHERE id=%s AND case_id=%s", (approval_id, case_id)
                )
            ).fetchone()
            if (
                not approval
                or approval["status"] != "approved"
                or approval["proposal_hash"] != case["proposal_hash"]
                or approval["case_version"] != case["version"]
                or approval["policy_version"] != self.policy_version
                or approval["order_version"] != case["order_version"]
            ):
                raise DomainError(
                    "Se requiere aprobación vigente vinculada a esta versión.",
                    "stale_approval",
                    409,
                )
            proposal = case["proposal"]
            if digest(proposal) != approval["proposal_hash"]:
                raise DomainError("La propuesta cambió.", "stale_approval", 409)
            process = case["process"]
            action = proposal.get("action")
            validate_action(process, action)
            actor.require(approval["required_role"])
            if approval["decision"].get("selection", {}) != selection:
                raise DomainError(
                    "La selección no coincide con la aprobada.", "selection_conflict", 409
                )
            order = None
            if case["order_id"]:
                order = await (
                    await conn.execute(
                        "SELECT * FROM app.orders WHERE id=%s FOR UPDATE", (case["order_id"],)
                    )
                ).fetchone()
                if not order or order["version"] != case["order_version"]:
                    raise DomainError(
                        "El pedido cambió. Recalcule la propuesta.", "stale_order", 409
                    )
                actor.scope(order["organization_id"], order["client_id"])
            result = {"command_id": command_id, "status": "pending", "case_id": case_id}
            result["process"] = process
            if process == "P1" and action in {"receive", "request_pickup"}:
                from aquaclean.infrastructure.persistence.retail import RetailRepository

                result.update(
                    await RetailRepository(self.db, self.clock, self.tariff_path).execute_attention(
                        conn, actor, case, proposal, approval, command_id
                    )
                )
            elif process == "P1" and action == "register":
                fields = legacy_request(
                    proposal["fields"], self.clock, self.max_bags, self.max_pickup_days
                )
                customer = await (
                    await conn.execute(
                        "SELECT * FROM app.customers WHERE organization_id=%s AND id=%s FOR SHARE",
                        (actor.organization_id, fields["cliente_id"]),
                    )
                ).fetchone()
                if not customer:
                    raise DomainError("Cliente no habilitado.")
                actor.scope(customer["organization_id"], customer["id"])
                if case["client_id"] and case["client_id"] != customer["id"]:
                    raise DomainError("El cliente no coincide con el caso.", "forbidden", 403)
                if customer["blocked"]:
                    human = await (
                        await conn.execute(
                            "SELECT id,decision FROM app.approvals WHERE case_id=%s AND status='approved' AND kind='human' AND required_role='admin' AND proposal_hash=%s AND policy_version=%s AND case_version=%s AND order_version IS NOT DISTINCT FROM %s",
                            (
                                case_id,
                                case["proposal_hash"],
                                self.policy_version,
                                approval["case_version"] - 1,
                                case["order_version"],
                            ),
                        )
                    ).fetchone()
                    if not human:
                        raise DomainError(
                            "Cliente bloqueado: requiere excepción administrativa.",
                            "human_required",
                            409,
                        )
                    validate_commercial_exception(
                        (human["decision"] or {}).get("commercial_exception")
                    )
                if approval["kind"] != "confirmation":
                    raise DomainError(
                        "Confirme los siete campos antes del registro.",
                        "confirmation_required",
                        409,
                    )
                if case["order_id"]:
                    raise DomainError("Este caso ya tiene un pedido.", "existing_order", 409)
                oid = str(uuid5(UUID(case_id), "order"))
                number = "DEMO-" + UUID(oid).hex[:10].upper()
                await conn.execute(
                    "INSERT INTO app.orders(id,organization_id,client_id,request_id,number,fields) VALUES(%s,%s,%s,%s,%s,%s)",
                    (oid, actor.organization_id, customer["id"], case_id, number, jsonb(fields)),
                )
                await conn.execute(
                    "UPDATE app.cases SET order_id=%s,client_id=%s,order_version=1 WHERE id=%s",
                    (oid, customer["id"], case_id),
                )
                result.update(
                    status="registered_notification_pending", order_id=oid, number=number, version=1
                )
            elif action == "cancel":
                if order and order["kind"] == "retail_v2":
                    if process != "P2":
                        raise DomainError(
                            "La recepción no cancela el ciclo de servicio. Use logística para coordinar entrega.",
                            "invalid_phase",
                            409,
                        )
                    from aquaclean.infrastructure.persistence.retail_logistics import (
                        cancel_delivery,
                    )

                    result.update(await cancel_delivery(conn, actor, case, order, proposal))
                elif case["pickup_request_id"]:
                    if process == "P2" and proposal.get("operation") != "pickup":
                        raise DomainError(
                            "El objetivo de cancelación es una solicitud de recojo, no una entrega.",
                            "invalid_phase",
                            409,
                        )
                    pickup = await (
                        await conn.execute(
                            "SELECT * FROM app.pickup_requests WHERE id=%s FOR UPDATE",
                            (case["pickup_request_id"],),
                        )
                    ).fetchone()
                    if pickup["version"] != approval["pickup_version"] or pickup["status"] not in {
                        "REQUESTED",
                        "SCHEDULED",
                    }:
                        raise DomainError(
                            "Solicitud de recojo no cancelable o cambió.", "invalid_phase", 409
                        )
                    reservations = await (
                        await conn.execute(
                            "DELETE FROM app.retail_reservations WHERE target_id=%s RETURNING slot_id",
                            (pickup["id"],),
                        )
                    ).fetchall()
                    for reservation in reservations:
                        await conn.execute(
                            "UPDATE app.slots SET reserved=reserved-1,version=version+1 WHERE id=%s",
                            (reservation["slot_id"],),
                        )
                    await conn.execute(
                        "UPDATE app.pickup_requests SET status='CANCELLED',version=version+1 WHERE id=%s",
                        (pickup["id"],),
                    )
                    await conn.execute(
                        "UPDATE app.cases SET pickup_version=%s WHERE id=%s",
                        (pickup["version"] + 1, case_id),
                    )
                elif order:
                    reservations = await (
                        await conn.execute(
                            "DELETE FROM app.reservations WHERE order_id=%s RETURNING slot_id",
                            (order["id"],),
                        )
                    ).fetchall()
                    for reservation in reservations:
                        await conn.execute(
                            "UPDATE app.slots SET reserved=reserved-1,version=version+1 WHERE id=%s",
                            (reservation["slot_id"],),
                        )
                    await conn.execute(
                        "UPDATE app.orders SET status='cancelled',version=version+1 WHERE id=%s",
                        (order["id"],),
                    )
                    await conn.execute(
                        "UPDATE app.cases SET order_version=order_version+1 WHERE id=%s", (case_id,)
                    )
                if not (order and order["kind"] == "retail_v2"):
                    result["status"] = "cancelled"
            elif process == "P2" and action == "reserve":
                if (order and order["kind"] == "retail_v2") or case["pickup_request_id"]:
                    from aquaclean.infrastructure.persistence.retail_logistics import reserve

                    result.update(
                        await reserve(
                            conn,
                            actor,
                            case,
                            order,
                            proposal,
                            approval,
                            selection,
                            self.clock,
                            self.shift_times,
                        )
                    )
                else:
                    result.update(
                        await self._reserve_legacy(
                            conn, actor, case, order, proposal, approval, selection
                        )
                    )
            elif process in {"P3", "P4"}:
                if not order:
                    raise DomainError(
                        "Pedido requerido para disponer un lote o una incidencia.",
                        "order_required",
                        409,
                    )
                if approval["kind"] != "human":
                    raise DomainError(
                        "Disposición/solución requiere decisión humana.", "human_required", 409
                    )
                policy_sources = []
                for source in proposal.get("sources", []):
                    if source.get("source_kind") == "external_historical_reference":
                        continue
                    verified = await (
                        await conn.execute(
                            """SELECT c.id FROM app.chunks c JOIN app.documents d ON d.id=c.document_id
                        WHERE c.id=%s AND c.hash=%s AND d.organization_id=%s AND d.approved
                        AND d.roles && %s::text[] AND (d.client_id IS NULL OR d.client_id=%s)
                        AND d.valid_from<=%s AND (d.valid_until IS NULL OR d.valid_until>%s)""",
                            (
                                source.get("chunk_id"),
                                source.get("hash"),
                                actor.organization_id,
                                list(actor.roles),
                                case["client_id"],
                                self.clock.now(),
                                self.clock.now(),
                            ),
                        )
                    ).fetchone()
                    if verified:
                        policy_sources.append(source)
                if not policy_sources:
                    raise DomainError(
                        "Falta procedimiento aprobado, vigente y accesible; una referencia pública no autoriza la disposición.",
                        "insufficient_evidence",
                        409,
                    )
                if process == "P3" and action == "open_incident":
                    inspection = await (
                        await conn.execute(
                            "SELECT id FROM app.operator_events WHERE case_id=%s AND kind='inspection' LIMIT 1",
                            (case_id,),
                        )
                    ).fetchone()
                    if not inspection:
                        raise DomainError(
                            "Incidencia desde calidad requiere inspección humana.",
                            "insufficient_evidence",
                            409,
                        )
                evidence = await (
                    await conn.execute(
                        "SELECT * FROM app.operator_events WHERE case_id=%s", (case_id,)
                    )
                ).fetchall()
                if action in {"release", "close_incident"}:
                    if action == "close_incident":
                        plan = await (
                            await conn.execute(
                                "SELECT created_at FROM app.command_ledger WHERE case_id=%s AND result->>'status'='awaiting_customer_acceptance_and_fulfillment' ORDER BY created_at DESC LIMIT 1",
                                (case_id,),
                            )
                        ).fetchone()
                        if not plan:
                            raise DomainError(
                                "Falta solución autorizada anterior.", "insufficient_evidence", 409
                            )
                        evidence = [e for e in evidence if e["created_at"] >= plan["created_at"]]
                    if process == "P3":
                        reprocessed = [
                            e["created_at"] for e in evidence if e["kind"] == "reprocess"
                        ]
                        if reprocessed:
                            evidence = [
                                e
                                for e in evidence
                                if e["kind"]
                                not in (
                                    {"inspection", "conformity"}
                                    if order["kind"] == "retail_v2"
                                    else {"conformity"}
                                )
                                or e["created_at"] >= max(reprocessed)
                            ]
                    validate_fulfillment(process, list(evidence))
                    if not policy_sources:
                        raise DomainError(
                            "Falta procedimiento vigente recuperado.", "insufficient_evidence", 409
                        )
                    result["status"] = "released" if process == "P3" else "closed"
                elif action == "reprocess":
                    if not any(e["kind"] == "inspection" for e in evidence) or not proposal.get(
                        "sources"
                    ):
                        raise DomainError(
                            "Inspección y procedimiento vigente son obligatorios.",
                            "insufficient_evidence",
                            409,
                        )
                    count_reprocess = sum(e["kind"] == "reprocess" for e in evidence)
                    if order["kind"] == "retail_v2":
                        count = await (
                            await conn.execute(
                                "SELECT count(*) n FROM app.operator_events e JOIN app.cases c ON c.id=e.case_id WHERE c.order_id=%s AND e.kind='reprocess'",
                                (order["id"],),
                            )
                        ).fetchone()
                        count_reprocess = count["n"]
                    if count_reprocess >= self.max_reprocesses:
                        raise DomainError("Límite piloto de reproceso agotado.", "policy", 409)
                    result["status"] = "awaiting_physical_reprocess"
                elif action == "resolve_incident":
                    result["status"] = "awaiting_customer_acceptance_and_fulfillment"
                elif action == "open_incident":
                    result["status"] = "incident_open"

                else:
                    raise DomainError("Disposición no ejecutable.")
                from aquaclean.infrastructure.persistence.retail_operations import quality_effect

                await quality_effect(conn, case, order, action, result, self.clock)
                if order and action == "release" and order["kind"] == "legacy_v1":
                    await conn.execute(
                        "UPDATE app.orders SET status='released',version=version+1 WHERE id=%s",
                        (order["id"],),
                    )
                    await conn.execute(
                        "UPDATE app.cases SET order_version=order_version+1 WHERE id=%s", (case_id,)
                    )
            else:
                raise DomainError("El proceso no permite ese comando.")
            await conn.execute(
                "UPDATE app.cases SET status=%s,version=version+1,deadline=NULL,updated_at=now() WHERE id=%s",
                (result["status"], case_id),
            )
            await conn.execute(
                "INSERT INTO app.command_ledger(organization_id,command_id,case_id,payload_hash,result) VALUES(%s,%s,%s,%s,%s)",
                (actor.organization_id, command_id, case_id, digest(payload), jsonb(result)),
            )
            await conn.execute(
                "INSERT INTO app.outbox(id,case_id,payload) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
                (str(uuid5(UUID(command_id), "notification")), case_id, jsonb(result)),
            )
            return result

    async def _reserve_legacy(self, conn, actor, case, order, proposal, approval, selection):
        if not order or order["status"] == "cancelled":
            raise DomainError("Se requiere un pedido activo.")
        option_id = selection.get("option_id")
        option = next((o for o in proposal["options"] if o["id"] == option_id), None)
        if not option:
            raise DomainError("La opción no fue calculada por el servicio.", "invalid_option", 409)
        if option["outside_policy"] and approval["kind"] != "human":
            raise DomainError(
                "Cambio fuera de compromiso: requiere logística.", "human_required", 409
            )
        slot = await (
            await conn.execute(
                "SELECT * FROM app.slots WHERE id=%s AND organization_id=%s FOR UPDATE",
                (option_id, actor.organization_id),
            )
        ).fetchone()
        if not slot or slot["version"] != option["version"] or slot["reserved"] >= slot["capacity"]:
            raise DomainError(
                "La capacidad cambió. Solicite alternativas actuales.",
                "capacity_conflict",
                409,
            )
        from datetime import datetime

        if (
            datetime.combine(
                slot["day"], self.shift_times[slot["shift"]], tzinfo=self.clock.now().tzinfo
            )
            <= self.clock.now()
        ):
            raise DomainError(
                "La ventana de agenda ya pasó. Recalcule alternativas.",
                "capacity_conflict",
                409,
            )
        operation = proposal.get("operation", "pickup")
        previous = await (
            await conn.execute(
                "SELECT * FROM app.reservations WHERE order_id=%s AND operation=%s",
                (order["id"], operation),
            )
        ).fetchone()
        if previous:
            await conn.execute(
                "UPDATE app.slots SET reserved=reserved-1,version=version+1 WHERE id=%s",
                (previous["slot_id"],),
            )
        await conn.execute(
            "UPDATE app.slots SET reserved=reserved+1,version=version+1 WHERE id=%s",
            (option_id,),
        )
        await conn.execute(
            "INSERT INTO app.reservations(order_id,operation,slot_id) VALUES(%s,%s,%s) ON CONFLICT(order_id,operation) DO UPDATE SET slot_id=excluded.slot_id",
            (order["id"], operation, option_id),
        )
        await conn.execute(
            "UPDATE app.orders SET status='scheduled',version=version+1 WHERE id=%s",
            (order["id"],),
        )
        await conn.execute(
            "UPDATE app.cases SET order_version=order_version+1 WHERE id=%s", (case["id"],)
        )
        return dict(
            status="scheduled",
            order_id=str(order["id"]),
            slot_id=option_id,
            day=str(slot["day"]),
            shift=slot["shift"],
        )
