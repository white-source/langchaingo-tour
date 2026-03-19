// =============================================================================
// Level 4: Memory —— 让 Chain 记住上下文
// =============================================================================
// 目标：理解 Memory 接口和两个核心时机（Load / Save）
//
// ┌─────────────────────────────────────────────────────────────────────────┐
// │  涉及的设计模式 & 设计原则                                                  │
// │                                                                          │
// │  1. 【策略模式 Strategy】                                                 │
// │     schema.Memory 是策略接口，Simple / ConversationBuffer /               │
// │     WindowBuffer / ZepMemory / MongoMemory 都是可替换的具体策略。           │
// │     Chain 不关心历史存在哪，只调用 LoadMemoryVariables / SaveContext。      │
// │                                                                          │
// │  2. 【装饰器模式 Decorator（思想）】                                        │
// │     chains.Call() 在执行业务逻辑前后自动插入 Load 和 Save，                  │
// │     相当于把"记忆能力"包装在任何一条 Chain 外面，而不需要 Chain 自己实现记忆。  │
// │                                                                          │
// │  3. 【仓储模式 Repository】                                               │
// │     Memory 接口抽象了"对话历史"的存取，屏蔽了存储细节（内存/Redis/向量库）。  │
// │     上层只和领域对象（Messages / string history）打交道，不管底层 IO。        │
// │                                                                          │
// │  4. 【依赖倒置原则 DIP（SOLID-D）】                                        │
// │     Chain 依赖 schema.Memory 抽象，不依赖具体 ConversationBuffer。         │
// │     测试时注入 Simple（空实现），生产时注入 MongoMemory，调用方零修改。       │
// └─────────────────────────────────────────────────────────────────────────┘
//
// Memory 接口（schema/memory.go）：
//   LoadMemoryVariables(ctx, inputs) → 每轮开始前注入历史到 inputs
//   SaveContext(ctx, inputs, outputs) → 每轮结束后保存本轮对话
//
// 内置实现：
//   memory.Simple             → 什么都不存（默认）
//   memory.ConversationBuffer → 全量保存对话文本
//   memory.ConversationWindowBuffer → 只保留最近 K 轮
//   memory.ConversationTokenBuffer   → 按 token 数限制
//   memory.ConversationSummaryBuffer → LLM 自动总结旧历史
//
// 关键 key：
//   MemoryKey 默认 "history" → 会把历史注入 prompt 的 {{.history}}
// =============================================================================

package main

import (
	"context"
	"fmt"

	"github.com/tmc/langchaingo/chains"
	"github.com/tmc/langchaingo/llms/fake"
	"github.com/tmc/langchaingo/memory"
	"github.com/tmc/langchaingo/prompts"
)

func main() {
	ctx := context.Background()

	// ① 无 Memory（默认 Simple）：每轮都忘记上一轮
	noMemLLM := fake.NewFakeLLM([]string{
		"你好！有什么可以帮你？",
		"我不知道你叫什么。",  // 没有记忆，第 2 轮忘记了第 1 轮
	})
	noMemChain := chains.NewConversation(noMemLLM, memory.NewSimple())

	_, _ = chains.Run(ctx, noMemChain, "我叫小明")
	r2, _ := chains.Run(ctx, noMemChain, "我叫什么名字？")
	fmt.Println("=== ① 无记忆 ===")
	fmt.Println("回答：", r2)

	// ② ConversationBuffer：全量记忆
	//    prompt 里有 {{.history}}，memory 会把以前的对话填进去
	bufLLM := fake.NewFakeLLM([]string{
		"你好小红！很高兴认识你。",
		"你叫小红，我刚才你说过了。",  // 因为有历史，"知道"了名字
	})

	// ConversationBuffer 需要 prompt 里有 {{.history}} 变量
	convPrompt := prompts.NewPromptTemplate(
		"以下是对话历史：\n{{.history}}\n\n人类：{{.input}}\nAI：",
		[]string{"input"},
	)

	bufChain := chains.NewLLMChain(bufLLM, convPrompt)
	bufChain.Memory = memory.NewConversationBuffer() // 换掉默认的 Simple Memory

	r3, _ := chains.Run(ctx, bufChain, "我叫小红")
	r4, _ := chains.Run(ctx, bufChain, "我叫什么名字？")
	fmt.Println("\n=== ② ConversationBuffer ===")
	fmt.Println("第1轮：", r3)
	fmt.Println("第2轮：", r4)

	// ③ 直接操作 Memory，查看它存了什么
	mem := memory.NewConversationBuffer()
	memCtx := context.Background()
	_ = mem.SaveContext(memCtx,
		map[string]any{"input": "我喜欢 Go 语言"},
		map[string]any{"output": "Go 是一门很棒的语言！"},
	)
	_ = mem.SaveContext(memCtx,
		map[string]any{"input": "我喜欢哪种语言？"},
		map[string]any{"output": "你说你喜欢 Go 语言。"},
	)

	vars, _ := mem.LoadMemoryVariables(memCtx, map[string]any{})
	fmt.Println("\n=== ③ 直接查看 Memory 内容 ===")
	fmt.Println("history:\n", vars["history"])

	fmt.Println("\n【设计启示】")
	fmt.Println("你的 fff_agent/memory.Memory 只有 Add/Messages，")
	fmt.Println("langchaingo 的 Memory 接口把'读'和'写'分离，并规定了 MemoryKey")
	fmt.Println("这样任何 Chain 只要拿到 Memory 接口就能接入任何存储后端（Redis/MongoDB/Zep）")
}
