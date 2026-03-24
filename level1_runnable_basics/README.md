# Level 1: Runnable 基础

> **学习时间**: 45-60 分钟  
> **难度**: ⭐ 初级  
> **前置要求**: Python 基础，了解类型提示  

---

## 🎯 学习目标

完成本级学习后，你应该能够：

1. **理解 Runnable 的核心概念**
   - 什么是 Runnable（`Runnable[Input, Output]`）
   - 为什么 Runnable 是 LangChain 的基础
   - Runnable 与普通函数的区别

2. **掌握基础 Runnable 方法**
   - `invoke()` - 处理单个输入
   - `batch()` - 批量处理多个输入
   - `stream()` - 流式获取结果
   - 异步版本：`ainvoke()`, `abatch()`, `astream()`

3. **理解类型系统**
   - 自动类型推断（`InputType`, `OutputType`）
   - JSON Schema 生成
   - 为什么类型很重要

4. **掌握实用技能**
   - 用 `RunnableLambda` 包装任何函数
   - 处理错误（`return_exceptions`）
   - 传递配置（`config`）

---

## 📚 核心概念

### 1. 什么是 Runnable？

```
Runnable[Input, Output]
    ↓
一个通用的处理单元，接收 Input，返回 Output
可以是：函数、LLM、提示模板、解析器、整条链...
```

**关键特性**：
- 所有 Runnable 都有统一的接口
- 自动支持同步/异步、单个/批量、非流式/流式
- 可以自由组合（下一级学习）

### 2. 为什么用 Runnable？

❌ **不用 Runnable**（普通函数）:
```python
def process(items):
    results = []
    for item in items:
        results.append(function(item))  # 顺序处理
    return results
```

✅ **用 Runnable**:
```python
runnable = RunnableLambda(function)
results = runnable.batch(items)  # 自动并行处理
```

### 3. 四种调用方式

| 方法 | 用途 | 同步/异步 | 单个/批量 |
|------|------|---------|----------|
| `invoke` | 处理单个输入 | 同步 | 单个 |
| `batch` | 处理多个输入 | 同步 | 批量 |
| `stream` | 逐个返回结果 | 同步 | 单个 |
| `ainvoke` | 异步处理单个 | 异步 | 单个 |
| `abatch` | 异步批量处理 | 异步 | 批量 |
| `astream` | 异步流式处理 | 异步 | 单个 |

### 4. 运行示意图

```
输入数据
   ↓
┌─────────────────────────────┐
│  RunnableLambda(function)   │
│                             │
│  - invoke()     → 同步单个   │
│  - batch()      → 同步批量   │
│  - stream()     → 同步流式   │
│  - ainvoke()    → 异步单个   │
│  - abatch()     → 异步批量   │
│  - astream()    → 异步流式   │
└─────────────────────────────┘
   ↓
输出数据
```

---

## 💻 代码详解

### 基础：包装函数

```python
from langchain_core.runnables import RunnableLambda

def add_one(x: int) -> int:
    return x + 1

# 将函数包装成 Runnable
runnable = RunnableLambda(add_one)

# 使用 invoke 调用
result = runnable.invoke(5)  # 6
```

**为什么要包装？**
- 普通函数只能 `.call()`
- Runnable 可以 `invoke/batch/stream/ainvoke/...`

### 批量处理

```python
# 一次处理多个输入
results = runnable.batch([1, 2, 3, 4, 5])
# [2, 3, 4, 5, 6]

# 可以配置最大并发数
config = {"max_concurrency": 2}
results = runnable.batch([1, 2, 3, 4, 5], config=config)
```

### 流式处理

```python
# 逐个返回结果（用于长时间运行的操作）
for chunk in runnable.stream(10):
    print(chunk)  # 应为 11
```

**适用场景**：
- LLM 流式输出文本
- 长列表的异步处理
- 实时反馈

### 异步处理

