from langgraph.graph import StateGraph, END

from src.game.state import State
from src.game.nodes.statement import (
    statement_start_node,
    statement_player_node,
    statement_speech_gate_node,
    route_after_statement,
    statement_end_node,
)
from src.game.nodes.voting import (
    voting_start_node,
    fanout_to_voting_players,
    voting_player_node,
    voting_end_node,
    route_after_voting,
)
from src.game.nodes.exchange_session import (
    exchange_session_start_node,
    exchange_session_player_node,
    exchange_speech_gate_node,
    route_after_exchange,
    exchange_session_end_node,
)
from src.game.nodes.game_init import game_init_node
from src.game.nodes.game_over import game_over_node


def build_graph(checkpointer):
    """构建游戏状态图；checkpointer 由运行方注入（CLI 用 InMemorySaver，服务端用 AsyncPostgresSaver）"""

    return (
        StateGraph(State)

        # 游戏初始化节点
        .add_node(game_init_node)
        # 发言阶段节点
        .add_node(statement_start_node)
        .add_node(statement_player_node)
        .add_node(statement_speech_gate_node)
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
        .add_node(exchange_speech_gate_node)
        .add_node(exchange_session_end_node)

        .set_entry_point("game_init_node")
        .add_edge("game_init_node", "statement_start_node")
        .add_edge("statement_start_node", "statement_player_node")
        .add_edge("statement_player_node", "statement_speech_gate_node")
        .add_conditional_edges(
            "statement_speech_gate_node",
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
        .add_edge("exchange_session_player_node", "exchange_speech_gate_node")
        .add_conditional_edges(
            "exchange_speech_gate_node",
            route_after_exchange,
            {
                "continue": "exchange_session_player_node",
                "end": "exchange_session_end_node",
            }
        )
        .add_edge("exchange_session_end_node", END)

        .compile(checkpointer=checkpointer)
    )
