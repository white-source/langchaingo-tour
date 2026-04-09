"""
Level 5: 复杂链组合 ⭐⭐⭐

学习目标：
1. RunnableParallel  - 并行执行，理解内部线程池实现
2. RunnablePassthrough - 数据直通/扩展
3. RunnableBranch - 条件路由
4. 深入理解 coerce_to_runnable() 的类型转换魔法

源码参考：
- RunnableParallel: langchain_core/runnables/base.py line 3565
- RunnablePassthrough: langchain_core/runnables/passthrough.py
- RunnableBranch: langchain_core/runnables/branch.py

注意：本例只展示概念，不需要真实 API
"""

from __future__ import annotations

import time
from langchain_core.runnables import (
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
    RunnableBranch,
)

print("=" * 80)
print("Level 5: 复杂组合 — 源码深度解析")
print("=" * 80)


# ============================================================================
# 第一部分：RunnableParallel 内部原理
# ============================================================================
print("\n" + "─" * 60)
print("【1】RunnableParallel：并行执行的秘密")
print("─" * 60)

# 源码关键点（base.py line 3565）：
#
# class RunnableParallel(RunnableSerializable[Input, dict]):
#     steps__: Mapping[str, Runnable]
#
#     def invoke(self, input, config=None):
#         # 使用线程池并行执行所有 steps
#         with get_executor_for_config(config) as executor:
#             futures = {
#                 key: executor.submit(step.invoke, input, config)
#                 for key, step in self.steps__.items()
#             }
#             return {key: f.result() for key, f in futures.items()}
#
# 注意：
# - 同步版本：ThreadPoolExecutor（每个 step 在独立线程中运行）
# - 异步版本：asyncio.gather（真正的并发）
# - output 始终是 dict，key 是你指定的名字


def slow_uppercase(text: str) -> str:
    """模拟耗时操作：转大写"""
    time.sleep(0.1)
    return text.upper()


def slow_reverse(text: str) -> str:
    """模拟耗时操作：倒序"""
    time.sleep(0.1)
    return text[::-1]


def slow_len(text: str) -> int:
    """模拟耗时操作：统计长度"""
    time.sleep(0.1)
    return len(text)


# 创建三个耗时的处理步骤
step_upper = RunnableLambda(slow_uppercase)
step_reverse = RunnableLambda(slow_reverse)
step_len = RunnableLambda(slow_len)


# 串行版本（for 对比）
def serial_version(text: str) -> dict:
    start = time.time()
    result = {
        "upper": slow_uppercase(text),
        "reverse": slow_reverse(text),
        "length": slow_len(text),
    }
    elapsed = time.time() - start
    print(f"  串行耗时: {elapsed:.3f}s")
    return result


# 并行版本
parallel = RunnableParallel(
    upper=step_upper,
    reverse=step_reverse,
    length=step_len,
)

print("串行执行（3 × 0.1s = ~0.3s）：")
serial_result = serial_version("Hello LangChain")

print("\nRunnableParallel（内部用线程池，~0.1s）：")
start = time.time()
parallel_result = parallel.invoke("Hello LangChain")
elapsed = time.time() - start
print(f"  并行耗时: {elapsed:.3f}s")
print(f"  结果: {parallel_result}")

print("\n📌 设计洞察：")
print("  并行不是 'for input in inputs'（批处理）")
print("  而是 'for step in steps'（同一个 input，多个 step 同时执行）")


# ============================================================================
# 第二部分：字典字面量的自动转换
# ============================================================================
print("\n" + "─" * 60)
print("【2】字典字面量自动变 RunnableParallel")
print("─" * 60)

# 源码关键点（base.py line 2586 coerce_to_runnable）：
#
# def coerce_to_runnable(thing: RunnableLike) -> Runnable:
#     if isinstance(thing, Runnable):
#         return thing
#     elif callable(thing):
#         return RunnableLambda(thing)
#     elif isinstance(thing, dict):
#         return RunnableParallel(thing)  # ← 字典被自动转换！
#     else:
#         raise TypeError(...)

add_prefix = RunnableLambda(lambda x: f"[INPUT] {x}")

# 这两种写法完全等价！
chain_v1 = add_prefix | RunnableParallel(
    upper=RunnableLambda(str.upper),
    lower=RunnableLambda(str.lower),
)

chain_v2 = add_prefix | {  # ← 字典字面量被 coerce_to_runnable 自动转换
    "upper": RunnableLambda(str.upper),
    "lower": RunnableLambda(str.lower),
}

r1 = chain_v1.invoke("hello")
r2 = chain_v2.invoke("hello")
print(f"链 v1 结果: {r1}")
print(f"链 v2 结果: {r2}")
print(f"结果相同: {r1 == r2}")

print("\n📌 设计洞察：")
print("  coerce_to_runnable() 是 LangChain 最重要的工厂函数")
print("  它让你用 Python 原生类型（dict, callable）构建链，无需显式包装")


