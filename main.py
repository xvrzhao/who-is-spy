import asyncio

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
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
from nodes.exchange_session import (
    exchange_session_start_node,
    exchange_session_player_node,
    route_after_exchange,
    exchange_session_end_node,
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
    # 赛后交流节点
    .add_node(exchange_session_start_node)
    .add_node(exchange_session_player_node)
    .add_node(exchange_session_end_node)

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
    .add_edge("game_over_node", "exchange_session_start_node")
    .add_edge("exchange_session_start_node", "exchange_session_player_node")
    .add_conditional_edges(
        "exchange_session_player_node",
        route_after_exchange,
        {
            "continue": "exchange_session_player_node",
            "end": "exchange_session_end_node",
        }
    )
    .add_edge("exchange_session_end_node", END)

    .compile(checkpointer=checkpointer)
)

# mermaid_code = graph.get_graph(xray=True).draw_mermaid()
# print(mermaid_code)

config = {"configurable": {"thread_id": "thread-1"}}

interrupt_prompts = {
    "need_statement": "轮到你发言了，请输入你的发言内容：",
    "need_vote": "轮到你投票了，请输入你要投票的玩家ID：",
    "need_exchange": "轮到你交流发言了。输入格式：发言内容|玩家ID（玩家ID为指定下一位发言的玩家，不能选自己），如：刚才真没看出你是卧底|2\n请输入：",
}

async def main():
    game_input = State(player_total=4)

    while True:
        async for chunk in graph.astream(game_input, config, stream_mode=["custom"], version="v2"):
            if chunk["type"] != "custom":
                continue
            event = chunk["data"]
            print("Event:", event)

        state = await graph.aget_state(config)
        if len(state.interrupts) < 1:
            break

        interrupt_info = state.interrupts[0].value
        user_input = input(interrupt_prompts.get(interrupt_info["interrupt"], str(interrupt_info)))
        game_input = Command(resume=user_input)


if __name__ == "__main__":
    asyncio.run(main())