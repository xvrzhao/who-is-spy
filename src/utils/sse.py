import json

def sse_event(event: str, data: dict) -> str:
    """构造一条标准 SSE 消息帧。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"