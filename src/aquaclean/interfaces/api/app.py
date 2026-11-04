import asyncio
import json
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI, File, Query, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from aquaclean.bootstrap import bootstrap
from aquaclean.config import Settings
from aquaclean.domain.entities import Actor
from aquaclean.domain.errors import DomainError
from aquaclean.interfaces.api.auth import actor, same_origin
from aquaclean.interfaces.api.limits import UploadLimitMiddleware
from aquaclean.interfaces.api.retail_routes import router as retail_router
from aquaclean.interfaces.api.schemas import (
    NewCase,
    NewRun,
    ObservationEdit,
    OperatorEvent,
    OrderLink,
    ReviewDecision,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with bootstrap() as runtime:
        app.state.runtime = runtime
        yield


app = FastAPI(
    title="Aqua Clean local",
    version="0.1.0",
    lifespan=lifespan,
    description="Demo sintética P1–P4. Actor fijo demo_operator; no acredita identidad real.",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url=None,
)
app.include_router(retail_router)
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver", "api"]
)
app.add_middleware(UploadLimitMiddleware, max_bytes=Settings().max_upload_mb * 1024 * 1024 + 65536)
app.middleware("http")(same_origin)


@app.exception_handler(DomainError)
async def domain_error(request: Request, exc: DomainError):
    return JSONResponse({"detail": str(exc), "code": exc.code}, status_code=exc.status)


def runtime(request: Request):
    return request.app.state.runtime


@app.get("/health/live")
async def live():
    return {"status": "alive"}


@app.get("/health/ready")
async def ready(request: Request):
    rt = runtime(request)
    try:
        row = await rt.repo.db.one(
            "SELECT (SELECT max(version) FROM app.schema_version) version, EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector') vector, to_regclass('checkpoints.checkpoints') IS NOT NULL checkpoints"
        )
        if not row or row["version"] < 6 or not row["vector"] or not row["checkpoints"]:
            raise ValueError("schema")
        return {
            "status": "ready",
            "database": True,
            "vector_extension": True,
            "checkpoints": True,
            "ai_configured": rt.settings.ai_available,
            "provider_verified": False,
        }
    except Exception:
        return JSONResponse(
            {"status": "not_ready", "detail": "Base o migraciones no disponibles."}, status_code=503
        )


@app.get("/api/session")
async def session(request: Request, current: Actor = Depends(actor)):
    rt = runtime(request)
    customers = await rt.repo.db.all(
        "SELECT id,name,blocked,synthetic FROM app.customers WHERE organization_id=%s AND (%s::text IS NULL OR id=%s) ORDER BY id",
        (current.organization_id, current.client_id, current.client_id),
    )
    return {
        "actor": {
            "id": current.id,
            "organization_id": current.organization_id,
            "roles": sorted(current.roles),
        },
        "auth_mode": rt.settings.auth_mode,
        "synthetic": True,
        "timezone": "America/Lima",
        "ai": {
            "configured": rt.settings.ai_available,
            "verified": False,
            "model": rt.settings.gemini_chat_model,
            "embeddings_model": rt.settings.gemini_embedding_model,
            "status": "Configurado; ejecutar smoke-local para verificar"
            if rt.settings.ai_available
            else "IA y embeddings no disponibles: falta GEMINI_API_KEY",
        },
        "customers": customers,
        "limits": {
            "upload_mb": rt.settings.max_upload_mb,
            "attachments": rt.settings.max_attachments,
        },
    }


@app.get("/api/cases")
async def cases(
    request: Request, q: str = Query(default="", max_length=100), current: Actor = Depends(actor)
):
    return await runtime(request).repo.db.all(
        "SELECT * FROM app.cases c WHERE organization_id=%s AND (%s::text IS NULL OR client_id=%s) AND (c.title ILIKE %s OR EXISTS(SELECT 1 FROM app.orders o WHERE o.id=c.order_id AND o.number ILIKE %s)) ORDER BY updated_at DESC LIMIT 100",
        (
            current.organization_id,
            current.client_id,
            current.client_id,
            "%" + q + "%",
            "%" + q + "%",
        ),
    )


