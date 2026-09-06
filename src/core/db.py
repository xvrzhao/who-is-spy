from logging import getLogger

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

logger = getLogger(__name__)


class Base(DeclarativeBase):
    pass


class DatabaseProvider:
    def __init__(self):
        self.engine = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def init(self, async_uri: str):
        self.engine = create_async_engine(async_uri, echo=False, pool_size=10, max_overflow=20)
        self._session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        logger.info("db engine init: complete")

    async def shutdown(self):
        if self.engine:
            await self.engine.dispose()
        logger.info("db engine shutdown: complete")

    async def get_db_session(self):
        """FastAPI Dependency"""
        async with self._session_factory() as session:
            yield session


db_provider = DatabaseProvider()
