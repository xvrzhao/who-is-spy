from typing import Any

from pydantic import BaseModel


class StartRequest(BaseModel):
    player_total: int = 6

class ResumeRequest(BaseModel):
    """
    resume 取值由 pending interrupt 的类型决定：
    - need_statement: 字符串（真人发言）
    - need_vote: 数字（玩家 ID，0 表示弃票）
    - need_exchange: 字符串，格式 "发言内容||下一位玩家ID"
    - speech_playback_done: true（客户端语音播放完成确认）
    """
    resume: Any
