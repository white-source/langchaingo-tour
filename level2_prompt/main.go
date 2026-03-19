// =============================================================================
// Level 2: Prompt Template
// =============================================================================
// 目标：理解 Prompt 不是硬编码字符串，而是"带占位符的模板"
//
// ┌─────────────────────────────────────────────────────────────────────────┐
// │  涉及的设计模式 & 设计原则                                                  │
// │                                                                          │
// │  1. 【模板方法模式 Template Method】                                       │
// │     PromptTemplate 定义了"填充变量 → 返回 PromptValue"的骨架流程，           │
// │     具体填什么内容由调用时传入的 map 决定。                                   │
// │     骨架不变（FormatPrompt 固定），变化点外置（变量 map 可替换）。             │
// │                                                                          │
// │  2. 【开闭原则 OCP（SOLID-O）】                                            │
// │     新增 ChatPromptTemplate / FewShotPromptTemplate 时不需要修改 Chain     │
// │     或 Agent，只需新增实现 FormatPrompter 接口的类型即可扩展。               │
// │                                                                          │
// │  3. 【关注点分离 SoC / 单一职责 SRP（SOLID-S）】                           │
// │     Prompt 只负责"拼文本"，不知道 LLM 是谁、Chain 怎么运行。                 │
// │     把"措辞 / 角色设定"与"业务执行逻辑"彻底分开。                            │
// │                                                                          │
// │  4. 【部分应用 Partial Application（函数式思想）】                           │
// │     PartialVariables 是柯里化的对象化表达：先固定部分参数（系统角色），         │
// │     延迟传入余下参数（用户问题），让同一模板服务多个调用场景。                    │
// └─────────────────────────────────────────────────────────────────────────┘
//
// 核心接口（prompts/）:
//   type FormatPrompter interface {
//       FormatPrompt(values map[string]any) (schema.PromptValue, error)
//   }
//
// PromptTemplate = 模板字符串 + 变量名列表
// 调用 FormatPrompt(map) 后返回 PromptValue
// PromptValue.String() → 最终发给 LLM 的文本
// PromptValue.Messages() → Chat 格式的消息列表
//
// 这一层的意义：
//   - 把"问题措辞"和"系统逻辑"分离
//   - 同一个 Chain 只改 Prompt 就能切换角色/语言/格式
// =============================================================================

package main

import (
	"fmt"

	"github.com/tmc/langchaingo/prompts"
)

func main() {
	// ① 最简单的 PromptTemplate：Go template 语法，{{.变量名}}
	pt := prompts.NewPromptTemplate(
		"你是一个{{.role}}。请用{{.language}}回答：{{.question}}",
		[]string{"role", "language", "question"},
	)

	// FormatPrompt 把 map 填进去，返回 PromptValue
	pv, err := pt.FormatPrompt(map[string]any{
		"role":     "地理老师",
		"language": "中文",
		"question": "中国最高的山是哪座？",
	})
	if err != nil {
		panic(err)
	}

	fmt.Println("=== ① 单轮 PromptTemplate ===")
	fmt.Println("最终 Prompt 文本：")
	fmt.Println(pv.String())

	// ② ChatPromptTemplate：多角色多轮消息
	//    更接近真实 Chat 模型的调用方式
	chatPT := prompts.NewChatPromptTemplate([]prompts.MessageFormatter{
		prompts.NewSystemMessagePromptTemplate(
			"你是一个专业的{{.domain}}顾问，回答时要严谨简洁。",
			[]string{"domain"},
		),
		prompts.NewHumanMessagePromptTemplate(
			"{{.question}}",
			[]string{"question"},
		),
	})

	chatPV, err := chatPT.FormatPrompt(map[string]any{
		"domain":   "投资理财",
		"question": "现在适合买黄金吗？",
	})
	if err != nil {
		panic(err)
	}

	fmt.Println("\n=== ② ChatPromptTemplate ===")
	fmt.Println("消息列表：")
	for _, msg := range chatPV.Messages() {
		fmt.Printf("  [%s]: %s\n", msg.GetType(), msg.GetContent())
	}

	// ③ PartialVariables：预填充部分变量，其余延迟填写
	//    常用来固定 system 角色，运行时只传 question
	ptWithPartial := prompts.PromptTemplate{
		Template:       "语言：{{.lang}}\n问题：{{.q}}",
		TemplateFormat: prompts.TemplateFormatGoTemplate,
		InputVariables: []string{"q"},
		PartialVariables: map[string]any{
			"lang": "中文", // 已经固定了，不需要每次传
		},
	}
	pv2, _ := ptWithPartial.FormatPrompt(map[string]any{"q": "今天几号？"})

	fmt.Println("\n=== ③ PartialVariables（预填充）===")
	fmt.Println(pv2.String())

	fmt.Println("\n【设计启示】")
	fmt.Println("你的 fff_agent 目前是硬编码字符串判断，Prompt Template 让你把")
	fmt.Println("'如何提问' 和 '执行逻辑' 分开，Agent 的 prompt 可以外部配置")
}
