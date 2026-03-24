"""
Level 3: 完整的 Chain 🔗

学习目标：
1. 掌握 | 操作符（管道操作符）
2. 理解自动组合的魔力
3. 学习链的组合原理
4. 体验数据自动流转

核心概念：
- | 操作符将多个 Runnable 连接起来
- 自动处理数据流：Output_i → Input_{i+1}
- 支持类型检查和自动转换

这一级是 LangChain 最优雅的部分！
"""

from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import time


# ============================================================================
# 准备：虚拟 LLM
# ============================================================================


class VirtualLLM(RunnableLambda):
    """虚拟 LLM 用于演示"""

    def __init__(self):
        self.responses = {
            "机器学习": "机器学习是一种AI技术，使计算机能从数据中学习。核心思想是通过大量数据训练模型来识别模式。",
            "深度学习": "深度学习是机器学习的一个分支，使用神经网络来处理复杂的模式识别任务。",
            "递归": "递归是一个函数调用自身来解决问题的编程技术。递归通常需要基本情况和递推关系。",
        }
        super().__init__(self._call)

    def _call(self, prompt_text) -> str:
        """虚拟 LLM 内部处理"""
        # 处理 PromptValue 对象或字符串
        if hasattr(prompt_text, "text"):
            text = prompt_text.text
        else:
            text = str(prompt_text)

        for key, response in self.responses.items():
            if key in text:
                time.sleep(0.1)
                return response
        return f"关于输入 '{text[:30]}...' 的回复。"


virtual_llm = VirtualLLM()


# ============================================================================
# 第一步：没有 | 操作符的时代（Layer 2 的方式）
# ============================================================================

print("=" * 80)
print("Level 3: 完整的 Chain（| 操作符）")
print("=" * 80)
print()

print("1️⃣  没有 | 操作符的时代（繁琐）：")
print("-" * 80)
print()

# 创建各个组件
prompt = PromptTemplate(input_variables=["topic"], template="请简洁地解释：{topic}")


# 旧的方式：手动组合
def old_chain(topic: str) -> str:
    """Level 2 的方式：手动组合"""
    step1 = prompt.invoke({"topic": topic})
    step2 = virtual_llm.invoke(step1.text)
    return step2


result = old_chain("机器学习")
print(f"输入: machine learning")
print(f"输出: {result[:50]}...")
print()
print("❌ 缺点：")
print("   - 需要手动处理每一步")
print("   - 容易在中间步骤出错")
print("   - 很难组合多个步骤")
print()


# ============================================================================
# 第二步：| 操作符的魔力！
# ============================================================================

print("-" * 80)
print("2️⃣  使用 | 操作符（优雅）：")
print("-" * 80)
print()

# 使用 | 组合：Prompt | LLM
chain_with_pipe = prompt | virtual_llm

print("代码：")
print("  chain = prompt | llm")
print()

result = chain_with_pipe.invoke({"topic": "深度学习"})
print(f"输入: {{'topic': '深度学习'}}")
print(f"输出: {result[:50]}...")
print()
print("✅ 优点：")
print("   - 代码简洁")
print("   - 数据自动流转")
print("   - 易于理解")
print()


# ============================================================================
# 第三步：| 操作符的工作原理
# ============================================================================

print("-" * 80)
print("3️⃣  | 操作符的工作原理：")
print("-" * 80)
print()

explanation = """
当你写：chain = A | B | C

LangChain 做的事情：

1️⃣ 解析输入
   Input: {"topic": "机器学习"}

2️⃣ 执行第一步（A = Prompt）
   A.invoke(Input)
   → "请简洁地解释：机器学习"
   
3️⃣ 自动将输出传给下一步（B = LLM）
   B.invoke(A_output)
   → "机器学习是一种AI技术..."
   
4️⃣ 如果有更多步骤，继续传递
   C.invoke(B_output)
   → ...

关键：LangChain 自动处理中间数据传递！
你只需要 | 连接，其他都是自动的。

类型检查：
Output_A: str       (LLM 输入的是字符串)
Input_B: str        ✅ 完美匹配！

这就是为什么 LangChain 这么强大：
类型安全 + 自动流转 + 链式组合
"""

