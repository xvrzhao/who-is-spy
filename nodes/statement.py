from langchain.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage, ToolCall, ToolCallChunk
from langgraph.types import Command, Send

from state import State, GameStage, StateRecord, VoteRecord, PlayerIdentity
from prompts import get_rules_prompt, get_statement_prompt, get_voting_prompt
from llm import llm


def statement_node(state: State):
    history = []

    # 若为新一轮开始
    if state["active_player_ptr"] == 0:
        print(f"> 第 {state['game_round']} 轮发言开始...")
        history.append(f"------ 第 {state['game_round']} 轮发言阶段：------")

    present_players = state["present_players"]
    active_player_ptr = state["active_player_ptr"]
    current_player = present_players[active_player_ptr]

    current_word = state["word_spy"] if current_player is state['spy_id'] else state["word_civilian"]

    print(f"> 玩家 {current_player} 思考中...")

    msg = llm.invoke([
        SystemMessage(content=get_rules_prompt(state["player_total"])),
        HumanMessage(content=get_statement_prompt(current_player, current_word, state["history"]+history)),
    ])

    thinking, statement = [text.strip() for text in msg.content.split("+++")]

    print(f"> 玩家 {current_player} 发言思考：{thinking}")
    print(f"> 玩家 {current_player} 发言内容：{statement}")

    history.append(f"玩家 {current_player} 发言：{statement}")

    if active_player_ptr >= len(present_players) - 1:
        # 本轮所有玩家发言结束，进入投票阶段
        return Command(
            update={
                "stage": GameStage.VOTING,
                "active_player_ptr": 0,
                "state_history": [StateRecord(
                    game_round=state['game_round'], 
                    player_id=current_player, 
                    content=statement, 
                    thinking=thinking,
                )],
                "history": history,
            }, 
            goto="voting_start_node",
        )
    else:
        # 下一个玩家发言
        return Command(
            update={
                "active_player_ptr": active_player_ptr + 1,
                "state_history": [StateRecord(
                    game_round=state['game_round'], 
                    player_id=current_player, 
                    content=statement, 
                    thinking=thinking,
                )],
                "history": history,
            },
            goto="statement_node",
        )
