// =============================================================================
// Level 8: 设计自己的 Agent —— 从头实现 Agent 接口
// =============================================================================
// 目标：实现 agents.Agent 接口，插入到 langchaingo 的 Executor 中
//
// ┌─────────────────────────────────────────────────────────────────────────┐
// │  涉及的设计模式 & 设计原则（综合运用，融会贯通）                              │
// │                                                                          │
// │  1. 【策略模式 Strategy —— Agent 即决策策略】                               │
// │     MyStructuredAgent 是一种新的"决策策略"：规则驱动，不需要调用 LLM。       │
// │     把它注入 Executor 后，整个 Loop 骨架不变，只换了决策大脑。                │
// │     算法（Plan）可替换，使用方（Executor）完全不感知。                        │
// │                                                                          │
// │  2. 【模板方法模式 Template Method —— Executor 是不变骨架】                 │
// │     Executor.Call() 是固定的 Loop 骨架（Plan→Execute→收集结果）。           │
// │     MyStructuredAgent.Plan() 是可变的"填空"部分。                          │
// │     父类定义算法流程，子类（Agent 实现）填充具体步骤。                        │
// │                                                                          │
// │  3. 【命令模式 Command —— AgentAction 是命令对象】                          │
// │     Plan() 返回的 AgentAction{Tool, ToolInput} 封装了一条命令：             │
// │     "执行哪个工具、传什么参数"对象化，Executor 作为 Invoker 负责执行。        │
// │                                                                          │
// │  4. 【迪米特法则 LoD / 最少知道原则】                                       │
// │     MyStructuredAgent 只知道 tools.Tool 接口，不知道 Executor 内部，        │
// │     不知道 LLMChain，不知道 Memory。每个组件只和直接"朋友"通信。             │
// │                                                                          │
// │  5. 【SOLID 全景回顾 —— 8 个 Level 的设计总结】                             │
// │     S-SRP：Agent / Tool / Memory / Prompt 各司其职，单一职责              │
// │     O-OCP：新增 Agent 类型或 Tool 无需改 Executor（对扩展开放）             │
// │     L-LSP：MyStructuredAgent 可以无缝替换任何内置 Agent（子类可替换父类）    │
// │     I-ISP：Agent 接口 4 个方法，Tool 接口 3 个方法，足够小                 │
// │     D-DIP：Executor 依赖 Agent/Tool 抽象，不依赖具体实现                   │
// └─────────────────────────────────────────────────────────────────────────┘
//
// 你需要实现：
//   Plan(ctx, intermediateSteps, inputs, options) → ([]AgentAction, *AgentFinish, error)
//   GetInputKeys() []string
//   GetOutputKeys() []string
//   GetTools() []tools.Tool
//
// 这一关实现一个"结构化思维 Agent"：
//   - 收到问题后，先把问题拆成子任务
//   - 依次执行每个子任务对应的工具
//   - 最后汇总结果
//
// 关键点：
//   - 你完全控制 Plan() 的逻辑（不需要 prompt 解析）
//   - intermediateSteps 包含之前执行的所有 Action+Observation
//   - 返回 AgentAction = 继续执行工具，返回 AgentFinish = 结束
// =============================================================================

package main

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/tmc/langchaingo/agents"
	"github.com/tmc/langchaingo/chains"
	"github.com/tmc/langchaingo/schema"
	"github.com/tmc/langchaingo/tools"
)

// ─────────────────────── 工具实现 ─────────────────────────────────

type TimeTool struct{}

func (t TimeTool) Name() string        { return "get_time" }
func (t TimeTool) Description() string { return "获取当前时间" }
func (t TimeTool) Call(_ context.Context, _ string) (string, error) {
	return time.Now().Format("15:04:05"), nil
}

type WeatherTool struct{}

func (w WeatherTool) Name() string        { return "get_weather" }
func (w WeatherTool) Description() string { return "查询城市天气" }
func (w WeatherTool) Call(_ context.Context, input string) (string, error) {
	city := strings.TrimSpace(input)
	if city == "" {
		city = "北京"
	}
	weather := map[string]string{
		"北京": "晴，22°C",
		"上海": "多云，18°C",
	}
	if w, ok := weather[city]; ok {
		return city + "：" + w, nil
	}
	return city + "：天气数据暂不可用", nil
}

// ─────────────────────── 自定义 Agent ────────────────────────────

// MyStructuredAgent 是一个"结构化任务分解 Agent"
// 它根据输入直接决定要执行哪些工具，不依赖文本解析，不需要 LLM
type MyStructuredAgent struct {
	toolList []tools.Tool
	// 跟踪任务队列
	taskQueue []schema.AgentAction
	queueInit bool
}

// 确保实现了 agents.Agent 接口
var _ agents.Agent = (*MyStructuredAgent)(nil)

func NewMyStructuredAgent(toolList []tools.Tool) *MyStructuredAgent {
	return &MyStructuredAgent{toolList: toolList}
}

