import asyncio
import logging
from pathlib import Path
from uuid import UUID, uuid5

from langgraph.types import Command

from aquaclean.bootstrap import bootstrap
from aquaclean.domain.errors import DomainError
from aquaclean.graphs.main import build_graph
from aquaclean.infrastructure.persistence.checkpointer import checkpointer
from aquaclean.workers.outbox import deliver, expire

logger = logging.getLogger("aquaclean.worker")


async def claim(runtime):
    async with runtime.repo.db.pool.connection() as conn, conn.transaction():
        row = await (
            await conn.execute(
                "SELECT * FROM app.runs WHERE status='queued' OR (status='running' AND lease_until<now()) ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1"
            )
        ).fetchone()
        if row:
            await conn.execute(
                "UPDATE app.runs SET status='running',attempts=attempts+1,lease_until=now()+interval '30 seconds' WHERE id=%s",
                (row["id"],),
            )
        return row


async def heartbeat(runtime, run_id):
    while True:
        await asyncio.sleep(8)
        Path("/tmp/aquaclean-worker-heartbeat").touch()
        await runtime.repo.db.execute(
            "UPDATE app.runs SET lease_until=now()+interval '30 seconds' WHERE id=%s AND status='running'",
            (run_id,),
        )


async def process_run(runtime, run):
    rid, cid = str(run["id"]), str(run["case_id"])
    runtime.current_run_id = rid
    task = asyncio.create_task(heartbeat(runtime, rid))
    try:
        await runtime.repo.case(runtime.actor, cid)
        if run["cancelled"]:
            raise DomainError(
                "Respuesta detenida; datos persistidos conservados.", "cancelled", 409
            )
        await runtime.repo.event(rid, cid, "run.started", {"status": "running"})
        async with runtime.repo.db.pool.connection() as lock_conn:
            locked = await (
                await lock_conn.execute(
                    "SELECT pg_try_advisory_lock(hashtextextended(%s,1)) AS ok", (cid,)
                )
            ).fetchone()
            if not locked["ok"]:
                await runtime.repo.db.execute(
                    "UPDATE app.runs SET status='queued' WHERE id=%s", (rid,)
                )
                return
            try:
                async with checkpointer(runtime.settings) as saver:
                    graph = build_graph(runtime, saver)
                    config = {
                        "configurable": {
                            "thread_id": f"org:{runtime.actor.organization_id}:case:{cid}"
                        },
                        "recursion_limit": 30,
                    }
                    data = run["input"]
                    snapshot = await graph.aget_state(config)
                    # A claimed job may resume after a crash between graph completion and job completion.
                    if snapshot.values.get("execution_run_id") == rid and not snapshot.next:
                        result = snapshot.values
                    elif (
                        snapshot.values.get("execution_run_id") == rid
                        and snapshot.next
                        and not any(task.interrupts for task in snapshot.tasks)
                    ):
                        result = await graph.ainvoke(None, config)
                    elif (
                        snapshot.values.get("execution_run_id") == rid
                        and snapshot.next
                        and any(task.interrupts for task in snapshot.tasks)
                        and (
                            not data.get("resume")
                            or str(snapshot.values.get("approval", {}).get("id"))
                            != data.get("approval_id")
                        )
                    ):
                        result = {**snapshot.values, "__interrupt__": True}
                    elif data.get("resume"):
                        # Store the new job identity without changing the stable case thread.
                        if not snapshot.next:
                            raise DomainError(
                                "El checkpoint ya no espera esta revisión. Recupere el caso.",
                                "resume_conflict",
                                409,
                            )
                        if not any(task.interrupts for task in snapshot.tasks):
                            # A crash/cancel may persist the review row before the interrupt checkpoint.
                            # Complete idempotent preparation first, then resume the actual interrupt.
                            prepared = await graph.ainvoke(None, config)
                            if not prepared.get("__interrupt__"):
                                raise DomainError(
                                    "El grafo no alcanzó la revisión esperada. Recupere el estado.",
                                    "resume_conflict",
                                    409,
                                )
                        result = await graph.ainvoke(
                            Command(resume={"approval_id": data["approval_id"]}), config
                        )
                    elif snapshot.values.get("run_id") == rid and snapshot.next:
                        result = await graph.ainvoke(None, config)
                    else:
                        if snapshot.next and any(task.interrupts for task in snapshot.tasks):
                            raise DomainError(
                                "Resuelva o corrija la revisión pendiente antes de enviar otro mensaje.",
                                "review_pending",
                                409,
                            )
                        result = await graph.ainvoke(
                            {
                                "case_id": cid,
                                "run_id": rid,
                                "execution_run_id": rid,
                                "text": data.get("text", ""),
                                "attachment_ids": data.get("attachment_ids", []),
                                "model_calls": 0,
                                "proposal": {},
                                "approval": {},
                                "result": {},
                                "response": "",
                                "skip_review": False,
                            },
                            config,
                        )
                    paused = bool(result.get("__interrupt__"))
                    if paused:
                        approval = result["approval"]
                        await runtime.repo.message(
                            cid,
                            str(uuid5(UUID(str(approval["id"])), "proposal")),
                            "assistant",
                            result["proposal"]["response"],
                            {
                                "rationale_summary": result["proposal"]["rationale_summary"],
                                "sources": result["proposal"].get("sources", []),
                                "approval_id": str(approval["id"]),
                            },
                        )
                    await runtime.repo.event(
                        rid, cid, "run.completed", {"status": "paused" if paused else "completed"}
                    )
                    await runtime.repo.db.execute(
                        "UPDATE app.runs SET status=%s,finished_at=now(),lease_until=NULL WHERE id=%s",
                        ("paused" if paused else "completed", rid),
                    )
            finally:
                await lock_conn.execute("SELECT pg_advisory_unlock(hashtextextended(%s,1))", (cid,))
    except Exception as exc:
        # No provider exception text is logged: some SDKs include URLs or request content.
        message = (
            str(exc)
            if isinstance(exc, DomainError)
            else "Error de integración. Caso conservado; revise el estado y reintente con el mismo identificador."
        )
        code = exc.code if isinstance(exc, DomainError) else "integration_error"
        committed = await runtime.repo.db.one(
            "SELECT result FROM app.command_ledger WHERE case_id=%s AND created_at>=(SELECT created_at FROM app.runs WHERE id=%s) ORDER BY created_at DESC LIMIT 1",
            (cid, rid),
        )
        if committed:
            from aquaclean.application.presentation import describe_result

            message += " " + describe_result(committed["result"])
        await runtime.repo.db.execute(
            "UPDATE app.runs SET status='failed',finished_at=now(),lease_until=NULL WHERE id=%s",
            (rid,),
        )
        await runtime.repo.db.execute(
            "UPDATE app.cases SET status='pending_operator' WHERE id=%s AND status NOT IN ('closed','released','cancelled') AND NOT EXISTS (SELECT 1 FROM app.command_ledger WHERE case_id=%s AND created_at>=(SELECT created_at FROM app.runs WHERE id=%s))",
            (cid, cid, rid),
        )
        await runtime.repo.message(
            cid,
            str(uuid5(UUID(rid), "error")),
            "assistant",
            message,
            {"error": code, "result": committed["result"] if committed else {}},
        )
        await runtime.repo.event(
            rid, cid, "run.failed", {"status": "failed", "code": code, "message": message}
        )
        logger.warning("run %s failed (%s)", rid, code)
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


async def main():
    async with bootstrap() as runtime:
        while True:
            Path("/tmp/aquaclean-worker-heartbeat").touch()
            await deliver(runtime.repo.db)
            await expire(runtime.repo.db)
            run = await claim(runtime)
            if run:
                await process_run(runtime, run)
            else:
                await asyncio.sleep(0.5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
