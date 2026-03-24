# Level 5: 复杂组合

> **学习时间**: 120 分钟  
> **难度**: ⭐⭐⭐⭐ 高级  
> **前置要求**: 完成 Level 1-4  

---

## 🎯 学习目标

1. **RunnableParallel** - 并行处理多个任务
2. **RunnableBranch** - 条件分支路由
3. **RunnableMapping** - 数据映射和转换
4. **复杂流控制** - 组合上述概念

---

## 📚 核心概念

### 1. RunnableParallel（并行处理）

```python
from langchain_core.runnables import RunnableParallel

# 并行执行多个任务
parallel = RunnableParallel(
    task1=chain1,
    task2=chain2,
    task3=chain3
)

# 所有任务同时执行
result = parallel.invoke(input)
# result = {"task1": ..., "task2": ..., "task3": ...}
```

**使用场景**:
- 同时处理多个相关任务
- 汇总不同维度的结果
- 并行加速

### 2. RunnableBranch（条件分支）

```python
from langchain_core.runnables import RunnableBranch

# 根据条件选择不同的处理路径
branch = RunnableBranch(
    (condition1, handler1),
    (condition2, handler2),
    default_handler
)
```

**使用场景**:
- 根据输入类型选择处理方式
- 不同难度问题使用不同策略
- 多语言支持

### 3. 常见组合模式

```
模式 1: 并行汇总
  Input → [Task1, Task2, Task3] → Merge → Output

模式 2: 顺序与并行混合
  Input → Task1 → [Task2a, Task2b] → Task3 → Output

模式 3: 条件+并行
  Input → Condition → (if A: Task1 | Task2)
                   ↓
                  [SubTask1, SubTask2] → Output
```

---

## 💻 代码示例

### 并行处理

```python
from langchain_core.runnables import RunnableParallel

# 创建多个链
chain1 = prompt1 | llm | parser1
chain2 = prompt2 | llm | parser2

# 并行执行
parallel = RunnableParallel(
    summary=chain1,
    keywords=chain2
)

result = parallel.invoke(input)
# {"summary": "...", "keywords": [...]}
```

### 条件分支

```python
from langchain_core.runnables import RunnableBranch

# 定义条件函数
def is_question(input):
    return "?" in input["text"]

# 定义处理链
qa_chain = prompt_qa | llm | parser
statement_chain = prompt_statement | llm | parser

# 创建分支
branch = RunnableBranch(
    (is_question, qa_chain),
    statement_chain  # 默认
)

result = branch.invoke({"text": "What is AI?"})
```

---

本级详细内容见 [main.py](./main.py)

