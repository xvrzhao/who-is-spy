from enum import Enum
from typing import TypedDict, Annotated, Literal
from operator import add

GameStage = Literal["statement", "voting"]
PlayerIdentity = Literal["civilian", "spy"]

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
    decision: int # 投给谁，0 表示弃票
    reason: str
    
class RawRecord(TypedDict):
    """游戏过程文本记录"""
    content: str
    is_private: bool            # 是否为仅单一玩家可见的私密记录
    read_only_by: int | None    # 私密记录对哪个玩家可见

class State(TypedDict):
    player_total: int       # 玩家数量
    real_player_id: int     # 真实玩家ID，其余为Agent
    spy_id: int             # 卧底ID
    word_civilian: str      # 平民词
    word_spy: str           # 卧底词

    game_round: int                         # 当前游戏轮数
    stage: GameStage                        # 游戏阶段：statement 发言、voting 投票
    present_players: list[int]              # 尚未被淘汰的玩家
    active_player_ptr: int                  # 当前该哪个玩家发言，值为 present_players 数组的索引

    exchange_next: int                          # 赛后交流阶段下一个发言的玩家ID
    exchange_round: int                         # 交流轮次（有多少次玩家发言）
    exchange_histoty: Annotated[list[str], add] # 交流阶段玩家聊天记录

    state_history: Annotated[list[StateRecord], add]    # 发言历史记录
    vote_history: Annotated[list[VoteRecord], add]      # 投票历史记录
    history: Annotated[list[RawRecord], add]            # 游戏过程文本记录，用于给 llm 决策

    winner: PlayerIdentity | None                       # 最后胜利的身份：civilian / spy
