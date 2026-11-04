from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from aquaclean.config import Settings


@asynccontextmanager
async def checkpointer(settings: Settings, setup: bool = False):
    async with await AsyncConnection.connect(
        settings.database_url.get_secret_value(),
        autocommit=True,
        prepare_threshold=0,
        row_factory=dict_row,
        options="-c search_path=checkpoints,public",
    ) as conn:
        saver = AsyncPostgresSaver(conn)
        if setup:
            await saver.setup()
        yield saver
