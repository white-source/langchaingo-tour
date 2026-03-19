// =============================================================================
// Level 7: Callbacks —— 观测 Agent 运行过程
// =============================================================================
// 目标：理解 Callback 机制如何实现无侵入式观测
//
// ┌─────────────────────────────────────────────────────────────────────────┐
// │  涉及的设计模式 & 设计原则                                                  │
// │                                                                          │
// │  1. 【观察者模式 Observer —— 核心模式】                                    │
// │     callbacks.Handler 是观察者接口（16 个 Handle* 方法）。                  │
// │     LLMChain / Executor / Tool 是主题（Subject）。                        │
// │     主题在生命周期节点调用 handler.HandleXxx()，不关心观察者的具体逻辑。      │
// │     → 可注入 MetricsHandler（采指标） / LogHandler（打日志） /              │
// │       OpenTelemetryHandler（分布式追踪），主题代码零修改。                   │
// │                                                                          │
// │  2. 【横切关注点 / AOP 思想 Cross-Cutting Concerns】                       │
// │     日志、指标、追踪不属于任何单一业务模块，是"横切关注点"。                   │
// │     Callback 机制把它们从业务逻辑里剥离，集中到 Handler 里处理。              │
// │     这是 AOP（面向切面编程）在 Go 接口体系下的实现方式。                      │
// │                                                                          │
// │  3. 【开闭原则 OCP（SOLID-O）】                                            │
// │     新增一种观测方式（如接入 Datadog）只需实现 Handler 接口并注入，            │
// │     不需要修改任何业务代码（Chain / Agent / Tool 都不用动）。                 │
// │                                                                          │
// │  4. 【接口隔离 + 空实现技巧 ISP（SOLID-I）】                               │
// │     Handler 接口有 16 个方法，通常只关心几个。                               │
// │     最佳实践：嵌入实现了所有方法空实现的 BaseHandler，只覆盖关心的方法，       │
// │     避免每次都写 16 个空方法（本关显式展示全部方法，便于理解接口全貌）。        │
// └─────────────────────────────────────────────────────────────────────────┘
//
// callbacks.Handler 接口（callbacks/callbacks.go）定义了 16 个钩子：
//   HandleLLMStart / HandleLLMGenerateContentEnd ...  ← LLM 相关
//   HandleChainStart / HandleChainEnd / HandleChainError  ← Chain 相关
//   HandleToolStart / HandleToolEnd / HandleToolError     ← 工具相关
//   HandleAgentAction / HandleAgentFinish                 ← Agent 相关
//   HandleStreamingFunc                                   ← 流式输出
//
// 所有内置组件（LLMChain、Executor、Tool）在关键节点调用这些钩子
// 你注入一个 CallbacksHandler 就能监控整个执行过程
//
// 内置实现：
//   callbacks.LogHandler      → 打印到 stderr
//   callbacks.StreamLogHandler → 流式打印
// =============================================================================

package main

import (
	"context"
	"fmt"
	"strings"

	"github.com/tmc/langchaingo/agents"
	"github.com/tmc/langchaingo/callbacks"
	"github.com/tmc/langchaingo/chains"
	"github.com/tmc/langchaingo/llms"
	"github.com/tmc/langchaingo/llms/fake"
	"github.com/tmc/langchaingo/schema"
	"github.com/tmc/langchaingo/tools"
)

// ─────────────────────── 自定义 Callback Handler ──────────────────

// MetricsHandler 模拟一个"采集 metrics"的 handler
type MetricsHandler struct {
	LLMCalls   int
	ToolCalls  int
	TotalSteps int
}

// 实现 16 个接口方法（只关心几个关键的）
var _ callbacks.Handler = (*MetricsHandler)(nil)

