from random import randint

from langchain.messages import HumanMessage

from llm import llm
from state import State, GameStage
from prompts import get_words_prompt


def init_node(state: State):
    player_total = 4
    spy_id = randint(1, 4)

    print("> 初始化阶段，获取词语中...")
    
    msg = llm.invoke([HumanMessage(content=get_words_prompt())])
    words = msg.content.split(" ")
    word_civilian, word_spy = [word.strip() for word in words]

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