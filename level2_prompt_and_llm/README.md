# Level 2: Prompt + LLM 交互

> **学习时间**: 60-90 分钟  
> **难度**: ⭐⭐ 初级-中级  
> **前置要求**: 完成 Level 1（理解 Runnable）  

---

## 🎯 学习目标

完成本级学习后，你应该能够：

1. **理解 Prompt 模板系统**
   - `PromptTemplate` - 参数化文本模板
   - `ChatPromptTemplate` - 多角色对话模板
   - 模板变量和格式化

2. **掌握 LLM 调用方式**
   - 准备和调用 LLM
   - 配置温度、最大令牌等参数
   - 理解不同的 LLM 提供商（OpenAI、Claude、DeepSeek）

3. **组合 Prompt + LLM**
   - Prompt → 格式化 → LLM → 响应
   - 理解数据流
   - 手动组合的实现方式

4. **LLM 的 Runnable 特性**
   - `invoke()` - 单个请求
   - `batch()` - 批量请求
   - `stream()` - 流式输出

---

## 📚 核心概念

### 1. 什么是 Prompt？

Prompt（提示）是指导 LLM 做什么的文本。

```
简单 Prompt：      "请翻译为中文：hello"
复杂 Prompt：      "你是专业翻译。请翻译为中文，并保持原意：hello"
模板化 Prompt：    "请翻译为{language}：{text}"
```

### 2. 为什么需要 PromptTemplate？

❌ **硬编码方式**:
```python
prompts = [
    "请解释：机器学习",
    "请解释：神经网络",
    "请解释：深度学习",
]
# 需要手动拼接，容易出错
```

✅ **模板方式**:
```python
template = PromptTemplate(
    input_variables=["topic"],
    template="请解释：{topic}"
)
# 自动格式化，干净、易维护
```

### 3. 两种 Prompt 类型

#### PromptTemplate（通用模板）
```python
from langchain_core.prompts import PromptTemplate

prompt = PromptTemplate(
    input_variables=["topic", "level"],
    template="用{level}级别解释{topic}"
)

result = prompt.invoke({"topic": "AI", "level": "初级"})
# → "用初级级别解释AI"
```

#### ChatPromptTemplate（对话模板）
```python
from langchain_core.prompts import ChatPromptTemplate

chat_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是有帮助的 AI 助手"),
    ("human", "请解释：{topic}"),
])
# 支持多个角色，适合对话模型
```

### 4. LLM 提供商对比

| 提供商 | 模型 | 特点 | API 成本 |
|--------|------|------|---------|
| OpenAI | GPT-4, GPT-3.5 | 能力最强，用户最多 | 较贵 |
| Anthropic | Claude 3 系列 | 长文本、安全性好 | 中等 |
| DeepSeek | DeepSeek Chat | 便宜、性能好 | 便宜 |
| 开源 | Llama, Mistral | 完全控制、可离线 | 0（自托管） |

### 5. 温度（Temperature）参数

```
Temperature = 0.0          Temperature = 0.7          Temperature = 1.0
（确定性）                  （平衡）                   （随机性）

选择：花        →          选择：花(80%)、树(15%)    →  选择：花(40%)、树(30%)
                                        └→树~1%(可能)                  └→天空(20%)


用途：                      用途：                      用途：
- 数据分析                 - 大多数对话                - 创意写作
- 翻译                     - 代码生成（默认）           - 头脑风暴
- 信息提取                 - QA 系统                   - 故事创作
```

### 6. LLM 调用流程

```
输入: {"topic": "机器学习"}
  ↓
┌───────────────────────────┐
│    ChatPromptTemplate     │
│  格式化：system + human    │
└───────────────┬───────────┘
  ↓ formatted_prompt
┌───────────────────────────┐
│     ChatOpenAI (LLM)      │
│  调用 OpenAI API          │
│  返回 AIMessage           │
└───────────────┬───────────┘
  ↓ response
输出: "机器学习是一种..."
```

---

## 💻 代码详解

### 基础：PromptTemplate

```python
from langchain_core.prompts import PromptTemplate

# 定义模板
template = PromptTemplate(
    input_variables=["topic"],
    template="请用简洁的方式解释：{topic}"
)

# 调用
result = template.invoke({"topic": "递归"})
print(result)
# → "请用简洁的方式解释：递归"
```

### 多变量模板

