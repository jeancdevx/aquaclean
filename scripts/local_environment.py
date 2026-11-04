"""Host-only local Docker connection helpers. Never print the resulting environment."""

import os
import subprocess

import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from aquaclean.config import Settings


def local_env(test=False):
    env = os.environ.copy()
    settings = Settings()
    params = conninfo_to_dict(settings.database_url.get_secret_value())
    if params.get("host") == "db":
        params["host"] = subprocess.check_output(
            [
                "docker",
                "inspect",
                "-f",
                "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
                "aquaclean-db-1",
            ],
            text=True,
        ).strip()
    env["DATABASE_URL"] = make_conninfo(**params)
    if test:
        params["dbname"] = "aquaclean_semana10_test"
        env["TEST_DATABASE_URL"] = make_conninfo(**params)
        # The suite's explicit URL safety guard expects a URL ending in _test.
        from urllib.parse import quote

        env["TEST_DATABASE_URL"] = (
            "postgresql://"
            + quote(params.get("user", "aquaclean"), safe="")
            + ":"
            + quote(params.get("password", ""), safe="")
            + "@"
            + params["host"]
            + ":"
            + params.get("port", "5432")
            + "/"
            + params["dbname"]
        )
        with psycopg.connect(env["DATABASE_URL"], autocommit=True) as conn:
            if not conn.execute(
                "SELECT 1 FROM pg_database WHERE datname=%s", (params["dbname"],)
            ).fetchone():
                conn.execute(
                    psycopg.sql.SQL("CREATE DATABASE {}").format(
                        psycopg.sql.Identifier(params["dbname"])
                    )
                )
    env["LANGSMITH_TRACING"] = "false"
    return env
