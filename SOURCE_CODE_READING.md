# LangChain 源码精读指南 🔍

> **目标**：通过阅读源码，理解 LangChain 的核心设计原理，为自主设计 Agent 积累经验
>
> **源码位置**：`/home/SENSETIME/fengxiaohui/agent_design/langchain/libs/core/langchain_core/`

---

## 🗺️ 源码地图

```
langchain_core/
├── runnables/          ← 🔴 最核心！先读这里
│   ├── base.py         (6261 行) - Runnable 协议 + 所有组合原语
│   ├── config.py       (641 行)  - RunnableConfig，贯穿全局的上下文
│   ├── passthrough.py  (841 行)  - RunnablePassthrough, RunnableAssign
│   ├── branch.py       (461 行)  - RunnableBranch (条件路由)
│   ├── fallbacks.py    (664 行)  - 自动重试降级
│   ├── history.py      (622 行)  - 会话历史集成
│   ├── configurable.py (716 行)  - 运行时动态配置
│   └── graph.py        (739 行)  - 计算图可视化
├── language_models/    ← 🟠 第二步
│   ├── base.py         - BaseLanguageModel
│   └── chat_models.py  (1834 行) - BaseChatModel，最重要
├── messages/           ← 🟡 与 LLM 的消息协议
│   ├── base.py         - BaseMessage
│   └── tool.py         - ToolCall, ToolMessage
├── prompts/            ← 🟢 提示模板
│   ├── base.py         - BasePromptTemplate(Runnable)
│   └── chat.py         - ChatPromptTemplate
├── tools/              ← 🔵 工具系统
│   ├── base.py         (1586 行) - BaseTool
│   └── convert.py      (476 行)  - @tool 装饰器原理
├── callbacks/          ← 🟣 事件/观察者系统
│   ├── base.py         - 所有 on_* 事件接口
│   └── manager.py      - CallbackManager（事件分发器）
└── output_parsers/     ← ⚪ 输出结构化
```

---

## 📖 第一章：Runnable 协议 — 万物之源

### 核心文件：`runnables/base.py`

**设计思想**：统一接口 + 管道组合

```python
# base.py line 124
class Runnable(ABC, Generic[Input, Output]):
    """任何有输入/输出的计算单元"""
    
    @abstractmethod
    def invoke(self, input: Input, config: RunnableConfig | None = None) -> Output:
        ...
    
    # 默认实现：用线程池并行运行 invoke
    def batch(self, inputs: list[Input], ...) -> list[Output]:
        ...
    
    # 默认实现：用 asyncio 运行 sync 的 invoke
    async def ainvoke(self, input: Input, ...) -> Output:
        return await run_in_executor(None, self.invoke, input, ...)
    
    # 关键：| 操作符创造一个新的 RunnableSequence
    def __or__(self, other) -> RunnableSerializable:
        return RunnableSequence(self, coerce_to_runnable(other))
    
    def __ror__(self, other) -> RunnableSerializable:
        return RunnableSequence(coerce_to_runnable(other), self)
```

**关键洞察**：`|` 操作符不执行任何计算，只是**声明**两个 Runnable 的顺序组合关系。

### RunnableSequence（管道链）

```python
# base.py line 2817
class RunnableSequence(RunnableSerializable[Input, Output]):
    first: Runnable[Input, Any]
    middle: list[Runnable[Any, Any]]
    last: Runnable[Any, Output]
    
    def invoke(self, input: Input, config=None):
        input = self.first.invoke(input, config)
        for step in self.middle:
            input = step.invoke(input, config)
        return self.last.invoke(input, config)
    
    # batch 的优化：按步骤批量处理，而不是对每个样本串行
    def batch(self, inputs, config=None, **kwargs):
        # 关键：self.steps 中的每一步都调用 .batch()，而不是多次调用 .invoke()
        inputs = self.first.batch(inputs, config)
        for step in self.middle:
            inputs = step.batch(inputs, config)
        return self.last.batch(inputs, config)
```

