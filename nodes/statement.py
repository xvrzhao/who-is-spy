from langchain.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from state import State, GameStage, StateRecord, RawRecord
from prompts import get_rules_prompt, get_statement_prompt
from llm import llm

class Statement(BaseModel):
    """玩家发言，包括发言思考和发言内容"""
    thinking: str = Field(description="玩家发言前的思考")
    content: str = Field(description="玩家发言内容")

state_llm = llm.with_structured_output(Statement, method="function_calling").with_retry()


def statement_start_node(state: State):
    """发言阶段开始节点"""

    print(f"> 第 {state['game_round']} 轮发言开始...")
    return State(history=[RawRecord(content=f"------ 第 {state['game_round']} 轮发言阶段：------")])


async def statement_player_node(state: State):
    """玩家发言节点"""

    present_players = state["present_players"]
    active_player_ptr = state["active_player_ptr"]

    current_player = present_players[active_player_ptr]
    current_word = state["word_spy"] if current_player == state['spy_id'] else state["word_civilian"]

    print(f"> 玩家 {current_player} 思考中...")

    stmt: Statement = await state_llm.ainvoke([
        SystemMessage(content=get_rules_prompt(state["player_total"])),
        HumanMessage(content=get_statement_prompt(current_player, current_word, state["history"])),
    ])

    thinking, statement = stmt.thinking, stmt.content

    print(f"> 玩家 {current_player} 发言思考：{thinking}")
    print(f"> 玩家 {current_player} 发言内容：{statement}")

    append_state_records = [
        StateRecord(game_round=state['game_round'], player_id=current_player, content=statement, thinking=thinking)
    ]

    append_raw_records = [
        RawRecord(is_private=True, read_only_by=current_player, content=f"玩家 {current_player} 内心独白：{thinking}"),
        RawRecord(content=f"玩家 {current_player} 发言：{statement}"),
    ]

    return {
        "active_player_ptr": active_player_ptr + 1, # 若本次发言已经为最后一名玩家，+1 后指针会越界，statement_end 节点中将指针重置
        "state_history": append_state_records,
        "history": append_raw_records,
    }


def route_after_statement(state: State) -> str:
    """statement_player_node 的条件路由"""

    # 指针越界说明本轮所有玩家都已发言
    if state["active_player_ptr"] >= len(state["present_players"]):
        return "end"
    return "continue"


def statement_end_node(state: State):
    """发言阶段结束节点"""
    print(f"> 第 {state['game_round']} 轮发言结束...")
    return {
        "stage": GameStage.VOTING,
        "active_player_ptr": 0,
    }
