from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.core.graph import graph_provider
from .schemas import StartRequest, ResumeRequest


router = APIRouter(prefix="/games", tags=["game"])

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform", # 防止 nginx 缓存导致前端收不到实时数据
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}

@router.post("", summary="游戏开局")
async def start_game(req: StartRequest):
    game_id = uuid4().hex
    stream = graph_provider.stream_start(game_id, req.player_total)

    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


def _is_int_str(s: str) -> bool:
    return s.strip().lstrip("-").isdigit()


RESUME_VALIDATORS = {
    "need_statement": lambda v: isinstance(v, str) and bool(v.strip()),
    "need_vote": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "need_exchange": lambda v: isinstance(v, str) and "||" in v and _is_int_str(v.rsplit("|", 1)[1]),
    "speech_playback_done": lambda v: v is True,
}


@router.post("/{game_id}/resume", summary="中断继续")
async def resume_game(game_id: str, req: ResumeRequest):
    graph = graph_provider.graph
    state = await graph.aget_state(graph_provider.get_config(game_id))

    interrupt: dict = state.interrupts[0].value
    validator = RESUME_VALIDATORS.get(interrupt["type"])
    if validator and not validator(req.resume):
        raise HTTPException(422, f"invalid resume payload for {interrupt["type"]}: {req.resume!r}")

    stream = graph_provider.stream_resume(game_id, req.resume)
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
