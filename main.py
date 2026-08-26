from langgraph.graph import StateGraph, START, END
from langchain.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage, ToolCall, ToolCallChunk
from random import randint
from state import State, GameStage, StateRecord, VoteRecord, PlayerIdentity
from nodes.statement import statement_node
from nodes.voting import voting_start_node, voting_player_node, voting_end_node
from llm import llm

graph = (
    StateGraph(State)
    .add_node("statement_node", statement_node)
    .add_node("voting_start_node", voting_start_node)
    .add_node("voting_player_node", voting_player_node)
    .add_node("voting_end_node", voting_end_node)
    .set_entry_point("statement_node")
    .compile()
)

if __name__ == "__main__":
    player_total = 4
    spy_id = randint(1, 4)

    print("> 游戏开始，获取词语中...")
    
    msg = llm.invoke([
        HumanMessage(content="""
            在“谁是卧底”游戏中，平民和卧底各自会拿到一个意思相近但又有细微差别的词语或成语，可以是物品、形容词、动词等等，给出的词语不要太过简单，请给出这样的一对词语。
            你的回答中只包含这一对词语，两个词语间用一个空格隔开。
        """)
    ])
    words = msg.content.split(" ")
    words = [word.strip() for word in words]
    word_civilian = words[0]
    word_spy = words[1]

    print(f"> 获取词语完成, 平民词: {word_civilian}, 卧底词: {word_spy}")
    print(f"> 卧底是：玩家 {spy_id}")

    init_state = State(
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

    final_state = graph.invoke(init_state)
    print("> 游戏结束！")