print(explanation)
print()


# ============================================================================
# 第四步：添加输出解析器
# ============================================================================

print("-" * 80)
print("4️⃣  三步链：Prompt | LLM | OutputParser：")
print("-" * 80)
print()

# StrOutputParser 提取字符串内容（从 AIMessage 中）
output_parser = StrOutputParser()

# 完整的链
full_chain = prompt | virtual_llm | output_parser

print("代码：")
print("  chain = prompt | llm | output_parser")
print()

result = full_chain.invoke({"topic": "递归"})
print(f"输入: {{'topic': '递归'}}")
print(f"输出类型: {type(result)}")
print(f"输出内容: {result[:50]}...")
print()

print("💡 三步链的作用：")
print("   1. PromptTemplate: 格式化输入")
print("   2. LLM: 调用语言模型")
print("   3. StrOutputParser: 提取和格式化输出")
print()


# ============================================================================
# 第五步：处理不同数据类型
# ============================================================================

print("-" * 80)
print("5️⃣  数据类型流转检查：")
print("-" * 80)
print()

# 检查类型
print("链的类型签名：")
print(f"  输入类型: {full_chain.InputType}")
print(f"  输出类型: {full_chain.OutputType}")
print()

# 获取 JSON Schema（用于 API 验证）
print("输入 Schema:")
input_schema = full_chain.get_input_jsonschema()
print(f"  {input_schema}")
print()

print("输出 Schema:")
output_schema = full_chain.get_output_jsonschema()
print(f"  {output_schema}")
print()


# ============================================================================
# 第六步：批量处理（Batch）
# ============================================================================

print("-" * 80)
print("6️⃣  链的批量处理：")
print("-" * 80)
print()

topics = ["机器学习", "深度学习", "递归"]
inputs = [{"topic": t} for t in topics]

print("批量输入：")
for inp in inputs:
    print(f"  {inp}")
print()

# 使用 batch 一次处理多个
results = full_chain.batch(inputs)

print("批量输出：")
for topic, result in zip(topics, results):
    print(f"  {topic}: {result[:40]}...")
print()


# ============================================================================
# 第七步：流式处理（Stream）
# ============================================================================

print("-" * 80)
print("7️⃣  链的流式处理：")
print("-" * 80)
print()

print("流式输出（模拟 LLM 的流式响应）：")
response = ""
for chunk in full_chain.stream({"topic": "机器学习"}):
    response += chunk
    # 在真实 LLM 中，这会逐个词输出
print(f"最终输出: {response[:50]}...")
print()


# ============================================================================
# 第八步：更复杂的链
# ============================================================================

print("-" * 80)
print("8️⃣  更复杂的链（含多个处理步骤）：")
print("-" * 80)
print()


# 定义一个字数计数函数
def count_words(text: str) -> dict:
    """计算字数"""
    return {"text": text, "word_count": len(text.split())}


# 将其包装成 Runnable
word_counter = RunnableLambda(count_words)

# 链：Prompt | LLM | Parser | WordCounter
complex_chain = prompt | virtual_llm | output_parser | word_counter

result = complex_chain.invoke({"topic": "机器学习"})

print("链：Prompt | LLM | Parser | WordCounter")
print()
print(f"输入: {{'topic': '机器学习'}}")
print(f"输出类型: {type(result)}")
print(f"字数: {result['word_count']}")
print(f"内容: {result['text'][:50]}...")
print()


# ============================================================================
# 第九步：异步链
# ============================================================================

print("-" * 80)
print("9️⃣  异步链操作：")
print("-" * 80)
print()

import asyncio


