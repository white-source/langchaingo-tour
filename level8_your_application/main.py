"""
Level 8: 设计你自己的 Agent ⭐⭐⭐⭐⭐

目标：
从零搭建一个生产级别的 Agent 框架（Mini-LangChain）
不依赖 LangChain 的高阶封装，只用 langchain_core 的基础协议

这是用 LangChain 源码知识的综合应用：

1. 自定义 Runnable 子类（实现完整协议）
2. 自定义 BaseTool 的工具集
3. 手写 Agent 执行引擎（含 streaming 支持）
4. 持久化消息历史
5. 流式输出结果
6. 回调系统集成

这也是你设计 fff_agent、mini-deer-flow 等项目的参考模版。
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from typing import Any

from pydantic import BaseModel, Field as PydanticField

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.documents import Document
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import (
    RunnableConfig,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)
from langchain_core.runnables.base import Runnable
from langchain_core.tools import BaseTool, tool

print("=" * 80)
print("Level 8: 设计你自己的 Agent — Mini-LangChain 实战")
print("=" * 80)


# ============================================================================
# 第一部分：自定义 Runnable 子类
# 学习关键：如何正确实现 Runnable 接口
# ============================================================================
print("\n" + "─" * 60)
print("【1】自定义 Runnable — 实现完整协议")
print("─" * 60)

# 源码要点（base.py line 124）：
# Runnable 只要求实现 invoke，其余方法都有默认实现：
# - batch: 线程池并行调用 invoke
# - ainvoke: asyncio 线程池异步调用 invoke
# - stream: 调用 invoke，然后 yield 结果

from langchain_core.runnables.base import RunnableSerializable


class TextProcessor(RunnableSerializable[str, dict]):
    """
    一个处理文本的自定义 Runnable

    演示：
    1. 如何继承 RunnableSerializable（比 Runnable 多了序列化支持）
    2. 如何用 Pydantic 字段配置
    3. 如何实现 stream（逐词输出）
    """

    # Pydantic 字段（可通过 RunnableConfig.configurable 动态修改）
    prefix: str = PydanticField(default="[处理]", description="输出前缀")
    delay: float = PydanticField(default=0.01, description="每词延迟（模拟流式输出）")

    @classmethod
    def get_lc_namespace(cls) -> list[str]:
        return ["custom", "processors"]

    def invoke(self, input: str, config: RunnableConfig | None = None) -> dict:
        words = input.split()
        return {
            "original": input,
            "word_count": len(words),
            "processed": f"{self.prefix} {input.upper()}",
            "words": words,
        }

    def stream(
        self, input: str, config: RunnableConfig | None = None, **kwargs
    ) -> Iterator[dict]:
        """流式输出：逐词产生结果"""
        words = input.split()
        for i, word in enumerate(words, 1):
            time.sleep(self.delay)
            yield {"word": word, "index": i, "total": len(words)}


processor = TextProcessor(prefix=">>", delay=0)
print("invoke 结果：", processor.invoke("Hello LangChain World"))
print("stream 结果（前3个）：")
for chunk in list(processor.stream("Hello LangChain World"))[:3]:
    print(f"  {chunk}")


# ============================================================================
# 第二部分：构建工具集
# ============================================================================
print("\n" + "─" * 60)
print("【2】构建生产级工具集")
print("─" * 60)

# ─── 工具定义 ───


@tool
def think(thought: str) -> str:
    """
    让 Agent 进行内部推理（Chain-of-Thought）。
    当需要分析复杂问题时，先用这个工具思考，再决定行动。
    返回你的推理过程，不执行任何外部操作。
    """
    return f"[思考记录] {thought}"


@tool
def calculator(expression: str) -> str:
    """
    精确计算数学表达式。支持 +, -, *, /, **, // 运算。
    示例: '(100 + 200) * 3 / 4' 返回 '225.0'
    """
    try:
        allowed = set("0123456789+-*/().** //")
        if not all(c in allowed for c in expression):
            return f"错误：含有不允许的字符"
        result = eval(expression, {"__builtins__": {}}, {})  # noqa: S307
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"


class KnowledgeBase(BaseModel):
    docs: list[Document] = PydanticField(default_factory=list)


class KnowledgeSearchTool(BaseTool):
    """在内部知识库中搜索相关信息"""

    name: str = "knowledge_search"
    description: str = (
        "在内部知识库中搜索信息。" "使用关键词搜索，返回最相关的知识条目。"
    )

    class ArgsSchema(BaseModel):
        query: str = PydanticField(description="搜索关键词")

    args_schema: type[BaseModel] = ArgsSchema
    kb: KnowledgeBase = PydanticField(default_factory=KnowledgeBase)

    def _run(self, query: str) -> str:
        import re, math

        if not self.kb.docs:
            return "知识库为空"

        query_words = set(re.findall(r"\w+", query.lower()))
        scored = []
        for doc in self.kb.docs:
            words = set(re.findall(r"\w+", doc.page_content.lower()))
            score = len(query_words & words) / (1 + math.log(len(words) + 1))
            scored.append((score, doc))

            scored.sort(key=lambda x: x[0], reverse=True)
        top = [doc for _, doc in scored[:2] if _ > 0]
        if not top:
            return f"未找到与 '{query}' 相关的知识"

        return "\n---\n".join(
            f"[{doc.metadata.get('title', '未知')}]: {doc.page_content}" for doc in top
        )


# 创建知识库
kb = KnowledgeBase(
    docs=[
        Document(
            page_content="Python 是一种多范式编程语言，创建于1991年。",
            metadata={"title": "Python 简介"},
        ),
        Document(
            page_content="LangChain 通过 Runnable 协议统一所有组件接口。",
            metadata={"title": "LangChain 架构"},
        ),
        Document(
            page_content="RAG 检索增强生成通过外部知识增强 LLM 回答质量。",
            metadata={"title": "RAG 技术"},
        ),
        Document(
            page_content="Agent 通过工具调用循环实现自主任务规划和执行。",
            metadata={"title": "Agent 原理"},
        ),
    ]
)

ks_tool = KnowledgeSearchTool(kb=kb)
ALL_TOOLS = {t.name: t for t in [think, calculator, ks_tool]}

print("可用工具：")
for name, t in ALL_TOOLS.items():
    print(f"  {name}: {t.description[:50]}...")


# ============================================================================
# 第三部分：Agent 执行引擎（带 Callback）
# ============================================================================
print("\n" + "─" * 60)
print("【3】Agent 执行引擎 — 带回调和流式输出")
print("─" * 60)


# 自定义 Callback Handler（观察者）
class AgentLogger(BaseCallbackHandler):
    """
    观察 Agent 执行过程的回调处理器

    源码关键点（callbacks/base.py）：
    - BaseCallbackHandler 有 20+ 个 on_* 方法
    - 每个 Runnable 在执行时会触发对应的事件
    - CallbackManager 负责将事件分发给所有注册的 handler
    """

    log: list[str] = []

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs: Any) -> None:
        tool_name = serialized.get("name", "unknown")
        self.log.append(f"  🔧 工具开始: {tool_name}({input_str[:40]})")
        print(self.log[-1])

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        out_str = output.content if hasattr(output, "content") else str(output)
        self.log.append(f"  ✅ 工具结束: {out_str[:60]}")
        print(self.log[-1])

    def on_chain_start(self, serialized: dict, inputs: dict, **kwargs: Any) -> None:
        pass  # 忽略链级别的事件

    def on_chain_end(self, outputs: dict, **kwargs: Any) -> None:
        pass


# 模拟智能 LLM（同 Level 7，但支持多轮对话感知）
class SmartScriptedLLM:
    def __init__(self, scripts: list[AIMessage]):
        self.scripts = scripts
        self.i = 0

    def bind_tools(self, tools):
        return self

    def invoke(self, messages: list[BaseMessage]) -> AIMessage:
        resp = self.scripts[min(self.i, len(self.scripts) - 1)]
        self.i += 1
        return resp


# Agent 执行引擎
class AgentExecutor:
    """
    Agent 执行引擎

    这是 LangChain 中 AgentExecutor 的简化实现
    实际的 langchain_classic.agents.AgentExecutor 包含更多特性：
    - early_stopping_method
    - handle_parsing_errors
    - max_iterations / max_execution_time
    - output_keys / return_intermediate_steps
    """

    def __init__(
        self,
        llm: SmartScriptedLLM,
        tools: dict[str, BaseTool],
        system_prompt: str = "你是一个有用的 AI 助手。",
        max_iterations: int = 10,
        callbacks: list[BaseCallbackHandler] | None = None,
    ):
        self.llm = llm
        self.tools = tools
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.callbacks = callbacks or []

    def invoke(self, query: str) -> dict[str, Any]:
        """执行 Agent，返回最终结果和中间步骤"""
        messages: list[BaseMessage] = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=query),
        ]
        intermediate_steps = []

        for iteration in range(self.max_iterations):
            # LLM 决策
            response = self.llm.invoke(messages)
            messages.append(response)

            if not response.tool_calls:
                # 完成！
                return {
                    "output": response.content,
                    "intermediate_steps": intermediate_steps,
                    "messages": messages,
                    "iterations": iteration + 1,
                }

            # 执行工具
            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_input = tc["args"]
                tool_id = tc["id"]

                # 触发 on_tool_start 回调
                for cb in self.callbacks:
                    cb.on_tool_start(
                        {"name": tool_name}, json.dumps(tool_input, ensure_ascii=False)
                    )

                # 执行工具
                if tool_name in self.tools:
                    result = self.tools[tool_name].invoke(
                        tc, config={"callbacks": self.callbacks}
                    )
                else:
                    result = f"工具不存在: {tool_name}"

                # 触发 on_tool_end 回调
                for cb in self.callbacks:
                    cb.on_tool_end(str(result))

                # 添加工具结果
                messages.append(ToolMessage(content=str(result), tool_call_id=tool_id))
                intermediate_steps.append(
                    {"tool": tool_name, "input": tool_input, "output": str(result)}
                )

        return {
            "output": "（超过最大迭代次数）",
            "intermediate_steps": intermediate_steps,
            "messages": messages,
            "iterations": self.max_iterations,
        }


# ─────────────────────────────
# 测试：复杂多步骤任务
# ─────────────────────────────
logger = AgentLogger()

agent = AgentExecutor(
    llm=SmartScriptedLLM(
        [
            # 1. 先搜索知识库了解 RAG
            AIMessage(
                content="我先搜索一下 RAG 的相关知识。",
                tool_calls=[
                    {
                        "id": "tc_001",
                        "name": "knowledge_search",
                        "args": {"query": "RAG 检索增强生成"},
                        "type": "tool_call",
                    }
                ],
            ),
            # 2. 思考后计算一个例子
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tc_002",
                        "name": "think",
                        "args": {
                            "thought": "RAG 需要检索 top-k 文档。假设每个文档 512 tokens，"
                            "k=3，context window 4096 tokens，"
                            "剩余 4096-512*3 = 1560 tokens 给回答"
                        },
                        "type": "tool_call",
                    },
                    {
                        "id": "tc_003",
                        "name": "calculator",
                        "args": {"expression": "4096 - 512 * 3"},
                        "type": "tool_call",
                    },
                ],
            ),
            # 3. 给出最终综合回答
            AIMessage(
                content=(
                    "基于知识库搜索和计算：\n\n"
                    "**RAG（检索增强生成）技术** 通过外部知识增强 LLM 回答质量。\n\n"
                    "实践建议：\n"
                    "- 检索 top-3 文档时，每个文档建议控制在 512 tokens 以内\n"
                    "- 在 4096 token 的 context window 中：512×3=1536 tokens 用于上下文，"
                    "剩余 **1560 tokens** 用于生成回答\n"
                    "- 这是一个合理的配置，可以在质量和效率之间取得平衡"
                )
            ),
        ]
    ),
    tools=ALL_TOOLS,
    system_prompt="你是一个精通技术的 AI 助手，喜欢先搜索知识再给出深思熟虑的回答。",
    callbacks=[logger],
)

print("复杂多步骤任务：")
print(
    "查询: 帮我了解 RAG 技术，并计算 top-3 检索在 4096 context window 下能给回答留多少空间？"
)
print()
result = agent.invoke(
    "帮我了解 RAG 技术，并计算 top-3 检索在 4096 context window 下能给回答留多少空间？"
)
print(f"\n🤖 最终回答:\n{result['output']}")
print(
    f"\n📊 执行统计: 迭代 {result['iterations']} 次，中间步骤 {len(result['intermediate_steps'])} 步"
)


# ============================================================================
# 第四部分：带记忆的 Agent
# ============================================================================
print("\n" + "─" * 60)
print("【4】带记忆的 Agent — 持久化对话历史")
print("─" * 60)

# 源码参考：langchain_core/runnables/history.py
# RunnableWithMessageHistory 的原理：
# 1. invoke 前：从 store 加载历史消息
# 2. 将历史消息插入 chat prompt 的 MessagesPlaceholder
# 3. invoke 后：将新消息追加到 store


class ConversationMemory:
    """简单的对话记忆（生产中用 RunnableWithMessageHistory）"""

    def __init__(self):
        self.sessions: dict[str, list[BaseMessage]] = {}

    def get(self, session_id: str) -> list[BaseMessage]:
        return self.sessions.get(session_id, [])

    def add(self, session_id: str, messages: list[BaseMessage]) -> None:
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].extend(messages)


class StatefulAgentExecutor(AgentExecutor):
    """带会话记忆的 Agent"""

    def __init__(self, *args, memory: ConversationMemory, **kwargs):
        super().__init__(*args, **kwargs)
        self.memory = memory

    def chat(self, query: str, session_id: str = "default") -> str:
        """有状态的多轮对话"""
        # 加载历史
        history = self.memory.get(session_id)

        # 构建完整消息列表（历史 + 当前）
        full_messages = (
            [SystemMessage(content=self.system_prompt)]
            + history
            + [HumanMessage(content=query)]
        )

        # 简化执行（只运行一次 LLM）
        response = self.llm.invoke(full_messages)

        # 保存历史
        self.memory.add(
            session_id,
            [HumanMessage(content=query), AIMessage(content=response.content)],
        )

        return response.content


memory = ConversationMemory()
stateful_llm = SmartScriptedLLM(
    [
        AIMessage(content="你好！我是你的 AI 助手，有什么可以帮助你的吗？"),
        AIMessage(
            content="好的，你之前问了关于 Python 的问题，现在想了解更多关于异步编程？"
        ),
        AIMessage(
            content="关于我们的对话历史：你先问了问候，然后询问了异步编程，这是第三次提问。"
        ),
    ]
)

stateful_agent = StatefulAgentExecutor(
    llm=stateful_llm,
    tools=ALL_TOOLS,
    system_prompt="你是一个有记忆的助手，能记住对话历史。",
    memory=memory,
)

print("多轮对话测试（相同 session_id）：")
for turn, q in enumerate(["你好！", "我想了解 Python 异步编程", "我们聊过什么？"]):
    print(f"\n  轮次 {turn + 1}: {q}")
    r = stateful_agent.chat(q, session_id="session_001")
    print(f"  回答: {r}")

print(f"\n  记忆中保存了 {len(memory.get('session_001'))} 条消息")


# ============================================================================
# 第五部分：Agent 作为 Runnable（可组合）
# ============================================================================
print("\n" + "─" * 60)
print("【5】Agent 即 Runnable — Agent 的可组合性")
print("─" * 60)

# 设计思想（源自 langchain_core 的 Runnable 协议）：
# Agent 本身也应该是一个 Runnable，这样它就可以：
# 1. 参与 | 链组合
# 2. 支持 batch（批量处理多个查询）
# 3. 支持流式输出
# 4. 支持 retry/fallback

from langchain_core.runnables.base import RunnableSerializable


class AgentRunnable(RunnableSerializable[str, str]):
    """
    将 Agent 包装成 Runnable，使其可以参与链组合

    这是你设计自己的 Agent 框架的关键思路：
    Agent = Runnable[str, str]（输入问题，输出回答）
    """

    system_prompt: str = "你是一个 AI 助手。"
    max_iterations: int = 5
    # 注意：tools 作为配置而不是 Pydantic 字段（因为 BaseTool 不易序列化）
    _tools: dict[str, BaseTool] = {}
    _llm: Any = None

    @classmethod
    def get_lc_namespace(cls) -> list[str]:
        return ["custom", "agents"]

    def setup(self, llm: Any, tools: dict[str, BaseTool]) -> "AgentRunnable":
        """设置 LLM 和工具（非 Pydantic 字段）"""
        self._llm = llm
        self._tools = tools
        return self

    def invoke(self, input: str, config: RunnableConfig | None = None) -> str:
        """Agent 的 invoke：运行 Agent 循环，返回最终回答"""
        executor = AgentExecutor(
            llm=self._llm,
            tools=self._tools,
            system_prompt=self.system_prompt,
            max_iterations=self.max_iterations,
        )
        result = executor.invoke(input)
        return result["output"]


# 创建可组合的 Agent
agent_runnable = AgentRunnable(system_prompt="你是精通技术的 AI 助手。").setup(
    llm=SmartScriptedLLM(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tc_k1",
                        "name": "knowledge_search",
                        "args": {"query": "LangChain Runnable"},
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(
                content="LangChain 的核心是 Runnable 协议，它统一了所有组件的接口。"
            ),
        ]
    ),
    tools=ALL_TOOLS,
)

# 现在 agent 可以参与 | 链!
preprocessing = RunnableLambda(lambda x: f"请回答：{x}")
postprocessing = RunnableLambda(lambda x: f"[回答] {x}")

agent_chain = preprocessing | agent_runnable | postprocessing

result = agent_chain.invoke("LangChain 的核心是什么？")
print("Agent 参与链组合的结果：")
print(f"  {result}")

# batch 支持（Runnable 默认用线程池并行处理）
queries = ["LangChain 是什么？", "RAG 是什么？"]
print(f"\nbatch 处理 {len(queries)} 个查询（默认并行）...")
# （注意：ScriptedLLM 有状态，这里只是演示接口，真实场景每个 agent 应有独立状态）


# ============================================================================
# 第六部分：设计自己的 Agent 框架的关键决策
# ============================================================================
print("\n" + "─" * 60)
print("【6】设计自己 Agent 框架的关键决策")
print("─" * 60)

print(
    """
