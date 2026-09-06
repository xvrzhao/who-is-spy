from logging import getLogger

from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.core.config import settings

logger = getLogger(__name__)

class CheckpointerProvider:
    """Postgres checkpointer provider：langgraph 图状态的持久化（多房间 = 多 thread_id 共享同一池）"""

    def __init__(self):
        self.pool: AsyncConnectionPool | None = None
        self.saver: AsyncPostgresSaver | None = None

    async def init(self):
        self.pool = AsyncConnectionPool(
            conninfo=settings.postgres_uri, # psycopg 原生连接串（不带 +psycopg 后缀）
            max_size=settings.PG_CONN_MAX,
            kwargs={"autocommit": True}, # 必须开启，事务模式下 saver 会挂起
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
