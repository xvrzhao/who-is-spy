import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.logging import setup_logging
from src.core.config import settings
from src.core.middlewares.trace import TraceMiddleware
from src.core.db import db_provider
from src.core.redis import redis_provider
from src.core.checkpointer import checkpointer_provider
from src.game.graph import build_graph
from src.domains.game import runner, runs
from src.domains import router

setup_logging()
logger = logging.getLogger(__name__)
logger.info("application environment variables: %s", settings.model_dump_json())

@asynccontextmanager
async def lifespan(app: FastAPI):
    db_provider.init(settings.postgres_async_uri)          # pg engine（预留，惰性连接）
    redis_provider.init()                                   # redis 池（预留，惰性连接）
    await checkpointer_provider.init()                      # psycopg 连接池 + checkpoints 建表
    await runs.init()                                       # game_threads 建表（run 互斥，幂等；复用上面的池）
    runner.init(build_graph(checkpointer_provider.saver))   # 用 PG saver 编译游戏图并注入 runner
    yield
    runner.init(None)                                       # 逆序关闭
    await checkpointer_provider.shutdown()
    await redis_provider.shutdown()
    await db_provider.shutdown()

app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TraceMiddleware)

app.include_router(router)
