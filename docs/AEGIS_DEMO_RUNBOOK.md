# Aegis × AI-First Runtime：Demo Runbook（端到端联调）

**执行时间**：2026-01-30

本 Runbook 提供一个典型场景的端到端 demo，用于 Aegis 联调：

- 成功执行（产物写入 workspace）
- 治理层 PAUSE（模拟 Handshake）
- 治理层 DENY（模拟 Constitution 拒绝）

Demo 使用 stdlib 的 `io.fs.write_file/read_file/list_dir`，不依赖外部网络。

---

## 1. Demo Workflow

- Pack：`packs/aegis-demo`
- Workflow：`aegis_financial_summary_ppt`
- 产物：
  - `workspace/demo/report.txt`
  - `workspace/demo/summary.md`
  - `workspace/demo/output.pptx`

---

## 2. 运行方式

### 2.1 Success（无治理拦截）

```bash
airun bridge exec-workflow \
  --execution-id exec-demo-001 \
  --trace-id trace-demo-001 \
  --user-id user-demo \
  --workflow-spec-path packs/aegis-demo/aegis_financial_summary_ppt.yaml \
  --workspace ./workspace
```

预期：

- stdout 输出单条 JSON
- `status: success`
- `steps` 至少包含 3 个 step
- `workflow.status` 为 `completed`

### 2.2 PAUSE（模拟 Handshake：在某一步前暂停）

```bash
airun bridge exec-workflow \
  --execution-id exec-demo-002 \
  --trace-id trace-demo-002 \
  --user-id user-demo \
  --workflow-spec-path packs/aegis-demo/aegis_financial_summary_ppt.yaml \
  --workspace ./workspace \
  --enable-governance-hooks \
  --governance-decisions-json '{"pre_step":{"write_ppt_artifact":"PAUSE"}}'
```

预期：

- stdout 输出单条 JSON
- `status: paused`
- exit code 为 `30`

### 2.3 DENY（模拟 Constitution：执行前拒绝）

```bash
airun bridge exec-workflow \
  --execution-id exec-demo-003 \
  --trace-id trace-demo-003 \
  --user-id user-demo \
  --workflow-spec-path packs/aegis-demo/aegis_financial_summary_ppt.yaml \
  --workspace ./workspace \
  --enable-governance-hooks \
  --governance-decisions-json '{"pre_execution":"DENY"}'
```

预期：

- stdout 输出单条 JSON
- `status: failure`

---

## 3. 对接建议（Aegis）

- Aegis 在 QuestToWorkflowAdapter 阶段直接生成 WorkflowSpec（JSON/YAML）
- 使用 `bridge exec-workflow` 执行，并将 stdout JSON ingest 到 ExecutionHistory
- 使用 `AEGIS_WORKFLOW_RECORD_SCHEMA` 在 Aegis CI 中做输出结构校验