func (m *MetricsHandler) HandleLLMStart(_ context.Context, prompts []string) {
	m.LLMCalls++
	fmt.Printf("[metrics] LLM call #%d (prompt len=%d)\n", m.LLMCalls, len(prompts[0]))
}
func (m *MetricsHandler) HandleLLMGenerateContentStart(_ context.Context, _ []llms.MessageContent) {
	m.LLMCalls++
}
func (m *MetricsHandler) HandleLLMGenerateContentEnd(_ context.Context, _ *llms.ContentResponse) {}
func (m *MetricsHandler) HandleLLMError(_ context.Context, err error) {
	fmt.Println("[metrics] LLM error:", err)
}
func (m *MetricsHandler) HandleChainStart(_ context.Context, _ map[string]any) {}
func (m *MetricsHandler) HandleChainEnd(_ context.Context, _ map[string]any) {
	m.TotalSteps++
}
func (m *MetricsHandler) HandleChainError(_ context.Context, _ error) {}
func (m *MetricsHandler) HandleToolStart(_ context.Context, input string) {
	m.ToolCalls++
	fmt.Printf("[metrics] Tool call #%d, input=%q\n", m.ToolCalls, input)
}
func (m *MetricsHandler) HandleToolEnd(_ context.Context, output string) {
	fmt.Printf("[metrics] Tool result=%q\n", output)
}
func (m *MetricsHandler) HandleToolError(_ context.Context, _ error) {}
func (m *MetricsHandler) HandleAgentAction(_ context.Context, a schema.AgentAction) {
	fmt.Printf("[metrics] AgentAction → tool=%s input=%s\n", a.Tool, a.ToolInput)
}
func (m *MetricsHandler) HandleAgentFinish(_ context.Context, f schema.AgentFinish) {
	fmt.Printf("[metrics] AgentFinish → %v\n", f.ReturnValues)
}
func (m *MetricsHandler) HandleRetrieverStart(_ context.Context, _ string) {}
func (m *MetricsHandler) HandleRetrieverEnd(_ context.Context, _ string, _ []schema.Document) {}
func (m *MetricsHandler) HandleStreamingFunc(_ context.Context, chunk []byte) {
	fmt.Print(string(chunk)) // 流式打印每个 chunk
}
func (m *MetricsHandler) HandleText(_ context.Context, text string) {
	_ = text
}

// ─────────────────────── 简单工具 ─────────────────────────────────

type UpperTool struct{}

func (u UpperTool) Name() string        { return "upper" }
func (u UpperTool) Description() string { return "把文字变成大写" }
func (u UpperTool) Call(_ context.Context, input string) (string, error) {
	return strings.ToUpper(input), nil
}

// ─────────────────────────── main ─────────────────────────────────

func main() {
	ctx := context.Background()
	metrics := &MetricsHandler{}

	llm := fake.NewFakeLLM([]string{
		"Thought: 需要把文字改成大写。\nAction: upper\nAction Input: hello langchaingo",
		"Thought: 完成了。\nFinal Answer: 转换结果是 HELLO LANGCHAINGO",
	})

	agentTools := []tools.Tool{UpperTool{}}

	agent := agents.NewOneShotAgent(
		llm,
		agentTools,
		agents.WithMaxIterations(3),
		agents.WithCallbacksHandler(metrics), // ← 注入 metrics handler
	)
	executor := agents.NewExecutor(agent,
		agents.WithCallbacksHandler(metrics),
	)

	fmt.Println("═══ 开始执行，观测 Callback 触发顺序 ═══")
	answer, err := chains.Run(ctx, executor, "把 hello langchaingo 变成大写")
	if err != nil {
		fmt.Println("Error:", err)
		return
	}

	fmt.Println("\n══ 最终答案:", answer)
	fmt.Println("\n══ 汇总统计：")
	fmt.Printf("   LLM 调用次数：%d\n", metrics.LLMCalls)
	fmt.Printf("   工具调用次数：%d\n", metrics.ToolCalls)
	fmt.Printf("   Chain 完成步数：%d\n", metrics.TotalSteps)

	fmt.Println("\n【设计启示】")
	fmt.Println("Callback 是零侵入的观测点——你不需要改任何业务代码")
	fmt.Println("日志、Tracing、指标采集、流式推送都可以挂在这里")
	fmt.Println("你的 fff_agent 目前没有 Callback，可以在 Execute/Plan 后加 Hook 接口")
}