```python
import asyncio

async def main():
    # 异步单个调用
    result = await runnable.ainvoke(5)  # 6
    
    # 异步批量
    results = await runnable.abatch([1, 2, 3])  # [2, 3, 4]
    
    # 异步流式
    async for chunk in runnable.astream(10):
        print(chunk)  # 11

asyncio.run(main())
```

### 错误处理

```python
def risky(x):
    if x < 0:
        raise ValueError("negative!")
    return x * 2

risky_runnable = RunnableLambda(risky)

# 方式 1：让异常抛出（默认行为）
try:
    results = risky_runnable.batch([-1, 0, 1])
except Exception as e:
    print(e)

# 方式 2：捕获异常，返回异常对象
results = risky_runnable.batch(
    [-1, 0, 1], 
    return_exceptions=True
)
# [ValueError(...), 0, 2]
```

### 类型系统

```python
runnable = RunnableLambda(add_one)

# 自动推断类型
print(runnable.InputType)   # <class 'int'>
print(runnable.OutputType)  # <class 'int'>

# 生成 JSON Schema（用于 API 验证）
input_schema = runnable.get_input_jsonschema()
output_schema = runnable.get_output_jsonschema()
```

---

## 📋 练习: 完成这些任务

### 练习 1：基础 Runnable（10 分钟）

**任务**: 创建一个 Runnable 来处理文本长度
```python
# TODO: 完成这个函数
def count_chars(text: str) -> int:
    """数字符数"""
    pass

# TODO: 包装成 Runnable
char_counter = None

# 测试
assert char_counter.invoke("hello") == 5
assert char_counter.batch(["hi", "bye"]) == [2, 3]
```

**提示**：
- 使用 `len()` 计算字符数
- 使用 `RunnableLambda` 包装

<details>
<summary>💡 查看答案</summary>

```python
from langchain_core.runnables import RunnableLambda

def count_chars(text: str) -> int:
    return len(text)

char_counter = RunnableLambda(count_chars)

# 测试
print(char_counter.invoke("hello"))  # 5
print(char_counter.batch(["hi", "bye"]))  # [2, 3]
```

</details>

### 练习 2：流式处理（10 分钟）

**任务**: 流式输出数字的平方

```python
# TODO: 创建一个计算平方的 Runnable
square_runnable = None

# 测试：逐个打印平方
# 预期输出：1, 4, 9, 16, 25（每个一行）
for square in square_runnable.stream(5):
    print(square)
```

<details>
<summary>💡 查看答案</summary>

```python
from langchain_core.runnables import RunnableLambda

def square(x: int) -> int:
    return x * x

square_runnable = RunnableLambda(square)

# stream 返回一个迭代器，每次返回一个值
for square in square_runnable.stream(5):
    print(square)  # 25
```

</details>

### 练习 3：处理对象（15 分钟）

**任务**: 处理 Person 对象

```python
from pydantic import BaseModel

class Person(BaseModel):
    name: str
    age: int

# TODO: 创建函数和 Runnable
def person_description(person: Person) -> str:
    """返回人的描述"""
    pass

person_runnable = None

# 测试
people = [
    Person(name="Alice", age=25),
    Person(name="Bob", age=30)
]

# TODO: 批量处理
descriptions = person_runnable.batch(people)
print(descriptions)
# ['Alice is 25 years old', 'Bob is 30 years old']
```

<details>
<summary>💡 查看答案</summary>

```python
from pydantic import BaseModel
from langchain_core.runnables import RunnableLambda

class Person(BaseModel):
    name: str
    age: int

def person_description(person: Person) -> str:
    return f"{person.name} is {person.age} years old"

person_runnable = RunnableLambda(person_description)

people = [
    Person(name="Alice", age=25),
    Person(name="Bob", age=30)
]

descriptions = person_runnable.batch(people)
print(descriptions)
```

</details>

### 练习 4：错误处理（10 分钟）

**任务**: 安全地计算列表中的倒数