@app.post("/api/cases", status_code=201)
async def create_case(data: NewCase, request: Request, current: Actor = Depends(actor)):
    return await runtime(request).repo.create_case(current, data.title, data.client_id)


@app.get("/api/cases/{case_id}")
async def case_snapshot(case_id: UUID, request: Request, current: Actor = Depends(actor)):
    return await runtime(request).repo.snapshot(current, str(case_id))


@app.post("/api/cases/{case_id}/runs", status_code=202)
async def start_run(case_id: UUID, data: NewRun, request: Request, current: Actor = Depends(actor)):
    rt, cid = runtime(request), str(case_id)
    if not data.text.strip() and not data.attachment_ids:
        raise DomainError("Escriba un mensaje o adjunte evidencia.")
    if len(data.attachment_ids) > rt.settings.max_attachments:
        raise DomainError("Demasiados adjuntos.")
    for aid in data.attachment_ids:
        await rt.media.get(current, cid, str(aid))
    pending = await rt.repo.db.one(
        "SELECT id,status FROM app.approvals WHERE case_id=%s ORDER BY created_at DESC LIMIT 1",
        (cid,),
    )
    if pending and pending["status"] in {"pending", "stale", "expired"}:
        raise DomainError(
            "Use Confirmar, Rechazar o Corregir en la propuesta pendiente antes de continuar.",
            "review_pending",
            409,
        )
    return await rt.repo.enqueue(
        current,
        cid,
        str(data.run_id),
        {"text": data.text, "attachment_ids": [str(a) for a in data.attachment_ids]},
    )


@app.post("/api/cases/{case_id}/approvals/{approval_id}", status_code=202)
async def review(
    case_id: UUID,
    approval_id: UUID,
    data: ReviewDecision,
    request: Request,
    current: Actor = Depends(actor),
):
    rt, cid = runtime(request), str(case_id)
    decision = data.model_dump(exclude={"decision_id"}, exclude_none=True)
    return await rt.repo.resolve_approval(
        current,
        cid,
        str(approval_id),
        str(data.decision_id),
        decision,
        enqueue_run=True,
    )


@app.get("/api/runs/{run_id}/events")
async def events(
    run_id: UUID,
    request: Request,
    after: int = Query(default=0, ge=0),
    current: Actor = Depends(actor),
):
    rt, rid = runtime(request), str(run_id)
    run = await rt.repo.db.one(
        "SELECT * FROM app.runs WHERE id=%s AND organization_id=%s", (rid, current.organization_id)
    )
    if not run:
        raise DomainError("Ejecución no disponible.", "not_found", 404)
    await rt.repo.case(current, str(run["case_id"]))
    try:
        cursor = max(after, int(request.headers.get("last-event-id", "0")))
    except ValueError:
        raise DomainError("Cursor de eventos inválido.") from None

    async def stream():
        nonlocal cursor
        while not await request.is_disconnected():
            rows = await rt.repo.db.all(
                "SELECT * FROM app.events WHERE run_id=%s AND sequence>%s ORDER BY sequence LIMIT 200",
                (rid, cursor),
            )
            for row in rows:
                cursor = row["sequence"]
                yield f"id: {cursor}\ndata: {json.dumps(jsonable_encoder(row), ensure_ascii=False)}\n\n"
            status = await rt.repo.db.one("SELECT status FROM app.runs WHERE id=%s", (rid,))
            if status["status"] not in {"queued", "running"}:
                # Read once more after observing terminal status (commit/event race).
                rest = await rt.repo.db.all(
                    "SELECT * FROM app.events WHERE run_id=%s AND sequence>%s ORDER BY sequence",
                    (rid, cursor),
                )
                for row in rest:
                    yield f"id: {row['sequence']}\ndata: {json.dumps(jsonable_encoder(row), ensure_ascii=False)}\n\n"
                yield "event: end\ndata: {}\n\n"
                break
            yield ": keepalive\n\n"
            await asyncio.sleep(0.4)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/runs/{run_id}/cancel")
