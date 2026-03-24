# LangChain 学习之旅 🚀

> 从 Runnable 的"你好世界"，到构建自己的 AI 应用

一个**8 个循序渐进的 Level**，帮助你深入理解 LangChain 的核心概念和实战应用。

---

## 📚 学习路线图

| Level | 题目 | 核心概念 | 难度 | 时间 |
|-------|------|---------|------|------|
| **1** | Runnable 基础 | Runnable 接口、Lambda 包装 | ⭐ | 20 min |
| **2** | Prompt + LLM | PromptTemplate、ChatOpenAI | ⭐⭐ | 30 min |
| **3** | 完整 Chain | 组合（\|）、数据流 | ⭐⭐ | 30 min |
| **4** | Output Parsers | 各种解析器、结构化输出 | ⭐⭐⭐ | 40 min |
| **5** | 复杂链组合 | Parallel、Conditional、Map | ⭐⭐⭐ | 45 min |
| **6** | RAG 系统 | 向量数据库、检索增强 | ⭐⭐⭐⭐ | 60 min |
| **7** | Agent 系统 | 工具调用、自主决策 | ⭐⭐⭐⭐ | 60 min |
| **8** | 你的应用 | 综合项目、完全定制 | ⭐⭐⭐⭐⭐ | 自由 |

---

## 🎯 每个 Level 包含什么

每个 Level 目录都有：

```
levelX_topic/
├── main.py              # ✅ 完整可运行代码，带详细注释
├── README.md            # 📖 概念讲解 + 练习题
└── utils.py             # (可选) 辅助函数
```

### 运行方式

```bash
# 进入某个 level
cd /level1_runnable_basics

# 运行代码
python main.py

# 或者 (推荐，使用虚拟环境)
poetry run python main.py
```

---

## 📖 Level 详解

### Level 1：Runnable 基础 ⭐

**目标**：理解什么是 Runnable，以及为什么它如此强大

**你将学到**：
- Runnable 接口和三个魔法方法：invoke, batch, stream
- 用 RunnableLambda 包装普通函数
- 自动获得的超能力：并行处理、异步操作、类型推断

**核心代码**：
```python
from langchain_core.runnables import RunnableLambda

# 普通函数
def add_one(x: int) -> int:
    return x + 1

# 包装成 Runnable
runnable = RunnableLambda(add_one)

# 自动获得这些方法
runnable.invoke(5)              # 6
runnable.batch([1, 2, 3])       # [2, 3, 4]
for chunk in runnable.stream(5):
    print(chunk)                # 6
```

**练习**：
- [ ] 创建一个计算阶乘的 RunnableLambda
- [ ] 使用 batch 处理多个输入
- [ ] 尝试使用 Schema 验证

---

### Level 2：Prompt + LLM ⭐⭐

**目标**：了解 Prompt 模板和 LLM 调用的基础

**你将学到**：
- PromptTemplate 的创建和使用
- ChatOpenAI 的基本调用
- Prompt 和 LLM 都是 Runnable！

**核心代码**：
```python
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

# 1. Prompt 是 Runnable[dict, PromptValue]
prompt = PromptTemplate(
    input_variables=["topic"],
    template="告诉我关于 {topic} 的三个有趣的事实"
)

# 2. LLM 是 Runnable[PromptValue, AIMessage]
llm = ChatOpenAI(model="gpt-4", temperature=0.7)

# 3. 分别使用
formatted = prompt.invoke({"topic": "机器学习"})
response = llm.invoke(formatted)
print(response.content)
```

**练习**：
- [ ] 创建不同的 Prompt 模板
- [ ] 尝试不同的 temperature 值
- [ ] 使用 batch 并行调用 LLM

---

### Level 3：完整 Chain ⭐⭐

**目标**：学会用 `|` 组合 Runnable，创建完整的链

**你将学到**：
- 使用 `|` 操作符组合 Runnable
- StrOutputParser 提取文本
- 类型安全的链式操作

**核心代码**：
```python
from langchain_core.output_parsers import StrOutputParser

# 组合：Prompt | LLM | Parser
chain = prompt | llm | StrOutputParser()

# 现在 chain 是 Runnable[dict, str]
result = chain.invoke({"topic": "深度学习"})
print(result)  # 直接是字符串！

# 自动支持所有方法
results = chain.batch([
    {"topic": "机器学习"},
    {"topic": "深度学习"}
])

for chunk in chain.stream({"topic": "强化学习"}):
    print(chunk, end="", flush=True)
```