```python
# TODO: 创建一个计算倒数的函数
def reciprocal(x: float) -> float:
    """计算 1/x"""
    pass

reciprocal_runnable = None

# 测试：包含正常数字和 0（会出错）
inputs = [1.0, 2.0, 0.0, 4.0]

# TODO: 使用 return_exceptions=True 处理
results = reciprocal_runnable.batch(
    inputs,
    return_exceptions=True
)

# 预期：[1.0, 0.5, ZeroDivisionError(...), 0.25]
for i, result in enumerate(results):
    if isinstance(result, Exception):
        print(f"错误 {inputs[i]}: {result}")
    else:
        print(f"结果 {inputs[i]}: {result}")
```

<details>
<summary>💡 查看答案</summary>

```python
from langchain_core.runnables import RunnableLambda

def reciprocal(x: float) -> float:
    return 1 / x

reciprocal_runnable = RunnableLambda(reciprocal)

inputs = [1.0, 2.0, 0.0, 4.0]

results = reciprocal_runnable.batch(
    inputs,
    return_exceptions=True
)

for i, result in enumerate(results):
    if isinstance(result, Exception):
        print(f"错误 {inputs[i]}: {type(result).__name__}")
    else:
        print(f"结果 {inputs[i]}: {result}")
```

</details>

---

## 🚀 学习路线

```
Level 1: Runnable 基础 ✅ (你在这里)
    ↓ (学会了 invoke/batch/stream)
Level 2: Prompt + LLM
    ↓ (学会了如何和 LLM 交互)
Level 3: 完整的 Chain（使用 | 操作符）
    ↓ (学会了如何组合 Runnable)
Level 4: 输出解析器
    ↓
Level 5: 复杂组合（并行、条件、映射）
    ↓
Level 6: RAG 系统
    ↓
Level 7: Agent 系统
    ↓
Level 8: 构建你的应用
```

---

## 📚 扩展阅读

1. **Runnable 接口详细文档**
   - 位置: `langchain_core/runnables/base.py`
   - 关键类: `Runnable`, `RunnableLambda`

2. **类型系统详解**
   - 查看如何推断 `InputType` 和 `OutputType`
   - 理解为什么类型安全很重要

3. **配置参数**
   - `max_concurrency` - 控制并发数
   - `callbacks` - 追踪运行过程
   - `tags` - 标签系统
   - `metadata` - 元数据存储

---

## ✅ 自检清单

在进入 Level 2 之前，确保你能：

- [ ] 解释什么是 Runnable
- [ ] 用 `RunnableLambda` 包装任意函数
- [ ] 区分 `invoke`, `batch`, `stream` 的用途
- [ ] 解释为什么 `batch()` 比循环调用快
- [ ] 使用 `return_exceptions=True` 处理错误
- [ ] 理解自动类型推断的好处
- [ ] 正确编写带类型提示的函数

---

## 🎓 常见问题

**Q: 为什么函数必须有类型提示？**  
A: LangChain 使用类型提示来自动推断 `InputType` 和 `OutputType`。没有类型提示时，会被当作 `Any`。

**Q: `stream()` 和 `batch()` 有什么区别？**  
A: 
- `batch()` - 同时处理所有输入，返回所有结果（效率高）
- `stream()` - 逐个返回结果，可实时处理（适合长流程）

**Q: 什么时候用异步版本？**  
A: 在 FastAPI/async 框架中使用 `ainvoke`, `abatch`, `astream`。避免阻塞线程。

**Q: `config` 参数是可选的吗？**  
A: 是的。`config` 用于高级用法（回调、标签、并发控制）。基础用法不需要。

---

## 🔗 下一步

完成本级所有练习后，准备进入 **Level 2: Prompt + LLM**，学习如何：
- 创建提示模板
- 调用 OpenAI/Claude/DeepSeek API
- 让 LLM 成为 Runnable
- 组合 Prompt + LLM + Parser

