from logging import getLogger

from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.core.config import settings

logger = getLogger(__name__)

class CheckpointerProvider:

    def __init__(self):
        self.pool: AsyncConnectionPool | None = None
        self.saver: AsyncPostgresSaver | None = None

    async def init(self):
        self.pool = AsyncConnectionPool(
            conninfo=settings.postgres_uri,
            max_size=settings.PG_CONN_MAX,
            kwargs={"autocommit": True},
            open=False,
        )
        await self.pool.open()

        self.saver = AsyncPostgresSaver(self.pool)
        await self.saver.setup() # 幂等建 checkpoints 相关表

        logger.info("checkpointer init: postgres checkpointer setup complete")

    async def shutdown(self):
        if self.pool is not None:
            await self.pool.close()
            
        logger.info("checkpointer shutdown: postgres connection pool closed")


checkpointer_provider = CheckpointerProvider()
