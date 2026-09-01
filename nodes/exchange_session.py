from random import randint

from pydantic import BaseModel, Field
from langchain.messages import SystemMessage, HumanMessage

from state import State, RawRecord
from prompts import get_rules_prompt
from events import emit, ExchangeSessionStart, ExchangeSessionPlayerStart, ExchangeSessionPlayerEnd
from llm import llm


class ExchangeStatement(BaseModel):
    """玩家赛后交流，包含发言内容和指定下一位发言的玩家"""
    content: str = Field(description="玩家赛后想要说的话")
    next_player_id: int = Field(description="想听听哪位玩家的想法，指定下一位发言的玩家")

exchange_llm = llm.with_structured_output(ExchangeStatement, method="function_calling").with_retry()


def exchange_session_start_node(state: State) -> State:
    emit(ExchangeSessionStart())
    return {
        "history": [RawRecord(content=f"------ 游戏结束 玩家交流阶段 ------", is_private=False, read_only_by=None)],
        "exchange_next": randint(1, state["player_total"]),
        "exchange_round": 0,
    }


async def exchange_session_player_node(state: State) -> State:
    player_id = state["exchange_next"]

    if player_id == state["real_player_id"]:
        # TODO: 补充真实玩家逻辑
        pass
    else:
        emit(ExchangeSessionPlayerStart(player_id=player_id))
        res: ExchangeStatement = await exchange_llm.ainvoke([
            SystemMessage(content=get_rules_prompt(state["player_total"])),
            HumanMessage(content="TODO"), # TODO：完善提示词函数
        ])
        emit(ExchangeSessionPlayerEnd(player_id=player_id, content=res.content, next_player_id=res.next_player_id))

        append_raw_records = [RawRecord(content=f"玩家 {player_id} 发言：{res.content}", is_private=False, read_only_by=None)]
        exchange_next = res.next_player_id

    return {
        "history": append_raw_records,
        "exchange_next": exchange_next,
        "exchange_round": state["exchange_round"] + 1,
    }

def route_after_exchange(state: State) -> str:
    if state["exchange_round"] >= state["player_total"] * 2:
        return "end"
    else:
        return "continue"


def exchange_session_end_node(state: State):
    # TODO: 向客户端 emit 结束事件，以便提示用户是否开启新的一局
    pass