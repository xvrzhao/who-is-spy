from os import getenv

from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(
    base_url="https://open.bigmodel.cn/api/paas/v4/",
    model="glm-5.2", # glm-5.3 不支持关闭思考模式
    api_key=getenv("LLM_API_KEY"),
    temperature=1.0,
    extra_body={"thinking": {"type": "disabled"}}, # 关闭思考模式，速度更快
)

async def ainvoke_structured(runnable: Runnable, messages, attempts: int = 3):
    """调用 with_structured_output 的 runnable，模型偶发不按约束输出 tool call 时会返回 None，视为失败重试

    （with_retry 只捕获异常，无法覆盖 None 返回值，故单独包一层）
    """
    last = None
    for _ in range(attempts):
        last = await runnable.ainvoke(messages)
        if last is not None:
            return last
    raise RuntimeError(f"structured output 连续 {attempts} 次返回 None")