```python
template = PromptTemplate(
    input_variables=["language", "code", "context"],
    template="""用 {language} 代码解决以下问题：
上下文：{context}
要求：{code}"""
)

result = template.invoke({
    "language": "Python",
    "code": "计算列表平均值",
    "context": "数据科学应用"
})
```

### ChatPromptTemplate

```python
from langchain_core.prompts import ChatPromptTemplate

chat_template = ChatPromptTemplate.from_messages([
    ("system", "你是一个 {role}。"),
    ("human", "请回答以下问题：{question}"),
])

# 输出是多个消息
result = chat_template.invoke({
    "role": "数学教师",
    "question": "什么是微积分？"
})
# result 包含两个消息：system 和 human
```

### 调用真实 LLM

```python
from langchain_openai import ChatOpenAI

# 初始化 LLM
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.7,
    api_key="sk-..."  # 你的 API 密钥
)

# 调用
response = llm.invoke("Hello, how are you?")
print(response.content)

# 流式调用
for chunk in llm.stream("Tell me a story"):
    print(chunk.content, end="", flush=True)
```

### DeepSeek 示例

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com/v1",
    api_key="sk-..."
)

response = llm.invoke("explain machine learning")
print(response.content)
```

### 手动组合 Prompt + LLM

```python
def qa_chain(topic: str) -> str:
    # Step 1: 格式化提示
    prompt_text = template.invoke({"topic": topic})
    
    # Step 2: 调用 LLM
    response = llm.invoke(prompt_text)
    
    # Step 3: 提取内容
    return response.content

# 使用
answer = qa_chain("机器学习")
print(answer)
```

---

## 📋 练习：完成这些任务

### 练习 1：创建 Prompt 模板（10 分钟）

**任务**: 创建一个翻译 Prompt 模板

```python
from langchain_core.prompts import PromptTemplate

# TODO: 创建模板
# - 输入变量：source_text, target_language
# - 模板：要求翻译成指定语言

translate_prompt = PromptTemplate(
    input_variables=["source_text", "target_language"],
    template="TODO: 完成模板..."
)

# 测试
result = translate_prompt.invoke({
    "source_text": "Hello world",
    "target_language": "中文"
})

assert "Hello world" in result.text or "中文" in result.text
print("✅ 通过！")
```

<details>
<summary>💡 查看答案</summary>

```python
from langchain_core.prompts import PromptTemplate

translate_prompt = PromptTemplate(
    input_variables=["source_text", "target_language"],
    template="请将以下文本翻译成{target_language}：\n{source_text}"
)

result = translate_prompt.invoke({
    "source_text": "Hello world",
    "target_language": "中文"
})

print(result)
# 输出：请将以下文本翻译成中文：\nHello world
```

</details>

### 练习 2：Chat 模板（15 分钟）

**任务**: 创建一个专家咨询 Chat 模板

```python
from langchain_core.prompts import ChatPromptTemplate

# TODO: 完成
chat_template = ChatPromptTemplate.from_messages([
    ("system", "TODO: 设定角色..."),
    ("human", "TODO: 用户问题..."),
])

# 测试
result = chat_template.invoke({
    "expert_type": "医生",
    "question": "如何保持健康？"
})

# 验证包含两个消息
assert len(result) == 2
print(f"✅ 包含 {len(result)} 个消息")
```

<details>
<summary>💡 查看答案</summary>

```python
from langchain_core.prompts import ChatPromptTemplate

chat_template = ChatPromptTemplate.from_messages([
    ("system", "你是一名经验丰富的{expert_type}"),
    ("human", "{question}"),
])

result = chat_template.invoke({
    "expert_type": "医生",
    "question": "如何保持健康？"
})

# result 包含两个消息对象
for msg in result:
    print(f"{msg.type}: {msg.content}")
```

</details>

### 练习 3：批量提示生成（10 分钟）

**任务**: 使用 batch 生成多个提示

```python
from langchain_core.prompts import PromptTemplate

prompt = PromptTemplate(
    input_variables=["skill"],
    template="{skill} 的关键概念是什么？"
)

# TODO: 为多个技能批量生成提示
skills = ["Python", "JavaScript", "SQL"]

# 使用 batch
prompts = prompt.batch([
    {"skill": s} for s in skills
])

# 验证
assert len(prompts) == 3
print("✅ 批量生成完成")
for i, p in enumerate(prompts):
    print(f"  {i+1}. {p}")
```

<details>
<summary>💡 查看答案</summary>

```python
from langchain_core.prompts import PromptTemplate

