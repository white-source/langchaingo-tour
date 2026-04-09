"""
Level 6: RAG 系统（检索增强生成）⭐⭐⭐⭐

学习目标：
1. 理解 RAG 的核心架构：Retrieve → Augment → Generate
2. 实现 BaseRetriever（Runnable 的又一子类）
3. 掌握经典 RAG 链的组合模式
4. 理解 Document 数据结构
5. 学会 RunnablePassthrough.assign 在 RAG 中的关键作用

源码参考：
- BaseRetriever: langchain_core/retrievers.py line 55
- Document: langchain_core/documents/base.py
- 关键调用链: input → retriever → docs → prompt → llm → answer

注意：本例使用模拟的 LLM 和向量数据库，无需 API 密钥
"""

from __future__ import annotations

import math
import re
from typing import Any

from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import FakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import (
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)

print("=" * 80)
print("Level 6: RAG 系统 — 源码深度解析")
print("=" * 80)


# ============================================================================
# 第一部分：Document 数据结构
# ============================================================================
print("\n" + "─" * 60)
print("【1】Document：RAG 的基本数据单元")
print("─" * 60)

# 源码：langchain_core/documents/base.py
# class Document(BaseModel):
#     page_content: str    # 文档内容
#     metadata: dict       # 元数据（来源、页码、时间等）
#     id: str | None       # 唯一标识

# 创建示例文档库
knowledge_base = [
    Document(
        page_content="Python 是一种高级编程语言，由 Guido van Rossum 于 1991 年创建。"
        "Python 以其简洁的语法著称，支持多种编程范式。",
        metadata={"source": "python_intro.txt", "page": 1, "topic": "python"},
    ),
    Document(
        page_content="LangChain 是一个用于构建 LLM 应用的框架。"
        "其核心是 Runnable 协议，使用 | 操作符组合各种组件。",
        metadata={"source": "langchain_guide.txt", "page": 1, "topic": "langchain"},
    ),
    Document(
        page_content="RAG（检索增强生成）是一种让 LLM 访问外部知识的技术。"
        "它通过检索相关文档 + 将文档作为上下文提供给 LLM 来增强回答质量。",
        metadata={"source": "rag_tutorial.txt", "page": 1, "topic": "rag"},
    ),
    Document(
        page_content="向量数据库是一种专门存储和检索高维向量的数据库。"
        "常见的向量数据库有 FAISS、Chroma、Pinecone 等。",
        metadata={"source": "vector_db.txt", "page": 1, "topic": "database"},
    ),
    Document(
        page_content="Transformer 架构由 Attention is All You Need 论文提出。"
        "它使用自注意力机制，是现代大语言模型的基础架构。",
        metadata={"source": "transformer.txt", "page": 1, "topic": "ml"},
    ),
    Document(
        page_content="Python 的异步编程使用 async/await 关键字。"
        "asyncio 是 Python 标准库中的异步 IO 框架，LangChain 的 ainvoke 使用它。",
        metadata={"source": "python_async.txt", "page": 2, "topic": "python"},
    ),
]

print(f"知识库共 {len(knowledge_base)} 个文档")
print(f"示例文档: {knowledge_base[0].page_content[:50]}...")
print(f"元数据: {knowledge_base[0].metadata}")


# ============================================================================
# 第二部分：实现 BaseRetriever（关键：它也是 Runnable）
# ############################################################################
print("\n" + "─" * 60)
print("【2】自定义 Retriever — 继承 BaseRetriever（Runnable 子类）")
print("─" * 60)

# 源码关键点（retrievers.py line 55）：
#
# class BaseRetriever(RunnableSerializable[str, list[Document]]):
#     """抽象基类，唯一需要实现的方法：_get_relevant_documents"""
#
# 注意：BaseRetriever 本身就是 Runnable[str, list[Document]]
# 这意味着它可以直接参与 | 组合！


