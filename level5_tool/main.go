// =============================================================================
// Level 5: Tool —— Agent 的手脚
// =============================================================================
// 目标：理解 Tool 接口，以及如何注册和被 Agent 调用
//
// ┌─────────────────────────────────────────────────────────────────────────┐
// │  涉及的设计模式 & 设计原则                                                  │
// │                                                                          │
// │  1. 【命令模式 Command】                                                   │
// │     每个 Tool 就是一个命令对象：把"做什么"（Name/Description）和             │
// │     "怎么做"（Call）封装在一起。                                             │
// │     Executor 作为 Invoker，不关心命令细节，只调 Call(input)。               │
// │                                                                          │
// │  2. 【单一职责原则 SRP（SOLID-S）】                                        │
// │     TimeTool 只负责取时间，WeatherTool 只负责查天气，Calculator 只做运算。  │
// │     每个工具只做一件事，容易独立测试和替换。                                   │
// │                                                                          │
// │  3. 【接口隔离原则 ISP（SOLID-I）】                                        │
// │     Tool 接口只有 3 个方法（Name/Description/Call），足够小。                │
// │     工具实现者不被迫实现用不上的方法。                                        │
// │                                                                          │
// │  4. 【两种参数风格的设计权衡】                                               │
// │     ReAct 风格：Call(input string)——LLM 直接生成文本参数，工具自己解析        │
// │     FunctionCall 风格：Call(json string)——LLM 产出 JSON，框架自动映射        │
// │     这是接口设计中"扩展性 vs 类型安全"的经典取舍。                            │
// └─────────────────────────────────────────────────────────────────────────┘
//
// Tool 接口（tools/tool.go）：
//   type Tool interface {
//       Name() string
//       Description() string
//       Call(ctx context.Context, input string) (string, error)
//   }
//
// 与你的 fff_agent 对比：
//   你的 Tool 接口：Schema() ToolSchema + Run(map[string]any)
//   langchaingo：Name/Description + Call(input string)
//
//   langchaingo 的工具输入是"字符串"，LLM 生成的是文本，
//   Agent 把 "Action Input: xxx" 直接传给 tool.Call()
//   解析 JSON args 是工具自己的事
// =============================================================================

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"
)

// ① 实现一个时间工具
type TimeTool struct{}

func (t *TimeTool) Name() string { return "get_time" }
func (t *TimeTool) Description() string {
	return "获取当前时间。无需参数，直接调用即可。"
}
func (t *TimeTool) Call(_ context.Context, _ string) (string, error) {
	return time.Now().Format("2006-01-02 15:04:05"), nil
}

// ② 实现一个天气工具（模拟，接受 JSON input）
type WeatherTool struct{}

func (w *WeatherTool) Name() string { return "get_weather" }
func (w *WeatherTool) Description() string {
	return `查询指定城市的天气。输入格式 JSON：{"city": "城市名"}`
}
func (w *WeatherTool) Call(_ context.Context, input string) (string, error) {
	var args struct {
		City string `json:"city"`
	}
	city := "北京" // 默认
	if err := json.Unmarshal([]byte(input), &args); err == nil && args.City != "" {
		city = args.City
	}
	weather := map[string]string{
		"北京": "晴，22°C",
		"上海": "多云，18°C",
		"深圳": "阵雨，25°C",
	}
	if w, ok := weather[city]; ok {
		return fmt.Sprintf("%s：%s", city, w), nil
	}
	return fmt.Sprintf("%s：天气数据暂不可用", city), nil
}

// ③ 实现一个计算器工具（接受表达式字符串）
type Calculator struct{}

func (c Calculator) Name() string { return "calculator" }
func (c Calculator) Description() string {
	return "执行简单的四则运算。输入格式：数字 运算符 数字，例如 3 + 5 或 10 * 2"
}
func (c Calculator) Call(_ context.Context, input string) (string, error) {
	parts := strings.Fields(strings.TrimSpace(input))
	if len(parts) != 3 {
		return "", fmt.Errorf("格式错误，应为：数字 运算符 数字")
	}
	a, err1 := strconv.ParseFloat(parts[0], 64)
	b, err2 := strconv.ParseFloat(parts[2], 64)
	if err1 != nil || err2 != nil {
		return "", fmt.Errorf("数字解析失败")
	}
	var result float64
	switch parts[1] {
	case "+":
		result = a + b
	case "-":
		result = a - b
	case "*":
		result = a * b
	case "/":
		if b == 0 {
			return "", fmt.Errorf("除数不能为零")
		}
		result = a / b
	default:
		return "", fmt.Errorf("不支持的运算符：%s", parts[1])
	}
	return strconv.FormatFloat(result, 'f', -1, 64), nil
}

func main() {
	ctx := context.Background()

	tools := []interface {
		Name() string
		Description() string
		Call(context.Context, string) (string, error)
	}{
		&TimeTool{},
		&WeatherTool{},
		Calculator{},
	}

	fmt.Println("=== 注册的工具列表 ===")
	for _, t := range tools {
		fmt.Printf("  %-12s : %s\n", t.Name(), t.Description())
	}

	fmt.Println("\n=== 直接调用工具（模拟 Agent 执行工具的过程）===")

	timeResult, _ := tools[0].Call(ctx, "")
	fmt.Printf("get_time('')           → %s\n", timeResult)

	weatherResult, _ := tools[1].Call(ctx, `{"city":"上海"}`)
	fmt.Printf(`get_weather({"city":"上海"}) → %s\n`, weatherResult)

	calcResult, _ := tools[2].Call(ctx, "3.14 * 2")
	fmt.Printf("calculator('3.14 * 2') → %s\n", calcResult)

	fmt.Println("\n【设计启示】")
	fmt.Println("langchaingo 的 Tool 输入是纯字符串")
	fmt.Println("这意味着 LLM 需要在 Action Input 里写好参数，工具自己负责解析")
	fmt.Println("你的 fff_agent Tool 用 map[string]any 更结构化，适合 FunctionCall 风格")
	fmt.Println("两种风格对应两种 Agent：ReAct（文本解析）vs FunctionCall（JSON schema）")
}
