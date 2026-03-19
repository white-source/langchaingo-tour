// =============================================================================
// Level 3: LLMChain —— Prompt + LLM 的流水线
// =============================================================================
// 目标：理解 Chain 接口，以及 LLMChain 是如何把 Prompt 和 LLM 串起来的
//
// ┌─────────────────────────────────────────────────────────────────────────┐
// │  涉及的设计模式 & 设计原则                                                  │
// │                                                                          │
// │  1. 【管道-过滤器模式 Pipe-Filter（责任链变体）】                             │
// │     LLMChain 内部：Prompt.Format → LLM.Generate → OutputParser.Parse    │
// │     每一步是一个"过滤器"，前一步的输出是后一步的输入。                         │
// │     SimpleSequentialChain 再把多个 LLMChain 串成更长的管道。                │
// │                                                                          │
// │  2. 【组合模式 Composite】                                                 │
// │     所有 Chain（LLMChain / SequentialChain / Executor）都实现同一接口，     │
// │     因此可以把 Chain 嵌套进 Chain，形成树状组合结构。                         │
// │     调用方无需区分叶子还是组合，统一用 chains.Call() 驱动。                   │
// │                                                                          │
// │  3. 【外观模式 Facade】                                                    │
// │     chains.Run() 封装了"建 ctx、调 Call、取输出值"三步，                     │
// │     让最简场景只需一行代码，屏蔽 map 操作细节。                               │
// │                                                                          │
// │  4. 【里氏替换原则 LSP（SOLID-L）】                                        │
// │     SequentialChain 可以出现在任何接受 Chain 接口的地方（如嵌套进 Executor）, │
// │     行为仍符合 Chain 契约，这就是 LSP。                                      │
// └─────────────────────────────────────────────────────────────────────────┘
//
// Chain 接口（chains/chains.go）:
//   type Chain interface {
//       Call(ctx, inputs map[string]any, ...option) (map[string]any, error)
//       GetMemory() schema.Memory
//       GetInputKeys() []string
//       GetOutputKeys() []string
//   }
//
// LLMChain 内部调用流程：
//   chains.Call(ctx, chain, inputs)
//     ① memory.LoadMemoryVariables()  → 把历史注入 inputs
//     ② chain.Call(ctx, fullInputs)
//        → Prompt.FormatPrompt(inputs)   ← 填充模板
//        → llm.GenerateContent(prompt)   ← 调 LLM
//        → OutputParser.Parse(result)    ← 解析输出
//     ③ memory.SaveContext()            → 保存本轮对话
//
// chains.Run  = 单输入单输出的快捷方式，内部调 Call
// chains.Call = 多输入/输出的完整方式
// chains.Predict = 只返回文本（跳过 memory save）
// =============================================================================

package main

import (
	"context"
	"fmt"

	"github.com/tmc/langchaingo/chains"
	"github.com/tmc/langchaingo/llms/fake"
	"github.com/tmc/langchaingo/prompts"
)

func main() {
	ctx := context.Background()

	// ① 最简单的 LLMChain：一个模板 + 一个 LLM
	llm := fake.NewFakeLLM([]string{
		"袜子公司可以叫：「足迹天下」",       // 第 1 次调用返回
		"Chaussettes Magiques", // 第 2 次调用返回（翻译结果）
	})

	prompt := prompts.NewPromptTemplate(
		"给一家生产 {{.product}} 的公司起个名字：",
		[]string{"product"},
	)
	llmChain := chains.NewLLMChain(llm, prompt)

	// ② 单输入：chains.Run（最简洁）
	out, err := chains.Run(ctx, llmChain, "袜子")
	if err != nil {
		panic(err)
	}
	fmt.Println("=== ① chains.Run（单输入）===")
	fmt.Println("公司名：", out)

	// ③ 多输入：chains.Call（返回 map）
	translatePrompt := prompts.NewPromptTemplate(
		"把下面这句 {{.from}} 翻译成 {{.to}}：{{.text}}",
		[]string{"from", "to", "text"},
	)
	translateChain := chains.NewLLMChain(llm, translatePrompt)

	result, err := chains.Call(ctx, translateChain, map[string]any{
		"from": "中文",
		"to":   "法语",
		"text": "魔法袜子",
	})
	if err != nil {
		panic(err)
	}
	fmt.Println("\n=== ② chains.Call（多输入）===")
	// 输出是 map，key 默认是 "text"（LLMChain.OutputKey）
	fmt.Println("翻译结果 map：", result)
	fmt.Println("翻译结果 str：", result[translateChain.OutputKey])

	// ④ SimpleSequentialChain：多个 Chain 串联
	//    Chain1 的输出自动成为 Chain2 的输入
	//    适合"写大纲 → 根据大纲写正文"这种流水线
	llm2 := fake.NewFakeLLM([]string{
		"大纲：1.起因 2.经过 3.结局", // chain1 输出
		"这是一篇根据大纲写的完整故事...", // chain2 输出
	})

	chain1 := chains.NewLLMChain(llm2,
		prompts.NewPromptTemplate("给这个故事写大纲：{{.input}}", []string{"input"}))
	chain2 := chains.NewLLMChain(llm2,
		prompts.NewPromptTemplate("根据大纲写故事：{{.input}}", []string{"input"}))

	seqChain, err := chains.NewSimpleSequentialChain([]chains.Chain{chain1, chain2})
	if err != nil {
		panic(err)
	}
	story, err := chains.Run(ctx, seqChain, "一只学会编程的猫")
	if err != nil {
		panic(err)
	}
	fmt.Println("\n=== ③ SimpleSequentialChain ===")
	fmt.Println("最终故事：", story)

	fmt.Println("\n【设计启示】")
	fmt.Println("Chain 是 langchaingo 最核心的抽象：任何'接受输入→产生输出'的逻辑都是 Chain")
	fmt.Println("Executor（Agent循环）本身也实现了 Chain 接口，所以 Agent 可以嵌入任何 Chain 里")
}
