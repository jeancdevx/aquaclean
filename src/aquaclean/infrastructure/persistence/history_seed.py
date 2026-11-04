from datetime import datetime, time, timedelta
from uuid import UUID, uuid5

from aquaclean.domain.entities import ORG, digest
from aquaclean.infrastructure.persistence.database import jsonb

NAMESPACE = UUID("9244c368-e38b-45f2-878b-a84bcc28e9b1")


def ident(label: str) -> str:
    return str(uuid5(NAMESPACE, label))


async def seed_history(runtime, orders: int = 3000) -> dict:
    """Explicit synthetic history. No customer, contact, event or employee is portrayed as real.

    Fixed namespace and event-relative timestamps make a repeated seed safe. Existing rows are
    never overwritten. Historical fixtures do not emit live traces or pretend an LLM ran in the past.
    """
    today = runtime.clock.now().date()
    zone = runtime.clock.now().tzinfo
    sectors = ["Hotel", "Restaurante", "Residencia", "Hostal", "Centro de eventos"]
    names = [
        "Bahía",
        "Los Olivos",
        "Mirador",
        "Alameda",
        "Parque",
        "Costa",
        "Jardín",
        "Puerto",
        "Terraza",
        "Ribera",
    ]
    counts = {"orders": 0, "cases": 0, "operator_events": 0, "customers": 0}
    async with runtime.repo.db.pool.connection() as conn, conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock(918202)")
        anchor = await (
            await conn.execute(
                "SELECT created_at FROM app.cases WHERE id=%s", (ident("history-case-0"),)
            )
        ).fetchone()
        if anchor:
            today = anchor["created_at"].astimezone(zone).date() + timedelta(days=730)
        for i in range(150):
            cid = f"CLI-{i + 101:04d}"
            result = await conn.execute(
                "INSERT INTO app.customers(organization_id,id,name,email,address,blocked,synthetic) VALUES(%s,%s,%s,%s,%s,false,true) ON CONFLICT DO NOTHING",
                (
                    ORG,
                    cid,
                    f"{sectors[i % 5]} {names[(i // 5) % 10]} {i + 1:03d} · DEMO SINTÉTICO",
                    f"historico-{i + 1:03d}@example.invalid",
                    f"Dirección sintética {100 + i}, Lima (sin local real)",
                ),
            )
            counts["customers"] += result.rowcount
        for i in range(orders):
            cid = f"CLI-{i % 150 + 101:04d}"
            # Historical horizon excludes today; all lifecycle events precede the execution date.
            requested_day = today - timedelta(days=730 - (i % 720))
            created = datetime.combine(requested_day, time(9, 15), tzinfo=zone)
            pickup = datetime.combine(
                requested_day + timedelta(days=1),
                time(10, 30) if i % 2 == 0 else time(16, 0),
                tzinfo=zone,
            )
            inspected = pickup + timedelta(hours=5)
            delivered = pickup + timedelta(days=2, hours=5)
            process = ["P1", "P2", "P3", "P4"][i % 4]
            status = "closed" if process == "P4" else "released" if process == "P3" else "delivered"
            order_status = "delivered" if process == "P3" else status
            case_id, order_id = ident(f"history-case-{i}"), ident(f"history-order-{i}")
            bags = 1 + (i * 7) % 18
            fields = {
                "cliente_id": cid,
                "solicitante": f"Operador histórico sintético {i % 12 + 1:02d}",
                "correo": f"historico-{i % 150 + 1:03d}@example.invalid",
                "fecha_recojo": str(pickup.date()),
                "turno": "manana" if i % 2 == 0 else "tarde",
                "tipo_ropa": ["manteleria", "toallas", "uniformes", "mixto"][i % 4],
                "bolsas": bags,
                "direccion_recojo": f"Dirección sintética {100 + i % 150}, Lima (sin local real)",
                "observaciones": "Fixture histórico sintético: no representa una operación real de Aqua Clean.",
                "canal": "demo_history",
            }
            result = await conn.execute(
                "INSERT INTO app.cases(id,organization_id,client_id,title,process,status,version,order_version,owner,created_at,updated_at,synthetic,data_origin) VALUES(%s,%s,%s,%s,%s,%s,1,1,'seed_demo',%s,%s,true,'synthetic_history_v1') ON CONFLICT DO NOTHING",
                (
                    case_id,
                    ORG,
                    cid,
                    f"DEMO histórico {i + 1:05d} · {fields['tipo_ropa']} · {process}",
                    process,
                    status,
                    created,
                    delivered,
                ),
            )
            counts["cases"] += result.rowcount
            result = await conn.execute(
                "INSERT INTO app.orders(id,organization_id,client_id,request_id,number,fields,status,version,created_at,synthetic) VALUES(%s,%s,%s,%s,%s,%s,%s,1,%s,true) ON CONFLICT DO NOTHING",
                (
                    order_id,
                    ORG,
                    cid,
                    case_id,
                    f"HIST-DEMO-{i + 1:05d}",
                    jsonb(fields),
                    order_status,
                    created,
                ),
            )
            counts["orders"] += result.rowcount
            await conn.execute(
                "UPDATE app.cases SET order_id=%s WHERE id=%s AND order_id IS NULL",
                (order_id, case_id),
            )
            events = [
                ("pickup", pickup, "Recojo ficticio registrado como parte del dataset sintético."),
                (
                    "inspection",
                    inspected,
                    "Inspección ficticia documentada para practicar consulta de historial.",
                ),
                ("delivery", delivered, "Entrega ficticia; no es una guía ni firma real."),
            ]
            if process == "P3":
                events.append(
                    (
                        "conformity",
                        inspected + timedelta(minutes=30),
                        "Conformidad ficticia del lote de demostración.",
                    )
                )
            if process == "P4":
                events += [
                    (
                        "observation",
                        pickup + timedelta(hours=6),
                        "Diferencia ficticia de conteo; expediente de demostración.",
                    ),
                    (
                        "customer_acceptance",
                        pickup + timedelta(days=1),
                        "Aceptación ficticia del plan de búsqueda; dato sintético.",
                    ),
                    (
                        "fulfillment",
                        delivered - timedelta(hours=1),
                        "Búsqueda y restitución ficticias completadas; sin compensación real.",
                    ),
                    (
                        "conformity",
                        delivered,
                        "Criterio ficticio de cierre de expediente sintético.",
                    ),
                ]
            for kind, at, note in events:
                result = await conn.execute(
                    "INSERT INTO app.operator_events(id,case_id,organization_id,actor_id,kind,note,created_at) VALUES(%s,%s,%s,'seed_demo',%s,%s,%s) ON CONFLICT DO NOTHING",
                    (ident(f"history-event-{i}-{kind}"), case_id, ORG, kind, note, at),
                )
                counts["operator_events"] += result.rowcount
            await conn.execute(
                "INSERT INTO app.messages(id,case_id,role,content,metadata,created_at) VALUES(%s,%s,'user',%s,%s,%s) ON CONFLICT DO NOTHING",
                (
                    ident(f"history-note-{i}"),
                    case_id,
                    f"Registro histórico SINTÉTICO {i + 1:05d}: {bags} bolsas de {fields['tipo_ropa']}. Este expediente se generó para pruebas, no acredita hechos reales.",
                    jsonb(
                        {
                            "synthetic": True,
                            "origin": "synthetic_history_v1",
                            "dataset_hash": digest(fields),
                        }
                    ),
                    created,
                ),
            )
    return {
        "status": "seeded",
        "synthetic": True,
        "requested_orders": orders,
        "inserted": counts,
        "period": {
            "from": str(today - timedelta(days=730)),
            "through": str(today - timedelta(days=8)),
        },
        "note": "Sin contactos personales reales, sin notificaciones ni trazas LLM históricas inventadas.",
    }
