from enum import Enum
from typing import TypedDict, Annotated
from operator import add

class GameStage(str, Enum):
    STATEMENT = "statement"
    VOTING = "voting"

class PlayerIdentity(str, Enum):
    CIVILIAN = "civilian"
    SPY = "spy"

class StateRecord(TypedDict):
    game_round: int
    player_id: int
    content: str
    thinking: str

class VoteRecord(TypedDict):
    game_round: int
    voter_id: int
    decision: int # 投给谁
    reason: str

class State(TypedDict):
    player_total: int     # 玩家数量
    spy_id: int        # 卧底id
    word_civilian: str  # 平民词
    word_spy: str       # 卧底词

    game_round: int     # 当前游戏轮数
    stage: GameStage # 游戏阶段：发言、投票
    present_players: list[int] # 尚未被淘汰的玩家
    active_player_ptr: int  # 当前该哪个玩家发言，值为 present_players 数组的索引

    state_history: Annotated[list[StateRecord], add] # 发言历史记录
    vote_history: Annotated[list[VoteRecord], add] # 投票历史记录
    history: Annotated[list[str], add] # 发言投票文本记录，用于 llm 决策

    winner: PlayerIdentity | None

class VotingState(TypedDict):
    game_round: int
    player_total: int
    player: int
    word: str
    history: Annotated[list[str], add]