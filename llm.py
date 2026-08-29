from os import getenv

from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

# llm = ChatDeepSeek(
#     model="deepseek-v4-flash",
#     api_key=getenv("LLM_API_KEY"),
#     extra_body={"thinking": {"type": "disabled"}}, # 关闭思考模式，deepseek 思考模式不支持 tool_choice 参数，没办法使用 function_calling 方式进行结构化输出
# )

llm = ChatOpenAI(
    base_url="https://open.bigmodel.cn/api/paas/v4/",
    model="glm-5.2", # glm-5.3 不支持关闭思考模式
    api_key=getenv("LLM_API_KEY"),
    temperature=1.0,
    extra_body={"thinking": {"type": "disabled"}}, # 关闭思考模式，速度更快
)
