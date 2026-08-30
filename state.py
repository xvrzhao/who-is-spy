from enum import Enum
from typing import TypedDict, Annotated
from operator import add
from dataclasses import dataclass, field, asdict

class GameStage(str, Enum):
    """游戏阶段"""
    STATEMENT = "statement"
    VOTING = "voting"

class PlayerIdentity(str, Enum):
    """玩家身份"""
    CIVILIAN = "civilian"
    SPY = "spy"

class StateRecord(TypedDict):
    """发言记录"""
    game_round: int
    player_id: int
    content: str
    thinking: str

class VoteRecord(TypedDict):
    """投票记录"""
    game_round: int
    voter_id: int
    decision: int # 投给谁
    reason: str
    
@dataclass
class RawRecord:
    content: str
    is_private: bool = False
    read_only_by: int | None = None

class State(TypedDict):
    player_total: int       # 玩家数量
    real_player_id: int     # 真实玩家ID，其余为Agent
    spy_id: int             # 卧底ID
    word_civilian: str      # 平民词
    word_spy: str           # 卧底词

    game_round: int             # 当前游戏轮数
    stage: GameStage            # 游戏阶段：发言、投票
    present_players: list[int]  # 尚未被淘汰的玩家
    active_player_ptr: int      # 当前该哪个玩家发言，值为 present_players 数组的索引

    state_history: Annotated[list[StateRecord], add]    # 发言历史记录
    vote_history: Annotated[list[VoteRecord], add]      # 投票历史记录
    history: Annotated[list[RawRecord], add]            # 游戏过程文本记录，用于给 llm 决策

    winner: PlayerIdentity | None # 最后胜利的身份