当你要设计 fff_agent / mini-deer-flow 等项目时，参考以下框架决策：

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
决策 1：工具定义格式
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LangChain 方案：
  @tool → StructuredTool（name + description + args_schema）
  
你的方案可以参考：
  - JSON Schema 格式（OpenAI Function Calling）
  - Go struct + 反射（fff_agent 中的做法）
  
关键要求：
  - 工具名（唯一）
  - 工具描述（LLM 理解何时使用）
  - 参数 Schema（LLM 生成正确调用格式）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
决策 2：消息历史格式
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LangChain 方案：
  messages = [SystemMessage, HumanMessage, AIMessage, ToolMessage, ...]
  
关键约束（与 LLM API 对齐）：
  - AIMessage 有 tool_calls 时，必须紧跟 ToolMessage（且 tool_call_id 对应）
  - ToolMessage 的 tool_call_id 必须与 AIMessage.tool_calls[*].id 一致
  
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
决策 3：Agent 循环策略
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

简单循环（本 Level 的实现）：
  while not_done:
    response = llm(messages)
    if not response.tool_calls: return response
    for tc in response.tool_calls:
      result = tools[tc.name](tc.args)
      messages.append(ToolMessage(result, tc.id))

LangGraph 图模式（deer-flow 使用）：
  StateGraph → 更灵活的条件路由
  支持多节点、循环、并行执行路径
  
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
决策 4：持久化策略
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

