"""Read-only delivery audit. Checks the configured key without printing or storing it."""

import asyncio
import json
from pathlib import Path

from aquaclean.config import Settings
from aquaclean.domain.entities import LimaClock
from aquaclean.infrastructure.persistence.database import Database


async def main():
    settings = Settings()
    key = settings.gemini_api_key.get_secret_value().encode()
    if not key:
        raise RuntimeError(
            "Se requiere una clave configurada para verificar su ausencia de artefactos; no se imprime."
        )
    checked = 0
    matches = []
    for root in [
        "src",
        "scripts",
        "tests",
        "docs",
        "knowledge",
        "reference_data",
        "web/src",
        "web/public",
        "web/dist",
        "artifacts",
    ]:
        for path in Path(root).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                checked += 1
                if key in path.read_bytes():
                    matches.append(str(path))
    db = Database(settings)
    await db.open()
    try:
        rows_checked = 0
        database_matches = 0
        for query in [
            "SELECT content FROM app.messages",
            "SELECT payload FROM app.events",
            "SELECT checkpoint FROM checkpoints.checkpoints",
            "SELECT blob FROM checkpoints.checkpoint_blobs",
        ]:
            for row in await db.all(query):
                rows_checked += 1
                for value in row.values():
                    raw = (
                        value
                        if isinstance(value, bytes)
                        else json.dumps(value, default=str).encode()
                    )
                    database_matches += int(key in raw)
        report = {
            "checked_at": LimaClock().now().isoformat(),
            "secret_scan": {
                "files_checked": checked,
                "matching_files": matches,
                "database_rows_checked": rows_checked,
                "database_matches": database_matches,
            },
            "runtime_role": await db.one(
                "SELECT rolname,rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname='aquaclean_runtime'"
            ),
            "schema": await db.one("SELECT max(version) version FROM app.schema_version"),
            "synthetic_history": await db.one(
                "SELECT count(*) cases,min(created_at) first_created,max(updated_at) last_updated FROM app.cases WHERE data_origin='synthetic_history_v1'"
            ),
            "public_history": await db.one(
                "SELECT count(*) records,min(event_date) first_date,max(event_date) last_date FROM reference.recalls"
            ),
            "vector_store": await db.all(
                "SELECT k.model,k.dimension,count(c.id) chunks,min(vector_dims(c.embedding)) min_dim,max(vector_dims(c.embedding)) max_dim FROM app.collections k LEFT JOIN app.chunks c ON c.collection_id=k.id GROUP BY k.id"
            ),
            "capacity_violations": await db.one(
                "SELECT count(*) n FROM app.slots WHERE reserved<0 OR reserved>capacity"
            ),
            "chronology_violations": await db.one(
                "SELECT count(*) n FROM app.operator_events e JOIN app.cases c ON c.id=e.case_id WHERE c.data_origin='synthetic_history_v1' AND (e.created_at<c.created_at OR e.created_at>c.updated_at)"
            ),
        }
        assert not matches and not database_matches, (
            "Clave encontrada en artefactos: revisar sin imprimirla"
        )
        assert report["capacity_violations"]["n"] == 0 and report["chronology_violations"]["n"] == 0
        Path("docs/validacion/security-and-data-audit.json").write_text(
            json.dumps(report, ensure_ascii=False, default=str, indent=2) + "\n"
        )
        print(json.dumps(report, ensure_ascii=False, default=str, indent=2))
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