**关键洞察**：`batch` 不是"多次 invoke"，而是按步骤批量处理——每一步都是批量的，这使得 LLM 的 batch API 能被充分利用。

### RunnableParallel（并行）

```python
# base.py line 3565
class RunnableParallel(RunnableSerializable[Input, dict]):
    steps__: Mapping[str, Runnable]
    
    def invoke(self, input: Input, config=None):
        # 用线程池并行执行所有 steps
        with get_executor_for_config(config) as executor:
            futures = {
                key: executor.submit(step.invoke, input, config)
                for key, step in self.steps__.items()
            }
            return {key: future.result() for key, future in futures.items()}
    
    async def ainvoke(self, input: Input, config=None):
        # 用 asyncio.gather 并发执行
        results = await asyncio.gather(*[
            step.ainvoke(input, config) 
            for step in self.steps__.values()
        ])
        return dict(zip(self.steps__.keys(), results))
```

**关键洞察**：同步版本用 `ThreadPoolExecutor`，异步版本用 `asyncio.gather`——这是 Python 并发的正确实践。

### RunnableLambda（装饰普通函数）

```python
# base.py line 4399
class RunnableLambda(Runnable[Input, Output]):
    func: Callable[[Input], Output]
    
    def invoke(self, input, config=None):
        return call_func_with_variable_args(self.func, input, config, **kwargs)
        # call_func_with_variable_args 会检查函数签名，
        # 如果需要 config 就注入，不需要就不传
```

**关键洞察**：`call_func_with_variable_args` 用 `inspect` 检查函数参数，实现了依赖注入式的接口——这允许函数既可以只接收 `input`，也可以同时接收 `config`。

### RunnableBinding（装饰器模式）

```python
# base.py line 5530
class RunnableBinding(RunnableSerializable[Input, Output]):
    """给 Runnable 添加固定的 config/kwargs"""
    bound: Runnable[Input, Output]
    config: RunnableConfig
    
    def invoke(self, input, config=None):
        return self.bound.invoke(input, merge_configs(self.config, config))
```

`chain.with_retry()`, `chain.with_fallbacks()`, `chain.bind(stop=[...])` 都返回 `RunnableBinding`。

---

## 📖 第二章：RunnableConfig — 全局上下文

### 文件：`runnables/config.py`

```python
class RunnableConfig(TypedDict, total=False):
    tags: list[str]           # 标签，用于过滤 callback 事件
    metadata: dict[str, Any]  # 元数据，透传给 callback
    callbacks: Callbacks      # 回调处理器列表
    run_name: str             # 运行名称（显示在 LangSmith）
    max_concurrency: int      # 并发上限
    recursion_limit: int      # 防止无限递归
    configurable: dict        # 运行时动态配置（用于热插拔组件）
```

**关键函数**：
- `ensure_config()` - 确保 config 不为 None
- `merge_configs(*configs)` - 合并多个 config（按列表追加 callbacks，后者覆盖前者的 metadata）
- `patch_config(config, **changes)` - 得到一个修改了部分字段的 config 副本

---

## 📖 第三章：Chat Models — LLM 封装

### 文件：`language_models/chat_models.py`

**调用链**（非常重要！）：

```
invoke(messages)
  └── _call_with_config()            # 启动 callback：on_chat_model_start
        └── _generate(messages)      # 子类实现：调用真实 API
              └── ChatResult         # 包含 ChatGeneration 列表
                    └── AIMessage    # 最终返回
```

```python
class BaseChatModel(BaseLanguageModel[BaseMessage]):
    
    def invoke(self, input, config=None, **kwargs):
        # 将 input 转换成消息列表（支持字符串、消息列表等多种格式）
        messages = self._convert_input(input).to_messages()
        result = self._call_with_config(self._generate, messages, config, **kwargs)
        return result.generations[0].message
    
    @abstractmethod
    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        """子类实现这个：调用具体的 LLM API"""
        ...
    
    def stream(self, input, config=None, **kwargs):
        # 调用 _stream() 方法（子类可选实现）
        # 如果子类没有实现 _stream，则 fallback 到 invoke 后 yield 整体结果
        ...
```

