// =============================================================================
// Level 1: LLM Model 接口
// =============================================================================
// 目标：理解 langchaingo 最底层的接口长什么样、怎么调用
//
// ┌─────────────────────────────────────────────────────────────────────────┐
// │  涉及的设计模式 & 设计原则                                                  │
// │                                                                          │
// │  1. 【策略模式 Strategy】                                                 │
// │     llms.Model 是策略接口，OpenAI / Anthropic / Ollama / FakeLLM 是       │
// │     具体策略。调用方只依赖接口，运行时可以随时换掉底层 LLM 而不改业务代码。    │
// │     → 你的代码只写 var m llms.Model，不写 *openai.LLM                     │
// │                                                                          │
// │  2. 【依赖倒置原则 DIP（SOLID-D）】                                        │
// │     上层模块（Chain/Agent）依赖 llms.Model 抽象，不依赖具体 OpenAI 实现。   │
// │     具体实现依赖抽象，而不是抽象依赖具体。                                    │
// │                                                                          │
// │  3. 【接口隔离原则 ISP（SOLID-I）】                                        │
// │     Model 接口只有 2 个方法，职责单一。需要推理能力时单独用 ReasoningModel  │
// │     子接口，不把所有功能堆到一个大接口上。                                    │
// │                                                                          │
// │  4. 【外观模式 Facade（变体）】                                             │
// │     Call() 是对 GenerateContent() 的简化外观，屏蔽了 MessageContent 结构、 │
// │     Choices 切片等复杂细节，让文本场景只用一行调用。                          │
// └─────────────────────────────────────────────────────────────────────────┘
//
// 核心接口（llms/llms.go）:
//   type Model interface {
//       GenerateContent(ctx, []MessageContent, ...CallOption) (*ContentResponse, error)
//       Call(ctx, prompt string, ...CallOption) (string, error)   // 简化版，deprecated
//   }
//
// FakeLLM 是一个预设回复队列的测试用 LLM，不需要 API Key，
// 每次 GenerateContent 按顺序弹出一条回复。
// =============================================================================

package main

import (
	"context"
	"fmt"

	"github.com/tmc/langchaingo/llms"
	"github.com/tmc/langchaingo/llms/fake"
)

func main() {
	// ① 创建 FakeLLM，预设两条回复
	llm := fake.NewFakeLLM([]string{
		"我是一个 AI 助理，很高兴认识你！",
		"北京今天晴，气温 22°C。",
	})

	ctx := context.Background()

	// ② 最通用的调用方式：GenerateContent
	//    MessageContent = {Role + []ContentPart}
	//    这是所有多模态/chat 模型的统一入口
	resp, err := llm.GenerateContent(ctx, []llms.MessageContent{
		llms.TextParts(llms.ChatMessageTypeHuman, "你好，介绍一下你自己"),
	})
	if err != nil {
		panic(err)
	}
	// resp.Choices 是一个切片，一般用 Choices[0].Content
	fmt.Println("【GenerateContent 回复】", resp.Choices[0].Content)

	// ③ 简化版：Call（内部也是调 GenerateContent）
	//    只接受字符串，返回字符串，适合 text-only 场景
	answer, err := llm.Call(ctx, "北京天气怎么样？")
	if err != nil {
		panic(err)
	}
	fmt.Println("【Call 回复】", answer)

	// ④ 关键设计启示：
	//    - Model 接口只有两个方法，任何 LLM 都实现这两个方法
	//    - OpenAI/Anthropic/Ollama/Bedrock... 全都换成这个接口
	//    - 你写 Chain/Agent 时面向接口编程，不依赖具体 LLM 实现
	fmt.Println("\n【设计启示】")
	fmt.Println("你的 fff_agent/llm.Client 接口 = langchaingo 的 llms.Model 接口")
	fmt.Println("区别：langchaingo 用 MessageContent 结构体统一多轮+多模态，你用 []Message")
}
