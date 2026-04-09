import os

from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI


# 虚拟 LLM（预设响应）
class SimpleLLM(RunnableLambda):
    def __init__(self):
        self.responses = {
            "Python": "Python 是一种高级编程语言...",
            "JavaScript": "JavaScript 是用于网络开发的语言...",
        }
        super().__init__(self._call)

    def _call(self, text: str) -> str:
        for key, response in self.responses.items():
            if key in text:
                return response
        return "无法回答"


# TODO: 创建 prompt 模板
prompt = PromptTemplate(
    input_variables=["test_key_parameter"],
    template="请描述 {test_key_parameter} 语言的特点。",
)

# TODO: 创建虚拟 LLM
# api_key = os.getenv("DEEPSEEK_API_KEY")
# if not api_key:
#     raise RuntimeError(
#         "Missing DEEPSEEK_API_KEY. Export your DeepSeek API key before running this script."
#     )

# llm = ChatOpenAI(
#     model="deepseek-chat",
#     base_url="https://api.deepseek.com/v1",
#     api_key="sk-06068cf7691d4e6db2f73d3ece70d636",
# )

# TODO: 创建本地 LLM
# 默认连接本机 Ollama 的 OpenAI 兼容接口。
local_model = os.getenv("LOCAL_OPENAI_MODEL", "qwen2.5:7b")
local_base_url = os.getenv("LOCAL_OPENAI_BASE_URL", "http://localhost:11434/v1")
local_api_key = os.getenv("LOCAL_OPENAI_API_KEY", "ollama")

llm = ChatOpenAI(
    model=local_model,
    base_url=local_base_url,
    api_key=local_api_key,
)



# TODO: 手动组合 prompt + llm
def chain(language: str) -> str:
    # Step 1: 格式化提示
    prompt_text = prompt.format(test_key_parameter=language)
    print("Prompt to LLM:", prompt_text)  # 调试输出
    # Step 2: 调用 LLM
    response = llm.invoke(prompt_text)
    return response.content


# 测试
result = chain("Python")
print(result)
