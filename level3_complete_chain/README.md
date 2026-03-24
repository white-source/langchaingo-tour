# Level 3: 完整的 Chain（| 操作符）

> **学习时间**: 90-120 分钟  
> **难度**: ⭐⭐⭐ 中级  
> **前置要求**: 完成 Level 1-2  
> **重要性**: ⭐⭐⭐⭐⭐ 这是 LangChain 最优雅的部分！

---

## 🎯 学习目标

完成本级学习后，你应该能够：

1. **掌握 | 操作符**
   - 理解管道的优雅性
   - 连接两个或多个 Runnable
   - 自动数据流转

2. **理解类型系统**
   - 自动类型检查（Output → Input 匹配）
   - 类型不兼容时的错误
   - JSON Schema 生成

3. **组合 Prompt + LLM + Parser**
   - 三步链的标准模式
   - 数据从 dict 到字符串的转换
   - 真实应用中的常见模式

4. **掌握高级链操作**
   - 多步链的组合
   - 批量和流式处理
   - 异步链操作
   - 配置和错误处理

---

## 📚 核心概念

### 1. 什么是 | 操作符？

| 操作符（管道操作符）用来**连接多个 Runnable**。

```python
# 创建链
chain = A | B | C

# 执行
result = chain.invoke(input)
# 内部：input → [A] → [B] → [C] → result
```

### 2. 为什么 | 操作符如此优雅？

❌ **没有 | 的时代**（Level 2）:
```python
def old_chain(topic):
    step1 = prompt.invoke({"topic": topic})
    step2 = llm.invoke(step1.text)
    step3 = parser.invoke(step2)
    return step3
```

✅ **使用 | 的时代**:
```python
chain = prompt | llm | parser
result = chain.invoke({"topic": topic})
```

### 3. 数据流程详解

```
invoke({"topic": "AI"})
  ↓
┌─────────────────────────┐
│   PromptTemplate        │
│   输出: "请解释：AI"      │
└─────────────┬───────────┘
  ↓ 自动传递
┌─────────────────────────┐
│   ChatOpenAI (LLM)      │
│   输入: "请解释：AI"      │
│   输出: AIMessage(...)  │
└─────────────┬───────────┘
  ↓ 自动传递
┌─────────────────────────┐
│   StrOutputParser       │
│   输入: AIMessage(...)  │
│   输出: "AI是..."       │
└─────────────┬───────────┘
  ↓
"AI是..."
```

### 4. 类型检查机制

LangChain 自动检查相邻 Runnable 的兼容性：

```python
# PromptTemplate 的输出
PromptTemplate.OutputType = str

# LLM 的输入
ChatOpenAI.InputType = str

# ✅ 兼容！str → str

chain = prompt | llm  # 成功

# ❌ 如果不兼容
chain = llm | prompt  # 错误！(dict → str 不匹配)
```

### 5. RunnableSequence（链容器）

当你使用 | 时，LangChain 创建一个 `RunnableSequence` 对象：

```python
chain = A | B | C
# chain 是一个 RunnableSequence，包含：
# - 步骤列表：[A, B, C]
# - 输入类型：A.InputType
# - 输出类型：C.OutputType
# - invoke/batch/stream 等方法
```

---

## 💻 代码详解

### 基础：两个 Runnable 的组合

```python
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

prompt = PromptTemplate(
    input_variables=["topic"],
    template="请解释：{topic}"
)

llm = ChatOpenAI(model="gpt-4")

# 使用 | 组合
chain = prompt | llm

# 调用
result = chain.invoke({"topic": "AI"})
print(result.content)
```

### 三步链（最常见的模式）

```python
from langchain_core.output_parsers import StrOutputParser

prompt = PromptTemplate(
    input_variables=["topic"],
    template="请解释：{topic}"
)

llm = ChatOpenAI(model="gpt-4")
parser = StrOutputParser()

# 完整的链
chain = prompt | llm | parser

# 调用（输出是字符串，不是 AIMessage）
result = chain.invoke({"topic": "AI"})
print(result)  # 直接是字符串
```

### 批量处理

```python
topics = ["AI", "ML", "DL"]
inputs = [{"topic": t} for t in topics]

# 批量调用
results = chain.batch(inputs)

# 自动并行处理，比逐个调用快
for result in results:
    print(result)
```

### 流式处理

```python
# 逐个字符输出（适合 UI 实时显示）
for chunk in chain.stream({"topic": "AI"}):
    print(chunk, end="", flush=True)

print()  # 换行
```

### 异步操作

```python
import asyncio

async def main():
    # 异步单个调用
    result = await chain.ainvoke({"topic": "AI"})
    print(result)
    
    # 异步批量
    results = await chain.abatch(inputs)
    print(f"{len(results)} 个结果")
    
    # 异步流式
    async for chunk in chain.astream({"topic": "AI"}):
        print(chunk, end="", flush=True)

asyncio.run(main())
```

