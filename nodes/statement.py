from langchain.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage, ToolCall, ToolCallChunk
from langgraph.types import Command, Send
from pydantic import BaseModel, Field

from state import State, GameStage, StateRecord, VoteRecord, PlayerIdentity, RawRecord
from prompts import get_rules_prompt, get_statement_prompt, get_voting_prompt
from llm import llm

class Statement(BaseModel):
    """玩家发言，包括发言思考和发言内容"""
    thinking: str = Field(description="玩家发言前的思考")
    content: str = Field(description="玩家发言内容")

state_llm = llm.with_structured_output(Statement, method="function_calling")

def statement_node(state: State):
    history = []

    # 若为新一轮开始
    if state["active_player_ptr"] == 0:
        print(f"> 第 {state['game_round']} 轮发言开始...")
        history.append(RawRecord(content=f"------ 第 {state['game_round']} 轮发言阶段：------"))

    present_players = state["present_players"]
    active_player_ptr = state["active_player_ptr"]
    current_player = present_players[active_player_ptr]

    current_word = state["word_spy"] if current_player == state['spy_id'] else state["word_civilian"]

    print(f"> 玩家 {current_player} 思考中...")

    p = get_statement_prompt(current_player, current_word, state["history"]+history)
    if state["game_round"] > 1:
        print(p)
    stmt: Statement = state_llm.invoke([
        SystemMessage(content=get_rules_prompt(state["player_total"])),
        HumanMessage(content=p),
    ])

    thinking, statement = stmt.thinking, stmt.content

    print(f"> 玩家 {current_player} 发言思考：{thinking}")
    print(f"> 玩家 {current_player} 发言内容：{statement}")

    history.append(RawRecord(is_private=True, read_only_by=current_player, content=f"玩家 {current_player} 内心独白：{thinking}"))
    history.append(RawRecord(content=f"玩家 {current_player} 发言：{statement}"))

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
