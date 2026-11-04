import asyncio
import json
import time
from pathlib import Path

import httpx
import typer

from aquaclean.bootstrap import bootstrap
from aquaclean.domain.entities import ORG
from aquaclean.domain.errors import DomainError
from aquaclean.infrastructure.persistence.checkpointer import checkpointer

app = typer.Typer(
    pretty_exceptions_show_locals=False,
    no_args_is_help=True,
    help="Operación local reproducible. Las llamadas Gemini son explícitas.",
)


def run(coro):
    try:
        value = asyncio.run(coro)
        typer.echo(json.dumps(value, ensure_ascii=False, default=str, indent=2))
    except DomainError as exc:
        typer.echo(
            json.dumps(
                {"status": "blocked", "code": exc.code, "detail": str(exc)}, ensure_ascii=False
            )
        )
        raise typer.Exit(2) from None
    except Exception as exc:
        typer.echo(
            json.dumps(
                {
                    "status": "error",
                    "type": type(exc).__name__,
                    "detail": "Operación no completada. Compruebe conectividad, permisos y configuración; no se muestran credenciales ni respuestas privadas.",
                },
                ensure_ascii=False,
            )
        )
        raise typer.Exit(1) from None


async def migrate_async():
    async with bootstrap() as rt:
        await rt.repo.db.migrate()
        async with checkpointer(rt.settings, setup=True):
            pass
        from aquaclean.infrastructure.persistence.privileges import grant_runtime_role

        await grant_runtime_role(
            rt.repo.db, rt.settings.runtime_database_password.get_secret_value()
        )
        version = await rt.repo.db.one("SELECT max(version) version FROM app.schema_version")
        return {
            "status": "migrated",
            "version": version["version"],
            "runtime_role": "aquaclean_runtime",
        }


@app.command()
def migrate():
    run(migrate_async())


async def seed_async():
    from datetime import timedelta

    async with bootstrap() as rt:
        async with rt.repo.db.pool.connection() as conn, conn.transaction():
            for cid, name, blocked in [
                ("CLI-0001", "Hotel Bahía Demo (sintético)", False),
                ("CLI-0002", "Restaurante Puerto Demo (sintético)", True),
            ]:
                await conn.execute(
                    "INSERT INTO app.customers(organization_id,id,name,email,address,blocked) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    (
                        ORG,
                        cid,
                        name,
                        f"{cid.lower()}@example.invalid",
                        "Av. Demostración 123, Lima (dirección sintética)",
                        blocked,
                    ),
                )
            for offset in range(14):
                day = rt.clock.now().date() + timedelta(days=offset)
                for shift in ["manana", "tarde"]:
                    await conn.execute(
                        "INSERT INTO app.slots(id,organization_id,day,shift,capacity) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                        (f"DEMO-{day}-{shift}", ORG, day, shift, rt.settings.slot_capacity),
                    )
        return {
            "status": "seeded",
            "customers": 2,
            "synthetic": True,
            "note": "No se sobrescriben reservas ni datos existentes.",
        }


@app.command("seed-demo")
def seed_demo():
    run(seed_async())


@app.command("seed-history")
def seed_history(orders: int = typer.Option(3000, min=1, max=10000)):
    async def action():
        from aquaclean.infrastructure.persistence.history_seed import seed_history as seed

        async with bootstrap() as rt:
            return await seed(rt, orders)

    run(action())


@app.command("import-public-history")
def import_public_history():
    async def action():
        from aquaclean.infrastructure.knowledge.public_history import import_history

        async with bootstrap() as rt:
            return await import_history(rt.repo.db)

    run(action())


async def ingest_async():
    async with bootstrap() as rt:
        rt.provider.require()
        return await rt.knowledge.ingest_demo()


@app.command("ingest-demo")
def ingest_demo():
    run(ingest_async())


async def verify_async():
    async with bootstrap() as rt:
        extension = await rt.repo.db.one(
            "SELECT extversion FROM pg_extension WHERE extname='vector'"
        )
        rows = await rt.repo.db.all(
            "SELECT k.id,k.model,k.dimension,count(c.id) chunks,min(vector_dims(c.embedding)) min_dimension,max(vector_dims(c.embedding)) max_dimension FROM app.collections k LEFT JOIN app.chunks c ON c.collection_id=k.id GROUP BY k.id"
        )
        selected = next((c for c in rows if c["id"] == rt.knowledge.collection), None)
        if (
            not extension
            or not selected
            or not selected["chunks"]
            or selected["min_dimension"] != rt.settings.embedding_dimension
            or selected["max_dimension"] != rt.settings.embedding_dimension
        ):
            raise DomainError(
                "pgvector: "
                + str(extension)
                + "; colección configurada sin embeddings reales verificados. Ejecute ingest-demo con clave válida.",
                "vector_unverified",
                503,
            )
        sources = await rt.knowledge.search(rt.actor, "¿Qué exige una liberación de calidad?")
        if not sources:
            raise DomainError("Búsqueda sin resultados.", "vector_unverified", 503)
        return {
            "extension": extension,
            "collection": selected,
            "query_verified": True,
            "sources": [{"id": s["chunk_id"], "distance": s["distance"]} for s in sources],
        }


@app.command("verify-vector-store")
def verify_vector_store():
    run(verify_async())


async def models_async():
    async with bootstrap() as rt:
        return await rt.provider.models()


@app.command()
def models():
    run(models_async())


async def smoke_async():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        health_response = await client.get("/health/ready")
        health_response.raise_for_status()
        health = health_response.json()
        session = (await client.get("/api/session")).json()
        home = await client.get("/")
        assert home.status_code == 200 and "astro-island" in home.text
        assert session["actor"]["id"] == "demo_operator"
    async with bootstrap() as rt:
        if not rt.settings.ai_available:
            return {
                "status": "partial",
                "http": True,
                "health": health,
                "provider": "blocked_missing_GEMINI_API_KEY",
                "embeddings": "not_verified",
                "multimodal": "not_verified",
            }
        models = await rt.provider.models()
        names = {m["name"].removeprefix("models/") for m in models}
        if (
            rt.settings.gemini_chat_model not in names
            or rt.settings.gemini_embedding_model not in names
        ):
            raise DomainError(
                "Modelo configurado no disponible en el catálogo de esta cuenta.",
                "model_unavailable",
                503,
            )
        response = []
        async for token in rt.provider.stream(
            [("human", "Responde con una frase: verificación de conectividad Aqua Clean demo.")]
        ):
            response.append(token)
        vectors = await rt.knowledge.embeddings.embed(["Comprobación sintética"], "RETRIEVAL_QUERY")
        return {
            "status": "verified",
            "http": True,
            "chat_model": rt.settings.gemini_chat_model,
            "chat_response_received": bool(response),
            "embedding_dimension": len(vectors[0]),
            "multimodal": "Ejecutar RUN_REAL_PROVIDER=1 uv run pytest tests/evaluations para verificar cada modalidad",
        }


@app.command("smoke-local")
def smoke_local():
    run(smoke_async())


@app.command("worker-health")
def worker_health():
    path = Path("/tmp/aquaclean-worker-heartbeat")
    if not path.exists() or time.time() - path.stat().st_mtime > 35:
        raise typer.Exit(1)


@app.command("export-openapi")
def export_openapi(output: str = "docs/openapi.json"):
    from aquaclean.interfaces.api.app import app as api

    Path(output).write_text(json.dumps(api.openapi(), ensure_ascii=False, indent=2))
    typer.echo(output)


if __name__ == "__main__":
    app()
