from logging import getLogger

from src.core.checkpointer import checkpointer_provider

logger = getLogger(__name__)

# 幂等建表：仓库无迁移机制，对齐 saver.setup() 的做法（lifespan 里每次启动执行）
_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS game_threads (
    thread_id text PRIMARY KEY,  -- 即 langgraph thread_id（= game_id）
    status    text NOT NULL      -- running | idle
)
"""

def _pool():
    if checkpointer_provider.pool is None:
        raise RuntimeError("runs.init() 必须在 checkpointer init 之后调用")
    return checkpointer_provider.pool

async def init():
    async with _pool().connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_CREATE_TABLE)
    logger.info("runs init: game_threads table ready")

async def try_begin(game_id: str) -> bool:
    """原子认领一局的 run 权：新 thread 插入 / idle 接管刷新 / running 拒绝（False）。

    单条 upsert 完成"检查+占位"：PG 行锁保证并发认领者在锁上排队重判，
    恰有一个赢家（DO UPDATE 的 WHERE 判 false 时不更新、不进 RETURNING）。
    注意：进程 kill -9 会把行留在 running 且无人接管，只能手动置 idle（前期取舍）。"""
    async with _pool().connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO game_threads (thread_id, status)
                VALUES (%(thread_id)s, 'running')
                ON CONFLICT (thread_id) DO UPDATE SET status = 'running'
                WHERE game_threads.status <> 'running'
                RETURNING thread_id
                """,
                {"thread_id": game_id},
            )
            return await cur.fetchone() is not None

async def is_running(game_id: str) -> bool:
    async with _pool().connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM game_threads WHERE thread_id = %(thread_id)s AND status = 'running' LIMIT 1",
                {"thread_id": game_id},
            )
            return await cur.fetchone() is not None

async def end_run(game_id: str) -> None:
    async with _pool().connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE game_threads SET status = 'idle' WHERE thread_id = %(thread_id)s",
                {"thread_id": game_id},
            )
