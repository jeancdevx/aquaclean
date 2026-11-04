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