async def cancel(run_id: UUID, request: Request, current: Actor = Depends(actor)):
    rt = runtime(request)
    run = await rt.repo.db.one(
        "SELECT * FROM app.runs WHERE id=%s AND organization_id=%s",
        (str(run_id), current.organization_id),
    )
    if not run:
        raise DomainError("Ejecución no disponible.", "not_found", 404)
    await rt.repo.case(current, str(run["case_id"]))
    await rt.repo.db.execute(
        "UPDATE app.runs SET cancelled=true WHERE id=%s AND status IN ('queued','running')",
        (str(run_id),),
    )
    return {"status": "stop_requested", "detail": "Los efectos confirmados permanecen registrados."}


@app.post("/api/cases/{case_id}/uploads", status_code=201)
async def upload(
    case_id: UUID, request: Request, file: UploadFile = File(...), current: Actor = Depends(actor)
):
    rt = runtime(request)
    data = await file.read(rt.settings.max_upload_mb * 1024 * 1024 + 1)
    row = await rt.media.save(current, str(case_id), file.filename or "archivo", data)
    return {k: v for k, v in row.items() if k != "storage_key"}


@app.get("/api/cases/{case_id}/attachments/{attachment_id}")
async def attachment(
    case_id: UUID, attachment_id: UUID, request: Request, current: Actor = Depends(actor)
):
    rt = runtime(request)
    row = await rt.media.get(current, str(case_id), str(attachment_id))
    return FileResponse(
        rt.media.path(row),
        media_type=row["mime"],
        filename=row["filename"],
        content_disposition_type="inline",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox",
            "Cache-Control": "private, no-store",
        },
    )


@app.patch("/api/cases/{case_id}/attachments/{attachment_id}")
async def edit_observation(
    case_id: UUID,
    attachment_id: UUID,
    data: ObservationEdit,
    request: Request,
    current: Actor = Depends(actor),
):
    rt = runtime(request)
    await rt.media.get(current, str(case_id), str(attachment_id))
    async with rt.repo.db.pool.connection() as conn, conn.transaction():
        row = await (
            await conn.execute(
                "UPDATE app.attachments SET observation=%s,observation_version=observation_version+1 WHERE id=%s AND observation_version=%s RETURNING id",
                (data.observation, str(attachment_id), data.expected_version),
            )
        ).fetchone()
        if not row:
            raise DomainError(
                "Observación modificada; recargue antes de corregir.", "stale_observation", 409
            )
        await conn.execute("UPDATE app.cases SET version=version+1 WHERE id=%s", (str(case_id),))
        await conn.execute(
            "UPDATE app.approvals SET status='stale' WHERE case_id=%s AND status='pending'",
            (str(case_id),),
        )
    return {"status": "updated", "requires_confirmation": True}


@app.post("/api/cases/{case_id}/operator-events", status_code=201)
async def operator_event(
    case_id: UUID, data: OperatorEvent, request: Request, current: Actor = Depends(actor)
):
    return await runtime(request).repo.operator_event(
        current,
        str(case_id),
        str(data.event_id),
        data.kind,
        data.note,
        str(data.attachment_id) if data.attachment_id else None,
    )


