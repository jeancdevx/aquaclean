"""A human opens a separate P4 dossier; this does not approve a solution."""

from uuid import UUID, uuid5

from aquaclean.domain.entities import digest
from aquaclean.domain.errors import DomainError
from aquaclean.infrastructure.persistence.database import jsonb


async def open_incident(repo, actor, case_id, command_id, expected_version, description):
    actor.require("admin")
    payload = {"case_id": case_id, "description": description, "expected_version": expected_version}
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
        prior = await (
            await conn.execute(
                "SELECT * FROM app.command_ledger WHERE organization_id=%s AND command_id=%s",
                (actor.organization_id, command_id),
            )
        ).fetchone()
        if prior:
            if prior["payload_hash"] != digest(payload):
                raise DomainError("Comando reutilizado.", "idempotency_conflict", 409)
            return prior["result"]
        order = await (
            await conn.execute(
                "SELECT * FROM app.orders WHERE id=%s FOR UPDATE", (case["order_id"],)
            )
        ).fetchone()
        if not order or order["kind"] != "retail_v2" or order["version"] != expected_version:
            raise DomainError(
                "Vincule una orden al detalle vigente para abrir incidencia.", "stale_order", 409
            )
        actor.scope(order["organization_id"], order["client_id"])
        cid = str(uuid5(UUID(command_id), "incident-case"))
        await conn.execute("UPDATE app.orders SET version=version+1 WHERE id=%s", (order["id"],))
        await conn.execute(
            "INSERT INTO app.cases(id,organization_id,client_id,title,process,order_id,order_version,parent_case_id) VALUES(%s,%s,%s,'Incidencia al detalle · sintética','P4',%s,%s,%s)",
            (
                cid,
                actor.organization_id,
                case["client_id"],
                order["id"],
                order["version"] + 1,
                case_id,
            ),
        )
        await conn.execute(
            "INSERT INTO app.operator_events(id,case_id,organization_id,actor_id,kind,note) VALUES(%s,%s,%s,%s,'observation',%s)",
            (command_id, cid, actor.organization_id, actor.id, description),
        )
        await conn.execute(
            "UPDATE app.cases SET order_version=%s WHERE order_id=%s",
            (order["version"] + 1, order["id"]),
        )
        await conn.execute(
            "UPDATE app.approvals SET status='stale' WHERE case_id IN (SELECT id FROM app.cases WHERE order_id=%s) AND status='pending'",
            (order["id"],),
        )
        result = {
            "status": "incident_open",
            "process": "P4",
            "incident_case_id": cid,
            "order_id": str(order["id"]),
        }
        await conn.execute(
            "INSERT INTO app.command_ledger(organization_id,command_id,case_id,payload_hash,result) VALUES(%s,%s,%s,%s,%s)",
            (actor.organization_id, command_id, case_id, digest(payload), jsonb(result)),
        )
        return result