**关键洞察**：`BaseChatModel._generate` 是唯一必须实现的抽象方法。实现一个新的 LLM 提供商，核心就是实现这个方法。

---

## 📖 第四章：Tools — 能力赋予 Agent 的工具

### 文件：`tools/base.py`

**类层次**：
```
RunnableSerializable[str|dict|ToolCall, Any]
  └── BaseTool
        ├── StructuredTool      ← @tool 装饰器产生的
        └── 各种具体工具
```

**调用链**：
```
tool.invoke(tool_call)
  └── tool.run(tool_input)
        ├── 验证输入 (args_schema.model_validate)
        ├── 调用 _run(*args, **kwargs)    ← 子类实现
        └── 处理错误 (handle_tool_error)
```

```python
class BaseTool(RunnableSerializable):
    name: str          # 工具名称（LLM 通过此名调用）
    description: str   # 描述（告诉 LLM 何时如何使用）
    args_schema: Type[BaseModel]  # 用 Pydantic 验证 LLM 的参数
    
    @abstractmethod
    def _run(self, **kwargs) -> Any:
        """实际执行逻辑"""
        ...
    
    def invoke(self, input: str | dict | ToolCall, config=None):
        # 如果 input 是 ToolCall（来自 LLM），提取参数
        tool_input, kwargs = self._parse_input(input)
        return self.run(tool_input, **kwargs)
```

### @tool 装饰器（`tools/convert.py`）

```python
@tool
def search(query: str) -> str:
    """搜索网络"""
    return f"搜索结果: {query}"

# 等价于：
search_tool = StructuredTool(
    name="search",
    description="搜索网络",
    func=search,
    args_schema=...  # 从函数签名自动生成的 Pydantic 模型
)
```

---

## 📖 第五章：Callbacks — 观察者模式

### 文件：`callbacks/base.py`

**事件系统**（共 20+ 个 on_* 事件）：

```python
class BaseCallbackHandler:
    def on_llm_start(self, serialized, prompts, **kwargs): ...
    def on_llm_new_token(self, token, **kwargs): ...          # streaming
    def on_llm_end(self, response, **kwargs): ...
    def on_llm_error(self, error, **kwargs): ...
    def on_chain_start(self, serialized, inputs, **kwargs): ...
    def on_chain_end(self, outputs, **kwargs): ...
    def on_tool_start(self, serialized, input_str, **kwargs): ...
    def on_tool_end(self, output, **kwargs): ...
    def on_agent_action(self, action, **kwargs): ...
    def on_agent_finish(self, finish, **kwargs): ...
    # ...
```

**关键洞察**：回调系统是 LangChain 的可观测性基础。LangSmith、ConsoleCallbackHandler 都是实现了这个接口的处理器。

### CallbackManager（事件分发）

```python
class CallbackManager:
    handlers: list[BaseCallbackHandler]
    
    def on_chain_start(self, serialized, inputs, **kwargs):
        for handler in self.handlers:
            handler.on_chain_start(serialized, inputs, **kwargs)
```

---

## 📖 第六章：Messages — LLM 会话协议

### 文件：`messages/`

```python
class BaseMessage:
    content: str | list  # 内容（支持多模态：文本/图片/文件）
    type: str            # 类型标识
    
# 消息类型：
HumanMessage(content="用户输入")
AIMessage(content="模型回复", tool_calls=[...])  # 可以包含工具调用
SystemMessage(content="系统提示")
ToolMessage(content="工具执行结果", tool_call_id="...")

# AIMessage 中的工具调用：
AIMessage(
    content="",
    tool_calls=[{
        "id": "call_123",
        "name": "search",
        "args": {"query": "Python"}
    }]
)
```

---

## 📖 第七章：Agent 工作原理

