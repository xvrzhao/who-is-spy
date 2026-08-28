from os import getenv

from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv

load_dotenv()

llm = ChatDeepSeek(
    model="deepseek-v4-flash",
    api_key=getenv("LLM_API_KEY"),
    extra_body={"thinking": {"type": "disabled"}},
)