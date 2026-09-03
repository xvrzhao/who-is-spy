from typing import TypedDict

from langchain.messages import HumanMessage, SystemMessage
from langgraph.types import Command, Send, interrupt
from langgraph.graph import END
from pydantic import BaseModel, Field

from state import State, VoteRecord, RawRecord
from prompts import get_rules_prompt, get_voting_prompt
from llm import llm
from events import emit, VoteStart, VotePlayerStart, VotePlayerEnd, VoteEnd

class Vote(BaseModel):
    """玩家投票，包括投票理由和投票决定"""
    reason: str = Field(description="玩家投票前的分析和理由")
    decision: int = Field(description="玩家投给的玩家数字ID")

vote_llm = llm.with_structured_output(Vote, method="function_calling").with_retry()


class VotingState(TypedDict):
    game_round: int
    player_total: int
    player: int # 投票人ID
    word: str   # 投票人手持的词语
    history: list[RawRecord]
    real_player_id: int # 本局游戏的真实玩家ID


def voting_start_node(state: State) -> State:
    emit(VoteStart(game_round=state["game_round"]))

    return {
        "history": [RawRecord(content=f"------ 第 {state['game_round']} 轮投票阶段 ------", is_private=False, read_only_by=None)],
    }


def fanout_to_voting_players(state: State):
    return [Send("voting_player_node", VotingState(
        game_round=state["game_round"],
        player_total=state["player_total"],
        player=player,
        word=state["word_spy"] if player == state["spy_id"] else state["word_civilian"],
        history=state['history'],
        real_player_id=state["real_player_id"]
    )) for player in state["present_players"]]


async def voting_player_node(state: VotingState) -> State:
    if state["player"] == state["real_player_id"]:
        # 真实用户投票
        real_player_decision = interrupt({"interrupt": "need_vote"})
        real_player_decision = int(real_player_decision)
        append_vote_records = [VoteRecord(game_round=state["game_round"], voter_id=state["real_player_id"], decision=real_player_decision, reason="")]
        append_raw_records = [RawRecord(content=f"玩家 {state['real_player_id']} 投给：玩家 {real_player_decision}", is_private=False, read_only_by=None)]
    else:
        # Agent 用户投票
        emit(VotePlayerStart(player_id=state["player"]))

        vote: Vote = await vote_llm.ainvoke([
            SystemMessage(content=get_rules_prompt(state["player_total"])),
            HumanMessage(content=get_voting_prompt(state["player"], state["word"], state["history"])),
        ])
        reason, decision = vote.reason, vote.decision

        emit(VotePlayerEnd(player_id=state["player"]))

        append_vote_records = [
            VoteRecord(game_round=state["game_round"], voter_id=state["player"], decision=decision, reason=reason),
        ]
        append_raw_records = [
            RawRecord(content=f"玩家 {state['player']} 内心独白：{reason}", is_private=True, read_only_by=state["player"]),
            RawRecord(content=f"玩家 {state['player']} 投给：玩家 {decision}", is_private=False, read_only_by=None),
        ]

    return {
        "vote_history": append_vote_records,
        "history": append_raw_records,
    }


def voting_end_node(state: State) -> State:
    round = state['game_round']
    votes = state['vote_history']
    votes = [vote for vote in votes if vote["game_round"] == round]

    vote_count = {}
    vote_collect: dict[int, list[int]] = {}

    for vote in votes:
        decision = vote["decision"]
        if decision not in vote_count:
            vote_count[decision] = 0
        if decision not in vote_collect:
            vote_collect[decision] = []
        vote_count[decision] += 1
        vote_collect[decision].append(vote["voter_id"])

    max_votes = max(vote_count.values())
    eliminated_players = [player for player, count in vote_count.items() if count == max_votes]


    # 平票，无人淘汰，游戏进入下一轮
    if len(eliminated_players) > 1:

        emit(VoteEnd(
            game_round=round, 
            vote_collect=vote_collect,
            present_players=state["present_players"],
        ))

        return {
            "history": [RawRecord(content=f"第 {round} 轮投票结果：平票，无人淘汰！游戏进入下一轮...", is_private=False, read_only_by=None)],
            "game_round": round + 1,
            "stage": "statement",
        }


    eliminated_player = eliminated_players[0]
    present_players = [player for player in state["present_players"] if player != eliminated_player]


    # 卧底被淘汰，平民胜利
    if eliminated_player == state['spy_id']:

        emit(VoteEnd(
            game_round=round, 
            vote_collect=vote_collect, 
            eliminated_player=eliminated_player, 
            eliminated_player_identity="spy",
            present_players=present_players,
        ))

        return {
            "history": [RawRecord(content=f"第 {round} 轮投票结果：玩家 {eliminated_player} （卧底）被淘汰！平民胜利！", is_private=False, read_only_by=None)],
            "present_players": present_players,
            "winner": "civilian",
        }


    if len(present_players) > 2:

        # 游戏继续，进入下一轮
        emit(VoteEnd(
            game_round=round,
            vote_collect=vote_collect,
            eliminated_player=eliminated_player,
            eliminated_player_identity="civilian",
            present_players=present_players,
        ))

        return {
            "history": [RawRecord(content=f"第 {round} 轮投票结果：玩家 {eliminated_player} （平民）被淘汰！游戏进入下一轮...", is_private=False, read_only_by=None)],
            "present_players": present_players,
            "game_round": round + 1,
            "stage": "statement",
        }
    
    else:

        # 剩余两人，卧底胜利
        emit(VoteEnd(
            game_round=round,
            vote_collect=vote_collect,
            eliminated_player=eliminated_player,
            eliminated_player_identity="civilian",
            present_players=present_players,
        ))

        return {
            "history": [RawRecord(content=f"第 {round} 轮投票结果：玩家 {eliminated_player} （平民）被淘汰！剩余两人，卧底（玩家 {state['spy_id']}）胜利！", is_private=False, read_only_by=None)],
            "present_players": present_players,
            "winner": "spy",
        }


def route_after_voting(state: State) -> str:
    if state["stage"] == "statement":
        return "next_round"
    else:
        return "game_over"