class TFIDFRetriever(BaseRetriever):
    """
    基于 TF-IDF 的简单检索器（无需向量数据库）

    真实场景中你会用：
    - FAISS + OpenAIEmbeddings
    - Chroma + HuggingFaceEmbeddings
    - Pinecone + 任意 Embeddings

    这里用简单的关键词匹配模拟向量相似度
    """

    docs: list[Document]
    k: int = 3

    def _get_relevant_documents(self, query: str) -> list[Document]:
        """
        这是 BaseRetriever 唯一需要实现的抽象方法
        BaseRetriever.invoke() 会调用这个方法
        """
        # 简单的 TF-IDF 模拟：计算查询词与文档的关键词重叠
        query_words = set(re.findall(r"\w+", query.lower()))

        scored_docs = []
        for doc in self.docs:
            doc_words = set(re.findall(r"\w+", doc.page_content.lower()))
            overlap = len(query_words & doc_words)
            # 用 TF-IDF 简化版：重叠词数 / 文档词数的对数
            score = overlap / (1 + math.log(len(doc_words) + 1))
            scored_docs.append((score, doc))

        # 按分数降序排列，取前 k 个
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored_docs[: self.k]]


# 创建检索器
retriever = TFIDFRetriever(docs=knowledge_base, k=2)

# 测试：BaseRetriever 实现了 Runnable 接口
print("BaseRetriever 继承了 Runnable，可以直接调用 invoke：")
test_query = "Python 异步编程"
retrieved = retriever.invoke(test_query)
print(f"  查询: {test_query!r}")
print(f"  检索到 {len(retrieved)} 个文档：")
for doc in retrieved:
    print(f"  - [{doc.metadata['source']}]: {doc.page_content[:60]}...")

print("\n📌 设计洞察：")
print("  BaseRetriever 是 Runnable[str, list[Document]]")
print("  可以直接用 | 串联：retriever | format_docs | prompt | llm")


# ============================================================================
# 第三部分：经典 RAG 链组合
# ============================================================================
print("\n" + "─" * 60)
print("【3】经典 RAG 链：三种写法对比")
print("─" * 60)


def format_docs(docs: list[Document]) -> str:
    """将文档列表格式化为字符串，作为 LLM 的上下文"""
    formatted = []
    for i, doc in enumerate(docs, 1):
        formatted.append(
            f"[文档 {i}]（来源: {doc.metadata['source']}）\n{doc.page_content}"
        )
    return "\n\n".join(formatted)


# Prompt 模板
rag_prompt = ChatPromptTemplate.from_template(
    """
你是一个知识问答助手。请根据以下检索到的文档回答问题。

检索到的相关文档：
{context}

用户问题：{question}

请基于文档内容给出准确、简洁的回答。如果文档中没有相关信息，请如实说明。
"""
)


# 模拟 LLM（真实场景替换为 ChatOpenAI、ChatDeepSeek 等）
class RAGChatModel(FakeChatModel):
    """模拟 LLM，根据上下文生成回答"""

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        from langchain_core.outputs import ChatGeneration, ChatResult

        # 从最后一条消息获取内容
        last_msg = messages[-1].content
        # 提取问题部分
        q_match = re.search(r"用户问题：(.+)", last_msg)
        question = q_match.group(1).strip() if q_match else "未知问题"

        # 提取文档数量
        doc_count = last_msg.count("[文档 ")

        response_content = (
            f"[模拟回答] 根据检索到的 {doc_count} 篇相关文档，"
            f"关于「{question}」的回答是：\n"
            "文档中提供了相关信息，经过分析后给出综合回答。"
            "（真实场景中，LLM 会根据文档内容生成具体回答）"
        )
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=response_content))]
        )


llm = RAGChatModel()

# ─────────────────────────────
# 写法 1：手动步骤（最清晰，便于理解原理）
# ─────────────────────────────
print("写法 1：手动步骤（理解 RAG 数据流）")