**练习**：
- [ ] 创建一个 QA 链
- [ ] 使用 stream 实现类似 ChatGPT 的流式输出
- [ ] 添加回调用于追踪执行

---

### Level 4：Output Parsers ⭐⭐⭐

**目标**：掌握各种输出解析器，处理结构化数据

**你将学到**：
- StrOutputParser - 字符串解析
- JsonOutputParser - JSON 解析
- PydanticOutputParser - 对象解析
- CommaSeparatedListOutputParser - 列表解析

**核心代码**：
```python
from langchain_core.output_parsers import (
    JsonOutputParser, PydanticOutputParser
)
from pydantic import BaseModel
from typing import List

# 1. 定义输出结构
class Recipe(BaseModel):
    name: str
    ingredients: List[str]
    steps: List[str]

# 2. 创建 Parser
parser = PydanticOutputParser(pydantic_object=Recipe)

# 3. 更新 Prompt（告诉 LLM 期望的格式）
prompt = PromptTemplate(
    input_variables=["dish"],
    template="提供一个 {dish} 的食谱\n{format_instructions}",
    partial_variables={"format_instructions": parser.get_format_instructions()}
)

# 4. 组合
chain = prompt | llm | parser

# 5. 获得结构化输出
recipe = chain.invoke({"dish": "红烧肉"})
print(recipe.name)
print(recipe.ingredients)
```

**练习**：
- [ ] 为 JSON 输出创建自定义类
- [ ] 处理解析错误（try-except）
- [ ] 创建列表和嵌套对象解析器

---

### Level 5：复杂链组合 ⭐⭐⭐

**目标**：学会高级组合技巧（并行、条件、映射）

**你将学到**：
- RunnableParallel - 并行执行
- RunnableMap - 映射操作
- Conditional 路由
- assign() 方法添加字段

**核心代码**：
```python
from langchain_core.runnables import RunnableParallel

# 1. 并行执行多个链
parallel_chain = RunnableParallel(
    analysis=analysis_chain,
    summary=summary_chain,
    keywords=keywords_chain
)

# 一次调用，三个结果
result = parallel_chain.invoke(text)
# {
#   "analysis": "...",
#   "summary": "...",
#   "keywords": [...]
# }

# 2. 条件路由
from langchain_core.runnables import RunnableBranch

def route_by_sentiment(input_dict):
    if input_dict["sentiment"] == "negative":
        return negative_response_chain
    elif input_dict["sentiment"] == "positive":
        return positive_response_chain
    else:
        return neutral_response_chain

# 3. assign() 添加新字段
chain = (
    initial_chain
    .assign(
        sentiment=sentiment_analysis_chain,
        keywords=extract_keywords_chain
    )
)
```

**练习**：
- [ ] 创建并行分析四个指标
- [ ] 实现条件路由（根据输入类型选择不同链）
- [ ] 组合多个 assign() 调用

---

### Level 6：RAG 系统 ⭐⭐⭐⭐

**目标**：构建检索增强生成(RAG)系统

**你将学到**：
- 向量数据库集成（Chroma、FAISS）
- 文件加载和分割
- 检索器(Retriever)的使用
- 完整的 RAG 流程

**核心代码**：
```python
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PDFLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

# 1. 加载文档
loader = PDFLoader("document.pdf")
documents = loader.load()

# 2. 分割文本
splitter = CharacterTextSplitter(chunk_size=1000)
chunks = splitter.split_documents(documents)

# 3. 创建向量数据库
embeddings = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(chunks, embeddings)

# 4. 创建检索器
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# 5. 构建 RAG 链
rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | parser
)

# 6. 使用
result = rag_chain.invoke("问题是什么？")
```

**练习**：
- [ ] 用自己的文档构建 RAG
- [ ] 尝试不同的检索参数（k 值、搜索类型）
- [ ] 添加重排序(Reranker)提高质量

---

### Level 7：Agent 系统 ⭐⭐⭐⭐

**目标**：构建能够自动选择和使用工具的 Agent

**你将学到**：
- 定义工具(Tool)
- 创建 Agent 执行器
- 工具选择和执行的循环
- 处理工具调用错误

