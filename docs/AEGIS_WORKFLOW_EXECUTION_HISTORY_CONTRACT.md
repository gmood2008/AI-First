# Aegis × AI-First Runtime：Workflow 执行历史导出契约（Contract）

**执行时间**：2026-01-30

本文定义 AI-First Runtime 向 Aegis Skill Memory / ExecutionHistory 导出 workflow 执行历史的结构化格式。

目标：

- Aegis 可稳定 ingest workflow 级与 step 级记录
- 支持 Pattern Extraction（从多次 workflow 执行中提取模式）
- 与 Aegis `FailureCategory`/`ExecutionHistoryRecord` 对齐

---

## 1. 设计原则

- `bridge exec-workflow` 以 **单条 JSON** 输出一次 workflow 执行的汇总与 step 明细（见 2.1）
- 其中包含 workflow 级信息与 N 条 step 级信息（可在 Aegis 侧拆分落库）
- 字段扩展使用对象形式，向后兼容
- 输出需包含：
  - 可定位：`trace_id` / `quest_id` / `workflow_id`
  - 可重放/可审计：输入、关键决策（deny/pause）、输出摘要、错误信息

---

## 2. Bridge 输出（workflow + steps 单条 JSON）

### 2.1 字段

```json
{
  "id": "<uuid>",
  "executionId": "exec-001",
  "traceId": "trace-001",
  "parentTraceId": null,
  "questId": "quest-001",
  "workflowExecutionId": "<workflow-exec-id>",
  "workflowName": "example_workflow",
  "status": "success",
  "error": null,
  "startTime": "2026-01-30T10:00:00Z",
  "endTime": "2026-01-30T10:00:05Z",
  "workflow": {
    "id": "<workflow-exec-id>",
    "name": "example_workflow",
    "owner": "aegis",
    "status": "completed",
    "createdAt": "2026-01-30T10:00:00Z",
    "updatedAt": "2026-01-30T10:00:05Z",
    "startedAt": "2026-01-30T10:00:00Z",
    "completedAt": "2026-01-30T10:00:05Z",
    "errorMessage": null,
    "rollbackReason": null
  },
  "steps": [
    {
      "stepId": "fetch_report",
      "stepName": "fetch_report",
      "capabilityId": "io.http.get",
      "agentName": "aegis",
      "status": "completed",
      "startedAt": "2026-01-30T10:00:00Z",
      "completedAt": "2026-01-30T10:00:01Z",
      "inputs": {"url": "https://example.com/report.pdf"},
      "outputs": {"status_code": 200},
      "errorMessage": null,
      "executionOrder": 1
    }
  ],
  "userId": "user-001",
  "metadata": null
}
```

### 2.2 status 建议枚举

- `success`
- `failure`
- `paused`
- `rolled_back`

---

## 3. Step 明细（steps[]）

### 3.1 字段

```json
{
  "stepId": "fetch_report",
  "stepName": "fetch_report",
  "capabilityId": "io.http.get",
  "agentName": "aegis",
  "status": "completed",
  "startedAt": "2026-01-30T10:00:00Z",
  "completedAt": "2026-01-30T10:00:01Z",
  "inputs": {"url": "https://example.com/report.pdf"},
  "outputs": {"status_code": 200},
  "errorMessage": null,
  "executionOrder": 1
}
```

### 3.2 status 建议枚举

- `SUCCESS`
- `FAILED`
- `DENIED`
- `ERROR`
- `SKIPPED`

---

## 4. FailureCategory 对齐建议

建议遵循当前 bridge 的分类映射（如需以 Aegis 为准可在此表更新）：

- 参数/输入错误：`VALIDATION_ERROR`
- 安全/权限：`SECURITY_VIOLATION`
- 人工确认拒绝：`CONFIRMATION_DENIED`
- 找不到能力/资源：`NOT_FOUND`
- 超时：`TIMEOUT`
- 运行时内部异常：`INTERNAL_ERROR`

治理相关：

- Constitution violation：`POLICY_VIOLATION`（或 Aegis 指定的 taxonomy）

---

## 5. Golden 示例（建议）

- `tests/bridge/golden_workflow_record_success.json`
- `tests/bridge/golden_workflow_record_failure.json`
- `tests/bridge/golden_workflow_record_paused.json`

---

## 6. Schema 校验（可选）

`bridge exec-workflow` 支持对输出 payload 做 JSON Schema 校验：

- CLI 参数：`--schema-path <schema.json>`
- 环境变量：`AEGIS_WORKFLOW_RECORD_SCHEMA=<schema.json>`

建议使用仓库内发布的参考 schema：

- `schemas/aegis/bridge_exec_workflow_output.schema.json`

若校验失败，将输出 `VALIDATION_ERROR` 并以非 0 退出码退出。

---

## 6. Aegis 需要明确的 ingest 要求

为让我们最终输出与 Aegis Skill Memory 最贴合，Aegis 需要确认：

- workflow 级与 step 级 record 的必填字段清单
- FailureCategory taxonomy 的最终枚举（以 Aegis 为准）
- step 输入/输出的脱敏规则（哪些字段不可记录）
- artifacts 的存储策略（仅引用路径/还是内联）

---

## 7. 版本与兼容性

- 本协议建议纳入 `docs/COMPATIBILITY_CONTRACT.md` 的“对外契约”范围
- 字段新增保持向后兼容，不做破坏性重命名
