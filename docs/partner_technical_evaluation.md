# AI‑First Runtime（AWE）生态合作方技术架构与产品结构评估文档

**文档目的**：为生态合作方提供一份可用于技术评估与集成决策的说明，覆盖系统架构、组件边界、安全治理、审计与回滚、接口与集成方式、性能与可靠性证据、PoC 验收清单。

**适用读者**：平台/中台架构师、AI 工程负责人、SRE/安全合规负责人、生态合作方 SDK/平台集成人员。

**版本**：0.1（面向评估）

---

## 1. 产品定位与核心价值

AI‑First Runtime 是一套面向智能应用的 **“可治理（Governance）、可审计（Audit）、可回滚（Rollback）”** 的执行运行时。

它解决的不是“模型更聪明”，而是“智能体对真实世界执行更安全、更可控、更可复现”。

### 1.1 关键差异化能力

- **Contract‑First（契约优先）**：能力通过规范（CapabilitySpec）描述输入/输出/风险/副作用，支持系统级校验与编排。
- **Aegis / 主权握手**：对真实世界副作用（写文件、网络访问等）提供可插拔确认机制，确保“人类最终控制权”。
- **Transactional Execution（事务式执行）**：执行产生的可逆操作记录为 undo/compensation，并在工作流失败时自动回滚。
- **治理红线**：新能力必须走治理链路（Proposal→Approval→Pack/Facade），禁止绕过治理直接注册高风险能力。

---

## 2. 核心概念（对外术语）

- **Skill（技能/原子能力）**：最小工具单元。对应一个 `capability_id`，由 `CapabilitySpec（契约）+ Handler（实现）` 组成。
- **Skill Library（技能库）**：存放经过认证/治理的 Skill（通常为 YAML Spec + 运行时 handler）。
- **AWE（Agile Workflow Engine）**：工作流执行引擎（状态机 + 编排执行 + 自动回滚）。
- **Aegis Handshake（主权握手）**：对高风险步骤/动作进行确认的安全控制点（可自动/可人工）。
- **Audit（审计）**：把执行、确认、状态流转、输入输出摘要写入审计库，并支持导出。

> 注：当前仓库中也存在 Pack/Facade 等概念用于治理链路组织（见第 4 节）。

---

## 3. 技术架构总览

### 3.1 逻辑架构（高层）

