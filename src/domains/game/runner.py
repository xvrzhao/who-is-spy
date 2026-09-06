import asyncio
from logging import getLogger
from typing import Any, AsyncIterator

from langgraph.types import Command
from langgraph.graph.state import CompiledStateGraph

from src.utils.sse import sse_event
from src.game.events import Event
from src.game.state import State

logger = getLogger(__name__)

# 编译图：lifespan 中注入（带 PG saver 的图必须在 saver 就绪后编译），endpoints 运行时从这里取
graph: CompiledStateGraph | None = None

def init(compiled: CompiledStateGraph | None):
    global graph
    graph = compiled

# 运行注册表：同一局同时只允许一个活跃 run（重复请求由端点回 409 拒绝而非排队——
# 排队的 SSE 在持锁期间零输出必然超时，且滞留的 resume 值会错位消费）。
# 互斥已下沉 PG（game_threads 表，见 runs.py），跨进程/多副本生效
from .runs import try_begin, end_run, is_running # noqa: F401 再导出保持 endpoints 调用点不变

def config_for(game_id: str) -> dict:
    return {"configurable": {"thread_id": game_id}}

def _game_frame(ev: Event) -> str:
    return sse_event(ev.type, {
        "event": ev.type,
        "payload": ev.model_dump(mode="json", exclude={"type"}),
    })

async def run_segment(game_id: str, graph_input) -> AsyncIterator[str]:
    """跑一段 astream 直到 interrupt / END，逐帧 yield SSE。调用方负责 try_begin / end_run"""

    try:
        async for chunk in graph.astream(graph_input, config_for(game_id), stream_mode=["custom"], version="v2"):
            if chunk.get("type") != "custom":
                continue
            event = chunk["data"]
            if isinstance(event, Event):
                yield _game_frame(event)

        state = await graph.aget_state(config_for(game_id))
        if state.interrupts:
            yield sse_event("interrupt", {"event": "interrupt", "payload": dict(state.interrupts[0].value)})
        else:
            yield sse_event("finished", {"event": "finished", "payload": {}})
    except asyncio.CancelledError:
        raise # 客户端断开时必须透传取消（吞掉会导致生成器无法关闭）；运行标记在外层 finally 释放
    except Exception as e:
        logger.exception("game %s run failed", game_id)
        yield sse_event("error", {"event": "error", "payload": {"type": type(e).__name__, "message": str(e)}})

async def _release(game_id: str):
    """尽力归还 run 权：可能运行在取消展开（客户端断开）路径上，失败只告警，
    不能让清理异常掩盖原始异常/取消（except Exception 不吞 CancelledError）"""
    try:
        await end_run(game_id)
    except Exception:
        logger.warning("game %s end_run failed", game_id, exc_info=True)

async def stream_start(game_id: str, player_total: int) -> AsyncIterator[str]:
    try:
        yield sse_event("game_started", {
            "event": "game_started",
            "payload": {"game_id": game_id, "player_total": player_total},
        })
        async for frame in run_segment(game_id, State(player_total=player_total)):
            yield frame
    finally:
        await _release(game_id)

async def stream_resume(game_id: str, resume_value: Any) -> AsyncIterator[str]:
    try:
        async for frame in run_segment(game_id, Command(resume=resume_value)):
            yield frame
    finally:
        await _release(game_id)

async def stream_continue(game_id: str) -> AsyncIterator[str]:
    """断线续驱：astream(None) 从最后完成的节点边界继续（被取消的超步会重放）"""
    try:
        async for frame in run_segment(game_id, None):
            yield frame
    finally:
        await _release(game_id)
