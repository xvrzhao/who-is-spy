from random import randint

from pydantic import BaseModel, Field
from langchain.messages import SystemMessage, HumanMessage
from langgraph.types import interrupt

from state import State, RawRecord
from prompts import get_rules_prompt, get_exchange_prompt
from events import emit, ExchangeSessionStart, ExchangeSessionPlayerStart, ExchangeSessionPlayerEnd, ExchangeSessionEnd
from llm import llm
from tts import speak


class ExchangeStatement(BaseModel):
    """玩家赛后交流，包含发言内容和指定下一位发言的玩家"""
    content: str = Field(description="玩家赛后想要说的话")
    next_player_id: int = Field(description="想听听哪位玩家的想法，指定下一位发言的玩家")

exchange_llm = llm.with_structured_output(ExchangeStatement, method="function_calling").with_retry()


def exchange_session_start_node(state: State) -> State:
    emit(ExchangeSessionStart())
    return {
        "exchange_histoty": ["------ 游戏结束 各玩家聊天记录 ------"],
        "exchange_next": randint(1, state["player_total"]),
        "exchange_round": 0,
    }


async def exchange_session_player_node(state: State) -> State:
    player_id = state["exchange_next"]

    if player_id == state["real_player_id"]:
        # 真实用户发言
        real_player_input = interrupt({"interrupt": "need_exchange"})
        content, next_player_id = real_player_input.rsplit("|", 1)
        next_player_id = int(next_player_id)

        emit(ExchangeSessionPlayerEnd(player_id=player_id, content=content, next_player_id=next_player_id))

        append_raw_records = [f"玩家{player_id}：{content}"]
        exchange_next = next_player_id
    else:
        emit(ExchangeSessionPlayerStart(player_id=player_id))

        your_word, another_word = (state["word_spy"], state['word_civilian']) if player_id == state["spy_id"] else (state["word_civilian"], state['word_spy'])
        your_identity = "spy" if player_id == state["spy_id"] else "civilian"
        is_win = state["winner"] == your_identity
        exchange_prompt = get_exchange_prompt(
            player_id,
            your_identity,
            your_word,
            another_word,
            is_win,
            state["history"],
            state["exchange_histoty"],
        )

        # debug code
        # print("\n", "-"*40, "\n", exchange_prompt, "\n", "-"*40)

        res: ExchangeStatement = await exchange_llm.ainvoke([
            SystemMessage(content=get_rules_prompt(state["player_total"])),
            HumanMessage(content=exchange_prompt),
        ])
        emit(ExchangeSessionPlayerEnd(player_id=player_id, content=res.content, next_player_id=res.next_player_id))
        await speak(player_id=player_id, text=res.content) # 语音合成 + 下发 PlayerSpeech 事件

        append_raw_records = [f"玩家{player_id}：{res.content}"]
        exchange_next = res.next_player_id

    return {
        "exchange_histoty": append_raw_records,
        "exchange_next": exchange_next,
        "exchange_round": state["exchange_round"] + 1,
    }


def exchange_speech_gate_node(state: State) -> State:
    """等待客户端确认语音播放完成后再继续"""
    
    interrupt({"interrupt": "speech_playback_done"})
    return {}


def route_after_exchange(state: State) -> str:
    if state["exchange_round"] >= state["player_total"] + 1:
        return "end"
    else:
        return "continue"


def exchange_session_end_node(state: State) -> State:
    """赛后交流阶段结束节点"""

    emit(ExchangeSessionEnd())

    return {}