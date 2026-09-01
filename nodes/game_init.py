from random import randint

from pydantic import BaseModel, Field

from llm import llm
from state import State
from prompts import get_words_prompt
from events import emit, GameInitStart, GameInitEnd

class Words(BaseModel):
    """“谁是卧底”游戏中发给玩家的一对词语"""
    word_civilian: str = Field(description="平民词，大多数玩家拿到的词")
    word_spy: str = Field(description="卧底词，少数卧底玩家拿到的词")

words_llm = llm.with_structured_output(Words, method="function_calling").with_retry()

async def game_init_node(state: State) -> State:
    player_total = state["player_total"]
    real_player_id = randint(1, player_total)
    spy_id = randint(1, player_total)

    emit(GameInitStart())

    words: Words = await words_llm.ainvoke(get_words_prompt())
    word_civilian, word_spy = words.word_civilian, words.word_spy

    emit(GameInitEnd(real_player_id=real_player_id, real_player_word=word_spy if real_player_id == spy_id else word_civilian))

    return State(
        player_total=player_total,
        real_player_id=real_player_id,
        spy_id=spy_id,
        word_civilian=word_civilian,
        word_spy=word_spy,
        game_round=1,
        stage="statement",
        present_players=[i for i in range(1, player_total+1)],
        active_player_ptr=0,
        state_history=[],
        vote_history=[],
        history=[],
        winner=None,
    )