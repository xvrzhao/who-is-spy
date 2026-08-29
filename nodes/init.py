from random import randint

from pydantic import BaseModel, Field

from llm import llm
from state import State, GameStage
from prompts import get_words_prompt


class Words(BaseModel):
    """“谁是卧底”游戏中发给玩家的一对词语"""
    word_civilian: str = Field(description="平民词，大多数玩家拿到的词")
    word_spy: str = Field(description="卧底词，少数卧底玩家拿到的词")

words_llm = llm.with_structured_output(Words, method="function_calling")

def init_node(state: State):
    player_total = 4
    spy_id = randint(1, 4)

    print("> 初始化阶段，获取词语中...")

    words: Words = words_llm.invoke(get_words_prompt())
    word_civilian, word_spy = words.word_civilian, words.word_spy

    print(f"> 获取词语完成, 平民词: {word_civilian}, 卧底词: {word_spy}")
    print(f"> 卧底是：玩家 {spy_id}")

    return State(
        player_total=player_total, 
        spy_id=spy_id,
        word_civilian=word_civilian, 
        word_spy=word_spy,
        game_round=1,
        stage=GameStage.STATEMENT,
        present_players=[i for i in range(1, player_total+1)],
        active_player_ptr=0,
        state_history=[],
        vote_history=[],
        history=[],
        winner=None,
    )