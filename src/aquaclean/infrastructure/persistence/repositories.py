from datetime import timedelta
from uuid import UUID, uuid4, uuid5

from aquaclean.domain.entities import POLICY, Actor, Clock, digest
from aquaclean.domain.errors import DomainError
from aquaclean.domain.policies import validate_commercial_exception
from aquaclean.infrastructure.persistence.database import Database, jsonb


class Repository:
    def __init__(
        self,
        db: Database,
        clock: Clock,
        wait_hours: int = 24,
        max_pending_runs: int = 20,
        policy_version: str = POLICY,
        max_reprocesses: int = 1,
        shift_times: dict | None = None,
    ):
        self.db, self.clock, self.wait_hours = db, clock, wait_hours
        self.max_pending_runs = max_pending_runs
        self.policy_version = policy_version
        self.max_reprocesses = max_reprocesses
        from datetime import time

        self.shift_times = shift_times or {"manana": time(10, 30), "tarde": time(16, 0)}

    async def case(self, actor: Actor, case_id: str) -> dict:
        row = await self.db.one(
            "SELECT * FROM app.cases WHERE id=%s AND organization_id=%s",
            (case_id, actor.organization_id),
        )
        if not row:
            raise DomainError("Caso no disponible.", "not_found", 404)
        actor.scope(row["organization_id"], row["client_id"])
        return row

    async def create_case(self, actor: Actor, title: str, client_id: str | None = None) -> dict:
        if client_id:
            await self.customer(actor, client_id)
        cid = str(uuid4())
        await self.db.execute(
            "INSERT INTO app.cases(id,organization_id,client_id,title,owner) VALUES(%s,%s,%s,%s,%s)",
            (cid, actor.organization_id, client_id or actor.client_id, title[:120], actor.id),
        )
        return await self.case(actor, cid)

    async def customer(self, actor: Actor, client_id: str) -> dict:
        actor.scope(actor.organization_id, client_id)
        row = await self.db.one(
            "SELECT * FROM app.customers WHERE organization_id=%s AND id=%s",
            (actor.organization_id, client_id),
        )
        if not row:
            raise DomainError("Cliente no disponible en el padrón sintético.", "not_found", 404)
        return row

    async def messages(self, actor: Actor, case_id: str) -> list[dict]:
        await self.case(actor, case_id)
        return await self.db.all(
            "SELECT * FROM app.messages WHERE case_id=%s ORDER BY created_at,id", (case_id,)
        )

    async def message(
        self, case_id: str, message_id: str, role: str, content: str, metadata: dict | None = None
    ):
        await self.db.execute(
            "INSERT INTO app.messages(id,case_id,role,content,metadata) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (message_id, case_id, role, content, jsonb(metadata or {})),
        )

    async def event(
        self, run_id: str, case_id: str, kind: str, payload: dict, event_key: str | None = None
    ):
        # Only public fields are passed by callers; model prompts/reasoning are never events.
        await self.db.execute(
            "INSERT INTO app.events(event_id,run_id,case_id,type,payload) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(event_id) DO NOTHING",
            (
                str(uuid5(UUID(run_id), event_key)) if event_key else str(uuid4()),
                run_id,
                case_id,
                kind,
                jsonb(payload),
            ),
        )

    async def snapshot(self, actor: Actor, case_id: str) -> dict:
        case = await self.case(actor, case_id)
        return {
            "linked_order_history": await self.order_history(actor, str(case["order_id"]))
            if case["order_id"]
            else [],
            "command_history": await self.db.all(
                "SELECT command_id,result,created_at FROM app.command_ledger WHERE case_id=%s ORDER BY created_at",
                (case_id,),
            ),
            "case": case,
            "messages": await self.messages(actor, case_id),
            "attachments": await self.db.all(
                "SELECT id,filename,mime,size,hash,pages,duration,observation,observation_version,perception_status FROM app.attachments WHERE case_id=%s ORDER BY created_at",
                (case_id,),
            ),
            "approvals": await self.db.all(
                "SELECT * FROM app.approvals WHERE case_id=%s ORDER BY created_at", (case_id,)
            ),
            "operator_events": await self.db.all(
                "SELECT * FROM app.operator_events WHERE case_id=%s ORDER BY created_at", (case_id,)
            ),
            "orders": await self.db.all(
                "SELECT * FROM app.orders WHERE id=%s", (case["order_id"],)
            ),
            "runs": await self.db.all(
                "SELECT id,status,cancelled,created_at FROM app.runs WHERE case_id=%s ORDER BY created_at",
                (case_id,),
            ),
            "events": await self.db.all(
                "SELECT * FROM app.events WHERE case_id=%s ORDER BY sequence", (case_id,)
            ),
            "inbox": await self.db.all(
                "SELECT * FROM app.inbox WHERE case_id=%s ORDER BY delivered_at", (case_id,)
            ),
        }

    async def order_history(self, actor: Actor, order_id: str) -> list[dict]:
        await self.order(actor, order_id)
        rows = await self.db.all(
            "SELECT e.kind,e.note,e.created_at,c.id case_id,c.process FROM app.operator_events e JOIN app.cases c ON c.id=e.case_id WHERE c.order_id=%s AND c.organization_id=%s ORDER BY e.created_at DESC LIMIT 100",
            (order_id, actor.organization_id),
        )
        return list(reversed(rows))

    async def save_clarification(self, case_id: str, process: str, proposal: dict, exhausted: bool):
        await self.db.execute(
            "UPDATE app.cases SET clarification_count=CASE WHEN process=%s THEN clarification_count+1 ELSE 1 END,process=%s,status=%s,proposal=%s,proposal_hash=%s,version=version+1,deadline=%s WHERE id=%s",
            (
                process,
                process,
                "pending_operator" if exhausted else "awaiting_information",
                jsonb(proposal),
                digest(proposal),
                self.clock.now() + timedelta(hours=self.wait_hours),
                case_id,
            ),
        )

    async def enqueue(self, actor: Actor, case_id: str, run_id: str, data: dict) -> dict:
        await self.case(actor, case_id)
        async with self.db.pool.connection() as conn, conn.transaction():
            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,2))",
                (actor.organization_id + ":queue",),
            )
            await conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (case_id,))
            return await self._enqueue_locked(conn, actor, case_id, run_id, data)

    async def _enqueue_locked(self, conn, actor: Actor, case_id: str, run_id: str, data: dict):
        # Caller holds organization queue and case advisory locks until commit.
        prior = await (
            await conn.execute("SELECT * FROM app.runs WHERE id=%s", (run_id,))
        ).fetchone()
        if prior:
            if str(prior["case_id"]) != case_id or prior["input_hash"] != digest(data):
                raise DomainError(
                    "Identificador de evento reutilizado con otro contenido.",
                    "idempotency_conflict",
                    409,
                )
            return prior
        active = await (
            await conn.execute(
                "SELECT id FROM app.runs WHERE case_id=%s AND status IN ('queued','running')",
                (case_id,),
            )
        ).fetchone()
        if active:
            raise DomainError("Hay una ejecución activa. Recupere su estado.", "run_active", 409)
        pending = await (
            await conn.execute(
                "SELECT count(*) n FROM app.runs WHERE organization_id=%s AND status IN ('queued','running')",
                (actor.organization_id,),
            )
        ).fetchone()
        if pending["n"] >= self.max_pending_runs:
            raise DomainError(
                "La cola alcanzó su límite local. Espere a que termine una ejecución.",
                "queue_limit",
                429,
            )
        row = await (
            await conn.execute(
                "INSERT INTO app.runs(id,case_id,organization_id,input,input_hash) VALUES(%s,%s,%s,%s,%s) RETURNING *",
                (run_id, case_id, actor.organization_id, jsonb(data), digest(data)),
            )
        ).fetchone()
        if data.get("text") or data.get("attachment_ids"):
            await conn.execute(
                "INSERT INTO app.messages(id,case_id,role,content,metadata) VALUES(%s,%s,'user',%s,%s) ON CONFLICT DO NOTHING",
                (
                    run_id,
                    case_id,
                    data.get("text", ""),
                    jsonb({"attachment_ids": data.get("attachment_ids", [])}),
                ),
            )
        return row

    async def stage_proposal(
        self,
        actor: Actor,
        case_id: str,
        run_id: str,
        process: str,
        proposal: dict,
        role: str,
        kind: str,
        expected_case_version: int | None = None,
        observed_order_version: int | None = None,
    ) -> dict:
        aid = str(uuid5(UUID(run_id), "approval:" + kind))
        async with self.db.pool.connection() as conn, conn.transaction():
            case = await (
                await conn.execute("SELECT * FROM app.cases WHERE id=%s FOR UPDATE", (case_id,))
            ).fetchone()
            actor.scope(case["organization_id"], case["client_id"])
            prior = await (
                await conn.execute("SELECT * FROM app.approvals WHERE id=%s", (aid,))
            ).fetchone()
            if prior:
                if str(prior["case_id"]) != case_id or prior["proposal_hash"] != digest(proposal):
                    raise DomainError(
                        "Identificador de propuesta reutilizado.", "idempotency_conflict", 409
                    )
                return prior
            if expected_case_version is not None and case["version"] != expected_case_version:
                raise DomainError(
                    "La evidencia del caso cambió durante el análisis. Recalcule la propuesta.",
                    "stale_case",
                    409,
                )
            if case["order_id"] and observed_order_version is not None:
                order = await (
                    await conn.execute(
                        "SELECT * FROM app.orders WHERE id=%s FOR SHARE", (case["order_id"],)
                    )
                ).fetchone()
                actor.scope(order["organization_id"], order["client_id"])
                if order["version"] != observed_order_version:
                    raise DomainError(
                        "El pedido cambió durante el análisis. Recalcule.", "stale_order", 409
                    )
                case["order_version"] = observed_order_version
                await conn.execute(
                    "UPDATE app.cases SET order_version=%s WHERE id=%s",
                    (observed_order_version, case_id),
                )
            await conn.execute(
                "UPDATE app.approvals SET status='stale' WHERE case_id=%s AND status='pending'",
                (case_id,),
            )
            phash = digest(proposal)
            version = case["version"] + 1
            await conn.execute(
                "UPDATE app.cases SET clarification_count=CASE WHEN process=%s THEN clarification_count ELSE 0 END,proposal=%s,proposal_hash=%s,version=%s,process=%s,status='awaiting_review',deadline=%s,updated_at=now() WHERE id=%s",
                (
                    process,
                    jsonb(proposal),
                    phash,
                    version,
                    process,
                    self.clock.now() + timedelta(hours=self.wait_hours),
                    case_id,
                ),
            )
            return await (
                await conn.execute(
                    "INSERT INTO app.approvals(id,case_id,organization_id,proposal_hash,case_version,order_version,policy_version,required_role,kind) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *",
                    (
                        aid,
                        case_id,
                        actor.organization_id,
                        phash,
                        version,
                        case["order_version"],
                        self.policy_version,
                        role,
                        kind,
                    ),
                )
            ).fetchone()

    async def resolve_approval(
        self,
        actor: Actor,
        case_id: str,
        approval_id: str,
        decision_id: str,
        decision: dict,
        *,
        enqueue_run: bool = False,
    ) -> dict:
        if decision.get("action") not in {"approve", "reject", "correct"} or set(
            decision.get("selection", {})
        ) - {"option_id"}:
            raise DomainError("Decisión o selección fuera del contrato.", "invalid_decision", 422)
        async with self.db.pool.connection() as conn, conn.transaction():
            if enqueue_run:
                # Same lock order as enqueue: queue -> case -> row locks.
                await conn.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s,2))",
                    (actor.organization_id + ":queue",),
                )
                await conn.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (case_id,)
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
            approval = await (
                await conn.execute(
                    "SELECT * FROM app.approvals WHERE id=%s AND case_id=%s FOR UPDATE",
                    (approval_id, case_id),
                )
            ).fetchone()
            if not approval:
                raise DomainError("Revisión no disponible.", "not_found", 404)
            actor.require(approval["required_role"])
            if approval["decision_id"]:
                if str(approval["decision_id"]) == decision_id and approval["decision"] == decision:
                    if enqueue_run:
                        return await self._enqueue_approval_resume(
                            conn, actor, case_id, approval_id, decision_id, decision
                        )
                    return approval
                raise DomainError("La revisión ya fue resuelta.", "approval_resolved", 409)
            if decision.get("action") == "approve" and (
                approval["status"] != "pending"
                or approval["proposal_hash"] != case["proposal_hash"]
                or approval["case_version"] != case["version"]
                or approval["order_version"] != case["order_version"]
                or approval["policy_version"] != self.policy_version
                or case["deadline"]
                and case["deadline"] <= self.clock.now()
            ):
                raise DomainError(
                    "La propuesta venció o cambió. Solicite una nueva revisión.",
                    "stale_approval",
                    409,
                )
            if (
                decision.get("proposal_hash") != approval["proposal_hash"]
                or decision.get("case_version") != approval["case_version"]
            ):
                raise DomainError("Hash o versión de revisión obsoletos.", "stale_approval", 409)
            commercial_review = (
                case["process"] == "P1"
                and case["proposal"].get("action") == "register"
                and approval["kind"] == "human"
                and approval["required_role"] == "admin"
            )
            if decision["action"] == "approve" and commercial_review:
                validate_commercial_exception(decision.get("commercial_exception"))
            elif decision.get("commercial_exception") is not None:
                raise DomainError(
                    "La autorización comercial no corresponde a esta revisión.",
                    "invalid_decision",
                    422,
                )
            status = "approved" if decision["action"] == "approve" else "rejected"
            resolved = await (
                await conn.execute(
                    "UPDATE app.approvals SET status=%s,actor_id=%s,decision_id=%s,decision=%s,decided_at=now() WHERE id=%s RETURNING *",
                    (status, actor.id, decision_id, jsonb(decision), approval_id),
                )
            ).fetchone()
            if enqueue_run:
                # Queue/ID conflicts roll the approval update back as well.
                return await self._enqueue_approval_resume(
                    conn, actor, case_id, approval_id, decision_id, decision
                )
            return resolved

    async def _enqueue_approval_resume(
        self, conn, actor: Actor, case_id: str, approval_id: str, decision_id: str, decision: dict
    ) -> dict:
        run = await self._enqueue_locked(
            conn, actor, case_id, decision_id, {"resume": True, "approval_id": approval_id}
        )
        await conn.execute(
            "INSERT INTO app.events(event_id,run_id,case_id,type,payload) VALUES(%s,%s,%s,'approval.resolved',%s) ON CONFLICT(event_id) DO NOTHING",
            (
                str(uuid5(UUID(decision_id), "approval.resolved:" + approval_id)),
                decision_id,
                case_id,
                jsonb(
                    {"approval_id": approval_id, "action": decision["action"], "actor": actor.id}
                ),
            ),
        )
        return run

    async def slots(self, actor: Actor, order_id: str) -> list[dict]:
        order = await self.order(actor, order_id)
        slots = await self.db.all(
            "SELECT *, (day > %s::date + 2) AS outside_policy FROM app.slots WHERE organization_id=%s AND day >= %s AND reserved<capacity AND (day>%s OR (CASE WHEN shift='manana' THEN %s::time ELSE %s::time END)>%s::time) ORDER BY day,shift LIMIT 8",
            (
                order["fields"]["fecha_recojo"],
                actor.organization_id,
                self.clock.now().date(),
                self.clock.now().date(),
                self.shift_times["manana"],
                self.shift_times["tarde"],
                self.clock.now().time().replace(tzinfo=None),
            ),
        )
        from datetime import datetime

        now = self.clock.now()
        return [
            slot
            for slot in slots
            if datetime.combine(
                slot["day"],
                self.shift_times[slot["shift"]],
                tzinfo=now.tzinfo,
            )
            > now
        ]

    async def order(self, actor: Actor, order_id: str) -> dict:
        row = await self.db.one(
            "SELECT * FROM app.orders WHERE id=%s AND organization_id=%s",
            (order_id, actor.organization_id),
        )
        if not row:
            raise DomainError("Pedido no disponible.", "not_found", 404)
        actor.scope(row["organization_id"], row["client_id"])
        return row

    async def operator_event(
        self,
        actor: Actor,
        case_id: str,
        event_id: str,
        kind: str,
        note: str,
        attachment_id: str | None,
    ) -> dict:
        case = await self.case(actor, case_id)
        actor.require(
            "quality"
            if kind in {"inspection", "reprocess"}
            or kind == "conformity"
            and case["process"] == "P3"
            else "logistics"
            if kind in {"pickup", "delivery"}
            else "admin"
        )
        if attachment_id and not await self.db.one(
            "SELECT id FROM app.attachments WHERE id=%s AND case_id=%s", (attachment_id, case_id)
        ):
            raise DomainError("Adjunto ajeno al caso.", "not_found", 404)
        async with self.db.pool.connection() as conn, conn.transaction():
            case = await (
                await conn.execute(
                    "SELECT * FROM app.cases WHERE id=%s AND organization_id=%s FOR UPDATE",
                    (case_id, actor.organization_id),
                )
            ).fetchone()
            if not case:
                raise DomainError("Caso no disponible.", "not_found", 404)
            actor.scope(case["organization_id"], case["client_id"])
            actor.require(
                "quality"
                if kind in {"inspection", "reprocess"}
                or kind == "conformity"
                and case["process"] == "P3"
                else "logistics"
                if kind in {"pickup", "delivery"}
                else "admin"
            )
            prior = await (
                await conn.execute("SELECT * FROM app.operator_events WHERE id=%s", (event_id,))
            ).fetchone()
            if prior:
                if (
                    str(prior["case_id"]) != case_id
                    or prior["kind"] != kind
                    or prior["note"] != note
                    or str(prior["attachment_id"] or "") != (attachment_id or "")
                ):
                    raise DomainError("Evento reutilizado.", "idempotency_conflict", 409)
                return prior
            if kind == "reprocess":
                count = await (
                    await conn.execute(
                        "SELECT count(*) n FROM app.operator_events WHERE case_id=%s AND kind='reprocess'",
                        (case_id,),
                    )
                ).fetchone()
                approved = await (
                    await conn.execute(
                        "SELECT id FROM app.approvals WHERE case_id=%s AND status='approved' AND kind='human' AND proposal_hash=%s",
                        (case_id, case["proposal_hash"]),
                    )
                ).fetchone()
                executed = await (
                    await conn.execute(
                        "SELECT command_id FROM app.command_ledger WHERE case_id=%s AND result->>'status'='awaiting_physical_reprocess'",
                        (case_id,),
                    )
                ).fetchone()
                if (
                    count["n"] >= self.max_reprocesses
                    or not approved
                    or not executed
                    or (case.get("proposal") or {}).get("action") != "reprocess"
                ):
                    raise DomainError(
                        "Reproceso requiere autorización vigente y admite un ciclo piloto.",
                        "policy",
                        409,
                    )
            if case["process"] == "P4" and kind in {
                "customer_acceptance",
                "fulfillment",
                "conformity",
            }:
                plan = await (
                    await conn.execute(
                        "SELECT command_id FROM app.command_ledger WHERE case_id=%s AND result->>'status'='awaiting_customer_acceptance_and_fulfillment'",
                        (case_id,),
                    )
                ).fetchone()
                if not plan:
                    raise DomainError(
                        "Se requiere plan autorizado antes de registrar aceptación o cumplimiento.",
                        "human_required",
                        409,
                    )
            row = await (
                await conn.execute(
                    "INSERT INTO app.operator_events(id,case_id,organization_id,actor_id,kind,note,attachment_id) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING *",
                    (event_id, case_id, actor.organization_id, actor.id, kind, note, attachment_id),
                )
            ).fetchone()
            # New evidence changes a proposal's meaning: approvals become stale.
            if case["order_id"]:
                order = await (
                    await conn.execute(
                        "UPDATE app.orders SET version=version+1 WHERE id=%s AND organization_id=%s RETURNING version",
                        (case["order_id"], actor.organization_id),
                    )
                ).fetchone()
                if not order:
                    raise DomainError("Pedido fuera del contexto.", "forbidden", 403)
                await conn.execute(
                    "UPDATE app.cases SET order_version=%s WHERE id=%s", (order["version"], case_id)
                )
            await conn.execute(
                "UPDATE app.cases SET version=version+1,updated_at=now() WHERE id=%s", (case_id,)
            )
            await conn.execute(
                "UPDATE app.approvals SET status='stale' WHERE case_id=%s AND status='pending'",
                (case_id,),
            )
            return row
