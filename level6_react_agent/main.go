// =============================================================================
// Level 6: ReAct Agent 全流程 —— 最核心的一关
// =============================================================================
// 目标：透明地看清 Agent Loop 每一步在做什么
//
// ┌─────────────────────────────────────────────────────────────────────────┐
// │  涉及的设计模式 & 设计原则                                                  │
// │                                                                          │
// │  1. 【模板方法模式 Template Method —— Loop 骨架】                          │
// │     Executor.Call() 定义不变的骨架：                                       │
// │       for { Plan() → doAction() → 追加 steps → 继续 or 退出 }            │
// │     Agent.Plan() 是"可变步骤"（钩子），由具体 Agent 实现，骨架不变。          │
// │                                                                          │
// │  2. 【策略模式 Strategy —— Agent 可替换】                                  │
// │     Executor 持有 agents.Agent 接口，可以插入：                             │
// │       OneShotZeroAgent（ReAct文本） / ConversationalAgent /               │
// │       OpenAIFunctionsAgent（FunctionCall） / 自定义 Agent                 │
// │     切换 Agent 类型不需要改 Executor 一行代码。                              │
// │                                                                          │
// │  3. 【观察者模式 Observer —— Callbacks】                                   │
// │     InspectHandler 是观察者，Executor/LLMChain/Tool 是主题（Subject）。    │
// │     主题在生命周期节点调 HandleXxx()，不关心观察者的具体实现。                 │
// │     实现了"监控/日志/追踪与业务逻辑解耦"。                                    │
// │                                                                          │
// │  4. 【状态机 State Machine（隐式）】                                        │
// │     Plan() 返回 AgentAction（继续执行工具） 或 AgentFinish（终止循环）。      │
// │     这是一个两状态机：Running → Finished，由 LLM 输出决定转移。              │
// │                                                                          │
// │  5. 【依赖注入 / 测试替身 —— FakeLLM】                                     │
// │     用 FakeLLM 预设响应替换真实 LLM，是 DI + Test Double 的经典用法：       │
// │     不需要 API Key、响应可控、测试速度快、行为可重复。                         │
// └─────────────────────────────────────────────────────────────────────────┘
//
// ReAct = Reason + Act，循环逻辑：
//
//   用户问题 → [Executor.Call]
//   ┌─────────────────── Agent Loop ───────────────────┐
//   │ 轮次 N                                            │
//   │  ① Agent.Plan(steps, inputs)                     │
//   │     → 构造 Prompt（含历史 scratchpad）            │
//   │     → LLM 回复文本                                │
//   │     → parseOutput()                              │
//   │        ├─ 发现 "Action: xxx\nAction Input: yyy"   │
//   │        │    → 返回 []AgentAction                 │
//   │        └─ 发现 "Final Answer: zzz"               │
//   │             → 返回 *AgentFinish → 退出            │
//   │  ② Executor.doAction(action)                     │
//   │     → tool.Call(input)                           │
//   │     → 把 Observation 存入 steps                  │
//   └──────────────── 进入下一轮 ──────────────────────┘
//
// FakeLLM 预设的响应：
//   Round 1: LLM 返回 "Action: calculator\nAction Input: 25 * 4"
//   Round 2: LLM 返回 "Final Answer: 25 乘以 4 等于 100"
// =============================================================================

package main

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/tmc/langchaingo/agents"
	"github.com/tmc/langchaingo/callbacks"
	"github.com/tmc/langchaingo/chains"
	"github.com/tmc/langchaingo/llms"
	"github.com/tmc/langchaingo/llms/fake"
	"github.com/tmc/langchaingo/schema"
	"github.com/tmc/langchaingo/tools"
)

// ─────────────────────────── 工具实现 ─────────────────────────────

// 计算器工具
type Calculator struct{}

func (c Calculator) Name() string        { return "calculator" }
func (c Calculator) Description() string { return "四则运算，输入格式：数字 运算符 数字" }
func (c Calculator) Call(_ context.Context, input string) (string, error) {
	// 简化版：只支持 25 * 4 这类
	var a, b float64
	var op string
	_, err := fmt.Sscanf(strings.TrimSpace(input), "%f %s %f", &a, &op, &b)
	if err != nil {
		return "无法解析：" + input, nil
	}
	switch op {
	case "*":
		return fmt.Sprintf("%.0f", a*b), nil
	case "+":
		return fmt.Sprintf("%.0f", a+b), nil
	case "-":
		return fmt.Sprintf("%.0f", a-b), nil
	case "/":
		return fmt.Sprintf("%.2f", a/b), nil
	}
	return "不支持的运算符", nil
}

// 时间工具
type TimeTool struct{}

func (t TimeTool) Name() string        { return "get_time" }
func (t TimeTool) Description() string { return "获取当前时间，无需参数" }
func (t TimeTool) Call(_ context.Context, _ string) (string, error) {
	return time.Now().Format("15:04:05"), nil
}

// ─────────────────────── 回调：透视每一步 ─────────────────────────

