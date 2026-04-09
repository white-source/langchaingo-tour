"""
Level 7: Agent 系统 ⭐⭐⭐⭐⭐

学习目标：
1. 理解 Agent 工作原理：LLM 驱动的循环决策
2. 掌握 Tool 的定义方式（@tool 装饰器原理）
3. 理解 tool_calls 在 AIMessage 中的结构
4. 自己实现一个完整的 ReAct Agent 循环
5. 理解 BaseTool 的 invoke 调用链

源码参考：
- BaseTool: langchain_core/tools/base.py line 405
- @tool 装饰器: langchain_core/tools/convert.py
- AgentAction/AgentFinish: langchain_core/agents.py
- ToolCall/ToolMessage: langchain_core/messages/tool.py

核心架构：
  LLM 决策 → 解析 ToolCall → 执行工具 → 反馈结果 → LLM 再决策 → 循环

注意：本例使用可控的模拟 LLM，无需 API，但忠实还原 Agent 真实行为
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool, tool

print("=" * 80)
print("Level 7: Agent 系统 — 从源码理解 ReAct 循环")
print("=" * 80)


# ============================================================================
# 第一部分：定义工具 — @tool 装饰器原理
# ============================================================================
print("\n" + "─" * 60)
print("【1】@tool 装饰器 — 源码解析")
print("─" * 60)

# 源码关键点（tools/convert.py）：
#
# @tool 装饰器做了什么？
# 1. 读取函数签名 → 生成 Pydantic args_schema（用于 LLM 的 JSON Schema）
# 2. 读取 docstring → 设为 description（LLM 用来决定何时调用）
# 3. 包装成 StructuredTool，继承 BaseTool
#
# StructuredTool._run(**kwargs) 会调用原始函数
# BaseTool.run(tool_input)：
#   1. 验证输入（args_schema.model_validate）
#   2. 调用 _run(**validated_kwargs)
#   3. 处理错误（handle_tool_error）


@tool
def calculator(expression: str) -> str:
    """
    执行数学计算。支持 +、-、*、/、** 运算。

    示例：
    - "2 + 3" → "5"
    - "10 * (3 + 2)" → "50"
    - "2 ** 10" → "1024"
    """
    try:
        # 安全的数学表达式求值（只允许数字和运算符）
        allowed = set("0123456789+-*/().** ")
        if not all(c in allowed for c in expression.replace("**", "")):
            return "错误：表达式包含不允许的字符"
        result = eval(expression, {"__builtins__": {}}, {})  # noqa: S307
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"


@tool
def weather_query(city: str) -> str:
    """
    查询指定城市的当前天气。

    参数：
    - city: 城市名称，如 "北京"、"上海"、"London"

    返回当前温度和天气状况。
    """
    # 模拟天气数据
    weather_data = {
        "北京": {"temp": 12, "condition": "晴"},
        "上海": {"temp": 18, "condition": "多云"},
        "广州": {"temp": 25, "condition": "小雨"},
        "london": {"temp": 8, "condition": "阴"},
    }
    city_lower = city.lower()
    if city_lower in weather_data:
        data = weather_data[city_lower]
        return f"{city}当前天气：{data['condition']}，温度 {data['temp']}°C"
    return f"暂无 {city} 的天气数据"


@tool
def web_search(query: str, max_results: int = 3) -> str:
    """
    搜索互联网获取信息。

    参数：
    - query: 搜索关键词
    - max_results: 最多返回结果数（默认 3）
    """
    # 模拟搜索结果
    return (
        f"搜索 '{query}' 的结果（前 {max_results} 条）：\n"
        f"1. {query} 的相关定义和基本概念...\n"
        f"2. {query} 的最新动态和研究进展...\n"
        f"3. {query} 的实际应用案例..."
    )


# 检查 @tool 生成的工具属性
print("@tool 装饰器生成的工具属性：")
print(f"  calculator.name: {calculator.name!r}")
print(f"  calculator.description: {calculator.description[:60]}...")
print(f"  calculator.args_schema: {calculator.args_schema}")
print(f"  calculator.inputType: {type(calculator).__mro__}")
print()

# 工具的 JSON Schema（这是发给 LLM 的格式）
print("发给 LLM 的工具 JSON Schema：")
print(
    json.dumps(calculator.args_schema.model_json_schema(), indent=2, ensure_ascii=False)
)


# ============================================================================
# 第二部分：BaseTool 的 invoke 调用链
# ============================================================================
print("\n" + "─" * 60)
print("【2】BaseTool.invoke 调用链详解")
print("─" * 60)

# 源码关键点（tools/base.py line 635）：
#
# class BaseTool:
#     def invoke(self, input: str | dict | ToolCall, config=None):
#         # 如果是 ToolCall（来自 AIMessage.tool_calls），提取 args
#         tool_input, kwargs = self._parse_input(input, config)
#         return self.run(tool_input, **kwargs)
#
#     def run(self, tool_input, run_manager=None, **kwargs):
#         # 1. 调用 callback: on_tool_start
#         # 2. 验证输入: args_schema.model_validate(tool_input)
#         # 3. 执行: self._run(**validated_input)
#         # 4. 调用 callback: on_tool_end
#         # 5. 处理错误: if handle_tool_error...

# 方式 1：字符串输入（旧风格）
result1 = calculator.invoke("2 + 3 * 4")
print(f"字符串输入: calculator.invoke('2 + 3 * 4') = {result1!r}")

# 方式 2：字典输入
result2 = calculator.invoke({"expression": "100 / 4"})
print(f"字典输入:   calculator.invoke({{'expression': '100 / 4'}}) = {result2!r}")

# 方式 3：ToolCall 输入（Agent 执行时的真实格式）
tool_call = {
    "id": "call_abc123",
    "name": "calculator",
    "args": {"expression": "2 ** 8"},
}
# 关键：必须有 "type": "tool_call" 才能被 _is_tool_call() 识别
# 源码: def _is_tool_call(x) -> bool: return isinstance(x, dict) and x.get("type") == "tool_call"
tool_call["type"] = "tool_call"
result3 = calculator.invoke(tool_call)
print(f"ToolCall:   = {result3!r}")
print()
print(
    f"weather_query.invoke({{'city': '北京'}}) = {weather_query.invoke({'city': '北京'})!r}"
)


# ============================================================================
# 第三部分：理解 tool_calls 的消息格式
# ============================================================================
print("\n" + "─" * 60)
print("【3】消息格式：LLM 如何表达工具调用意图")
print("─" * 60)

# 源码关键点（messages/tool.py）：
#
# class ToolCall(TypedDict):
#     name: str         # 工具名
#     args: dict        # 参数（LLM 生成的 JSON）
#     id: str           # 唯一 ID（ToolMessage 用这个来关联）
#     type: Literal["tool_call"]
#
# AIMessage 中的 tool_calls 字段：
# AIMessage(
#     content="",  # 有 tool_calls 时 content 通常为空
#     tool_calls=[ToolCall(name="calculator", args={"expression": "2+2"}, id="call_1")]
# )

# 模拟 LLM 返回"我想调用计算器"
ai_wants_to_calculate = AIMessage(
    content="让我帮你计算。",
    tool_calls=[
        {
            "id": "call_001",
            "name": "calculator",
            "args": {"expression": "15 * 7 + 3"},
            "type": "tool_call",
        }
    ],
)

print("AIMessage 带工具调用：")
print(f"  content: {ai_wants_to_calculate.content!r}")
print(f"  tool_calls: {ai_wants_to_calculate.tool_calls}")

# 执行工具后，返回 ToolMessage
tool_result = calculator.invoke(ai_wants_to_calculate.tool_calls[0])
tool_message = ToolMessage(
    content=str(tool_result),
    tool_call_id="call_001",  # 必须与 AIMessage.tool_calls[*].id 对应
)

print(f"\nToolMessage（工具执行结果）：")
print(f"  content: {tool_message.content!r}")
print(f"  tool_call_id: {tool_message.tool_call_id!r}")


# ============================================================================
# 第四部分：手动实现 ReAct Agent 循环
# ============================================================================
print("\n" + "─" * 60)
print("【4】手动实现 ReAct Agent 循环（最重要的部分！）")
print("─" * 60)


# 模拟智能 LLM（能理解工具调用格式）
class ScriptedAgentLLM:
    """
    模拟一个能调用工具的 LLM

    真实场景中这是 ChatOpenAI(model="gpt-4o") 或 ChatDeepSeek() 等
    """

    def __init__(self, scripts: list):
        """scripts: 预设的回复序列，按顺序返回"""
        self.scripts = scripts
        self.call_count = 0

    def invoke_with_tools(
        self, messages: list[BaseMessage], tools: list[BaseTool]
    ) -> AIMessage:
        """模拟 llm.bind_tools(tools).invoke(messages)"""
        script = self.scripts[min(self.call_count, len(self.scripts) - 1)]
        self.call_count += 1
        return script


# 工具注册表（name → tool）
tool_registry = {
    "calculator": calculator,
    "weather_query": weather_query,
    "web_search": web_search,
}


def run_agent(
    user_query: str,
    agent_llm: ScriptedAgentLLM,
    tools: dict[str, BaseTool],
    system_prompt: str = "你是一个能使用工具的智能助手。",
    max_iterations: int = 10,
) -> str:
    """
    手动实现的 ReAct Agent 核心循环

    这是 Agent 最本质的工作方式：
    1. LLM 决策（使用工具？直接回答？）
    2. 如果使用工具：执行工具，把结果加入历史
    3. 重复，直到 LLM 决定直接回答
    """
    # 初始化消息历史
    messages: list[BaseMessage] = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_query),
    ]

    print(f"\n🧑 用户: {user_query}")
    print(f"  系统提示: {system_prompt}")

    for iteration in range(max_iterations):
        print(f"\n  [循环 {iteration + 1}] 调用 LLM...")

        # Step 1: LLM 决策
        ai_response = agent_llm.invoke_with_tools(messages, list(tools.values()))
        messages.append(ai_response)

        print(f"  🤖 LLM 回复: content={ai_response.content!r}")

        # Step 2: 检查是否有工具调用
        if not ai_response.tool_calls:
            # 没有工具调用 → LLM 给出了最终回答
            print(f"\n✅ Agent 完成，最终回答:")
            print(f"   {ai_response.content}")
            return ai_response.content

        # Step 3: 执行所有工具调用
        print(f"  🔧 需要调用 {len(ai_response.tool_calls)} 个工具：")
        for tc in ai_response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_id = tc["id"]

            print(f"     → {tool_name}({tool_args})")

            if tool_name not in tools:
                tool_result = f"错误：工具 '{tool_name}' 不存在"
            else:
                # 执行工具（BaseTool.invoke 接收 ToolCall dict）
                tool_result = tools[tool_name].invoke(tc)

            print(f"     ← {tool_result!r}")

            # 将工具结果作为 ToolMessage 加入历史
            messages.append(
                ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_id,
                )
            )

    return "（超过最大迭代次数，停止）"


# ─────────────────────────────
# 场景 1：单工具调用（计算）
# ─────────────────────────────
print("\n场景 1：单工具调用")
scene1_llm = ScriptedAgentLLM(
    [
        # 第一次：决定调用计算器
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call_math_001",
                    "name": "calculator",
                    "args": {"expression": "1234 * 5678"},
                    "type": "tool_call",
                }
            ],
        ),
        # 第二次：给出最终答案
        AIMessage(
            content="1234 × 5678 = 7,006,652。这是通过计算器工具计算的精确结果。"
        ),
    ]
)

run_agent("1234 乘以 5678 等于多少？", scene1_llm, tool_registry)


# ─────────────────────────────
# 场景 2：多工具串行调用
# ─────────────────────────────
print("\n" + "─" * 40)
print("场景 2：多工具串行调用（需要前一个结果才能调用下一个）")

scene2_llm = ScriptedAgentLLM(
    [
        # 第一次：查天气
        AIMessage(
            content="我先查一下北京的天气。",
            tool_calls=[
                {
                    "id": "call_weather_001",
                    "name": "weather_query",
                    "args": {"city": "北京"},
                    "type": "tool_call",
                }
            ],
        ),
        # 第二次：根据天气搜索相关信息
        AIMessage(
            content="让我进一步搜索相关信息。",
            tool_calls=[
                {
                    "id": "call_search_001",
                    "name": "web_search",
                    "args": {"query": "北京晴天 户外活动推荐", "max_results": 2},
                    "type": "tool_call",
                }
            ],
        ),
        # 第三次：综合给出答案
        AIMessage(
            content="根据天气查询和搜索结果：北京今天是晴天，温度12°C，适合户外活动。建议可以去长城、颐和园等景点游览。"
        ),
    ]
)

run_agent("今天北京天气如何？适合出门吗？", scene2_llm, tool_registry)


# ─────────────────────────────
# 场景 3：并行工具调用
# ─────────────────────────────
print("\n" + "─" * 40)
print("场景 3：并行工具调用（同时调用多个工具）")

scene3_llm = ScriptedAgentLLM(
    [
        # 第一次：同时调用两个工具（现代 LLM 支持并行 tool_calls）
        AIMessage(
            content="我同时查询北上广的天气。",
            tool_calls=[
                {
                    "id": "call_bj",
                    "name": "weather_query",
                    "args": {"city": "北京"},
                    "type": "tool_call",
                },
                {
                    "id": "call_sh",
                    "name": "weather_query",
                    "args": {"city": "上海"},
                    "type": "tool_call",
                },
                {
                    "id": "call_gz",
                    "name": "weather_query",
                    "args": {"city": "广州"},
                    "type": "tool_call",
                },
            ],
        ),
        # 第二次：综合回答
        AIMessage(
            content=(
                "三城天气对比：\n"
                "• 北京：晴，12°C（偏冷）\n"
                "• 上海：多云，18°C（适中）\n"
                "• 广州：小雨，25°C（温暖但有雨）\n"
                "总体来说，上海天气最舒适。"
            )
        ),
    ]
)

run_agent("帮我比较北京、上海、广州三个城市今天的天气", scene3_llm, tool_registry)


# ============================================================================
# 第五部分：理解 bind_tools（真实 LLM 的工具绑定）
# ============================================================================
print("\n" + "─" * 60)
print("【5】真实 LLM 中的 bind_tools 原理")
print("─" * 60)

# 源码关键点（language_models/chat_models.py）：
#
# def bind_tools(self, tools, tool_choice=None, **kwargs):
#     """将工具绑定到 LLM，生成新的 Runnable"""
#     formatted_tools = [convert_to_openai_tool(tool) for tool in tools]
#     # 等价于：
#     return self.bind(tools=formatted_tools, **kwargs)
#     # bind() 返回 RunnableBinding，每次 invoke 时自动传递 tools 参数给 API


# 工具的 OpenAI Function Calling 格式
def show_tool_schema(t: BaseTool):
    schema = {
        "type": "function",
        "function": {
            "name": t.name,
            "description": t.description,
            "parameters": t.args_schema.model_json_schema(),
        },
    }
    print(json.dumps(schema, indent=2, ensure_ascii=False))


print("calculator 工具的 OpenAI Function Calling 格式：")
show_tool_schema(calculator)

print("\n📌 bind_tools 实现原理：")
print("  1. 遍历工具列表，调用 tool.args_schema.model_json_schema() 生成 JSON Schema")
print("  2. 调用 self.bind(tools=[...]) → 返回 RunnableBinding")
print("  3. RunnableBinding 在每次 invoke 时，把 tools 参数传给底层 API")
print("  4. LLM 根据工具描述和参数 Schema，决定何时调用哪个工具")


# ============================================================================
# 第六部分：自己实现 BaseTool 子类
# ============================================================================
print("\n" + "─" * 60)
print("【6】自己实现 BaseTool 子类（不用 @tool）")
print("─" * 60)

# 当你需要：
# - 工具有状态（数据库连接等）
# - 复杂的初始化逻辑
# - 精细控制错误处理
# 就用继承 BaseTool 的方式

from pydantic import BaseModel, Field as PydanticField

from langchain_core.runnables import RunnableLambda


class StockQueryInput(BaseModel):
    """股票查询工具的输入模式"""

    ticker: str = PydanticField(description="股票代码，如 AAPL、TSLA")
    period: str = PydanticField(default="1d", description="查询周期：1d/1w/1m")


class StockQueryTool(BaseTool):
    """查询股票价格"""

    name: str = "stock_query"
    description: str = (
        "查询指定股票的价格信息。" "输入股票代码（如 AAPL），返回当前价格和涨跌幅。"
    )
    args_schema: type[BaseModel] = StockQueryInput

    # 工具可以有状态（数据库连接、API 客户端等）
    api_endpoint: str = "https://api.example.com/stock"

    def _run(self, ticker: str, period: str = "1d") -> str:
        """实际执行逻辑"""
        # 模拟股票数据
        fake_prices = {"AAPL": 195.5, "TSLA": 248.3, "MSFT": 412.1}
        price = fake_prices.get(ticker.upper(), 100.0)
        change = "+2.3%"  # 模拟涨跌幅
        return f"{ticker.upper()}: ${price:.2f} ({change}) [周期: {period}]"

    async def _arun(self, ticker: str, period: str = "1d") -> str:
        """异步版本（Agent.abatch 时使用）"""
        import asyncio

        await asyncio.sleep(0.01)  # 模拟异步 API 调用
        return self._run(ticker, period)


stock_tool = StockQueryTool()
print("自定义 BaseTool 测试：")
print(
    f"  stock_tool.invoke({{'ticker': 'AAPL'}}) = {stock_tool.invoke({'ticker': 'AAPL'})!r}"
)
print(
    f"  stock_tool.invoke({{'ticker': 'TSLA', 'period': '1w'}}) = "
    f"{stock_tool.invoke({'ticker': 'TSLA', 'period': '1w'})!r}"
)

# BaseTool 也是 Runnable，可以参与 | 链（适配 str → dict 的包装）
stock_chain = (
    RunnableLambda(lambda ticker: {"ticker": ticker})
    | stock_tool
    | RunnableLambda(lambda r: f"📊 {r}")
)

print(f"\n  stock_chain.invoke('MSFT') = {stock_chain.invoke('MSFT')!r}")


# ============================================================================
# 小结
# ============================================================================
print("\n" + "=" * 80)
print("Level 7 完成！关键收获：")
print("=" * 80)
print(
    """
