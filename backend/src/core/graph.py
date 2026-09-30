from logging import getLogger
from typing import AsyncIterator

from langgraph.types import Checkpointer, Command
from langgraph.graph.state import CompiledStateGraph

from src.core.game.graph import build_graph
from src.core.game.events import Event
from src.core.game.state import State
from src.utils.sse import sse_event


logger = getLogger(__name__)


class GraphProvider:
    def __init__(self):
        self.checkpointer: Checkpointer = None
        self.graph: CompiledStateGraph = None


    def init(self, checkpointer: Checkpointer):
        self.checkpointer = checkpointer
        self.graph = build_graph(self.checkpointer)

        logger.info("graph init: graph compiled")


    @staticmethod
    def game_event_to_sse(event: Event):
        return sse_event(event.type, event.model_dump(mode="json", exclude={"type"}))


    @staticmethod
    def get_config(thread_id: str):
        return {"configurable": {"thread_id": thread_id}}


    async def run_graph(self, thread_id: str, graph_input) -> AsyncIterator[str]:
        """运行 graph 直到中断或结束"""

        try:

            # 运行 graph 并 yield 游戏进度事件
            async for chunk in self.graph.astream(
                graph_input, 
                self.get_config(thread_id), 
                stream_mode=["custom"], 
                version="v2"
            ):
                if chunk.get("type") != "custom":
                    continue
                event = chunk["data"]
                if isinstance(event, Event):
                    yield self.game_event_to_sse(event)

            # 运行完毕，最后 yield 中断或结束事件
            state = await self.graph.aget_state(self.get_config(thread_id))
            if state.interrupts:
                yield sse_event("interrupt", state.interrupts[0].value)
            else:
                yield sse_event("finished", {})

        except Exception as e:

            logger.exception("game %s run failed", thread_id)
            yield sse_event("error", {"type": type(e).__name__, "message": str(e)})


    async def stream_start(self, thread_id: str, player_total: int) -> AsyncIterator[str]:
        """游戏开局，SSE 帧输出"""

        yield sse_event("game_started", {"game_id": thread_id, "player_total": player_total})
        async for frame in self.run_graph(thread_id, State(player_total=player_total)):
            yield frame


    async def stream_resume(self, game_id: str, resume_value) -> AsyncIterator[str]:
        """游戏中断继续，SSE 帧输出"""

        async for frame in self.run_graph(game_id, Command(resume=resume_value)):
            yield frame


graph_provider = GraphProvider()