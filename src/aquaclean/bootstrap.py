from contextlib import asynccontextmanager

from aquaclean.application.command_executor import CommandExecutor
from aquaclean.config import Settings
from aquaclean.domain.entities import DEMO_ACTOR, LimaClock
from aquaclean.graphs.main import GraphRuntime
from aquaclean.infrastructure.knowledge.retrieval import KnowledgeRepository
from aquaclean.infrastructure.llm.embeddings import GeminiEmbeddings
from aquaclean.infrastructure.llm.provider import GeminiProvider
from aquaclean.infrastructure.media.storage import MediaStorage
from aquaclean.infrastructure.persistence.commands import CommandRepository
from aquaclean.infrastructure.persistence.database import Database
from aquaclean.infrastructure.persistence.repositories import Repository


@asynccontextmanager
async def bootstrap(settings: Settings | None = None):
    settings = settings or Settings()
    if settings.auth_mode != "demo_local":
        raise RuntimeError(
            "Solo está implementado AUTH_MODE=demo_local. El perfil autenticado requiere otro adaptador."
        )
    db = Database(settings)
    await db.open()
    clock = LimaClock()
    shift_times = {
        "manana": settings.pilot_morning_dispatch,
        "tarde": settings.pilot_afternoon_dispatch,
    }
    repo = Repository(
        db,
        clock,
        settings.wait_hours,
        settings.max_pending_runs,
        settings.policy_version,
        settings.max_reprocesses,
        shift_times,
    )
    provider = GeminiProvider(settings)
    runtime = GraphRuntime(
        settings,
        DEMO_ACTOR,
        clock,
        repo,
        provider,
        KnowledgeRepository(db, GeminiEmbeddings(provider), clock),
        MediaStorage(repo, settings),
        CommandExecutor(
            CommandRepository(
                db,
                clock,
                settings.policy_version,
                settings.max_bags,
                settings.max_pickup_days,
                settings.max_reprocesses,
                shift_times,
            )
        ),
    )
    try:
        yield runtime
    finally:
        if provider.client:
            await provider.client.aio.aclose()
            provider.client.close()
        await db.close()