🔑 Agent 的本质是一个循环：
      response = llm.invoke(messages)
      if not response.tool_calls:
          return response.content   # 完成
      for tc in response.tool_calls:
          result = tools[tc.name].invoke(tc)
          messages.append(ToolMessage(result, tc.id))

    # BaseTool 也是 Runnable，可以参与 | 链
    from langchain_core.runnables import RunnableLambda
🔑 工具的两种定义方式：
  1. @tool 装饰器（简洁）：
     - 从函数签名自动生成 Pydantic args_schema
     - 函数 docstring 成为 description
     - 底层创建 StructuredTool（BaseTool 子类）
  
  2. 继承 BaseTool（灵活）：
     - 支持有状态工具（数据库连接等）
     - 精细控制 args_schema
     - 实现自定义错误处理

🔑 消息格式（消息历史的演化过程）：
  [SystemMessage, HumanMessage]
  → [SystemMessage, HumanMessage, AIMessage(tool_calls=[...])]
  → [SystemMessage, HumanMessage, AIMessage, ToolMessage(call_001)]
  → [SystemMessage, HumanMessage, AIMessage, ToolMessage, AIMessage(最终回答)]

🔑 并行工具调用：
  AIMessage.tool_calls 可以包含多个工具调用
  Agent 循环中：for tc in response.tool_calls（顺序执行）
  优化：用 asyncio.gather 并行执行多个工具

🔑 bind_tools 原理：
  llm.bind_tools([tool1, tool2]) = RunnableBinding(llm, tools=[tool_schemas])
  → 每次调用时自动把 tool schemas 添加到 API 请求的 tools 字段

下一步 Level 8：设计你自己的 Agent！
"""
)
