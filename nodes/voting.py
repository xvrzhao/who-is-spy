from langchain.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage, ToolCall, ToolCallChunk
from langgraph.types import Command, Send
from langgraph.graph import StateGraph, START, END

from state import State, GameStage, StateRecord, VoteRecord, PlayerIdentity, VotingState
from prompts import get_rules_prompt, get_statement_prompt, get_voting_prompt
from llm import llm


def voting_start_node(state: State):
    print(f"> 第 {state['game_round']} 轮投票开始...")
    return Command(update={
        "history": [f"------ 第 {state['game_round']} 轮投票阶段：------"]
    }, goto=[
        Send("voting_player_node", {
            "game_round": state["game_round"],
            "player_total": state["player_total"],
            "player": player, 
            "word": state["word_spy"] if player is state["spy_id"] else state["word_civilian"],
            "history": state['history']
        }) for player in state["present_players"]
    ])


def voting_player_node(state: VotingState):
    player = state["player"]
    word = state["word"]
    history = state['history']

    print(f"> 玩家 {player} 开始投票...")

    msg = llm.invoke([
        SystemMessage(content=get_rules_prompt(state["player_total"])),
        HumanMessage(content=get_voting_prompt(player, state["word"], state["history"])),
    ])

    reason, decision = [part.strip() for part in msg.content.split("+++")]
    decision = int(decision)

    print(f"> 玩家 {player} 投票理由：{reason}")
    print(f"> 玩家 {player} 投票结果：玩家 {decision}")

    return Command(update={
        "history": [f"玩家 {player} 投给：玩家 {decision}"],
        "vote_history": [VoteRecord(
            game_round=state["game_round"], 
            voter_id=player, 
            decision=decision,
            reason=reason,
        )]
    }, goto="voting_end_node")


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
            "history": [f"第 {round} 轮投票结果：平票，无人淘汰！游戏进入下一轮..."],
            "game_round": round + 1,
            "stage": GameStage.STATEMENT,
        }, goto="statement_node")

    eliminated_player = eliminated_players[0]
    present_players = [player for player in state["present_players"] if player != eliminated_player]

    # 卧底被淘汰，平民胜利
    if eliminated_player == state['spy_id']:
        print(f"> 第 {round} 轮投票结果：玩家 {eliminated_player}（卧底）被淘汰，平民胜利！")
        return Command(update={
            "history": [f"第 {round} 轮投票结果：玩家 {eliminated_player} （卧底）被淘汰，平民胜利！"],
            "present_players": present_players,
            "winner": PlayerIdentity.CIVILIAN,
        }, goto=END)

    if len(present_players) == 2:
        # 剩余两人，卧底胜利
        print(f"> 第 {round} 轮投票结果：玩家 {eliminated_player}（平民）被淘汰，剩余两人，卧底（玩家 {state['spy_id']}）胜利！")
        return Command(update={
            "history": [f"第 {round} 轮投票结果：玩家 {eliminated_player} （平民）被淘汰，剩余两人，卧底（玩家 {state['spy_id']}）胜利！"],
            "present_players": present_players,
            "winner": PlayerIdentity.SPY,
        }, goto=END)
    else:
        # 游戏继续，进入下一轮
        print(f"> 第 {round} 轮投票结果：玩家 {eliminated_player}（平民）被淘汰！游戏进入下一轮...")
        return Command(update={
            "history": [f"第 {round} 轮投票结果：玩家 {eliminated_player} （平民）被淘汰！游戏进入下一轮..."],
            "present_players": present_players,
            "game_round": round + 1,
            "stage": GameStage.STATEMENT,
        }, goto="statement_node")
