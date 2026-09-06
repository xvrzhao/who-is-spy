from logging import getLogger

import redis.asyncio as aioredis

from src.core.config import settings

logger = getLogger(__name__)

class RedisProvider:
    def __init__(self):
        self.pool_db0: aioredis.ConnectionPool | None = None
        # self.pool_db1: aioredis.ConnectionPool | None = None

    def init(self):
        self.pool_db0 = self._create_conn_pool(db=0, max_conn=20)
        # self.pool_db1 = self._create_conn_pool(db=1, max_conn=20)
        logger.info("redis init: complete")

    @staticmethod
    def _create_conn_pool(*, db: int, max_conn: int):
        return aioredis.ConnectionPool(
            max_connections=max_conn,
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=db,
            password=settings.REDIS_PSW or None,
            decode_responses=True,
        )

    async def shutdown(self):
        if self.pool_db0 is not None:
            await self.pool_db0.disconnect()
        # if self.pool_db1 is not None:
        #     await self.pool_db1.disconnect()
        logger.info("redis shutdown: complete")

    async def get_redis_db0(self):
        """FastAPI Dependency"""
        async with aioredis.Redis(connection_pool=self.pool_db0) as client:
            yield client


redis_provider = RedisProvider()