# ============================================================================
# 第三部分：RunnablePassthrough 的双重用法
# ============================================================================
print("\n" + "─" * 60)
print("【3】RunnablePassthrough：数据直通 & 扩展")
print("─" * 60)

# 源码关键点（passthrough.py）：
#
# class RunnablePassthrough(RunnableSerializable[Input, Input]):
#     """直接透传 input，可以选择性地对 input 进行 side-effect 操作"""
#
# class RunnableAssign(RunnableSerializable[dict, dict]):
#     """扩展字典：保留原有 key，新增 runnable 计算的 key"""
#
# Passthrough.assign(key=runnable) → 返回一个 RunnableAssign

# 用法 1：直接透传
passthrough = RunnablePassthrough()
print("直接透传：")
print(f"  passthrough.invoke('hello') = {passthrough.invoke('hello')}")
print(f"  passthrough.invoke(42) = {passthrough.invoke(42)}")

# 用法 2：在链中透传（保留原始 input 同时传递到 parallel 的某个分支）
chain_with_passthrough = RunnableLambda(lambda x: x.upper()) | RunnableParallel(
    processed=RunnablePassthrough(),  # 透传处理后的值
    length=RunnableLambda(len),
    is_long=RunnableLambda(lambda x: len(x) > 5),
)

result = chain_with_passthrough.invoke("hello")
print(f"\n带 passthrough 的链结果: {result}")

# 用法 3：RunnableAssign（扩展字典，RAG 中常用！）
print("\nRunnablePassthrough.assign（字典扩展）：")


# 模拟 RAG 场景：原始查询 + 检索到的上下文
def fake_retrieve(query: str) -> list[str]:
    """模拟向量检索"""
    return [f"文档片段 1: 关于 {query}", f"文档片段 2: {query} 的相关内容"]


# 经典 RAG 链模式：
# 关键：assign 的输入必须是 dict（不能是 str）
# 通常先用 {"question": PassThrough} 将 str 转成 dict，再用 assign 添加 context
rag_prep_chain = RunnableLambda(
    lambda q: {"question": q}
) | RunnablePassthrough.assign(  # str → dict
    context=RunnableLambda(lambda x: fake_retrieve(x["question"]))
)

query = "Python 异步编程"
rag_input = rag_prep_chain.invoke(query)
print(f"  输入: '{query}'")
print(f"  经过 assign 后变成: {rag_input}")
print("  → 字符串先转成 dict，assign 再添加 context 字段")

print("\n📌 设计洞察：")
print("  RunnableAssign 是 RAG 链的关键：")
print("  {'question': input} + retrieve(input) → {'question': ..., 'context': [...]}")


# ============================================================================
# 第四部分：RunnableBranch 条件路由
# ############################################################################
print("\n" + "─" * 60)
print("【4】RunnableBranch：条件路由（if-elif-else 的 Runnable 版本）")
print("─" * 60)

# 源码关键点（branch.py）：
#
# class RunnableBranch(RunnableSerializable):
#     branches: Sequence[Tuple[Runnable, Runnable]]  # [(condition, handler)]
#     default: Runnable
#
#     def invoke(self, input, config=None):
#         for condition, handler in self.branches:
#             if condition.invoke(input, config):
#                 return handler.invoke(input, config)
#         return self.default.invoke(input, config)


def is_question(text: str) -> bool:
    return text.strip().endswith("?") or text.strip().endswith("？")


def is_greeting(text: str) -> bool:
    greetings = ["你好", "hello", "hi", "嗨", "Hey"]
    return any(g.lower() in text.lower() for g in greetings)


# 路由链
router = RunnableBranch(
    # (条件, 处理器) 对
    (
        RunnableLambda(is_question),
        RunnableLambda(lambda x: f"[问题回答] 你问的是：{x}"),
    ),
    (
        RunnableLambda(is_greeting),
        RunnableLambda(lambda x: f"[问候回复] 你好！收到你的问候：{x}"),
    ),
    # default：如果所有条件都不满足
    RunnableLambda(lambda x: f"[通用回复] 收到消息：{x}"),
)

test_inputs = [
    "Python 怎么学？",
    "你好啊！",
    "今天天气不错",
    "LangChain 的 Runnable 协议是什么？",
]

print("条件路由测试：")
for inp in test_inputs:
    result = router.invoke(inp)
    print(f"  输入: {inp!r}")
    print(f"  输出: {result}")
    print()

print("📌 设计洞察：")
print("  RunnableBranch 的 condition 也是 Runnable，这意味着：")
print("  - condition 可以是任意复杂的链（比如 prompt | llm | parser）")
print("  - 可以用 LLM 来做路由决策（意图识别 → 路由）")


# ============================================================================
# 第五部分：完整的组合链 — 模拟多路分析管道
# ============================================================================
print("\n" + "─" * 60)
print("【5】综合实战：多维度文本分析管道")
print("─" * 60)