prompt = PromptTemplate(
    input_variables=["skill"],
    template="{skill} 的关键概念是什么？"
)

skills = ["Python", "JavaScript", "SQL"]

prompts = prompt.batch([{"skill": s} for s in skills])

for i, p in enumerate(prompts):
    print(f"{i+1}. {p}")
```

</details>

### 练习 4：虚拟 LLM 链（20 分钟）

**任务**: 实现一个简单的 Prompt → LLM 链

```python
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda

# 虚拟 LLM（预设响应）
class SimpleLLM(RunnableLambda):
    def __init__(self):
        self.responses = {
            "Python": "Python 是一种高级编程语言...",
            "JavaScript": "JavaScript 是用于网络开发的语言...",
        }
        super().__init__(self._call)
    
    def _call(self, text: str) -> str:
        for key, response in self.responses.items():
            if key in text:
                return response
        return "无法回答"

# TODO: 创建 prompt 模板
prompt = PromptTemplate(
    input_variables=["language"],
    template="TODO: 完成..."
)

# TODO: 创建虚拟 LLM
llm = SimpleLLM()

# TODO: 手动组合 prompt + llm
def chain(language: str) -> str:
    # Step 1: 格式化提示
    # Step 2: 调用 LLM
    pass

# 测试
result = chain("Python")
print(result)
```

<details>
<summary>💡 查看答案</summary>

```python
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda

class SimpleLLM(RunnableLambda):
    def __init__(self):
        self.responses = {
            "Python": "Python 是一种高级编程语言...",
            "JavaScript": "JavaScript 是用于网络开发的语言...",
        }
        super().__init__(self._call)
    
    def _call(self, text: str) -> str:
        for key, response in self.responses.items():
            if key in text:
                return response
        return "无法回答"

prompt = PromptTemplate(
    input_variables=["language"],
    template="请介绍编程语言：{language}"
)

llm = SimpleLLM()

def chain(language: str) -> str:
    prompt_text = prompt.invoke({"language": language})
    response = llm.invoke(prompt_text.text)
    return response

result = chain("Python")
print(result)
```

</details>

---

## 🚀 配置真实 API（可选）

### OpenAI

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.7,
    api_key="sk-..."  # 或设置环境变量 OPENAI_API_KEY
)
```

### DeepSeek

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com/v1",
    api_key="sk-..."
)
```

### Claude (Anthropic)

```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(
    model="claude-3-opus-20240229",
    api_key="sk-..."
)
```

---

## 📖 学习路线

```
Level 1: Runnable 基础 ✅
  ↓
Level 2: Prompt + LLM ✅ (你在这里)
  ↓ (学会了如何用 | 自动组合)
Level 3: 完整的 Chain（魔法的 | 操作符）
  ↓
Level 4: 输出解析器
  ↓
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

在进入 Level 3 之前，确保你能：

- [ ] 解释什么是 Prompt 模板
- [ ] 创建 `PromptTemplate` 与多个变量
- [ ] 理解 `ChatPromptTemplate` 的多角色消息
- [ ] 解释温度（temperature）参数的含义
- [ ] 调用真实 LLM（或理解调用方式）
- [ ] 手动组合 Prompt + LLM
- [ ] 使用 `batch()` 处理多个提示
- [ ] 理解不同 LLM 提供商的选择标准

---

## 🎓 常见问题

**Q: 我没有 API 密钥，能学吗？**  
A: 完全可以！课程代码包含虚拟 LLM，不需要真实 API。真实 API 调用是可选的。

**Q: 应该选择哪个 LLM？**  
A:
- **初学者**: GPT-3.5-turbo（便宜、足够用）
- **追求性能**: GPT-4（最强，但贵）
- **追求性价比**: DeepSeek（便宜、性能不错）
- **隐私关注**: 开源模型（Llama）

**Q: 温度应该设多少？**  
A:
- 0.0-0.3: 精确任务（翻译、信息提取）
- 0.5-0.7: 平衡（大多数应用，默认值）
- 0.8-1.0: 创意任务（写作、头脑风暴）

**Q: Prompt 和 ChatPrompt 的区别？**  
A:
- `PromptTemplate`: 单个字符串输出
- `ChatPromptTemplate`: 多个消息对象，适合对话模型

---

## 🔗 下一步

完成本级所有练习后，准备进入 **Level 3: 完整的 Chain**，学习：
- 使用 `|` 操作符自动组合 Runnable
- 理解管道的优雅性
- 自动数据流处理

