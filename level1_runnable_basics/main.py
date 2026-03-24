"""
Level 1: Runnable 基础 ⭐

学习目标：
1. 理解什么是 Runnable
2. 用 RunnableLambda 包装函数
3. 体验 invoke, batch, stream 的威力
4. 理解类型系统和 Schema

核心概念：
- Runnable 是一个通用的接口：Runnable[Input, Output]
- 任何有输入和输出的东西都可以是 Runnable
- Runnable 自动支持：同步/异步、单个/批量、非流式/流式

注意：这个例子使用虚拟数据，不需要 API 密钥
"""

from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel


# ============================================================================
# 第一步：理解最简单的 Runnable
# ============================================================================

print("=" * 80)
print("Level 1: Runnable 基础概念")
print("=" * 80)
print()
print()



# 最简单的函数
def add_one(x: int) -> int:
    """给输入加 1"""
    return x + 1


print("1️⃣  普通函数：")
print(f"   add_one(5) = {add_one(5)}")
print()

# 包装成 Runnable
runnable = RunnableLambda(add_one)

print("2️⃣  包装成 Runnable 后，获得超能力：")
print(f"   invoke(5) = {runnable.invoke(5)}")
print()


# ============================================================================
# 第二步：批量处理（Batch）
# ============================================================================

print("-" * 80)
print("批量处理：同时处理多个输入")
print("-" * 80)
print()

inputs = [1, 2, 3, 4, 5]
results = runnable.batch(inputs)

print(f"输入：{inputs}")
print(f"批量调用 batch()：{results}")
print("✅ 自动并行处理，比逐个调用快！")
print()


# ============================================================================
# 第三步：流式处理（Stream）
# ============================================================================

print("-" * 80)
print("流式处理：逐个返回结果")
print("-" * 80)
print()

print("使用 stream() 逐个输出：")
for chunk in runnable.stream(10):
    print(f"  收到结果：{chunk}")
print()


# ============================================================================
# 第四步：异步处理（Async）
# ============================================================================

import asyncio

print("-" * 80)
print("异步处理：不阻塞主线程")
print("-" * 80)
print()


async def test_async():
    """异步调用 Runnable"""
    # 异步调用单个输入
    result = await runnable.ainvoke(5)
    print(f"异步 ainvoke(5) = {result}")

    # 异步批量调用
    results = await runnable.abatch([1, 2, 3])
    print(f"异步 abatch([1,2,3]) = {results}")

    # 异步流式
    print("异步流式处理：")
    async for chunk in runnable.astream(10):
        print(f"  收到：{chunk}")


# 运行异步代码
asyncio.run(test_async())
print()


# ============================================================================
# 第五步：类型系统和 Schema
# ============================================================================

print("-" * 80)
print("类型系统：LangChain 自动推断输入和输出类型")
print("-" * 80)
print()

# LangChain 能自动推断类型
print(f"输入类型：{runnable.InputType}")
print(f"输出类型：{runnable.OutputType}")
print()

# 自动生成 JSON Schema（用于 API 文档、验证等）
print("输入 JSON Schema：")
print(runnable.get_input_jsonschema())
print()

print("输出 JSON Schema：")
print(runnable.get_output_jsonschema())
print()


# ============================================================================
# 第六步：更复杂的例子 - 多步处理
# ============================================================================

print("-" * 80)
print("更复杂的例子：处理对象")
print("-" * 80)
print()


# 定义数据结构
class Person(BaseModel):
    name: str
    age: int


# 处理 Person 对象的函数
def greet_person(person: Person) -> str:
    """问候一个人"""
    return f"你好 {person.name}，你 {person.age} 岁了！"


# 包装成 Runnable
greet_runnable = RunnableLambda(greet_person)

# 创建测试数据
people = [
    Person(name="Alice", age=25),
    Person(name="Bob", age=30),
    Person(name="Charlie", age=35),
]

print("处理对象列表：")
results = greet_runnable.batch(people)
for result in results:
    print(f"  {result}")
print()


# ============================================================================
# 第七步：错误处理
# ============================================================================

print("-" * 80)
print("错误处理：batch with return_exceptions")
print("-" * 80)
print()


def risky_operation(x: int) -> int:
    """可能会失败的操作"""
    if x < 0:
        raise ValueError("不接受负数！")
    return x * 2


risky_runnable = RunnableLambda(risky_operation)

# 正常批处理（遇到错误会抛异常）
print("输入：[-1, 0, 1, 2]")

try:
    results = risky_runnable.batch([-1, 0, 1, 2])
except Exception as e:
    print(f"❌ 错误：{e}")

# 使用 return_exceptions=True 返回异常而不抛出
print()
print("使用 return_exceptions=True：")
results = risky_runnable.batch([-1, 0, 1, 2], return_exceptions=True)
for i, result in enumerate(results):
    if isinstance(result, Exception):
        print(f"  输入 {[-1, 0, 1, 2][i]}：❌ {result}")
    else:
        print(f"  输入 {[-1, 0, 1, 2][i]}：✅ {result}")
print()


# ============================================================================
# 第八步：配置（Config）
# ============================================================================

print("-" * 80)
print("配置：传递运行时配置")
print("-" * 80)
print()

# 配置可以包含：
# - callbacks: 回调处理（用于追踪、日志）
# - tags: 标签（用于识别和过滤）
# - metadata: 元数据（额外信息）
# - run_id: 运行 ID
# - max_concurrency: 最大并发数

config = {
    "tags": ["my_runnable", "v1"],
    "metadata": {"version": "1.0", "author": "me"},
    "max_concurrency": 2,
}

result = runnable.invoke(5, config=config)
print(f"带配置的调用：{result}")
print("✅ 配置会被用于追踪和监控")
print()


# ============================================================================
# 核心总结
# ============================================================================

print("=" * 80)
print("核心要点总结")
print("=" * 80)
print()

summary = """
1. 🎯 Runnable 是通用接口
   - Runnable[Input, Output]
   - 任何有输入输出的东西都可以包装

2. 🚀 自动获得的超能力
   - invoke(input) - 处理单个输入
   - batch(inputs) - 批量处理
   - stream(input) - 流式输出
   - ainvoke, abatch, astream - 异步版本

3. 🔒 类型安全
   - 自动推断 InputType 和 OutputType
   - 生成 JSON Schema
   - 编译时类型检查

4. 🔧 配置灵活
   - 可以传递 config 参数
   - 配置 callbacks、tags、metadata 等

5. 🔄 关键方法
   - invoke(input) → output
   - batch(inputs) → outputs
   - stream(input) → Iterator[output]
   - (还有异步版本)

下一步：学习如何组合多个 Runnable（使用 | 操作符）
"""

print(summary)

print("=" * 80)
print("✅ Level 1 完成！")
print("=" * 80)
