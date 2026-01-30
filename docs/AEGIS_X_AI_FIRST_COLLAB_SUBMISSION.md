# Aegis × AI-First

协同方案与独立需求说明（提交版 | 面向 AI-First 研发团队）

## 文档目的

本文件用于向 AI-First 团队明确说明：

1. Aegis 是什么
2. AI-First 在 Aegis 体系中的不可替代角色
3. Aegis 对 AI-First 的明确能力需求、接口契约与设计约束
4. 双方如何协同，构建一个可扩展、可治理的 AI OS 生态

---

## 1. 背景说明：为什么需要重新定义 AI-First 的角色

在 Aegis 体系中，我们正在解决的不是“AI 能不能生成”，而是一个更本质的问题：

AI 是否可以被用户真正授权，去执行真实世界中的复杂行为？

这要求生成能力本身发生质变：

- 从一次性输出 → 持续可修正
- 从黑箱生成 → 可解释、可约束
- 从“结果正确” → “行为合规 + 可托付”

这正是 AI-First 在 Aegis 体系中的战略价值所在。

---

## 2. Aegis 是什么（对齐定义）

Aegis 是一个以“用户主权”为核心的 AI 工作操作系统（AI Work OS）。

它不是聊天机器人，也不是自动化脚本工具，而是一个：

可被教导、可被审计、可被激活与撤回的智能执行体管理系统。

Aegis 的目标是让 AI 成为“可以被授予真实系统权力的协作体”，而不是一个只会输出文本的工具。

关键含义：

- AI 必须可被观察
- AI 必须可被约束
- AI 必须可被中止 / 回滚
- AI 的能力必须通过用户授权逐步解锁

---

## 3. Aegis 对 AI-First 的战略定位

### 3.1 系统分层与职责

| 层级 | 系统 | 核心职责 |
| --- | --- | --- |
| Control Plane | Aegis | 主权、状态、生命周期、治理 |
| Cognition Plane | AI-First | 理解、生成、解释、修正 |
| OS Plane | k-os | 权限、状态机、安全 |
| Execution Plane | ascend-ai | 沙箱、执行、资源监控 |

核心结论：

AI-First 是 Aegis 的“智能生成与推理引擎（Cognitive Engine）”，而不是执行器或调度器。

AI-First 不直接“做事”，而是负责“如何做才对”。

### 3.2 AI-First 必须承担的核心价值

AI-First 在 Aegis 体系中的价值，不是“更聪明”，而是：

- 可被约束的智能
- 可被教导的智能
- 可被追责的智能

---

## 4. AI-First 的核心功能职责（必须具备）

本章为“必须具备”的强约束清单。

### 4.1 AutoForge：技能生成引擎（非一次性生成）

AI-First 的 AutoForge 不再是：

输入意图 → 输出代码

而必须演进为：

输入意图 → 生成方案 → 接受反馈 → 迭代修正 → 可固化技能

强制能力要求：

- 支持多轮生成会话
- 每一轮生成必须：
  - 绑定明确意图
  - 产生可 Diff 的代码变化
  - 支持 Teaching Mode

### 4.2 Teaching Mode 支持（人机共创）

#### 4.2.1 Diff 感知生成

必须支持：

- 识别“用户反馈”与“代码修改”的对应关系
- 输出自然语言解释：为什么改这几行

禁止：

- 全量重写但无法解释

#### 4.2.2 反馈驱动生成

用户反馈必须作为一等输入上下文。

下一次生成必须显式说明：

- 本轮修改如何回应用户反馈

### 4.3 Constitution 感知生成（关键）

这是 AI-First 与普通生成模型的分水岭。

强制要求：

- AI-First 在生成任何技能代码时，必须读取用户 Constitution
- 在生成阶段主动规避违规行为
- 将 Constitution 视为高优先级约束，不可绕过

禁止行为：

- 先生成违规代码，再交给系统拦截
- 静默 Auto-Rewrite

### 4.4 Auto-Rewrite 的行为约束（极其重要）