// InspectHandler 实现 callbacks.Handler，打印每个关键节点
type InspectHandler struct{}

var _ callbacks.Handler = InspectHandler{}

func (InspectHandler) HandleText(_ context.Context, text string) {
}
func (InspectHandler) HandleLLMStart(_ context.Context, prompts []string) {
	fmt.Println("\n┌─── LLM 调用开始 ────────────────────────────────────")
	for _, p := range prompts {
		// 只打印最后 200 字，避免输出太长
		if len(p) > 200 {
			p = "..." + p[len(p)-200:]
		}
		fmt.Println("  PROMPT:", p)
	}
	fmt.Println("└─────────────────────────────────────────────────────")
}
func (InspectHandler) HandleLLMGenerateContentStart(_ context.Context, _ []llms.MessageContent) {}
func (InspectHandler) HandleLLMGenerateContentEnd(_ context.Context, _ *llms.ContentResponse)   {}
func (InspectHandler) HandleLLMError(_ context.Context, err error) {
	fmt.Println("  LLM ERROR:", err)
}
func (InspectHandler) HandleChainStart(_ context.Context, inputs map[string]any) {
	fmt.Println("\n▶ Chain 开始，inputs keys:", keys(inputs))
}
func (InspectHandler) HandleChainEnd(_ context.Context, outputs map[string]any) {
	fmt.Println("◀ Chain 结束，outputs keys:", keys(outputs))
}
func (InspectHandler) HandleChainError(_ context.Context, err error) {
	fmt.Println("  Chain ERROR:", err)
}
func (InspectHandler) HandleToolStart(_ context.Context, input string) {
	fmt.Println("\n🔧 工具调用开始，input:", input)
}
func (InspectHandler) HandleToolEnd(_ context.Context, output string) {
	fmt.Println("✅ 工具调用结束，output:", output)
}
func (InspectHandler) HandleToolError(_ context.Context, err error) {
	fmt.Println("  工具 ERROR:", err)
}
func (InspectHandler) HandleAgentAction(_ context.Context, action schema.AgentAction) {
	fmt.Printf("\n🤔 Agent 决策：调用工具 [%s]，输入 [%s]\n", action.Tool, action.ToolInput)
}
func (InspectHandler) HandleAgentFinish(_ context.Context, finish schema.AgentFinish) {
	fmt.Printf("🏁 Agent 完成：%v\n", finish.ReturnValues)
}
func (InspectHandler) HandleRetrieverStart(_ context.Context, query string) {}
func (InspectHandler) HandleRetrieverEnd(_ context.Context, query string, docs []schema.Document) {
}
func (InspectHandler) HandleStreamingFunc(_ context.Context, chunk []byte) {}

func keys(m map[string]any) []string {
	ks := make([]string, 0, len(m))
	for k := range m {
		ks = append(ks, k)
	}
	return ks
}

// ─────────────────────────── main ─────────────────────────────────

func main() {
	ctx := context.Background()

	// FakeLLM 预设两条响应，精确模拟 ReAct 两轮：
	//   Round 1 → LLM 决定调计算器
	//   Round 2 → LLM 看到 Observation 后给出 Final Answer
	llm := fake.NewFakeLLM([]string{
		// Round 1：ReAct 格式，Action+ Action Input
		"Thought: 我需要用计算器来计算这个。\nAction: calculator\nAction Input: 25 * 4",
		// Round 2：看到计算结果后直接回答
		"Thought: 我已经得到了计算结果。\nFinal Answer: 25 乘以 4 等于 100",
	})

	agentTools := []tools.Tool{
		Calculator{},
		TimeTool{},
	}

	// 创建 OneShotZeroAgent（ReAct 风格）
	agent := agents.NewOneShotAgent(
		llm,
		agentTools,
		agents.WithMaxIterations(5),
		agents.WithCallbacksHandler(InspectHandler{}),
	)

	executor := agents.NewExecutor(agent,
		agents.WithCallbacksHandler(InspectHandler{}),
	)

	fmt.Println("═══════════════════════════════════════════════════")
	fmt.Println("问题：25 乘以 4 是多少？")
	fmt.Println("═══════════════════════════════════════════════════")

	answer, err := chains.Run(ctx, executor, "25 乘以 4 是多少？")
	if err != nil {
		fmt.Println("Error:", err)
		return
	}

	fmt.Println("\n═══════════════════════════════════════════════════")
	fmt.Println("最终答案：", answer)
	fmt.Println("═══════════════════════════════════════════════════")

	fmt.Println("\n【核心设计总结】")
	fmt.Println("1. FakeLLM.responses[i] 对应第 i 次 LLM 调用的输出")
	fmt.Println("2. parseOutput() 用正则解析 'Action: xxx\\nAction Input: yyy'")
	fmt.Println("3. 每轮工具结果以 'Observation: result' 追加到 scratchpad")
	fmt.Println("4. 下一轮 LLM 看到 scratchpad 后决策，直到输出 'Final Answer:'")
	fmt.Println("\n这就是 ReAct 循环的全部秘密！")
}
