import base64
from os import getenv

import httpx
from dotenv import load_dotenv
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from events import emit, PlayerSpeech

load_dotenv()

MINIMAX_API_KEY = getenv("MINIMAX_API_KEY", "")
MINIMAX_TTS_MODEL = getenv("MINIMAX_TTS_MODEL", "speech-2.6-hd")
T2A_URL = "https://api.minimax.cn/v1/t2a_v2"
REQUEST_TIMEOUT = 30.0
SAMPLE_RATE = 22050

# 中文系统音色表（按玩家 ID 取模固定分配，保证同一玩家音色不变）
VOICE_IDS = [
    "female-shaonv",
    "male-qn-jingying",
    "female-chengshu",
    "Chinese (Mandarin)_Southern_Young_Man",
    "Chinese (Mandarin)_Warm_Bestie",
    "Chinese_cixianglaoren",
]

# 限流/临时性业务码可重试；1004 鉴权失败等不可重试
RETRYABLE_STATUS_CODES = {1002, 1039}


class TTSError(RuntimeError):
    """可重试的业务失败（限流等）"""


class TerminalTTSError(RuntimeError):
    """不可重试的失败（鉴权/参数/音色无效等）"""


def get_voice_id(player_id: int) -> str:
    return VOICE_IDS[(player_id - 1) % len(VOICE_IDS)]


@retry(
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError, TTSError)),
    stop=stop_after_attempt(3),
    wait=wait_fixed(1),
    reraise=True,
)
async def synthesize(text: str, voice_id: str) -> tuple[bytes, int]:
    """调用 Minimax T2A 非流式接口合成语音，返回 (mp3 字节, 时长毫秒)"""

    payload = {
        "model": MINIMAX_TTS_MODEL,
        "text": text,
        "stream": False,
        "voice_setting": {"voice_id": voice_id, "speed": 1.0, "vol": 1.0, "pitch": 0},
        "audio_setting": {"sample_rate": SAMPLE_RATE, "bitrate": 128000, "format": "mp3", "channel": 1},
        "language_boost": "Chinese",
    }
    headers = {"Authorization": f"Bearer {MINIMAX_API_KEY}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.post(T2A_URL, json=payload, headers=headers)

    if resp.status_code in (401, 403):
        raise TerminalTTSError(f"HTTP {resp.status_code} 鉴权失败")
    resp.raise_for_status()

    body = resp.json()
    status_code = body.get("base_resp", {}).get("status_code", -1)
    if status_code != 0:  # Minimax 约定 HTTP 200 也可能携带业务错误
        status_msg = body.get("base_resp", {}).get("status_msg", "")
        if status_code in RETRYABLE_STATUS_CODES:
            raise TTSError(f"Minimax {status_code}: {status_msg}")
        raise TerminalTTSError(f"Minimax {status_code}: {status_msg}")

    audio = bytes.fromhex(body["data"]["audio"])  # 接口返回的是 hex 编码，不是 base64
    audio_length_ms = int(body.get("extra_info", {}).get("audio_length", 0))
    return audio, audio_length_ms


async def speak(player_id: int, text: str) -> None:
    """合成语音并下发 PlayerSpeech 事件"""

    if not MINIMAX_API_KEY:
        emit(PlayerSpeech(player_id=player_id, text=text))
        return

    try:
        audio, audio_length_ms = await synthesize(text, get_voice_id(player_id))
    except Exception as e:
        print(f"[TTS 降级] player {player_id}: {e!r}")
        emit(PlayerSpeech(player_id=player_id, text=text))  # audio_base64 默认空串
        return

    emit(PlayerSpeech(
        player_id=player_id,
        text=text,
        audio_base64=base64.b64encode(audio).decode("ascii"),
        audio_length_ms=audio_length_ms,
    ))