def rag_manual(question: str) -> str:
    # Step 1: Retrieve
    docs = retriever.invoke(question)
    # Step 2: Augment (格式化上下文)
    context = format_docs(docs)
    # Step 3: Generate
    prompt_value = rag_prompt.invoke({"question": question, "context": context})
    response = llm.invoke(prompt_value)
    return StrOutputParser().invoke(response)


q1 = "LangChain 的核心是什么？"
print(f"  问题: {q1}")
answer1 = rag_manual(q1)
print(f"  回答: {answer1[:100]}...")


# ─────────────────────────────
# 写法 2：用 | 组合（简洁但信息流不透明）
# ─────────────────────────────
print("\n写法 2：| 链式组合")

rag_chain_v2 = (
    retriever
    | RunnableLambda(format_docs)
    | RunnableLambda(lambda ctx: rag_prompt.invoke({"question": "?", "context": ctx}))
    | llm
    | StrOutputParser()
)
# 注意：这个写法有问题！question 没有传入 prompt！
# 这就是为什么要用写法 3


# ─────────────────────────────
# 写法 3：经典 RAG 链（最常见，生产推荐）
# ─────────────────────────────
print("写法 3：经典 RAG 链（推荐模式）")
print()

# 核心技巧：RunnablePassthrough 保留原始问题
#
# 数据流图：
# question (str)
#   ↓
#   ├─ "question" → RunnablePassthrough() → 原样保留 question
#   └─ "context"  → retriever | format_docs → 检索并格式化文档
#   ↓
#   {"question": "...", "context": "..."}
#   ↓
#   rag_prompt → ChatPromptValue
#   ↓
#   llm → AIMessage
#   ↓
#   StrOutputParser → str

rag_chain_v3 = (
    RunnableParallel(
        question=RunnablePassthrough(),  # 保留原始问题
        context=(retriever | RunnableLambda(format_docs)),  # 检索并格式化
    )
    | rag_prompt
    | llm
    | StrOutputParser()
)

q2 = "LangChain 的核心是什么？"
q3 = "RAG 技术是如何工作的？"

for q in [q2, q3]:
    print(f"  问题: {q}")
    answer = rag_chain_v3.invoke(q)
    print(f"  回答: {answer[:120]}...")
    print()

print("📌 设计洞察：")
print("  经典 RAG 链的核心是'分叉再合并'：")
print("  - 分叉：同一个 question 同时送入 Passthrough 和 Retriever")
print("  - 合并：RunnableParallel({question:..., context:...}) 聚合成字典")
print("  - 这个字典恰好是 rag_prompt 的输入格式")


# ============================================================================
# 第四部分：用 RunnablePassthrough.assign 的方式（更紧凑）
# ============================================================================
print("\n" + "─" * 60)
print("【4】RunnablePassthrough.assign 写法对比")
print("─" * 60)

# assign 写法（等价但更紧凑）
rag_chain_assign = (
    RunnablePassthrough.assign(context=lambda x: format_docs(retriever.invoke(x)))
    | RunnableLambda(
        lambda x: rag_prompt.invoke(
            {
                "question": x if isinstance(x, str) else x.get("question", ""),
                "context": x.get("context", "") if isinstance(x, dict) else "",
            }
        )
    )
    | llm
    | StrOutputParser()
)

# 更清晰的 assign 写法（question 在字典中）
rag_chain_assign_v2 = (
    # 假设输入是 {"question": "..."}
    RunnablePassthrough.assign(
        context=RunnableLambda(lambda x: format_docs(retriever.invoke(x["question"])))
    )
    | rag_prompt
    | llm
    | StrOutputParser()
)

print("assign 写法（输入为 dict）：")
result = rag_chain_assign_v2.invoke({"question": "Python 异步编程"})
print(f"  问题: Python 异步编程")
print(f"  回答: {result[:120]}...")

print("\n📌 两种写法的差别：")
print("  写法3 (RunnableParallel)：输入是 str，链内部将 str 和检索结果打包成 dict")
print("  写法4 (assign)：输入已经是 dict，assign 向 dict 追加 context 字段")
print("  两种都是 RAG 常见模式，选哪个取决于上下游的数据格式")