### 现代 Agent 的核心循环（ReAct 模式）

```python
# 伪代码描述 Agent 的核心工作原理
def agent_loop(messages, tools, llm):
    while True:
        # 1. LLM 决策：是否调用工具，调用哪个
        response = llm.invoke(messages)  # 返回 AIMessage
        
        if not response.tool_calls:
            # 没有工具调用 → 任务完成，返回结果
            return response
        
        # 2. 执行工具调用
        messages.append(response)  # 添加 AIMessage（含 tool_calls）
        for tool_call in response.tool_calls:
            tool = tools[tool_call["name"]]
            result = tool.invoke(tool_call)
            messages.append(ToolMessage(
                content=str(result),
                tool_call_id=tool_call["id"]
            ))
        
        # 3. 把工具结果反馈给 LLM，继续循环
```

### 工具绑定到模型

```python
# LLM 如何"知道"有哪些工具？
llm_with_tools = llm.bind_tools(tools)
# 这实际上是：
# llm.bind(tools=[tool.as_tool_definition() for tool in tools])
# 把工具的 JSON Schema 加入到 API 请求的 tools 字段
```

---

## 📖 第八章：关键设计模式总结

### 1. 协议模式（Protocol Pattern）
`Runnable[Input, Output]` 是一个泛型抽象基类，定义了统一接口。任何实现 `invoke` 的对象都可以参与组合。

### 2. 管道模式（Pipeline Pattern）
`|` 操作符将多个 Runnable 串联，数据从左到右流动，形成 DAG（有向无环图）。

### 3. 装饰器模式（Decorator Pattern）
`RunnableBinding` 包裹一个 Runnable，注入额外的 config（retry、fallback、tags 等），不改变接口。

### 4. 工厂/转换函数（Factory Pattern）
`coerce_to_runnable()` 将 Python 字典、函数、列表自动转换为对应的 Runnable 实现。

### 5. 观察者模式（Observer Pattern）
Callbacks 系统解耦了"执行"与"观测"——执行逻辑不知道谁在监听事件。

### 6. 策略模式（Strategy Pattern）
`BaseChatModel._generate` 是策略接口，每个 LLM 提供商（OpenAI、DeepSeek、Anthropic）都是一个具体策略。

---

## 🎯 源码阅读顺序建议

### 第一轮（理解基础，3 天）
1. `runnables/base.py` 前 800 行 → 理解 `Runnable` ABC + `RunnableSequence` + `RunnableParallel`
2. `runnables/config.py` → 理解 `RunnableConfig` 数据结构
3. `messages/` 目录 → 理解消息协议
4. `language_models/chat_models.py` 前 500 行 → 理解 LLM 封装

### 第二轮（深入工具与 Agent，2 天）
5. `tools/base.py` → 理解 `BaseTool` 和调用链
6. `tools/convert.py` → 理解 `@tool` 装饰器如何生成 Pydantic schema
7. `callbacks/base.py` → 理解事件系统

### 第三轮（精通高级特性，2 天）
8. `runnables/passthrough.py` → 理解 `RunnablePassthrough` 和 `RunnableAssign`
9. `runnables/branch.py` → 理解条件路由
10. `runnables/history.py` → 理解历史管理
11. `runnables/configurable.py` → 理解运行时热替换

### 第四轮（自己设计 Agent）
基于以上理解，参考 [Level 8](./level8_your_application/) 来设计自己的 Agent。

---

## 💡 学完后你能做什么

掌握这些设计后，自己实现一个 Mini LangChain 需要：
1. 实现 `Runnable` ABC + `RunnableSequence`（`|` 操作符）
2. 实现 `BaseChatModel`（包装任意 LLM API）
3. 实现 `BaseTool` + 工具描述（JSON Schema）
4. 实现 Agent 循环（消息累积 + 工具调用）

这正是 [fff_agent](../fff_agent/) 项目和 [mini-deer-flow](../mini-deer-flow/) 的目标！
