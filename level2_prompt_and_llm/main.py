"""
Level 2: Prompt + LLM 交互 🚀

学习目标：
1. 理解 Prompt（提示）的作用和模板系统
2. 掌握如何调用 LLM（大语言模型）
3. 理解 LLM 作为 Runnable 的原理
4. 体验完整的 Prompt → LLM → 响应流程

核心概念：
- Prompt: 指导 LLM 做什么
- LLM: 处理输入，返回输出
- 两者都是 Runnable，可以 invoke/batch/stream

演示方法：
- 使用"虚拟" LLM（预设响应）以避免 API 调用
- 真实 API 调用示例在注释中
"""

from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.language_models import LLM
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import json
import time


# ============================================================================
# 第一步：理解 Prompt 模板
# ============================================================================

print("=" * 80)
print("Level 2: Prompt + LLM 交互")
print("=" * 80)
print()

print("1️⃣  基础 Prompt 模板：")
print("-" * 80)
print()

# 创建一个简单的 Prompt 模板
simple_prompt = PromptTemplate(
    input_variables=["topic"], template="请用简洁的方式解释：{topic}"
)

# 看看模板如何工作
formatted_prompt = simple_prompt.invoke({"topic": "机器学习"})
print(f"输入：topic='机器学习'")
print(f"格式化后的 Prompt：\n{formatted_prompt}")
print()


# ============================================================================
# 第二步：模板的多个变量
# ============================================================================

print("-" * 80)
print("2️⃣  多变量 Prompt 模板：")
print("-" * 80)
print()

multi_var_prompt = PromptTemplate(
    input_variables=["language", "concept"],
    template="""你是一个专业的教师。
用 {language} 解释以下概念（包含例子）：
概念：{concept}

解释：""",
)

# 格式化模板
formatted = multi_var_prompt.invoke({"language": "英文", "concept": "递归"})
print(formatted)
print()


# ============================================================================
# 第三步：Chat Prompt（对话格式）
# ============================================================================

print("-" * 80)
print("3️⃣  Chat Prompt（对话格式）：")
print("-" * 80)
print()

# Chat Prompt 用于对话模型（如 GPT-4）
# 它支持多个角色（System, Human, AI, Assistant）

chat_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "你是一个有帮助的 AI 助手。你擅长解释复杂的概念。"),
        ("human", "请解释 {concept}，用 {level} 级别的难度。"),
    ]
)

# 格式化 Chat Prompt
formatted_chat = chat_prompt.format_messages(concept="神经网络", level="初级")

print(f"格式化后的消息序列：")
for msg in formatted_chat:
    print(f"  角色: {msg.type}")
    print(f"  内容: {msg.content}")
print()


# ============================================================================
# 第四步：虚拟 LLM（用于演示）
# ============================================================================

print("-" * 80)
print("4️⃣  虚拟 LLM（用于演示）：")
print("-" * 80)
print()


class VirtualLLM(RunnableLambda):
    """虚拟 LLM，模拟真实 LLM 的行为（不调用真实 API）"""

    def __init__(self):
        # 预设的响应字典
        self.responses = {
            "机器学习": "机器学习是一种 AI 技术，使计算机能从数据中学习。",
            "递归": "递归是一种函数调用自身的编程技术。",
            "神经网络": "神经网络是模拟生物神经元的计算模型。",
            "提示工程": "提示工程是艺术和科学，用来设计有效的 AI 提示。",
        }
        super().__init__(self._call)

    def _call(self, prompt_text: str) -> str:
        """虚拟 LLM 内部处理"""
        # 简单的匹配逻辑
        for key, response in self.responses.items():
            if key in prompt_text:
                # 模拟 API 延迟
                time.sleep(0.1)
                return response
        # 默认响应
        return f"关于输入 '{prompt_text[:30]}'... 的回复。"


# 创建虚拟 LLM
virtual_llm = VirtualLLM()

# 测试虚拟 LLM
print("测试虚拟 LLM：")
result = virtual_llm.invoke("请解释：机器学习")
print(f"输出: {result}")
print()


# ============================================================================
# 第五步：组合 Prompt + LLM（不使用 | 操作符）
# ============================================================================

print("-" * 80)
print("5️⃣  组合 Prompt + LLM（简单方式）：")
print("-" * 80)
print()


# 方式 1：手动组合（Level 3 会学习自动组合）
def simple_qa(topic: str) -> str:
    """简单的问答：Prompt → LLM"""
    # 第一步：格式化 Prompt
    prompt = simple_prompt.invoke({"topic": topic})

    # 第二步：调用 LLM
    response = virtual_llm.invoke(prompt.text)

    return response


# 测试
print("设问：'机器学习'")
answer = simple_qa("机器学习")
print(f"回答：{answer}")
print()


# ============================================================================
# 第六步：Prompt 作为 Runnable
# ============================================================================

print("-" * 80)
print("6️⃣  Prompt 作为 Runnable（invoke/batch/stream）：")
print("-" * 80)
print()

# Prompt 本身也是 Runnable！
print("单个调用 (invoke)：")
result = simple_prompt.invoke({"topic": "深度学习"})
print(f"  {result}")
print()

# 批量处理多个主题
print("批量调用 (batch)：")
topics = ["强化学习", "自然语言处理", "计算机视觉"]
results = simple_prompt.batch([{"topic": t} for t in topics])
for i, result in enumerate(results):
    print(f"  {i+1}. {result}")
