from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field
from langgraph.config import get_stream_writer
from state import PlayerIdentity


class Event(BaseModel):
    """custom stream 事件基类"""


class GameInitStart(Event):
    type: Literal["init_start"] = "init_start"


class GameInitEnd(Event):
    type: Literal["init_end"] = "init_end"
    real_player_id: int    # 下发给真实玩家的玩家ID
    real_player_word: str  # 分配给真实玩家的词


class StatementStart(Event):
    type: Literal["statement_start"] = "statement_start"
    game_round: int


class StatementPlayerStart(Event):
    type: Literal["statement_player_start"] = "statement_player_start"
    player_id: int


class StatementPlayerEnd(Event):
    type: Literal["statement_player_end"] = "statement_player_end"
    player_id: int
    statement: str


class StatementEnd(Event):
    type: Literal["statement_end"] = "statement_end"
    game_round: int


class VoteStart(Event):
    type: Literal["vote_start"] = "vote_start"
    game_round: int


class VotePlayerStart(Event):
    type: Literal["vote_player_start"] = "vote_player_start"
    player_id: int


class VotePlayerEnd(Event):
    type: Literal["vote_player_end"] = "vote_player_end"
    player_id: int


class VoteEnd(Event):
    type: Literal["vote_end"] = "vote_end"
    game_round: int
    vote_collect: dict[int, list[int]]                          # 每位玩家的得票（弃票不计入）
    abstain_voters: list[int] = []                              # 本轮弃票的玩家
    eliminated_player: int | None = None                        # 被淘汰的玩家，平票/全员弃票为 None
    eliminated_player_identity: PlayerIdentity | None = None    # 被淘汰玩家身份，平票/全员弃票为 None
    present_players: list[int]                                  # 淘汰后在场玩家 ID 列表


class GameOver(Event):
    type: Literal["game_over"] = "game_over"
    winner: PlayerIdentity
    real_player_identity: PlayerIdentity
    is_real_player_win: bool
    real_player_id: int
    spy_id: int
    word_spy: str
    word_civilian: str


class ExchangeSessionStart(Event):
    type: Literal["exchange_session_start"] = "exchange_session_start"


class ExchangeSessionPlayerStart(Event):
    type: Literal["exchange_session_player_start"] = "exchange_session_player_start"
    player_id: int


class ExchangeSessionPlayerEnd(Event):
    type: Literal["exchange_session_player_end"] = "exchange_session_player_end"
    player_id: int      # 发言玩家
    content: str        # 发言内容
    next_player_id: int # 让哪一位玩家接话


class ExchangeSessionEnd(Event):
    type: Literal["exchange_session_end"] = "exchange_session_end"


class PlayerSpeech(Event):
    """Agent 发言语音（发言/赛后交流环节）"""
    type: Literal["player_speech"] = "player_speech"
    player_id: int
    text: str                      # 字幕原文
    audio_base64: str = ""         # mp3 音频 base64
    audio_format: Literal["mp3"] = "mp3"
    audio_length_ms: int = 0       # 音频时长毫秒


def emit(event: Event) -> None:
    """在节点内调用，将事件写入 custom stream；未启用 streaming 时为 no-op"""
    get_stream_writer()(event)