# ============================================================================
# 第五部分：带引用来源的 RAG（生产级功能）
# ============================================================================
print("\n" + "─" * 60)
print("【5】带引用来源的 RAG")
print("─" * 60)


def format_docs_with_sources(docs: list[Document]) -> dict:
    """返回格式化文档和来源列表"""
    formatted = format_docs(docs)
    sources = [doc.metadata["source"] for doc in docs]
    return {"context": formatted, "sources": list(set(sources))}


# 构建带来源的 RAG 链
rag_with_sources = RunnableParallel(
    answer=(
        RunnableParallel(
            question=RunnablePassthrough(),
            context=(retriever | RunnableLambda(format_docs)),
        )
        | rag_prompt
        | llm
        | StrOutputParser()
    ),
    sources=(
        retriever | RunnableLambda(lambda docs: [d.metadata["source"] for d in docs])
    ),
    num_docs=(retriever | RunnableLambda(len)),
)

q_with_sources = "向量数据库有哪些？"
result_with_sources = rag_with_sources.invoke(q_with_sources)
print(f"问题: {q_with_sources}")
print(f"回答: {result_with_sources['answer'][:100]}...")
print(f"引用来源: {result_with_sources['sources']}")
print(f"检索到文档数: {result_with_sources['num_docs']}")


# ============================================================================
# 第六部分：理解 RAG 的可视化（链结构）
# ============================================================================
print("\n" + "─" * 60)
print("【6】RAG 链的结构图（get_graph）")
print("─" * 60)

# LangChain 的 get_graph() 方法来自 runnables/graph.py
# 它通过遍历 Runnable 的 steps/bound 属性来构建 DAG
try:
    graph = rag_chain_v3.get_graph()
    print("RAG 链的节点：")
    for node_id, node in graph.nodes.items():
        node_name = getattr(node.data, "__name__", None) or type(node.data).__name__
        print(f"  [{node_id[:8]}] {node_name}")
except Exception:
    print("（graph 可视化需要额外依赖，跳过）")

print("\n手动描述 RAG 链的数据流：")
print(
    """
  question (str)
      │
      ├──────────────────────────────────┐
      │                                  │
  RunnablePassthrough              TFIDFRetriever
   (保留原始问题)                  (检索相关文档)
      │                                  │
      │                           format_docs
      │                           (转字符串)
      │                                  │
      └──────── dict(question, context) ─┘
                          │
                    rag_prompt (ChatPromptTemplate)
                          │
                    ChatPromptValue
                          │
                      llm (ChatModel)
                          │
                      AIMessage
                          │
                   StrOutputParser
                          │
                       str (最终回答)
"""
)


# ============================================================================
# 小结
# ============================================================================
print("=" * 80)
print("Level 6 完成！关键收获：")
print("=" * 80)
print(
    """
🔑 RAG 架构的三个核心步骤：
1. Retrieve（检索）：BaseRetriever.invoke(query) → list[Document]
2. Augment（增强）：将文档格式化，与原始问题组合成 prompt 输入
3. Generate（生成）：LLM 根据上下文生成回答

🔑 RAG 链中 RunnablePassthrough 的不可或缺性：
   - 问题：检索器消耗 question 之后，question 就"消失"了
   - 解决：用 RunnablePassthrough 开一个"旁路"保留 question
   - 最终：Parallel 将 question + context 合并成 prompt 的输入

🔑 BaseRetriever 是 Runnable[str, list[Document]]：
   - 实现 _get_relevant_documents 即可
   - 自动支持 invoke, batch, astream 等所有 Runnable 方法

🔑 经典写法模式：
   RunnableParallel(question=PassThrough, context=retriever|format) | prompt | llm | parser

下一步 Level 7：Agent 系统 —— LLM 自主决策调用工具！
"""
)