print()


# ============================================================================
# 第七步：LLM 批量和流式处理
# ============================================================================

print("-" * 80)
print("7️⃣  LLM 的批量和流式处理：")
print("-" * 80)
print()

# 批量处理多个提示
print("LLM 批量处理：")
prompts = ["请解释：机器学习", "请解释：递归", "请解释：神经网络"]
results = virtual_llm.batch(prompts)
for prompt, result in zip(prompts, results):
    print(f"  Q: {prompt[:20]}...")
    print(f"  A: {result[:30]}...")
print()

# 流式处理（逐个返回）
print("LLM 流式处理：")
prompt = "请解释：提示工程"
print(f"询问: {prompt}")
print("响应: ", end="", flush=True)
for chunk in virtual_llm.stream(prompt):
    print(chunk, end="", flush=True)
    time.sleep(0.05)
print("\n")


# ============================================================================
# 第八步：真实 API 调用（注释示例）
# ============================================================================

print("-" * 80)
print("8️⃣  真实 API 调用示例（已注释）：")
print("-" * 80)
print()

# ✅ 打开注释来使用真实 LLM（需要 API 密钥）

"""
真实 API 调用示例（需要安装：pip install langchain-openai）

# 方式 1：使用 OpenAI
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4",           # 或 gpt-3.5-turbo
    temperature=0.7,         # 创意度（0=确定，1=创意）
    api_key="sk-...",        # 你的 API 密钥
)

# 方式 2：使用 DeepSeek（通过 OpenAI 兼容接口）
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key="sk-...",
)

# 方式 3：使用 Claude（Anthropic）
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(
    model="claude-3-opus-20240229",
    api_key="sk-...",
)

# 使用真实 LLM
result = llm.invoke("请解释机器学习")
print(result.content)

# 流式调用
for chunk in llm.stream("请解释机器学习"):
    print(chunk.content, end="", flush=True)
"""

print("✅ 真实 API 调用示例见上（注释代码）")
print()


# ============================================================================
# 第九步：LLM 链（Prompt → LLM）
# ============================================================================

print("-" * 80)
print("9️⃣  完整的 LLM 链流程：")
print("-" * 80)
print()

# 虽然我们还没学 | 操作符，但这是基本思想：
# Input → [Prompt] → [LLM] → Output

print(
    """
流程：
Input: {"topic": "机器学习"}
  ↓
[PromptTemplate] → "请用简洁的方式解释：机器学习"
  ↓
[LLM] → "机器学习是一种 AI 技术..."
  ↓
Output: "机器学习是一种 AI 技术..."

现实中这会用 | 操作符：
chain = prompt_template | llm

然后：
result = chain.invoke({"topic": "机器学习"})
"""
)


# 手动实现这个流程
def manual_chain(topic: str) -> str:
    # 步骤 1：格式化 Prompt
    prompt_text = simple_prompt.invoke({"topic": topic})

    # 步骤 2：调用 LLM
    response = virtual_llm.invoke(prompt_text.text)

    return response


print("手动实现的链：")
result = manual_chain("深度学习")
print(f"  输入: 深度学习")
print(f"  输出: {result}")
print()


# ============================================================================
# 第十步：配置 LLM 参数
# ============================================================================

print("-" * 80)
print("🔟 LLM 参数配置：")
print("-" * 80)
print()

config_info = """
常见的 LLM 参数：

1. temperature (0.0 - 2.0)
   - 0.0: 完全确定性，总是选择最可能的词
   - 0.5: 平衡创意和确定性
   - 1.0: 默认随机性
   - >1.0: 高度创意，可能出错
   
   使用场景：
   - 数据分析、翻译 → temperature=0.0
   - 创意写作、头脑风暴 → temperature=0.8-1.0

2. top_p (0.0 - 1.0)
   - 另一种控制多样性的方式
   - 0.9: 只考虑前 90% 的可能性
   
3. max_tokens
   - 限制输出长度
   - {model} 最多生成 max_tokens 个词
   
4. system_prompt
   - 设定 LLM 的角色和行为

示例：
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.7,
    max_tokens=500,
)
"""

print(config_info)
print()


# ============================================================================
# 核心总结
# ============================================================================

print("=" * 80)
print("Level 2 核心要点")
print("=" * 80)
print()

summary = """
1. 🎯 Prompt（提示）
   - PromptTemplate：单变量模板
   - ChatPromptTemplate：多角色模板（对话）
   - 参数化输入使用 {variable} 占位符

2. 🚀 LLM（语言模型）
   - ChatOpenAI：OpenAI 的对话模型
   - ChatAnthropic：Anthropic 的 Claude
   - 支持 invoke/batch/stream 等 Runnable 方法

3. 🔧 关键参数
   - temperature：控制随机性（0=确定，1=创意）
   - max_tokens：限制输出长度
   - api_key：API 密钥

4. 📝 基本流程
   Input → [Prompt] → [Formatted Text] → [LLM] → Output

5. 🔄 方法
   - invoke(input) → 单个响应
   - batch(inputs) → 多个响应（并行）
   - stream(input) → 流式输出
   - ainvoke/abatch/astream → 异步版本

下一步：学习如何用 | 操作符组合 Prompt + LLM（Level 3）
"""

print(summary)

print("=" * 80)
print("✅ Level 2 完成！")
print("=" * 80)