async def test_async_chain():
    """异步调用链"""
    # 异步单个调用
    result = await full_chain.ainvoke({"topic": "深度学习"})
    print(f"异步 ainvoke: {result[:40]}...")

    # 异步批量调用
    results = await full_chain.abatch(inputs)
    print(f"异步 abatch: {len(results)} 个结果")

    # 异步流式
    print("异步流式处理：")
    response = ""
    async for chunk in full_chain.astream({"topic": "递归"}):
        response += chunk
    print(f"  最终输出: {response[:40]}...")


print("运行异步链...")
asyncio.run(test_async_chain())
print()


# ============================================================================
# 第十步：链的组合模式
# ============================================================================

print("-" * 80)
print("🔟 常见的链组合模式：")
print("-" * 80)
print()

patterns = """
模式 1：顺序链
  A | B | C
  用途：线性处理（Prompt → LLM → Parser）

模式 2：多路输出
  (A | B) | (C | D) | E
  用途：多个独立的处理路径，然后合并

模式 3：条件链（级别 5 学习）
  A | (If Condition1 then B else C) | D
  用途：根据条件选择不同的处理路径

模式 4：循环链
  A | B | C，然后 C 的输出作为 B 的输入（多次）
  用途：迭代处理直到条件满足

我们学到的是模式 1：顺序链
这是最基础也是最常用的模式！
"""

print(patterns)
print()


# ============================================================================
# 第十一步：错误处理和配置
# ============================================================================

print("-" * 80)
print("1️⃣1️⃣ 链的配置和错误处理：")
print("-" * 80)
print()

# 配置项
config = {
    "tags": ["qa-chain"],
    "metadata": {"version": "1.0"},
    "max_concurrency": 2,
}

result = full_chain.invoke({"topic": "机器学习"}, config=config)

print("带配置的调用：")
print(f"  config: {config}")
print(f"  输出: {result[:40]}...")
print()

# 错误处理
print("批量处理中的错误处理：")

bad_inputs = [
    {"topic": "机器学习"},  # ✅ 有预设响应
    {"topic": "UFO"},  # ❌ 没有预设响应
]

# 方式 1：让错误抛出（默认）
print("  默认行为：遇到错误则停止")
try:
    results = full_chain.batch(bad_inputs)
except Exception as e:
    print(f"  错误: {type(e).__name__}")

# 方式 2：继续处理，返回异常对象
print()
print("  使用 return_exceptions=True：")
results = full_chain.batch(bad_inputs, return_exceptions=True)
for i, result in enumerate(results):
    if isinstance(result, Exception):
        print(f"    输入 {i}: ❌ 异常")
    else:
        print(f"    输入 {i}: ✅ {result[:30]}...")
print()


# ============================================================================
# 核心总结
# ============================================================================

print("=" * 80)
print("Level 3 核心要点")
print("=" * 80)
print()

summary = """
1. 🔗 | 操作符的魔力
   - 连接 Runnable：A | B | C
   - 自动处理数据传递
   - 类型检查和验证

2. 🎯 自动数据流
   Input → [A] → [B] → [C] → Output
        自动传递     自动传递

3. 📊 常见的三步链
   Prompt | LLM | OutputParser
   格式化   调用   提取输出

4. 🚀 链的四种调用方式
   - invoke(input)      → 单个响应
   - batch(inputs)      → 批量响应（并行）
   - stream(input)      → 流式响应
   - ainvoke/abatch/astream → 异步版本

5. 🔒 类型安全
   - LangChain 自动检查类型兼容性
   - Output_A: str → Input_B: str ✅
   - 编译时发现 bug

6. ⚙️ 配置和错误处理
   - config: tags, metadata, max_concurrency
   - return_exceptions=True: 继续处理错误

下一步：学习输出解析器（Level 4）
- JSON 解析
- 结构化数据提取
- Pydantic 集成
"""

print(summary)

print("=" * 80)
print("✅ Level 3 完成！")
print("=" * 80)