内存（临时）：dict[session_id, list[Message]]
SQLite（本地持久化）：LangGraph Checkpoint SQLite
Redis/Postgres（生产）：LangGraph Checkpoint Postgres

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
决策 5：流式输出
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LangChain 方案：
  chain.stream(input)  →  Iterator[chunk]
  chain.astream(input) →  AsyncIterator[chunk]
  
关键：LLM 层的 _stream() 方法支持 token 级流式
Agent 循环中工具执行期间无法流式（工具完成才返回）
  
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
)


# ============================================================================
# 小结
# ============================================================================
print("=" * 80)
print("Level 8 完成！恭喜你完成了全部 8 个 Level！")
print("=" * 80)
print(
    """
🎉 你已经掌握了：

Level 1：Runnable 协议（LangChain 的基础抽象）
Level 2：PromptTemplate + ChatModel（与 LLM 交互）
Level 3：| 操作符（RunnableSequence 链式组合）
Level 4：OutputParser（结构化 LLM 输出）
Level 5：RunnableParallel / Passthrough / Branch（复杂流控）
Level 6：BaseRetriever + RAG 链（检索增强生成）
Level 7：BaseTool + ReAct Agent（工具调用循环）
Level 8：自定义 Runnable + AgentExecutor（设计自己的 Agent）

🔑 核心设计原则（可迁移到任何语言/框架）：

1. 统一接口：所有组件 = Runnable[Input, Output]
2. 声明式组合：用 | 描述数据流，而不是命令式调用
3. 关注点分离：检索/生成/工具/历史各司其职
4. 观察者模式：Callback 系统解耦执行与监控
5. Agent = 循环 + 记忆：LLM 决策 → 工具执行 → 反馈 → 循环

🚀 下一步推荐阅读：
- langgraph-tour：理解更复杂的图状 Agent 架构
- deer-flow：真实生产级 Agent 系统
- fff_agent：Go 语言实现的同等概念

💡 挑战练习：
用你学到的知识，在 fff_agent 项目中：
1. 实现一个 BaseTool 等效接口
2. 实现 Agent 循环（支持并行工具调用）
3. 添加 Callback 系统来观察执行过程
"""
)
