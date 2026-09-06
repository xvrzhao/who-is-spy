from typing import Any

from pydantic import BaseModel, Field

class StartRequest(BaseModel):
    """开一局游戏"""
    player_total: int = Field(default=6, ge=3, le=12)

class ResumeRequest(BaseModel):
    """应答 interrupt 或断线续驱

    resume 取值由 pending interrupt 类型决定：
    - need_statement: 字符串（真人发言）
    - need_vote: 数字（玩家 ID，0 表示弃票）
    - need_exchange: 字符串，格式 "发言内容|下一位玩家ID"
    - speech_playback_done: true（客户端语音播放完成确认）
    省略 resume：有 pending interrupt 时幂等重发 interrupt 帧（断线重连）；无 interrupt 时从 checkpoint 续跑
    """
    resume: Any | None = None
