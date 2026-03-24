"""
Level 4: 输出解析器 📊

学习目标：
1. 理解 OutputParser 的作用
2. 掌握 StrOutputParser
3. 学习 JSONParser 和 Pydantic
4. 理解类型验证和结构化数据

核心概念：
- OutputParser: 将 LLM 原始输出转换为有用的格式
- StrOutputParser: 提取字符串内容
- JSONParser: 解析 JSON 字符串为 Python 对象
- PydanticOutputParser: 验证 Pydantic 模型
"""

from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field
from typing import List
import json


# ============================================================================
# 准备：虚拟 LLM
# ============================================================================


class VirtualLLM(RunnableLambda):
    """虚拟 LLM"""

    def __init__(self):
        self.responses = {
            "提取信息": '{"name": "Alice", "age": 30, "city": "Beijing"}',
            "列表": '{"items": ["Python", "JavaScript", "Go"]}',
        }
        super().__init__(self._call)

    def _call(self, text) -> str:
        # 处理 PromptValue 对象或字符串
        if hasattr(text, "text"):
            text_content = text.text
        else:
            text_content = str(text)

        for key, resp in self.responses.items():
            if key in text_content:
                return resp
        return '{"result": "default"}'


virtual_llm = VirtualLLM()


# ============================================================================
# 第一步：StrOutputParser
# ============================================================================

print("=" * 80)
print("Level 4: 输出解析器")
print("=" * 80)
print()

print("1️⃣  StrOutputParser（提取字符串）：")
print("-" * 80)
print()

prompt = PromptTemplate(input_variables=["topic"], template="解释：{topic}")

parser = StrOutputParser()

# 组合
chain = prompt | virtual_llm | parser

result = chain.invoke({"topic": "算法"})

print(f"输出: {result}")
print(f"类型: {type(result)}")
print()

print("✅ StrOutputParser 的作用：")
print("   - 从 LLM 响应提取文本")
print("   - 移除元数据和格式")
print("   - 适合需要纯文本的场景")
print()


# ============================================================================
# 第二步：JSONParser
# ============================================================================

print("-" * 80)
print("2️⃣  JSONOutputParser（解析 JSON）：")
print("-" * 80)
print()

json_parser = JsonOutputParser()

prompt = PromptTemplate(
    input_variables=["requirement"], template="返回 JSON 格式：{requirement}"
)

json_chain = prompt | virtual_llm | json_parser

result = json_chain.invoke({"requirement": "提取信息"})

print(f"输出: {result}")
print(f"类型: {type(result)}")
print()

print("✅ JSONOutputParser 的作用：")
print("   - LLM 输出 JSON 字符串")
print("   - 自动转换为 Python dict")
print("   - 支持嵌套结构")
print()


# ============================================================================
# 第三步：Pydantic 模型解析
# ============================================================================

print("-" * 80)
print("3️⃣  PydanticOutputParser（结构化验证）：")
print("-" * 80)
print()


# 定义数据结构
class Person(BaseModel):
    """人物信息"""

    name: str = Field(..., description="名字")
    age: int = Field(..., description="年龄")
    city: str = Field(..., description="城市")


# 创建 parser
from langchain_core.output_parsers import PydanticOutputParser

pydantic_parser = PydanticOutputParser(pydantic_object=Person)

prompt = PromptTemplate(
    input_variables=["requirement"],
    template="返回 JSON：{requirement}",
    partial_variables={
        "format_instructions": pydantic_parser.get_format_instructions()
    },
)

chain = prompt | virtual_llm | pydantic_parser

result = chain.invoke({"requirement": "提取信息"})

print(f"输出: {result}")
print(f"类型: {type(result)}")
print(f"名字: {result.name}")
print(f"年龄: {result.age}")
print()

print("✅ PydanticOutputParser 的作用：")
print("   - 自动验证必填字段")
print("   - 类型转换（str→int）")
print("   - 生成 API 文档")
print()


# ============================================================================
# 第四步：复杂数据结构
# ============================================================================

