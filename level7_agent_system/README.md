# Level 7: Agent 系统

> **学习时间**: 180 分钟  
> **难度**: ⭐⭐⭐⭐⭐ 高级  
> **前置要求**: 完成 Level 1-6  

---

## 🎯 学习目标

1. **理解 Agent 的核心思想** - 自主规划和执行
2. **定义工具（Tools）** - 为 Agent 赋能
3. **创建 Agent** - 使用 LangGraph 构建
4. **处理迭代循环** - Plan → Act → Observe → Refine

---

## 📚 核心概念

### Agent 流程

```
问题
  ↓
[规划] LLM 思考需要调用哪些工具
  ↓
[行动] 调用相应的工具
  ↓
[观察] 工具返回结果
  ↓
[判断] 是否需要继续或已完成？
  ├─ 需要继续 → 回到规划
  └─ 已完成 → 返回最终答案
```

### 关键概念

- **Tool**：Agent 可以调用的函数
- **Agent**：决定调用哪个 Tool 的智能体
- **State**：维护对话状态和历史
- **Loop**：Agent 迭代直到任务完成

---

## 💻 核心 API

```python
from langchain_core.tools import tool
from langgraph.graph import StateGraph

# 定义工具
@tool
def calculate(expression: str) -> float:
    """计算数学表达式"""
    return eval(expression)

@tool
def search(query: str) -> str:
    """搜索信息"""
    return f"关于 {query} 的结果..."

# 创建 Agent
tools = [calculate, search]
agent = create_react_agent(llm, tools)

# 执行
result = agent.invoke({
    "input": "计算 2+2，并搜索 AI 相关信息"
})
```

---

本级详细内容见 [main.py](./main.py)