当 AI-First 参与“自动修正”时：

强制交互模式（Proposal 模式）。

Auto-Rewrite 必须以提案形式输出：

- 违反了哪一条规则（Rule ID）
- 为什么必须修改
- 修改 Diff（最小侵入）
- 是否还有替代方案

核心原则：

AI-First 不能成为“算法审查者”，只能是“合规建议者”。

### 4.5 Skill Memory 的读取与利用

AI-First 必须支持：

- 读取 Skill Memory：
  - 成功模式
  - 失败原因
  - 历史上下文

并在以下场景主动使用：

- Hotfix
- 再生成
- Teaching Mode 迭代

生成不能是“健忘的”。

---

## 5. AI-First 与 Aegis 的接口契约（必须明确）

本章为对接工程的“硬契约”。Aegis 不负责猜测 AI-First 的真实意图，因此必须结构化 I/O。

### 5.1 输入接口（来自 Aegis）

AI-First 必须接受的结构化输入：

```json
{
  "intent": "自然语言意图",
  "constitution": {},
  "skillMemory": {},
  "previousCode": "...",
  "userFeedback": "...",
  "executionContext": {}
}
```

约束：

- `constitution` 必须被当作高优先级约束参与生成，而不是事后审查。
- `userFeedback` 必须影响下一轮生成，并要求产出“反馈映射解释”。

### 5.2 输出接口（返回给 Aegis）

AI-First 的输出必须是结构化对象，而非纯文本：

```json
{
  "generatedCode": "...",
  "diff": "...",
  "explanation": "...",
  "riskNotes": "...",
  "requiresConfirmation": true
}
```

约束：

- `diff` 必须可用于 Aegis 展示与审计
- `explanation` 必须可用于“责任交接/教学”
- `riskNotes` 用于提示风险与建议的治理动作

---

## 6. 明确边界：AI-First 不应该做什么

为了系统稳定与责任清晰，AI-First 明确禁止：

- 自行决定 Skill 是否 ACTIVE
- 绕过 Aegis 的 Handshake
- 直接调用 k-os / ascend-ai 执行
- 静默修改用户技能

---

## 7. AI-First 的演进路线建议（与 Aegis 对齐）

### Phase A（近期 / 必须）

- Teaching Mode 支持
- Constitution 感知生成
- Diff + Explanation 输出

### Phase B（中期）

- Skill Memory 深度利用
- 多策略生成（Plan A / B / C）
- 风险评分输出

### Phase C（远期）

- 企业级 Constitution
- 团队 Skill 继承与冲突解析
- 跨用户 Skill 泛化能力（在 Aegis 授权下）

---

## 8. 双方协作方式建议（工程落地角度）

> 本节为 AI-First 研发团队提供“怎么做才算达标”的工程化落地建议。

建议在 AI-First 侧落实以下工程约束：

- 任何 Auto-Rewrite 必须走 Proposal 输出结构（Rule ID + 最小 diff + 备选方案）
- 任何生成必须输出 diff 与 explanation，并能追溯“用户反馈 → 修改映射”
- Constitution 违规不应在执行阶段才暴露，而应在生成阶段主动规避
- Skill Memory 必须作为输入上下文显式注入（并可在输出中标注“使用了哪些记忆/经验”）

验收建议（可由 Aegis 提供用例集合）：

- 给定同一 intent + constitution，AI-First 输出的 diff 不得包含明显违规操作
- 给定 userFeedback，下一轮必须在 explanation 中指出对应修正点
- 在强约束 constitution 下，禁止出现“先违规再解释/再拦截”的输出策略

---

## 9. 最终定位声明

在 Aegis 体系中，AI-First 不只是一个模型服务，而是一个：

受宪法约束、可被教导、承担解释责任的智能系统。

如果 AI-First 能做到这一点，它将成为 Aegis 生态中最具价值的智能底座，从“模型能力”升级为“文明接口”。

---

## 10. 总结（一句话给 AI-First）

Aegis 负责“能不能托付”，AI-First 负责“值不值得托付”。
