import asyncio

from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import InMemorySaver

from state import State
from nodes.statement import (
    statement_start_node,
    statement_player_node,
    route_after_statement,
    statement_end_node,
)
from nodes.voting import voting_start_node, voting_player_node, voting_end_node
from nodes.init import init_node

checkpointer = InMemorySaver()

graph = (
    StateGraph(State)

    # 游戏初始化节点
    .add_node(init_node)

    # 发言阶段节点
    .add_node(statement_start_node)
    .add_node(statement_player_node)
    .add_node(statement_end_node)

    # 投票阶段节点
    .add_node(voting_start_node)
    .add_node(voting_player_node)
    .add_node(voting_end_node)

    .set_entry_point("init_node")
    .add_edge("init_node", "statement_start_node")
    .add_edge("statement_start_node", "statement_player_node")
    .add_conditional_edges(
        "statement_player_node",
        route_after_statement,
        {"continue": "statement_player_node", "end": "statement_end_node"},
    )
    .add_edge("statement_end_node", "voting_start_node")
    .add_edge("voting_player_node", "voting_end_node")

    .compile(checkpointer=checkpointer)
)

# mermaid_code = graph.get_graph(xray=True).draw_mermaid()
# print(mermaid_code)

config = {"configurable": {"thread_id": "thread-1"}}


async def main():
    print("> 游戏开始！")

    init_state = State(player_total=4)
    await graph.ainvoke(init_state, config)

    print("> 游戏结束！")


if __name__ == "__main__":
    asyncio.run(main())