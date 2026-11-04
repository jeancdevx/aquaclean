from pathlib import Path
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from aquaclean.config import Settings


class Database:
    def __init__(self, settings: Settings):
        self.pool = AsyncConnectionPool(
            settings.database_url.get_secret_value(),
            open=False,
            min_size=1,
            max_size=12,
            kwargs={"row_factory": dict_row, "autocommit": True},
        )

    async def open(self):
        await self.pool.open(wait=True)

    async def close(self):
        await self.pool.close()

    async def all(self, sql: str, args: tuple = ()) -> list[dict[str, Any]]:
        async with self.pool.connection() as conn:
            return list(await (await conn.execute(sql, args)).fetchall())

    async def one(self, sql: str, args: tuple = ()) -> dict[str, Any] | None:
        rows = await self.all(sql, args)
        return rows[0] if rows else None

    async def execute(self, sql: str, args: tuple = ()):
        async with self.pool.connection() as conn:
            await conn.execute(sql, args)

    async def migrate(self):
        async with self.pool.connection() as conn, conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(918201)")
            schema = await (
                await conn.execute("SELECT to_regclass('app.schema_version') AS table_name")
            ).fetchone()
            versions = set()
            if schema["table_name"]:
                versions = {
                    r["version"]
                    for r in await (
                        await conn.execute("SELECT version FROM app.schema_version")
                    ).fetchall()
                }
            for path in sorted(Path("migrations").glob("*.sql")):
                number = int(path.name.split("_")[0])
                if number in versions:
                    continue
                await conn.execute(path.read_text())
                await conn.execute(
                    "INSERT INTO app.schema_version VALUES(%s) ON CONFLICT DO NOTHING", (number,)
                )


def jsonb(value: Any) -> Jsonb:
    import json

    return Jsonb(value, dumps=lambda obj: json.dumps(obj, default=str))
