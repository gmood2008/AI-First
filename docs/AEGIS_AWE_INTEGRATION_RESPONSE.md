# Aegis × AI-First Runtime：AWE 集成对齐回复（阶段性结论与下一步）

**执行时间**：2026-01-30

本文用于回复 Aegis 团队提出的《AWE 集成策略：利用 AI-First Runtime 现有能力》需求，明确：

- 我们（AI-First Runtime）已经具备/已交付的能力与接口
- 我们建议的集成边界与协作方式（谁负责什么）
- 我们将补齐的支撑项（优先级与交付物）
- Aegis 需要调整的 Phase 9 任务拆分与他们需要提供/实现的内容

---

## 1. 重要澄清：AWE 的边界（避免误判能力范围）

AI-First Runtime 当前提供的是 **“确定性工作流执行引擎（状态机 + 回滚 + 审计 + 恢复）”**。

- 我们擅长：执行编排、失败回滚、持久化恢复、治理拦截点、执行历史结构化输出
- 我们不主张：把“动态流程规划/自动串联”当作运行时职责

建议对齐：

- **规划（Quest/意图 → 具体步骤）由 Aegis Quest 层负责**（可由 LLM/Planner 驱动）
- **执行（WorkflowSpec 的确定性执行）由 AI-First Runtime AWE 负责**

---

## 2. AI-First Runtime 已具备的能力（可直接复用）

### 2.1 AWE：工作流引擎（Workflow Engine）

我们已经具备：

- WorkflowSpec（YAML/JSON）驱动的执行模型
- 依赖编排与 step 执行（ACTION / PARALLEL / HUMAN_APPROVAL）
- 自动回滚（compensation / undo）
- 持久化与 crash recovery（workflow 可恢复/续跑）

### 2.2 RuntimeEngine：能力执行内核

- Capability 注册/发现/执行
- 参数校验
- Undo 记录与可逆操作管理
- 审计日志

### 2.3 Pack/Facade/Assets 交付与加载

- 支持 wheel 内置资产（`share/ai-first-runtime/...`）
- 支持明文资产模式（`AI_FIRST_ASSETS_DIR=<assets_root>`）
- 支持离线 bundle-first 交付（tar.gz）

---

## 3. 已交付给 Aegis 的 P0 接口（本地桥接）

### 3.1 Local Bridge（Aegis spawn subprocess）

已提供 CLI 命令：

- `airun bridge exec-capability`

能力：

- Aegis 通过 `spawn` 调用，stdout **严格输出单条 JSON**
- 退出码稳定映射 FailureCategory
- 支持可选 JSON Schema 校验：
  - `--schema-path <schema.json>`
  - `AEGIS_EXECUTION_RECORD_SCHEMA=<schema.json>`

### 3.2 Golden 样例（用于集成测试/契约对齐）

- `tests/bridge/golden_execution_record_success.json`
- `tests/bridge/golden_execution_record_failure.json`

### 3.3 稳定性契约

- `docs/COMPATIBILITY_CONTRACT.md`
  - SemVer
  - 资产 schema 演进/弃用/回滚
  - bridge JSON 与退出码稳定性规则

---

## 4. 面向 Aegis Phase 9 的推荐集成架构（对齐 Aegis 文档）

Aegis 文档中的 Phase 9（Quest → Workflow → Governance → Skill Memory）建议按下述边界执行：

- **Aegis Quest Layer**
  - Quest 模型/状态/目标/约束
  - QuestToWorkflowAdapter（生成 WorkflowSpec）

- **Aegis Governance Layer**
  - Constitution checker（合规）
  - Handshake authorization（关键步骤授权）
  - Panic state / Recovery policy（中止/回滚策略）

- **AI-First Runtime AWE**
  - Workflow 执行状态机
  - rollback/crash recovery
  - step execution（调用能力）

- **Aegis Skill Memory**
  - ingest execution history
  - pattern extraction
  - optimization suggestion

---

## 5. 我们将为 Aegis 补齐的支撑项（建议作为 Phase 9 的关键加速器）

为最大化支撑 Aegis Phase 9（特别是 9.2/9.3/9.4），我们建议新增以下交付：

