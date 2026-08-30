from dataclasses import dataclass

from langchain.messages import HumanMessage, SystemMessage
from langgraph.types import Command, Send
from langgraph.graph import END
from pydantic import BaseModel, Field

from state import State, GameStage, VoteRecord, PlayerIdentity, RawRecord
from prompts import get_rules_prompt, get_voting_prompt
from llm import llm

class Vote(BaseModel):
    """玩家投票，包括投票理由和投票决定"""
    reason: str = Field(description="玩家投票前的分析和理由")
    decision: int = Field(description="玩家投给的玩家数字ID")

vote_llm = llm.with_structured_output(Vote, method="function_calling").with_retry()

@dataclass
class VotingState:
    game_round: int
    player_total: int
    player: int
    word: str
    history: list[RawRecord]

def voting_start_node(state: State):
    print(f"> 第 {state['game_round']} 轮投票开始...")
    return Command(update={
        "history": [RawRecord(content=f"------ 第 {state['game_round']} 轮投票阶段：------")],
    }, goto=[Send(
        "voting_player_node",
        VotingState(
            game_round=state["game_round"],
            player_total=state["player_total"],
            player=player,
            word=state["word_spy"] if player == state["spy_id"] else state["word_civilian"],
            history=state['history'],
        )) for player in state["present_players"]
    ])


async def voting_player_node(state: VotingState):
    print(f"> 玩家 {state.player} 开始投票...")

    vote: Vote = await vote_llm.ainvoke([
        SystemMessage(content=get_rules_prompt(state.player_total)),
        HumanMessage(content=get_voting_prompt(state.player, state.word, state.history)),
    ])

    reason, decision = vote.reason, vote.decision

    print(f"> 玩家 {state.player} 投票理由：{reason}")
    print(f"> 玩家 {state.player} 投票结果：玩家 {decision}")

    return {
        "history": [
            RawRecord(is_private=True, read_only_by=state.player, content=f"玩家 {state.player} 内心独白：{reason}"),
            RawRecord(content=f"玩家 {state.player} 投给：玩家 {decision}"),
        ],
        "vote_history": [VoteRecord(
            game_round=state.game_round, 
            voter_id=state.player, 
            decision=decision,
            reason=reason,
        )]
    }


def voting_end_node(state: State):
    round = state['game_round']
    votes = state['vote_history']
    votes = [vote for vote in votes if vote["game_round"] == round]

    vote_count = {}
    for vote in votes:
        decision = vote["decision"]
        if decision not in vote_count:
            vote_count[decision] = 0
        vote_count[decision] += 1

    max_votes = max(vote_count.values())
    eliminated_players = [player for player, count in vote_count.items() if count == max_votes]

    # 平票，无人淘汰，游戏进入下一轮
    if len(eliminated_players) > 1:
        print(f"> 第 {round} 轮投票结果：平票，无人淘汰！游戏进入下一轮...")
        return Command(update={
            "history": [RawRecord(content=f"第 {round} 轮投票结果：平票，无人淘汰！游戏进入下一轮...")],
            "game_round": round + 1,
            "stage": GameStage.STATEMENT,
        }, goto="statement_start_node")

    eliminated_player = eliminated_players[0]
    present_players = [player for player in state["present_players"] if player != eliminated_player]

    # 卧底被淘汰，平民胜利
    if eliminated_player == state['spy_id']:
        print(f"> 第 {round} 轮投票结果：玩家 {eliminated_player}（卧底）被淘汰，平民胜利！")
        return Command(update={
            "history": [RawRecord(content=f"第 {round} 轮投票结果：玩家 {eliminated_player} （卧底）被淘汰，平民胜利！")],
            "present_players": present_players,
            "winner": PlayerIdentity.CIVILIAN,
        }, goto=END)

    if len(present_players) > 2:
        # 游戏继续，进入下一轮
        print(f"> 第 {round} 轮投票结果：玩家 {eliminated_player}（平民）被淘汰！游戏进入下一轮...")
        return Command(update={
            "history": [RawRecord(content=f"第 {round} 轮投票结果：玩家 {eliminated_player} （平民）被淘汰！游戏进入下一轮...")],
            "present_players": present_players,
            "game_round": round + 1,
            "stage": GameStage.STATEMENT,
        }, goto="statement_start_node")
    else:
        # 剩余两人，卧底胜利
        print(f"> 第 {round} 轮投票结果：玩家 {eliminated_player}（平民）被淘汰，剩余两人，卧底（玩家 {state['spy_id']}）胜利！")
        return Command(update={
            "history": [RawRecord(content=f"第 {round} 轮投票结果：玩家 {eliminated_player} （平民）被淘汰，剩余两人，卧底（玩家 {state['spy_id']}）胜利！")],
            "present_players": present_players,
            "winner": PlayerIdentity.SPY,
        }, goto=END)