```text
┌─────────────────────────────────────────────────────────────┐
│                 智能体/应用（Claude/GPT/自研 Agent）          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ MCP / Function Calling / SDK / REST
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      接入层（Adapter）                        │
│  - MCP Server（工具列表、调用路由）                           │
│  - REST API（Mission Control / 运维控制面）                   │
│  - Python SDK（嵌入式调用）                                   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                Runtime Kernel（执行内核）                      │
│  - CapabilityRegistry（能力注册/治理约束）                     │
│  - RuntimeEngine（参数校验、handler 调用、安全中间件）          │
│  - UndoManager（原子回滚）                                     │
│  - AuditLogger（审计落库）                                     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                AWE Workflow Engine（工作流引擎）               │
│  - WorkflowSpec（步骤、依赖、风险、回滚策略）                  │
│  - 状态机：PENDING/RUNNING/PAUSED/FAILED/ROLLED_BACK/COMPLETED │
│  - 自动回滚：undo_record → compensation_stack                  │
│  - Persistence / Recovery（持久化、断点与恢复）                │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     Skill Library（技能库）                    │
│  - stdlib skills（受治理）                                     │
│  - external proposals（外部能力仅作为提案）                     │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 与仓库文档的对应关系

- 架构总体：`ARCHITECTURE.md`
- 外部集成快速开始：`QUICKSTART_EXTERNAL_INTEGRATION.md`
- MCP/IDE 集成：`docs/INTEGRATION_GUIDE.md`
- 外部能力治理红线：`docs/EXTERNAL_CAPABILITY_INTEGRATION.md`

---

## 4. 产品结构（对外可交付模块）

### 4.1 Runtime Kernel（执行内核）

**目标**：提供可校验、可审计、可回滚的能力执行。

关键组件（代码路径以仓库为准）：

- `CapabilityRegistry`：能力注册、治理约束与查询
- `RuntimeEngine`：统一执行入口（参数校验→安全中间件→handler 调用→生成执行结果）
- `ExecutionContext`：执行上下文（workspace、user/session、确认回调、undo 开关）
- `UndoManager`：原子撤销（写文件等可逆操作）
- `AuditLogger`：审计落库（SQLite）

### 4.2 AWE Workflow Engine（工作流引擎）

**目标**：将多个原子能力编排为具备事务语义的工作流。

关键能力：

- 工作流状态机与执行：`WorkflowEngine`
- 自动回滚：`spec.enable_auto_rollback == true` 时，失败触发 `_rollback_workflow()`
- Undo/Compensation 统一：优先使用 runtime 的 `undo_record.undo_function` 作为补偿闭包

### 4.3 Governance Chain（治理链路，v3 核心约束）

**目标**：确保任何可执行能力都经过审核/批准流程，避免绕过治理直接把高风险能力暴露给模型。

**v3 治理红线（必须遵守）**：

- 外部能力（HTTP API / 第三方工具）**不得**直接注册为可执行能力
- 外部能力加载只能生成 **Proposal（候选提案）**
- 可执行能力必须通过治理链路进入：
  - `Capability → Workflow → Pack(ACTIVE) → Facade(ACTIVE) → CLI/MCP/REST`

详见：`docs/EXTERNAL_CAPABILITY_INTEGRATION.md`。

### 4.4 Mission Control API（控制面 / 运维集成）

**目标**：为平台方提供工作流的查询、控制、事件订阅能力。

- FastAPI 模块：`src/runtime/api/mission_control.py`
- 兼容入口：`governance/mission_control_api.py`（重导出）
- 运行脚本：`scripts/run_mission_control_api.py`
- 支持：Token/JWT 验证、工作流查询/控制、SSE 事件流

---

## 5. 集成方式（合作方可选路径）

合作方可以根据自身系统形态选择以下一种或多种集成方式。

### 5.1 方式 A：MCP Server（推荐用于智能体/对话型集成）

**适合**：Claude Desktop、Cursor/VS Code、任何 MCP 兼容客户端。

- 启动 MCP Server：
  - 参考 `docs/INTEGRATION_GUIDE.md`
  - 典型命令：`python3 src/runtime/mcp/server_v2.py`

**特点**：

- 自动暴露能力为 MCP tools
- 可与多种模型客户端解耦
- 适合快速 PoC

### 5.2 方式 B：Python SDK（推荐用于平台/服务端集成）

**适合**：将 Runtime 嵌入现有后端服务、批处理、CI 自动化、内部平台。

典型流程（概念级）：

1. 初始化 `CapabilityRegistry` 并加载 stdlib 或受控能力集合
2. 初始化 `UndoManager` 与 `AuditLogger`
3. 构造 `RuntimeEngine`
4. 构造 `ExecutionContext`
5. 直接执行 capability，或通过 `WorkflowEngine` 执行工作流

### 5.3 方式 C：REST API（推荐用于控制面/平台观测）

**适合**：平台化产品、运维控制台、SRE 可观测需求。

建议用法：

- 平台发起 workflow（或由内部服务提交）
- 控制面查询状态、暂停/恢复
- 通过 SSE 订阅事件

---

## 6. 安全与治理（技术评估重点）

### 6.1 防御纵深（Defense‑in‑Depth）

运行时对敏感动作提供分层保护：

- **Schema/参数校验**：输入参数与规范契约一致
- **权限/副作用检查**：动作需与 spec 声明一致（路径/网络等）
- **Workspace 隔离**：文件操作限制在 workspace
- **确认门（Aegis Handshake）**：对高风险动作要求确认
- **审计落库**：所有关键点留痕

### 6.2 外部能力治理红线

合作方若要接入外部系统（Slack/Jira/GitHub/自研 API），必须遵循：

- 外部能力先进入 **Proposal**（候选能力）
- 通过治理批准后，进入可执行链路（Pack/Facade/Workflow）

这保证：

- 模型无法直接“发现并调用”未经批准的外部能力
- 审计可追溯“谁批准了什么”

---

## 7. 审计与合规

### 7.1 审计落库

- 审计默认写入 SQLite（按 workspace/session 隔离）
- 建议合作方将审计 DB 归档或导出到 SIEM/审计平台

### 7.2 审计导出

项目支持导出审计数据（JSONL）用于合规留存与复盘。

（合作方评估建议）

- 验证：审计记录是否包含 request/decision/step outputs 摘要
- 验证：敏感信息是否脱敏/不落盘

---

## 8. 回滚与可靠性

### 8.1 原子回滚（Undo）

- 对可逆操作（如文件写入）生成 undo 记录
- undo 记录可在 workflow failure 时用于 compensation

### 8.2 工作流自动回滚（AWE Transaction）

- 工作流 spec 中 `enable_auto_rollback: true` 时
- 任意 step 失败 → 引擎自动按 LIFO 执行补偿闭包 → 状态变为 `ROLLED_BACK`

---

## 9. 性能与稳定性证据（Phase 5 测试结果摘要）

### 9.1 Load Test（stdlib‑only 基准工作流）

- 脚本：`scripts/load_test_workflows.py`
- 基准 workflow：`packs/load-test/load_test_quick.yaml`
- 关键设计：并发运行隔离 workspace 与 audit DB，降低噪声能力加载

示例一次运行结果（20 并发/20 总量）：

- Throughput：约 44.8 workflows/s
- Latency：p50 ~ 88ms，p95 ~ 114ms（样本环境相关）

> 合作方应在自身环境复测；我们提供脚本与基准 workflow 以保证可重复。

### 9.2 Chaos Rollback（一致性验证）

- 脚本：`scripts/chaos_rollback_test.py`
- 结果示例（100 次，20 并发，注入概率 0.5）：
  - `injected_failures = 56`
  - `rolled_back = 56`
  - `file_removed = 56`

结论：注入失败与回滚/撤销一致，事务语义在该基准链路上可验证。

---

## 10. 合作方扩展与二开指南（建议实践）

### 10.1 新增/集成能力（Skill）

- 内部能力（可逆/可控）建议提供：
  - 明确输入/输出契约
  - 风险等级与副作用声明
  - undo 或 compensation 策略
  - 单元测试与集成测试

- 外部能力（HTTP API / 第三方服务）建议走：
  - 先 Proposal（候选）
  - 再审核批准
  - 再纳入 Pack/Facade/Workflow 执行链路

参考：

- `QUICKSTART_EXTERNAL_INTEGRATION.md`
- `docs/CAPABILITY_REVIEW_AND_INTEGRATION.md`

### 10.2 运行隔离建议

- 每次并发执行建议使用独立 workspace 根目录
- 每次并发执行建议使用独立 audit DB

> 项目压测脚本已实现该隔离策略，可作为合作方集成模板。

---

## 11. 部署与依赖

### 11.1 Python 版本与依赖

- 建议合作方固定 Python 解释器版本（例如 3.11），并确保同一解释器安装依赖
- 依赖以 `pyproject.toml` / `requirements.txt` 为准

### 11.2 运行模式

- 本地/开发：CLI/MCP Server
- 平台化：服务端嵌入式 SDK + Mission Control API

---

## 12. PoC 评估清单（建议 1～3 天可完成）

### 12.1 基础能力验证

- [ ] 能列出能力清单（通过 MCP/SDK）
- [ ] 能执行 stdlib 基础能力（读/写文件、hash、template 等）
- [ ] workspace 隔离生效（路径逃逸被拒绝）

### 12.2 治理与主权握手

- [ ] 高风险能力需要确认（或可配置自动确认）
- [ ] v3 红线：未经批准外部能力不可执行（只能成为 proposal）

### 12.3 审计与导出

- [ ] 审计数据库写入完整
- [ ] 可导出 JSONL 并用于回放/审计系统摄取

### 12.4 回滚与一致性

- [ ] 工作流失败触发自动回滚
- [ ] 回滚后副作用撤销一致（以文件写入为基准）
- [ ] 运行 chaos rollback 脚本复测通过（100 次）

### 12.5 性能基线

- [ ] 在合作方目标环境上复测吞吐与延迟
- [ ] 100+ 并发下无资源泄漏（连接、线程、DB 文件句柄）

---

## 13. 参考资料（仓库内）

- `ARCHITECTURE.md`
- `INSTALL.md` / `QUICKSTART.md`
- `docs/INTEGRATION_GUIDE.md`
- `QUICKSTART_EXTERNAL_INTEGRATION.md`
- `docs/EXTERNAL_CAPABILITY_INTEGRATION.md`（v3 治理红线）
- `docs/CAPABILITY_REVIEW_AND_INTEGRATION.md`

---

## 14. 联系与下一步（建议合作方式）

建议合作方在技术评估后，选择以下合作路径之一：

- **路径 1：集成执行层**：将 Runtime 作为智能应用的“安全执行底座”（SDK/MCP）。
- **路径 2：共建技能库**：共同定义 CapabilitySpec 标准与治理流程，沉淀可复用原子技能。
- **路径 3：平台化控制面**：以 Mission Control API 为基础接入既有运维/审计/权限体系。