**核心代码**：
```python
from langchain.agents import tool, AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

# 1. 定义工具
@tool
def get_weather(location: str) -> str:
    """获取指定地点的天气"""
    return f"{location} 的天气是晴天，温度 25°C"

@tool
def calculate(expression: str) -> str:
    """计算数学表达式"""
    return f"结果是: {eval(expression)}"

tools = [get_weather, calculate]

# 2. 创建 Agent
llm = ChatOpenAI(model="gpt-4")

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个有用的助手，可以使用工具。"),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

agent = create_openai_functions_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# 3. 使用
result = executor.invoke({
    "input": "北京的天气怎样？3+5等于多少？"
})
print(result["output"])
```

**练习**：
- [ ] 添加你自己的工具（数据库查询、API 调用等）
- [ ] 处理工具调用失败的情况
- [ ] 使用 memory 记住对话历史

---

### Level 8：你的应用 ⭐⭐⭐⭐⭐

**目标**：设计和实现你自己的完整应用

**选项**：

**选项 A：个性化推荐系统**
```python
# 用户输入行为 → 分析偏好 → 推荐内容 → 个性化讲解
# 涉及：Agent、RAG、Parser、并行处理
```

**选项 B：客服系统**
```python
# 用户问题 → 分类 → 检索知识库 → 生成回复 → 收集反馈
# 涉及：分类、检索、Agent、追踪
```

**选项 C：数据分析助手**
```python
# 上传数据 → 数据探索 → 生成查询 → 执行代码 → 可视化
# 涉及：工具使用、代码执行、Parser
```

**选项 D：内容创建系统**
```python
# 创意 → 大纲生成 → 段落写作 → 编辑修改 → 发布
# 涉及：多链协作、条件路由、反馈循环
```

**框架**：
```python
# 选择一个想法，实现完整系统：

class MyLLMApplication:
    def __init__(self):
        self.chain1 = ...  # 分析链
        self.chain2 = ...  # 处理链
        self.chain3 = ...  # 生成链
    
    def run(self, input: str):
        # 整合所有链
        step1 = self.chain1.invoke(input)
        step2 = self.chain2.invoke(step1)
        step3 = self.chain3.invoke(step2)
        return step3

# 测试
app = MyLLMApplication()
result = app.run("用户输入")
```

**评估标准**：
- ✅ 至少使用 3 个不同的 Runnable
- ✅ 实现错误处理和日志
- ✅ 有流式或批量处理
- ✅ 完整的文档和示例

---

## 🎓 学习建议

### 时间分配
- **快速学习者**：3-4 小时完成所有 Level
- **正常学习者**：1-2 周，每天 1-2 个 Level
- **深度学习者**：2-4 周，反复研究代码

### 学习方法
1. **阅读** README.md 理解概念
2. **运行** main.py 看实际效果
3. **修改** 代码，尝试变化
4. **编写** 练习题的解决方案
5. **扩展** 添加自己的功能

### 常见问题

**Q: 需要 OpenAI API 密钥吗？**
A: 是的，但可以用 FakeOpenAI 测试（不消耗费用）

**Q: 如何离线运行？**
A: 使用本地 LLM（Ollama）或 FakeOpenAI

**Q: 需要什么 Python 版本？**
A: Python 3.8+，推荐 3.10+

---

## 📚 额外资源

- 📖 [LangChain 官方文档](https://python.langchain.com/)
- 🎥 [LangChain YouTube 教程](https://www.youtube.com/langchain)
- 💬 [LangChain Discord 社区](https://discord.gg/langchain)
- 📝 [CORE_CONCEPTS_GUIDE.md](../CORE_CONCEPTS_GUIDE.md) - 深度概念讲解

---

## 🚀 如何开始

```bash
# 1. 进入 level1
cd /level1_runnable_basics

# 2. 安装依赖
pip install -r requirements.txt

# 3. 设置 API key
export OPENAI_API_KEY="你的密钥"

# 4. 运行代码
python main.py

# 5. 阅读 README 了解更多
cat README.md
```

---

**祝你学习愉快！🎉**

> "从 Runnable 的"你好世界"开始，最终你将能用 LangChain 构建任何 AI 应用。"

---

**版本**：1.0  
**最后更新**：2026-03-19  
**维护者**：LangChain Learning Community
