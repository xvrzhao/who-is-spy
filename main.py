from langgraph.graph import StateGraph, START, END
from state import State
from nodes.statement import statement_node
from nodes.voting import voting_start_node, voting_player_node, voting_end_node
from nodes.init import init_node

graph = (
    StateGraph(State)
    .add_node(init_node)
    .add_node(statement_node)
    .add_node(voting_start_node)
    .add_node(voting_player_node)
    .add_node(voting_end_node)
    .set_entry_point("init_node")
    .add_edge("init_node", "statement_node")
    .compile()
)

if __name__ == "__main__":
    print("> 游戏开始！")
    final_state = graph.invoke({})
    print("> 游戏结束！")