import asyncio
import base64
import os
import shutil
import tempfile

from langgraph.types import Command
from langgraph.checkpoint.memory import InMemorySaver

from src.game.graph import build_graph
from src.game.state import State
from src.game.events import PlayerSpeech

graph = build_graph(InMemorySaver()) # CLI 路径不依赖 Postgres

config = {"configurable": {"thread_id": "thread-1"}}

interrupt_prompts = {
    "need_statement": "轮到你发言了，请输入你的发言内容：",
    "need_vote": "轮到你投票了，请输入你要投票的玩家ID（输入 0 表示弃票）：",
    "need_exchange": "轮到你交流发言了。输入格式：发言内容|玩家ID（玩家ID为指定下一位发言的玩家，不能选自己），如：刚才真没看出你是卧底|2\n请输入：",
    "speech_playback_done": "（等待音频播放完成确认，正常会自动通过）：",
}

AFPLAY = shutil.which("afplay") # darwin 自带；无则跳过播放（无声环境）

async def play_speech(event: PlayerSpeech) -> None:
    """解码音频写入临时文件并用 afplay 播放，阻塞至播放完成（临时文件播完即删）"""

    if not event.audio_base64:
        print(f"[TTS 降级] 玩家 {event.player_id} 无音频，仅文字展示")
        return
    if AFPLAY is None:
        print(f"[无声环境] 跳过播放玩家 {event.player_id} 的语音（{event.audio_length_ms}ms）")
        return

    fd, path = tempfile.mkstemp(suffix=".mp3") # 默认落在 /tmp
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(base64.b64decode(event.audio_base64))
        proc = await asyncio.create_subprocess_exec(AFPLAY, path)
        await proc.wait() # 等待播放完成；期间图已停在 speech gate 的 interrupt 上
    finally:
        os.unlink(path)

async def main():
    game_input = State(player_total=6)

    while True:
        async for chunk in graph.astream(game_input, config, stream_mode=["custom"], version="v2"):
            if chunk["type"] != "custom":
                continue
            event = chunk["data"]
            if isinstance(event, PlayerSpeech):
                # 不打印整个事件 repr，base64 会刷屏
                print(f"Event: player_speech 玩家{event.player_id} 语音({event.audio_length_ms}ms)：{event.text}")
                await play_speech(event) # 播完才继续消费，与 speech gate 天然对齐
            else:
                print("Event:", event)

        state = await graph.aget_state(config)
        if len(state.interrupts) < 1:
            break

        interrupt_info = state.interrupts[0].value
        if interrupt_info["interrupt"] == "speech_playback_done":
            game_input = Command(resume=True) # afplay 已阻塞至播放完成，直接确认
            continue
        user_input = input(interrupt_prompts.get(interrupt_info["interrupt"], str(interrupt_info)))
        game_input = Command(resume=user_input)
