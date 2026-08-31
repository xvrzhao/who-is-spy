import asyncio

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from state import State
from nodes.statement import (
    statement_start_node,
    statement_player_node,
    route_after_statement,
    statement_end_node,
)
from nodes.voting import (
    voting_start_node, 
    fanout_to_voting_players, 
    voting_player_node, 
    voting_end_node,
    route_after_voting,
)
from nodes.game_init import game_init_node
from nodes.game_over import game_over_node

checkpointer = InMemorySaver()

graph = (
    StateGraph(State)

    # 游戏初始化节点
    .add_node(game_init_node)
    # 发言阶段节点
    .add_node(statement_start_node)
    .add_node(statement_player_node)
    .add_node(statement_end_node)
    # 投票阶段节点
    .add_node(voting_start_node)
    .add_node(voting_player_node)
    .add_node(voting_end_node)
    # 游戏结束节点
    .add_node(game_over_node)

    .set_entry_point("game_init_node")
    .add_edge("game_init_node", "statement_start_node")
    .add_edge("statement_start_node", "statement_player_node")
    .add_conditional_edges(
        "statement_player_node",
        route_after_statement,
        {
            "continue": "statement_player_node", 
            "end": "statement_end_node",
        },
    )
    .add_edge("statement_end_node", "voting_start_node")
    .add_conditional_edges(
        "voting_start_node",
        fanout_to_voting_players,
        ["voting_player_node"],
    )
    .add_edge("voting_player_node", "voting_end_node")
    .add_conditional_edges(
        "voting_end_node",
        route_after_voting,
        {
            "next_round": "statement_start_node",
            "game_over": "game_over_node",
        }
    )
    .add_edge("game_over_node", END)

    .compile(checkpointer=checkpointer)
)

# mermaid_code = graph.get_graph(xray=True).draw_mermaid()
# print(mermaid_code)

config = {"configurable": {"thread_id": "thread-1"}}

async def main():
    init_state = State(player_total=6)
    async for chunk in graph.astream(init_state, config, stream_mode=["custom"], version="v2"):
        if chunk["type"] != "custom":
            continue
        event = chunk["data"]
        print("Event:", event)


if __name__ == "__main__":
    asyncio.run(main())