# 模拟各种分析器（真实场景中这些是 prompt | llm | parser 链）
def analyze_sentiment(text: str) -> str:
    """模拟情感分析"""
    positive_words = ["好", "棒", "优秀", "喜欢", "great", "good", "love"]
    if any(w in text.lower() for w in positive_words):
        return "正向"
    negative_words = ["差", "糟", "讨厌", "hate", "bad", "terrible"]
    if any(w in text.lower() for w in negative_words):
        return "负向"
    return "中性"


def extract_keywords(text: str) -> list[str]:
    """模拟关键词提取"""
    words = text.replace("，", " ").replace("。", " ").replace("！", " ").split()
    return [w for w in words if len(w) > 1][:5]  # 取前 5 个词


def classify_topic(text: str) -> str:
    """模拟主题分类"""
    if any(w in text for w in ["Python", "代码", "编程", "AI", "模型"]):
        return "技术"
    if any(w in text for w in ["天气", "饮食", "运动", "健康"]):
        return "生活"
    return "其他"


# 构建分析管道
analysis_pipeline = (
    # 第一步：预处理 - 保留原始文本，添加长度信息
    RunnablePassthrough.assign(
        char_count=RunnableLambda(len),
        word_count=RunnableLambda(lambda x: len(x.split())),
    )
    |
    # 第二步：并行执行三种分析
    RunnablePassthrough.assign(
        sentiment=RunnableLambda(
            lambda x: analyze_sentiment(
                x if isinstance(x, str) else x.get("__root__", str(x))
            )
        ),
        keywords=RunnableLambda(
            lambda x: extract_keywords(x if isinstance(x, str) else str(x))
        ),
        topic=RunnableLambda(
            lambda x: classify_topic(x if isinstance(x, str) else str(x))
        ),
    )
)

# 更清晰的写法（字符串直接进入）：
clean_pipeline = RunnableParallel(
    original=RunnablePassthrough(),
    sentiment=RunnableLambda(analyze_sentiment),
    keywords=RunnableLambda(extract_keywords),
    topic=RunnableLambda(classify_topic),
    stats=RunnableLambda(
        lambda x: {"char_count": len(x), "word_count": len(x.split())}
    ),
)

test_texts = [
    "Python 真是太棒了，用它写 AI 很爽！",
    "今天天气很差，心情不太好",
    "langchain 的设计模式值得深入学习",
]

print("多维度文本分析结果：")
for text in test_texts:
    result = clean_pipeline.invoke(text)
    print(f"\n  输入: {text!r}")
    print(f"  情感: {result['sentiment']}")
    print(f"  主题: {result['topic']}")
    print(f"  关键词: {result['keywords']}")
    print(f"  统计: {result['stats']}")


# ============================================================================
# 第六部分：用链的方式做决策路由（真实 Agent 路由的简化版）
# ============================================================================
print("\n" + "─" * 60)
print("【6】智能路由：根据分析结果动态选择处理器")
print("─" * 60)


def handle_tech(data: dict) -> str:
    return f"技术问题回复：关于 {data.get('keywords', ['未知'])[0] if data.get('keywords') else '未知'} 的技术内容..."


def handle_life(data: dict) -> str:
    return f"生活问题回复：关于日常生活的建议..."


def handle_other(data: dict) -> str:
    return f"通用回复：感谢你的消息（情感{data.get('sentiment', '未知')}）"


# 组合：先分析，再路由
analyze_then_route = clean_pipeline | RunnableBranch(
    (RunnableLambda(lambda x: x["topic"] == "技术"), RunnableLambda(handle_tech)),
    (RunnableLambda(lambda x: x["topic"] == "生活"), RunnableLambda(handle_life)),
    RunnableLambda(handle_other),
)

print("分析后路由测试：")
for text in test_texts:
    response = analyze_then_route.invoke(text)
    print(f"\n  输入: {text!r}")
    print(f"  回复: {response}")


# ============================================================================
# 小结
# ============================================================================
print("\n" + "=" * 80)
print("Level 5 完成！关键收获：")
print("=" * 80)
print(
    """
🔑 核心原语（4 个必须掌握的组合原语）：

1. RunnableSequence（通过 | 创建）
   - 顺序执行，前一步的输出是后一步的输入
   - batch 优化：按步骤批量，不是按样本串行

2. RunnableParallel（通过 dict 或 RunnableParallel() 创建）
   - 同一个输入，同时交给多个 runnable 处理
   - 同步: ThreadPoolExecutor，异步: asyncio.gather
   - 输出是 dict，key 是你指定的名字

3. RunnablePassthrough（保留/扩展原始输入）
   - passthrough = 原样透传
   - passthrough.assign(key=runnable) = 扩展字典（RAG 的核心！）

4. RunnableBranch（条件路由）
   - [(condition1, handler1), (condition2, handler2), default]
   - condition 本身也是 Runnable，可以是任意复杂的链

🔑 coerce_to_runnable() 的自动转换：
   - dict → RunnableParallel
   - callable → RunnableLambda
   - list → RunnableSequence（子元素各自转换）
   这使得链的声明非常简洁自然

下一步 Level 6：RAG 系统，将这些原语组合成真实的检索增强生成管道！
"""
)
