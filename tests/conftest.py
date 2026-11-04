import os
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from pydantic import SecretStr

from aquaclean.application.command_executor import CommandExecutor
from aquaclean.config import Settings
from aquaclean.domain.entities import DEMO_ACTOR, ORG
from aquaclean.graphs.main import GraphRuntime
from aquaclean.infrastructure.knowledge.retrieval import KnowledgeRepository
from aquaclean.infrastructure.media.storage import MediaStorage
from aquaclean.infrastructure.persistence.commands import CommandRepository
from aquaclean.infrastructure.persistence.database import Database
from aquaclean.infrastructure.persistence.repositories import Repository
from tests.fakes import FakeEmbeddings, FakeProvider


class FrozenClock:
    def now(self):
        return datetime(2026, 10, 16, 20, 30, tzinfo=ZoneInfo("America/Lima"))


@pytest.fixture
def clock():
    return FrozenClock()


@pytest.fixture
async def rt(tmp_path, clock):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Requiere TEST_DATABASE_URL explícita de una base terminada en _test")
    if not url.split("?")[0].endswith("_test"):
        pytest.fail("La base de pruebas debe terminar en _test; no se utiliza la base demo")
    settings = Settings(
        database_url=SecretStr(url),
        gemini_api_key=SecretStr(""),
        media_root=tmp_path,
        max_model_calls=24,
    )
    db = Database(settings)
    await db.open()
    await db.migrate()
    # This fixture has already enforced the explicit _test URL. Retain all data,
    # but cancel unfinished synthetic jobs left by previous test invocations.
    # No runtime worker consumes this isolated test database.
    await db.execute(
        "UPDATE app.runs SET status='cancelled',cancelled=true,finished_at=now() WHERE organization_id=%s AND status IN ('queued','running')",
        (ORG,),
    )
    from aquaclean.infrastructure.persistence.checkpointer import checkpointer

    async with checkpointer(settings, setup=True):
        pass
    repo = Repository(db, clock)
    for cid, blocked in [("CLI-0001", False), ("CLI-0002", True)]:
        await db.execute(
            "INSERT INTO app.customers(organization_id,id,name,email,address,blocked) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (
                ORG,
                cid,
                "Cliente test sintético",
                "demo@example.invalid",
                "Dirección test sintética",
                blocked,
            ),
        )
    provider = FakeProvider(clock)
    knowledge = KnowledgeRepository(db, FakeEmbeddings(), clock)
    await knowledge.ingest_demo()
    runtime = GraphRuntime(
        settings,
        DEMO_ACTOR,
        clock,
        repo,
        provider,
        knowledge,
        MediaStorage(repo, settings),
        CommandExecutor(CommandRepository(db, clock)),
    )
    try:
        yield runtime
    finally:
        await db.execute(
            "UPDATE app.runs SET status='cancelled',cancelled=true,finished_at=now() WHERE organization_id=%s AND status IN ('queued','running')",
            (ORG,),
        )
        await db.close()


@pytest.fixture
async def case(rt):
    return await rt.repo.create_case(rt.actor, "Caso de prueba " + str(uuid4())[:8], "CLI-0001")
