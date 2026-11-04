from psycopg import sql


async def grant_runtime_role(db, password):
    """Owner-only migration operation. Runtime processes cannot create roles or schemas."""
    async with db.pool.connection() as conn, conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock(918203)")
        exists = await (
            await conn.execute("SELECT 1 FROM pg_roles WHERE rolname='aquaclean_runtime'")
        ).fetchone()
        if not exists:
            await conn.execute(
                sql.SQL(
                    "CREATE ROLE aquaclean_runtime LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION"
                ).format(sql.Literal(password))
            )
        else:
            await conn.execute(
                sql.SQL(
                    "ALTER ROLE aquaclean_runtime PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION"
                ).format(sql.Literal(password))
            )
        for schema in ["app", "checkpoints", "reference"]:
            await conn.execute(
                sql.SQL("GRANT USAGE ON SCHEMA {} TO aquaclean_runtime").format(
                    sql.Identifier(schema)
                )
            )
            await conn.execute(
                sql.SQL(
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {} TO aquaclean_runtime"
                ).format(sql.Identifier(schema))
            )
            await conn.execute(
                sql.SQL(
                    "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {} TO aquaclean_runtime"
                ).format(sql.Identifier(schema))
            )
        await conn.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        await conn.execute(
            "REVOKE INSERT,UPDATE,DELETE ON app.schema_version FROM aquaclean_runtime"
        )
