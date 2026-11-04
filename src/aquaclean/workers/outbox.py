from uuid import uuid4

from aquaclean.infrastructure.persistence.database import Database, jsonb


async def deliver(db: Database, fail: bool = False) -> int:
    count = 0
    async with db.pool.connection() as conn, conn.transaction():
        rows = await (
            await conn.execute(
                "SELECT * FROM app.outbox WHERE status='pending' AND next_attempt_at<=now() ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 20"
            )
        ).fetchall()
        for row in rows:
            if fail:
                await conn.execute(
                    "UPDATE app.outbox SET attempts=attempts+1,next_attempt_at=now()+interval '2 seconds' WHERE id=%s",
                    (row["id"],),
                )
                continue
            await conn.execute(
                "INSERT INTO app.inbox(event_id,case_id,payload) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
                (row["id"], row["case_id"], jsonb(row["payload"])),
            )
            await conn.execute(
                "UPDATE app.outbox SET status='delivered_local',attempts=attempts+1 WHERE id=%s",
                (row["id"],),
            )
            await conn.execute(
                "UPDATE app.cases SET status='registered' WHERE id=%s AND status='registered_notification_pending'",
                (row["case_id"],),
            )
            # This is a local inbox delivery only; no email transport is configured.
            count += 1
    return count


async def expire(db: Database) -> int:
    async with db.pool.connection() as conn, conn.transaction():
        rows = await (
            await conn.execute(
                "UPDATE app.cases SET status='pending_timeout',deadline=NULL,version=version+1 WHERE deadline<=now() AND status IN ('awaiting_information','awaiting_review') RETURNING id"
            )
        ).fetchall()
        for row in rows:
            await conn.execute(
                "UPDATE app.approvals SET status='expired' WHERE case_id=%s AND status='pending'",
                (row["id"],),
            )
            await conn.execute(
                "INSERT INTO app.outbox(id,case_id,payload) VALUES(%s,%s,%s)",
                (
                    str(uuid4()),
                    row["id"],
                    jsonb(
                        {
                            "status": "pending_timeout",
                            "next_action": "Revisión del operador; silencio no es conformidad",
                        }
                    ),
                ),
            )
        return len(rows)


async def processing_alerts(db, clock, threshold_hours: int = 24) -> int:
    """Non-interrupting laboratory timer, independent from review/information expiry."""
    from datetime import timedelta
    from uuid import UUID, uuid5

    if threshold_hours < 1:
        raise ValueError("processing alert hours must be positive")
    async with db.pool.connection() as conn, conn.transaction():
        rows = await (
            await conn.execute(
                "SELECT o.id,c.id case_id FROM app.orders o JOIN app.cases c ON c.id=o.request_id WHERE o.kind='retail_v2' AND o.status='IN_PROCESSING' AND o.processing_started_at<=%s AND NOT EXISTS(SELECT 1 FROM app.processing_alerts a WHERE a.order_id=o.id) FOR UPDATE OF o SKIP LOCKED",
                (clock.now() - timedelta(hours=threshold_hours),),
            )
        ).fetchall()
        for row in rows:
            event_id = str(uuid5(UUID(str(row["id"])), "processing-alert"))
            await conn.execute(
                "INSERT INTO app.outbox(id,case_id,payload) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
                (
                    event_id,
                    row["case_id"],
                    jsonb(
                        {
                            "type": "processing_alert",
                            "order_id": str(row["id"]),
                            "threshold_hours": threshold_hours,
                            "laboratory_parameter": True,
                            "non_interrupting": True,
                        }
                    ),
                ),
            )
            await conn.execute(
                "INSERT INTO app.processing_alerts VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (row["id"], event_id, threshold_hours, clock.now()),
            )
        return len(rows)