print("-" * 80)
print("4️⃣  处理复杂结构（列表、嵌套）：")
print("-" * 80)
print()


class Item(BaseModel):
    """单个项目"""

    name: str
    description: str


class ResultList(BaseModel):
    """结果列表"""

    items: List[Item]


# parser
from langchain_core.output_parsers import PydanticOutputParser

list_parser = PydanticOutputParser(pydantic_object=ResultList)

prompt = PromptTemplate(
    input_variables=["requirement"], template="返回项目列表 JSON：{requirement}"
)

chain = prompt | virtual_llm | list_parser


# 模拟 LLM 返回列表
class VirtualLLMList(RunnableLambda):
    def __init__(self):
        super().__init__(self._call)

    def _call(self, text: str) -> str:
        return """{"items": [
            {"name": "Python", "description": "编程语言"},
            {"name": "JavaScript", "description": "网页脚本"}
        ]}"""


prompt = PromptTemplate(
    input_variables=["requirement"], template="返回列表：{requirement}"
)

chain = prompt | VirtualLLMList() | list_parser
result = chain.invoke({"requirement": "列表"})

print(f"输出: {result}")
print(f"项目数: {len(result.items)}")
for item in result.items:
    print(f"  - {item.name}: {item.description}")
print()


# ============================================================================
# 第五步：自定义 Parser
# ============================================================================

print("-" * 80)
print("5️⃣  自定义输出解析器：")
print("-" * 80)
print()

from langchain_core.output_parsers import BaseOutputParser


class UppercaseParser(BaseOutputParser[str]):
    """自定义：转换为大写"""

    def parse(self, text: str) -> str:
        return text.upper()


uppercase_parser = UppercaseParser()

prompt = PromptTemplate(input_variables=["topic"], template="解释：{topic}")

chain = prompt | virtual_llm | uppercase_parser

result = chain.invoke({"topic": "算法"})

print(f"输出: {result}")
print()

print("✅ 自定义 Parser 的好处：")
print("   - 灵活处理特殊格式")
print("   - 集成到链中")
print("   - 支持复杂转换")
print()


# ============================================================================
# 第六步：Parser 的错误处理
# ============================================================================

print("-" * 80)
print("6️⃣  错误处理：")
print("-" * 80)
print()


# JSON 解析失败
class FailingLLM(RunnableLambda):
    def __init__(self):
        super().__init__(self._call)

    def _call(self, text: str) -> str:
        return "不是 JSON 格式"


prompt = PromptTemplate(input_variables=["x"], template="返回 JSON: {x}")

chain = prompt | FailingLLM() | json_parser

print("尝试解析无效的 JSON：")
try:
    result = chain.invoke({"x": "test"})
except Exception as e:
    print(f"  ❌ 错误: {type(e).__name__}: {str(e)[:50]}")

print()


# ============================================================================
# 核心总结
# ============================================================================

print("=" * 80)
print("Level 4 核心要点")
print("=" * 80)
print()

summary = """
1. 📊 OutputParser 的作用
   - 将 LLM 原始输出转换为有用格式
   - 验证数据结构
   - 类型转换

2. 🎯 常见的 Parser
   - StrOutputParser: 提取字符串
   - JsonOutputParser: 解析 JSON
   - PydanticOutputParser: 验证模型
   - 自定义: BaseOutputParser

3. 🔒 Pydantic 验证
   - 类型检查 (str/int/bool)
   - 必填字段验证
   - 默认值
   - 嵌套模型支持

4. 📝 使用模式
   Prompt | LLM | Parser
   
   输入: {"topic": "AI"}
   LLM 输出: {"type": "AI", "description": "..."}
   Parser 输出: ParsedModel(type="AI", ...)

5. 🚨 错误处理
   - 解析失败时捕获异常
   - 提供默认值
   - 使用 return_exceptions=True

下一步：学习复杂组合（Level 5）
- RunnableParallel：并行处理
- RunnableBranch：条件分支
- RunnableMapping：数据映射
"""

print(summary)

print("=" * 80)
print("✅ Level 4 完成！")
print("=" * 80)