@app.post("/api/cases/{case_id}/order-link")
async def link_order(
    case_id: UUID, data: OrderLink, request: Request, current: Actor = Depends(actor)
):
    rt, cid = runtime(request), str(case_id)
    current.require("attention")
    await rt.repo.case(current, cid)
    order = await rt.repo.db.one(
        "SELECT id FROM app.orders WHERE number=%s AND organization_id=%s",
        (data.order_number, current.organization_id),
    )
    if not order:
        raise DomainError("Pedido no disponible.", "not_found", 404)
    order = await rt.repo.order(current, str(order["id"]))
    async with rt.repo.db.pool.connection() as conn, conn.transaction():
        case = await (
            await conn.execute("SELECT * FROM app.cases WHERE id=%s FOR UPDATE", (cid,))
        ).fetchone()
        if (
            case["order_id"]
            and case["order_id"] != order["id"]
            or case["version"] != data.expected_version
        ):
            raise DomainError("El caso ya está vinculado o su versión cambió.", "stale_case", 409)
        if case["client_id"] and case["client_id"] != order["client_id"]:
            raise DomainError("El pedido pertenece a otro cliente.", "forbidden", 403)
        active = await (
            await conn.execute(
                "SELECT id FROM app.runs WHERE case_id=%s AND status IN ('queued','running') UNION ALL SELECT id FROM app.approvals WHERE case_id=%s AND status='pending'",
                (cid, cid),
            )
        ).fetchone()
        if active:
            raise DomainError(
                "Resuelva la ejecución o revisión pendiente antes de vincular.", "run_active", 409
            )
        await conn.execute(
            "UPDATE app.cases SET order_id=%s,client_id=%s,order_version=%s,version=version+1,proposal=NULL,proposal_hash=NULL WHERE id=%s",
            (order["id"], order["client_id"], order["version"], cid),
        )
    return {"status": "linked", "order_id": str(order["id"]), "order_number": data.order_number}


@app.get("/api/knowledge")
async def knowledge(
    request: Request,
    q: str = Query(min_length=2, max_length=1000),
    case_id: UUID | None = None,
    current: Actor = Depends(actor),
):
    rt = runtime(request)
    case = await rt.repo.case(current, str(case_id)) if case_id else None
    return await rt.knowledge.search(current, q, case["client_id"] if case else None)


@app.get("/api/history")
async def history(
    request: Request,
    q: str = Query(default="Samsung", max_length=200),
    current: Actor = Depends(actor),
):
    from aquaclean.infrastructure.knowledge.public_history import search_history

    current.require("attention")
    return await search_history(runtime(request).repo.db, q)


@app.get("/api/data-summary")
async def data_summary(request: Request, current: Actor = Depends(actor)):
    db = runtime(request).repo.db
    return {
        "synthetic": await db.one(
            "SELECT (SELECT count(*) FROM app.customers WHERE organization_id=%s) customers,(SELECT count(*) FROM app.orders WHERE organization_id=%s) orders,(SELECT count(*) FROM app.cases WHERE organization_id=%s) cases",
            (current.organization_id, current.organization_id, current.organization_id),
        ),
        "external_public": await db.one(
            "SELECT count(*) records,min(event_date) first_date,max(event_date) last_date FROM reference.recalls"
        ),
        "notice": "Los datos operativos son sintéticos. Los registros CPSC son referencias públicas externas, no hechos de Aqua Clean.",
    }


# Explicit mount only for built assets; API 404s never fall back to index.html.
static_root = Settings().static_root
if (static_root / "_astro").exists():
    app.mount("/_astro", StaticFiles(directory=static_root / "_astro"), name="assets")
if (static_root / "fonts").exists():
    app.mount("/fonts", StaticFiles(directory=static_root / "fonts"), name="fonts")


@app.get("/", include_in_schema=False)
async def index():
    if not (static_root / "index.html").exists():
        return JSONResponse(
            {
                "detail": "Compile web con pnpm install --frozen-lockfile y pnpm build, o use Docker."
            },
            status_code=503,
        )
    return FileResponse(static_root / "index.html")


@app.get("/favicon.svg", include_in_schema=False)
async def favicon():
    return FileResponse(static_root / "favicon.svg", media_type="image/svg+xml")