// Plan 是 Agent 的核心方法，每轮被 Executor 调用一次
// intermediateSteps 包含之前已执行的所有 Action+Observation
func (a *MyStructuredAgent) Plan(
	_ context.Context,
	intermediateSteps []schema.AgentStep,
	inputs map[string]string,
	_ ...chains.ChainCallOption,
) ([]schema.AgentAction, *schema.AgentFinish, error) {

	// 第一次调用：根据输入初始化任务队列
	if !a.queueInit {
		a.queueInit = true
		query := strings.ToLower(inputs["input"])

		// 规则：分析问题需要哪些工具
		if strings.Contains(query, "时间") || strings.Contains(query, "几点") {
			a.taskQueue = append(a.taskQueue, schema.AgentAction{
				Tool:      "get_time",
				ToolInput: "",
				Log:       "需要查询时间",
			})
		}
		if strings.Contains(query, "天气") {
			city := extractCity(query)
			a.taskQueue = append(a.taskQueue, schema.AgentAction{
				Tool:      "get_weather",
				ToolInput: city,
				Log:       "需要查询" + city + "天气",
			})
		}

		if len(a.taskQueue) == 0 {
			// 没匹配到工具，直接回答
			return nil, &schema.AgentFinish{
				ReturnValues: map[string]any{"output": "我不知道如何回答这个问题"},
			}, nil
		}
	}

	// 判断已完成的步骤数
	doneTasks := len(intermediateSteps)
	remainingTasks := len(a.taskQueue) - doneTasks

	fmt.Printf("  [MyAgent] 共 %d 个任务，已完成 %d 个，还剩 %d 个\n",
		len(a.taskQueue), doneTasks, remainingTasks)

	// 还有任务未执行
	if doneTasks < len(a.taskQueue) {
		nextAction := a.taskQueue[doneTasks]
		return []schema.AgentAction{nextAction}, nil, nil
	}

	// 所有任务执行完毕，汇总结果
	var observations []string
	for _, step := range intermediateSteps {
		observations = append(observations, step.Observation)
	}
	summary := "查询结果：" + strings.Join(observations, "，")

	return nil, &schema.AgentFinish{
		ReturnValues: map[string]any{"output": summary},
	}, nil
}

func (a *MyStructuredAgent) GetInputKeys() []string  { return []string{"input"} }
func (a *MyStructuredAgent) GetOutputKeys() []string { return []string{"output"} }
func (a *MyStructuredAgent) GetTools() []tools.Tool  { return a.toolList }

// 简单城市提取
func extractCity(query string) string {
	for _, city := range []string{"北京", "上海", "深圳", "广州"} {
		if strings.Contains(query, city) {
			return city
		}
	}
	return "北京"
}

// ─────────────────────────── main ─────────────────────────────────

func main() {
	ctx := context.Background()

	agentTools := []tools.Tool{
		TimeTool{},
		WeatherTool{},
	}

	fmt.Println("═══ 测试 1：同时查时间和北京天气 ═══")
	myAgent := NewMyStructuredAgent(agentTools)
	executor := agents.NewExecutor(myAgent, agents.WithMaxIterations(5))

	answer, err := chains.Run(ctx, executor, "现在几点了？北京天气怎么样？")
	if err != nil {
		fmt.Println("Error:", err)
	} else {
		fmt.Println("最终答案：", answer)
	}

	fmt.Println("\n═══ 测试 2：只查上海天气 ═══")
	myAgent2 := NewMyStructuredAgent(agentTools)
	executor2 := agents.NewExecutor(myAgent2, agents.WithMaxIterations(5))

	answer2, err := chains.Run(ctx, executor2, "上海今天天气如何？")
	if err != nil {
		fmt.Println("Error:", err)
	} else {
		fmt.Println("最终答案：", answer2)
	}

	fmt.Println("\n═══ 测试 3：未知问题 ═══")
	myAgent3 := NewMyStructuredAgent(agentTools)
	executor3 := agents.NewExecutor(myAgent3, agents.WithMaxIterations(5))

	answer3, _ := chains.Run(ctx, executor3, "推荐一本书")
	fmt.Println("最终答案：", answer3)

	fmt.Println("\n【你学到了什么】")
	fmt.Println("1. Agent 接口只有一个核心方法 Plan()，其余都是元数据")
	fmt.Println("2. intermediateSteps 是 Agent 的'记忆'，记录所有已做的动作和观测")
	fmt.Println("3. 返回 AgentAction = 让 Executor 执行工具，然后再调 Plan()")
	fmt.Println("4. 返回 AgentFinish = Agent 认为任务完成，Executor 退出循环")
	fmt.Println("5. Plan() 可以是纯规则（这一关），也可以调 LLM（ReAct），也可以调 FunctionCall")
	fmt.Println("")
	fmt.Println("【下一步：设计你自己的框架时可以考虑的扩展点】")
	fmt.Println("  □ 并行执行多个工具（langchaingo 现在是串行）")
	fmt.Println("  □ 工具执行失败时的重试/降级策略")
	fmt.Println("  □ 动态注册工具（运行时插拔）")
	fmt.Println("  □ 多 Agent 协作（Supervisor + SubAgent 模式）")
	fmt.Println("  □ 持久化 intermediateSteps（断点续跑）")
	fmt.Println("  □ Plan 返回的 Action 带置信度/优先级")
}