### 5.1 P1（最高优先级）：workflow 级本地桥接

新增 CLI：

- `airun bridge exec-workflow`

目标：

- Aegis 直接 `spawn` 执行 workflow（而非仅能力）
- stdout 输出单条 JSON，包含：workflow 级 summary + step 明细
- 支持：
  - 失败分类（FailureCategory）
  - 可选 schema 校验
  - golden 输出样例（workflow success/failure/paused）

### 5.2 P1：治理 Hook 协议（接口 + 注入点）

我们将明确并文档化可插拔 hook 的调用时机与数据形态：

- `pre_execution(workflow_spec, context)`
- `pre_step(step, resolved_inputs, context)`
- `on_step_result(step, result, context)`
- `on_workflow_complete(workflow_id, summary, context)`
- `on_panic(workflow_id, reason, context)`

其中：

- Constitution：主要对齐 `pre_execution`
- Handshake：主要对齐 `pre_step`
- Panic/Recovery：对齐 `on_panic` + workflow cancel/rollback

### 5.3 P1：workflow execution history 导出格式

我们将提供：

- workflow 级 record + step 级 record 的导出格式
- 映射指南：WorkflowStatus / step status → Aegis FailureCategory/ExecutionHistory
- golden 样例（workflow 级）

---

## 6. Aegis 需要提供/实现的内容（便于调整任务计划）

### 6.1 QuestToWorkflowAdapter（Aegis 侧）

Aegis 需要负责：

- Quest（intent/goals/constraints）→ WorkflowSpec（确定性步骤）的生成
- 将约束映射到 workflow：
  - timeout / maxCost（如需）
  - 需要授权的步骤标记（用于 handshake）

### 6.2 治理实现（Aegis 侧）

Aegis 需要负责：

- Constitution checker 实现与 violation schema
- Handshake authorization 的 UI/交互与审批结果返回
- Panic state 与策略（何时中止、何时回滚、何时恢复）

### 6.3 Skill Memory ingest（Aegis 侧）

Aegis 需要负责：

- 将执行历史（workflow + steps）落入 ExecutionHistory
- PatternExtractor 对 workflow 级模式的提取策略

---

## 7. 建议 Aegis 调整 Phase 9 的任务拆分（结合现实接口）

建议将 Phase 9 的关键路径调整为：

- **9.1（缩短）**：基于我们提供的 AWE 清单 + 示例 workflow 跑通
- **9.2（核心）**：QuestToWorkflowAdapter 产出 WorkflowSpec + schema 校验
- **9.3（核心）**：治理 hook 实现（Constitution/Handshake/Panic）
- **9.4（核心）**：workflow 级执行历史 ingest + pattern 提取

并将“动态规划/自动串联”明确放在 Aegis Quest/Planner 层，不要求 runtime 承担。

---

## 8. 下一步对齐建议（双方各自行动项）

### 8.1 AI-First Runtime（我们）

- 提供 `airun bridge exec-workflow`（含 schema/golden）
- 输出治理 hook 协议与最小示例
- 输出 workflow execution history 导出格式与映射指南

### 8.2 Aegis（对方）

- 提供 Quest → WorkflowSpec 的目标字段与约束字段清单（最小闭环）
- 提供 Constitution violation 的结构化 schema（用于对齐映射）
- 明确 handshake 的判定规则（哪些 step 需要授权）
- 明确 Skill Memory ingest 的目标字段（workflow/step record 需要哪些字段）

---

## 9. 参考链接（当前仓库内）

- `docs/INTEGRATION_GUIDE.md`
- `docs/COMPATIBILITY_CONTRACT.md`
- `docs/AEGIS_GOVERNANCE_HOOKS_CONTRACT.md`
- `docs/AEGIS_WORKFLOW_EXECUTION_HISTORY_CONTRACT.md`
- `docs/PROJECT_INTEGRATION_TEMPLATE.md`
- `docs/PLAINTEXT_ASSETS_MODE_GUIDE.md`
- `docs/INTERNAL_PYPI_DISTRIBUTION_SOP.md`
- `tests/bridge/*.json`