### 更复杂的链

```python
from langchain_core.runnables import RunnableLambda

# 定义处理函数
def uppercase(text: str) -> str:
    return text.upper()

# 包装成 Runnable
uppercase_runnable = RunnableLambda(uppercase)

# 扩展链
chain = prompt | llm | parser | uppercase_runnable

result = chain.invoke({"topic": "AI"})
print(result)  # 全是大写
```

### 类型检查

```python
# 查看输入和输出类型
print(chain.InputType)   # <class 'dict'>
print(chain.OutputType)  # <class 'str'>

# 获取 JSON Schema
input_schema = chain.get_input_jsonschema()
output_schema = chain.get_output_jsonschema()

print(input_schema)
print(output_schema)
```

---

## 📋 练习：完成这些任务

### 练习 1：创建简单的两步链（15 分钟）

**任务**: 创建 Prompt | LLM 链

```python
from langchain_core.prompts import PromptTemplate
# 你需要一个虚拟 LLM（或真实 API）

# TODO: 定义 prompt
prompt = PromptTemplate(
    input_variables=["language"],
    template="TODO: ..."
)

# TODO: 创建虚拟 LLM（从 Level 2 代码复制）
# 或使用真实 API（需要密钥）

# TODO: 组合
chain = prompt | llm

# 测试
result = chain.invoke({"language": "Python"})
print(result)
```

<details>
<summary>💡 查看答案</summary>

```python
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda

# 虚拟 LLM
class SimpleLLM(RunnableLambda):
    def __init__(self):
        self.responses = {
            "Python": "Python 是高级编程语言",
            "JavaScript": "JavaScript 是网络编程语言"
        }
        super().__init__(self._call)
    
    def _call(self, text: str) -> str:
        for key, resp in self.responses.items():
            if key in text:
                return resp
        return "默认响应"

prompt = PromptTemplate(
    input_variables=["language"],
    template="请介绍编程语言：{language}"
)

llm = SimpleLLM()
chain = prompt | llm

result = chain.invoke({"language": "Python"})
print(result)
```

</details>

### 练习 2：三步链（20 分钟）

**任务**: 创建 Prompt | LLM | Parser 链

```python
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# TODO: 使用 Level 1 或 Level 2 的虚拟 LLM

prompt = PromptTemplate(
    input_variables=["topic"],
    template="请简洁解释：{topic}"
)

llm = None  # TODO: 创建 LLM

parser = StrOutputParser()

# TODO: 组合三步链
chain = None

# 测试
result = chain.invoke({"topic": "递归"})
print(f"类型: {type(result)}")
print(f"内容: {result}")

assert isinstance(result, str)
print("✅ 通过！")
```

<details>
<summary>💡 查看答案</summary>

```python
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda

class SimpleLLM(RunnableLambda):
    def __init__(self):
        self.responses = {
            "递归": "递归是函数调用自身的技术",
        }
        super().__init__(self._call)
    
    def _call(self, text: str) -> str:
        for key, resp in self.responses.items():
            if key in text:
                return resp
        return text

prompt = PromptTemplate(
    input_variables=["topic"],
    template="请简洁解释：{topic}"
)

llm = SimpleLLM()
parser = StrOutputParser()

chain = prompt | llm | parser

result = chain.invoke({"topic": "递归"})
print(f"类型: {type(result)}")
print(f"内容: {result}")
```

</details>

### 练习 3：批量处理（15 分钟）

**任务**: 使用 batch 处理多个输入

```python
# TODO: 使用练习 2 的链

topics = ["递归", "迭代", "动态规划"]
inputs = [{"topic": t} for t in topics]

# TODO: 批量调用
results = None  # chain.batch(...)

# 验证
assert len(results) == 3
for topic, result in zip(topics, results):
    print(f"{topic}: {result[:30]}...")

print("✅ 批量处理完成！")
```

<details>
<summary>💡 查看答案</summary>

```python
topics = ["递归", "迭代", "动态规划"]
inputs = [{"topic": t} for t in topics]

results = chain.batch(inputs)

for topic, result in zip(topics, results):
    print(f"{topic}: {result[:30]}...")
```

</details>

### 练习 4：扩展链（20 分钟）

**任务**: 添加更多处理步骤

```python
from langchain_core.runnables import RunnableLambda

# TODO: 定义一个字数计算函数
def count_chars(text: str) -> dict:
    """返回文本和字符数"""
    pass

char_counter = RunnableLambda(count_chars)

# TODO: 扩展链
# chain 原本是：prompt | llm | parser
# 现在改为：prompt | llm | parser | char_counter

extended_chain = None

# 测试
result = extended_chain.invoke({"topic": "AI"})

print(f"文本: {result['text'][:30]}...")
print(f"字数: {result['char_count']}")

assert "char_count" in result
print("✅ 通过！")
```

<details>
<summary>💡 查看答案</summary>

