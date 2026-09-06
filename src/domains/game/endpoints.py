from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.utils.sse import sse_event
from . import runner
from .schemas import StartRequest, ResumeRequest

router = APIRouter(prefix="/games", tags=["game"])

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform", # 防止反向代理（如 nginx）缓冲响应，导致前端收不到实时数据
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}

def _is_int_str(s: str) -> bool:
    return s.strip().lstrip("-").isdigit()

# 按 interrupt 类型预校验 resume 值：节点内 int()/rsplit 的解析错误发生在 interrupt 消费之后，
# 会把 thread 留在诡异状态，所以在入口就把明显坏值挡掉
_RESUME_VALIDATORS = {
    "need_statement": lambda v: isinstance(v, str) and bool(v.strip()),
    "need_vote": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "need_exchange": lambda v: isinstance(v, str) and "|" in v and _is_int_str(v.rsplit("|", 1)[1]),
    "speech_playback_done": lambda v: v is True,
}


@router.post("", summary="开局（SSE）")
async def start_game(req: StartRequest):
    if runner.graph is None:
        raise HTTPException(503, "graph not initialized")

    game_id = uuid4().hex # 即 langgraph thread_id
    await runner.try_begin(game_id) # 新 uuid 必然成功

    return StreamingResponse(
        runner.stream_start(game_id, req.player_total),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post("/{game_id}/resume", summary="应答 interrupt / 断线续跑（SSE）")
async def resume_game(game_id: str, req: ResumeRequest):
    if runner.graph is None:
        raise HTTPException(503, "graph not initialized")

    snap = await runner.graph.aget_state(runner.config_for(game_id))

    if not snap.values and not snap.next:
        raise HTTPException(404, "unknown game_id")
    if snap.next == ():
        raise HTTPException(409, "game already finished")

    if req.resume is None:
        # 省略 resume：
        #   有 pending interrupt -> 幂等重发 interrupt 帧（断线重连后找回现场，不跑图）
        #   无 interrupt 但有 next -> astream(None) 从最后完成的节点边界续跑（SSE 中途断掉的场景）
        if snap.interrupts:
            async def replay():
                yield sse_event("interrupt", {"event": "interrupt", "payload": dict(snap.interrupts[0].value)})
            return StreamingResponse(replay(), media_type="text/event-stream", headers=SSE_HEADERS)

        if not await runner.try_begin(game_id):
            raise HTTPException(409, "a run is already active for this game")
        return StreamingResponse(
            runner.stream_continue(game_id),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    # 显式 resume 值：必须没有并发 run、有 pending interrupt、且类型匹配
    if await runner.is_running(game_id):
        raise HTTPException(409, "a run is already active for this game")

    if not snap.interrupts:
        raise HTTPException(409, "no pending interrupt (run interrupted mid-stream? omit resume to continue)")

    interrupt_value = snap.interrupts[0].value
    interrupt_type = interrupt_value.get("interrupt") if isinstance(interrupt_value, dict) else None
    validator = _RESUME_VALIDATORS.get(interrupt_type)
    if validator and not validator(req.resume):
        raise HTTPException(422, f"invalid resume payload for {interrupt_type}: {req.resume!r}")

    if not await runner.try_begin(game_id):
        raise HTTPException(409, "a run is already active for this game")

    return StreamingResponse(
        runner.stream_resume(game_id, req.resume),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.get("/{game_id}/status", summary="状态查询（断线重连判断）")
async def game_status(game_id: str):
    if runner.graph is None:
        raise HTTPException(503, "graph not initialized")

    snap = await runner.graph.aget_state(runner.config_for(game_id))

    if not snap.values and not snap.next:
        raise HTTPException(404, "unknown game_id")

    values = snap.values
    if await runner.is_running(game_id):
        status = "running"
    elif snap.interrupts:
        status = "waiting_input"
    elif snap.next:
        status = "continuable"
    else:
        status = "finished"

    return {
        "game_id": game_id,
        "status": status,
        "interrupt": dict(snap.interrupts[0].value) if snap.interrupts else None,
        # 白名单字段：state.values 含 spy_id / word_* / state_history（私密 thinking 直接提词），严禁整包返回
        "state": {k: values.get(k) for k in (
            "player_total", "real_player_id", "game_round", "stage",
            "present_players", "winner",
        )},
    }
