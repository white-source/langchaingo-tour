# Level 4: 输出解析器

> **学习时间**: 60-90 分钟  
> **难度**: ⭐⭐⭐ 中级  
> **前置要求**: 完成 Level 1-3  

---

## 🎯 学习目标

完成本级学习后，你应该能够：

1. **理解输出解析的概念**
   - 为什么需要 OutputParser
   - 解析流程

2. **掌握常见的 Parser**
   - `StrOutputParser` - 提取纯文本
   - `JsonOutputParser` - 解析 JSON
   - `PydanticOutputParser` - 验证模型

3. **处理结构化数据**
   - 定义 Pydantic 模型
   - 类型验证和转换
   - 嵌套数据结构

4. **故障排除**
   - 处理解析错误
   - 验证失败处理
   - 调试技巧

---

## 📚 核心概念

### 1. 为什么需要 OutputParser？

LLM 返回的是**原始文本**，需要转换为**结构化数据**：

```python
# ❌ 没有 Parser
llm_output = '{"name": "Alice", "age": 30}'  # 字符串
# 手动处理：json.loads()，类型检查...

# ✅ 有 Parser
llm_output = Person(name="Alice", age=30)  # 对象
# 自动验证，类型安全，可直接使用
```

### 2. Parser 的位置

```
Prompt | LLM | Parser
               ↓
           转换和验证
```

### 3. 常见 Parser 对比

| Parser | 输入 | 输出 | 用途 |
|--------|------|------|------|
| StrOutputParser | 任何字符串 | `str` | 纯文本 |
| JsonOutputParser | JSON 字符串 | `dict` | 非结构数据 |
| PydanticOutputParser | JSON 字符串 | 模型对象 | 结构化数据 |
| 自定义 | 任何 | 任何 | 特殊转换 |

### 4. Pydantic 模型验证

```python
from pydantic import BaseModel, Field

class Person(BaseModel):
    name: str = Field(..., description="名字", min_length=1)
    age: int = Field(..., gt=0, lt=150)
    email: str = Field(..., regex=r".*@.*")
```

验证功能：
- ✅ 类型转换：`"30"` → `30`
- ✅ 默认值：`Field(default="Unknown")`
- ✅ 范围检查：`gt=0, lt=150`
- ✅ 正则验证：`regex=r"..."`
- ✅ 必填检查：`...` 表示必填

---

## 💻 代码详解

### StrOutputParser

```python
from langchain_core.output_parsers import StrOutputParser

parser = StrOutputParser()

# 在链中使用
chain = prompt | llm | parser

result = chain.invoke({"topic": "AI"})
# 结果是纯字符串
```

### JsonOutputParser

```python
from langchain_core.output_parsers import JsonOutputParser

parser = JsonOutputParser()

chain = prompt | llm | parser

result = chain.invoke({"requirement": "return json"})
# 结果是 Python dict
# {"key": "value"}
```

### PydanticOutputParser

```python
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

class Person(BaseModel):
    name: str = Field(description="名字")
    age: int = Field(description="年龄")

parser = PydanticOutputParser(pydantic_object=Person)

# 生成提示词说明
format_instructions = parser.get_format_instructions()
print(format_instructions)
# 输出给 LLM，告诉它应该返回什么格式

prompt = PromptTemplate(
    input_variables=["requirement"],
    template="Extract: {requirement}\n{format_instructions}",
    partial_variables={"format_instructions": format_instructions}
)

chain = prompt | llm | parser

result = chain.invoke({"requirement": "Alice, 30"})
print(result)  # Person(name="Alice", age=30)
```

### 自定义 Parser

```python
from langchain_core.output_parsers import BaseOutputParser

class CustomParser(BaseOutputParser[str]):
    def parse(self, text: str) -> str:
        # 自定义逻辑
        return text.upper()

parser = CustomParser()
chain = prompt | llm | parser
```

### 错误处理

```python
# 方式 1: 捕获异常
try:
    result = chain.invoke(input)
except Exception as e:
    print(f"解析失败: {e}")

# 方式 2: 提供默认值
def safe_parse(text):
    try:
        return parser.parse(text)
    except:
        return {}

# 方式 3: return_exceptions 在 batch 中
results = chain.batch(inputs, return_exceptions=True)
```

---

## 📋 练习：完成这些任务

### 练习 1：使用 StrOutputParser（10 分钟）

```python
from langchain_core.output_parsers import StrOutputParser

# TODO: 创建 parser
parser = StrOutputParser()

# TODO: 使用 Level 3 的链加上 parser
# chain = ... | parser

# 测试
result = chain.invoke({"topic": "AI"})
assert isinstance(result, str)
print("✅ 通过")
```

### 练习 2：JSON 解析（15 分钟）

```python
from langchain_core.output_parsers import JsonOutputParser

# 虚拟 LLM 返回 JSON
class JsonLLM(RunnableLambda):
    def __init__(self):
        super().__init__(self._call)
    
    def _call(self, text: str) -> str:
        return '{"language": "Python", "use": "AI/ML"}'

# TODO: 创建 parser
parser = JsonOutputParser()

# TODO: 组合
llm = JsonLLM()
prompt = PromptTemplate(
    input_variables=["x"],
    template="JSON: {x}"
)
chain = prompt | llm | parser

# 测试
result = chain.invoke({"x": "test"})
assert isinstance(result, dict)
assert "language" in result
print("✅ 通过")
```

### 练习 3：Pydantic 验证（20 分钟）

```python
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

# TODO: 定义数据模型
class Product(BaseModel):
    name: str = Field(..., description="产品名")
    price: float = Field(..., gt=0, description="价格")
    in_stock: bool = Field(default=True, description="库存")

# TODO: 创建 parser
parser = PydanticOutputParser(pydantic_object=Product)

# TODO: 创建链
# 注意：需要 format_instructions

# 测试
# result = chain.invoke(...)
# assert isinstance(result, Product)
```

---

## ✅ 自检清单

- [ ] 理解 OutputParser 的作用
- [ ] 使用三种内置 Parser（Str/Json/Pydantic）
- [ ] 定义 Pydantic 模型
- [ ] 添加验证规则（范围、正则等）
- [ ] 处理解析错误
- [ ] 使用 `get_format_instructions()`
- [ ] 理解类型转换过程

---

## 🔗 下一步

进入 **Level 5: 复杂组合**，学习：
- 并行处理（RunnableParallel）
- 条件分支（RunnableBranch）
- 数据映射
- 高级流控制