```python
from langchain_core.runnables import RunnableLambda

def count_chars(text: str) -> dict:
    return {"text": text, "char_count": len(text)}

char_counter = RunnableLambda(count_chars)

# 假设之前已有 chain
extended_chain = chain | char_counter

result = extended_chain.invoke({"topic": "AI"})
print(f"文本: {result['text'][:30]}...")
print(f"字数: {result['char_count']}")
```

</details>

### 练习 5：类型检查（10 分钟）

**任务**: 检查链的输入和输出类型

```python
# 使用练习 2 的链

# TODO: 获取输入类型
input_type = chain.InputType

# TODO: 获取输出类型
output_type = chain.OutputType

# TODO: 获取 JSON Schema
# input_schema = chain.get_input_jsonschema()
# output_schema = chain.get_output_jsonschema()

print(f"输入类型: {input_type}")
print(f"输出类型: {output_type}")

# 验证
assert input_type == dict
assert output_type == str

print("✅ 类型检查通过！")
```

<details>
<summary>💡 查看答案</summary>

```python
input_type = chain.InputType
output_type = chain.OutputType

print(f"输入类型: {input_type}")
print(f"输出类型: {output_type}")

# 获取 Schema
input_schema = chain.get_input_jsonschema()
output_schema = chain.get_output_jsonschema()

print("输入 Schema:", input_schema)
print("输出 Schema:", output_schema)
```

</details>

---

## 🎨 | 操作符的美学

LangChain 的 | 操作符在语言设计上模仿了 Unix 管道：

```bash
# Unix 管道（经典）
cat file.txt | grep "pattern" | sort | uniq

# Python + LangChain（现代）
chain = read_file | extract_text | parse_json | format_output
```

这种设计的好处：
- 📖 **可读性**: 左到右，易于理解流程
- 🔧 **可组合性**: 任何 Runnable 都可以组合
- 🏗️ **可扩展性**: 轻松添加新步骤
- 🔒 **类型安全**: 自动检查兼容性

---

## 📖 学习路线

```
Level 1: Runnable 基础 ✅
  ↓ (学会了基础方法：invoke/batch/stream)
Level 2: Prompt + LLM ✅
  ↓ (学会了 Prompt 和 LLM 的基础)
Level 3: 完整的 Chain ✅ (你在这里)
  ↓ (学会了 | 操作符和链的威力)
Level 4: 输出解析器
  ↓ (学会如何的提取结构化数据)
Level 5: 复杂组合
  ↓
Level 6: RAG 系统
  ↓
Level 7: Agent 系统
  ↓
Level 8: 构建你的应用
```

---

## ✅ 自检清单

在进入 Level 4 之前，确保你能：

- [ ] 解释 | 操作符的作用
- [ ] 创建两步链（A | B）
- [ ] 创建三步链（Prompt | LLM | Parser）
- [ ] 使用 batch() 处理多个输入
- [ ] 使用 stream() 获取流式输出
- [ ] 理解数据自动流转的原理
- [ ] 检查链的输入和输出类型
- [ ] 理解 RunnableSequence 的概念
- [ ] 处理链中的错误（return_exceptions）

---

## 🎓 常见问题

**Q: 为什么必须用 | ？不能直接调用吗？**  
A: 可以直接调用（像 Level 2），但 | 的优点是：
- 代码简洁
- 类型检查
- 自动优化（并行、批处理等）

**Q: 能否在链中间检查数据？**  
A: 可以！使用 `RunnablePassthrough` 或调试函数：
```python
def debug(x):
    print(f"调试: {x}")
    return x

chain = A | RunnableLambda(debug) | B
```

**Q: 如何处理链中的错误？**  
A:
```python
# 方式 1: 让错误抛出（默认）
results = chain.batch(inputs)

# 方式 2: 继续处理，返回异常对象
results = chain.batch(inputs, return_exceptions=True)
```

**Q: 能否创建条件链（if-else）？**  
A: 可以！这是 Level 5 的内容（RunnableBranch）。

---

## 📚 扩展阅读

1. **RunnableSequence 源码**
   - 位置: `langchain_core/runnables/`
   - 文件: `sequence.py`

2. **| 操作符的实现**
   - 方法: `Runnable.__or__`
   - 创建 `RunnableSequence`

3. **类型系统详解**
   - `get_input_jsonschema()`
   - `get_output_jsonschema()`
   - Pydantic 集成

---

## 🔗 下一步

完成本级所有练习后，准备进入 **Level 4: 输出解析器**，学习：
- JSON 解析
- Pydantic 模型验证
- 结构化数据提取
- 自定义解析器

本杰明·富兰克林曾说："告诉我，我会忘记；教我，我会记住；让我参与其中，我才会理解。"

Level 3 完成后，你已经能够：
✅ 创建实用的 LLM 链
✅ 处理多种数据类型
✅ 自动处理复杂流程
✅ 为真实应用奠定基础

继续前进吧！🚀

