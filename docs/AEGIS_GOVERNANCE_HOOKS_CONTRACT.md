# Aegis × AI-First Runtime：治理 Hook 协议（Contract）

**执行时间**：2026-01-30

本文定义 Aegis 治理层与 AI-First Runtime 工作流引擎（AWE）之间的 **治理注入点（Hooks）契约**。

目标：

- 让 Aegis 可以在 **workflow 执行前 / step 执行前后** 注入 Constitution 检查与 Handshake 授权
- 让 Aegis 可以触发 Panic（中止/回滚）并获得可追踪的执行事件
- 明确 hook 的 **调用时机、输入输出字段、失败/暂停语义与建议的错误映射**

---

## 1. 术语

- **Workflow**：AI-First Runtime 的工作流执行单元，由 `workflow_id` 标识。
- **Step**：Workflow 内部的执行步骤，通常对应一次 capability 执行。
- **Governance Hook**：由工作流引擎在特定时机调用的治理回调。
- **Constitution**：Aegis 侧的合规/策略检查体系。
- **Handshake**：Aegis 侧的关键节点授权流程（人机审批/外部系统审批）。
- **Panic**：紧急中止/回滚/冻结的操作模式。

---

## 2. Hook 调用时机（Invocation Points）

工作流执行的关键节点：

1. `pre_execution`
2. `pre_step`
3. `post_step`
4. `post_execution`
5. `on_panic`（外部触发）

### 2.1 pre_execution

**调用时机**：workflow 被接收并完成静态校验后、开始执行任何 step 之前。

**用途**：

- Aegis Constitution 对 workflow 全局进行合规检查
- 预算/成本/敏感资源约束预检查
- 对部分 workflow 直接拒绝执行

### 2.2 pre_step

**调用时机**：单个 step 的 inputs 已完成解析（模板变量/上游输出注入后）且即将执行 capability 之前。

**用途**：

- Aegis Handshake：对高风险 step 进行授权
- 对 step 做二次合规检查（细粒度）
- 对 step 做风险分级与审计标签注入

### 2.3 post_step

**调用时机**：step 执行完成（成功/失败/拒绝/错误）之后，step 结果已形成（含输出与错误）。

**用途**：

- Aegis Skill Memory 记录 step 级事件
- Aegis 侧指标采集（耗时、失败原因）

### 2.4 post_execution

**调用时机**：workflow 终态形成（SUCCESS / FAILED / PAUSED / CANCELED / ROLLED_BACK），并完成必要的回滚动作之后。

**用途**：

- Aegis Skill Memory 记录 workflow 级结果
- Aegis Quest 状态落库

### 2.5 on_panic

**调用时机**：Aegis 主动发起 panic 操作（例如 UI 上点击“终止并回滚”）。

**用途**：

- 触发 workflow 中止
- 触发回滚（如果策略要求）

---

## 3. Hook 载荷（Payload Shapes）

本文以 JSON 形态描述载荷（不约束传输方式）。

### 3.1 通用字段

所有 hook 请求建议包含：

- `trace_id`：Aegis 侧链路追踪 ID
- `quest_id`：Aegis Quest ID（如有）
- `workflow_id`
- `timestamp`：ISO 8601
- `runtime_version`：AI-First Runtime 版本

### 3.2 pre_execution 请求

```json
{
  "trace_id": "...",
  "quest_id": "quest-001",
  "workflow_id": "quest-001",
  "timestamp": "2026-01-30T10:00:00Z",
  "runtime_version": "3.x",
  "workflow_spec": {
    "steps": [
      {
        "step_id": "fetch_report",
        "capability": "...",
        "inputs": {"...": "..."},
        "risk": {"level": "HIGH"}
      }
    ],
    "constraints": {
      "timeout_ms": 300000,
      "max_cost": 10
    }
  }
}
```

### 3.3 pre_step 请求

```json
{
  "trace_id": "...",
  "quest_id": "quest-001",
  "workflow_id": "quest-001",
  "step": {
    "step_id": "delete_prod_data",
    "capability": "io.fs.remove",
    "inputs": {"path": "/prod/..."},
    "risk": {"level": "HIGH", "requires_handshake": true}
  },
  "resolved_context": {
    "workspace_root": "...",
    "user_id": "..."
  }
}
```

### 3.4 post_step 请求

```json
{
  "trace_id": "...",
  "quest_id": "quest-001",
  "workflow_id": "quest-001",
  "step": {
    "step_id": "fetch_report",
    "capability": "..."
  },
  "result": {
    "status": "SUCCESS",
    "started_at": "...",
    "ended_at": "...",
    "execution_time_ms": 1234,
    "outputs": {"...": "..."},
    "error": null
  }
}
```

### 3.5 post_execution 请求

```json
{
  "trace_id": "...",
  "quest_id": "quest-001",
  "workflow_id": "quest-001",
  "summary": {
    "status": "FAILED",
    "started_at": "...",
    "ended_at": "...",
    "execution_time_ms": 4567,
    "failure_category": "VALIDATION_ERROR"
  }
}
```

### 3.6 on_panic 请求

```json
{
  "trace_id": "...",
  "quest_id": "quest-001",
  "workflow_id": "quest-001",
  "action": "CANCEL_AND_ROLLBACK",
  "reason": "user_requested"
}
```

---

## 4. Hook 返回值（Decision Model）

为支持 Aegis 的 Constitution/Handshake 场景，建议 hook 返回三类决策：

- `ALLOW`：允许继续
- `DENY`：拒绝执行（workflow/step 进入失败）
- `PAUSE`：暂停执行，等待外部批准（适用于 handshake）

### 4.1 返回格式

```json
{
  "decision": "ALLOW",
  "reason": "ok",
  "violation_id": null,
  "approval": {
    "required": false,
    "approval_id": null
  }
}
```

### 4.2 DENY 语义

- pre_execution DENY：workflow 不进入执行阶段，终态为 FAILED（或 DENIED）
- pre_step DENY：当前 step 被拒绝，workflow 终态为 FAILED（或 DENIED），并触发回滚（如果 workflow 策略为失败回滚）

### 4.3 PAUSE 语义（Handshake）

- pre_step 返回 PAUSE：workflow 进入 PAUSED
- Aegis 需要提供恢复动作（approve/reject）：
  - approve：workflow 从 PAUSED 继续执行
  - reject：workflow 终止并按策略回滚

---

## 5. 错误与 FailureCategory 映射建议

为对齐 Aegis `FailureCategory`，建议将治理相关失败映射为：

- Constitution 违规：`POLICY_VIOLATION`（或 Aegis 指定分类）
- Handshake 被拒：`CONFIRMATION_DENIED`
- Hook 调用失败（网络/超时/异常）：`INTERNAL_ERROR`

---

## 6. Aegis 需要提供的信息（用于最终落地实现）

为完成实现对齐，Aegis 需要明确：

- Constitution violation 的结构化 schema（violation_id、规则编号、文本说明）
- 哪些 step 需要 handshake（判定规则、字段承载方式）
- PAUSE 恢复接口设计（approve/reject 的调用方式与幂等要求）
- Panic 的策略矩阵：
  - CANCEL_ONLY / CANCEL_AND_ROLLBACK / FREEZE

---

## 7. CLI 本地验证（Aegis 可直接用来联调）

AI-First Runtime 提供 `bridge exec-workflow` 的本地验证模式，用于在 Aegis 接入前快速验证：

- hooks 调用时机（pre_execution/pre_step/post_step/post_execution）
- `DENY/PAUSE` 对 workflow 执行状态与退出码的影响

### 7.1 启用 hooks

- CLI 参数：`--enable-governance-hooks`
- 决策注入：
  - CLI 参数：`--governance-decisions-json '<json>'`
  - 环境变量：`AEGIS_GOVERNANCE_DECISIONS_JSON='<json>'`

决策 JSON 格式（最小）：

```json
{
  "pre_execution": "ALLOW",
  "pre_step": {
    "fetch_report": "ALLOW",
    "generate_ppt": "PAUSE"
  }
}
```

### 7.2 示例：在 workflow 启动前 DENY（pre_execution）

```bash
airun bridge exec-workflow \
  --execution-id exec-001 \
  --trace-id trace-001 \
  --user-id user-001 \
  --workflow-spec-path /path/to/workflow.yaml \
  --enable-governance-hooks \
  --governance-decisions-json '{"pre_execution":"DENY"}'
```

预期：

- stdout 输出单条 JSON
- workflow 终态为失败（`status: failure`）

### 7.3 示例：在某个 step 前 PAUSE（pre_step）

```bash
airun bridge exec-workflow \
  --execution-id exec-002 \
  --trace-id trace-002 \
  --user-id user-002 \
  --workflow-spec-path /path/to/workflow.yaml \
  --enable-governance-hooks \
  --governance-decisions-json '{"pre_step":{"generate_ppt":"PAUSE"}}'
```

预期：

- stdout 输出单条 JSON
- `status: paused`
- exit code 为 `30`

---

## 8. HTTP Hooks（面向 Aegis 服务化接入）

除本地 decisions 模式外，`bridge exec-workflow` 也支持将 governance hook 事件通过 HTTP POST 回调到 Aegis 服务。

### 8.1 启用方式（与本地 decisions 模式互斥）

- CLI 参数：
  - `--governance-hook-url <url>`
  - `--governance-hook-timeout-ms <int>`（默认 2000）
  - `--governance-hook-fail-mode <ALLOW|DENY|PAUSE>`（默认 DENY）
- 环境变量：
  - `AEGIS_GOVERNANCE_HOOK_URL=<url>`
  - `AEGIS_GOVERNANCE_HOOK_TIMEOUT_MS=<int>`
  - `AEGIS_GOVERNANCE_HOOK_FAIL_MODE=<ALLOW|DENY|PAUSE>`

约束：

- `--enable-governance-hooks`（本地 decisions）与 `--governance-hook-url`（HTTP hooks）不可同时使用。

### 8.2 Hook 请求格式（POST JSON）

当触发 hook 时，runtime 会向 `--governance-hook-url` 发起 HTTP POST，请求体为 JSON。

字段（最小）：

```json
{
  "event": "pre_step",
  "traceId": "trace-001",
  "workflowId": "<workflow-exec-id>",
  "step": {
    "name": "generate_ppt",
    "stepType": "ACTION",
    "capabilityId": "io.fs.write_file",
    "agentName": "aegis",
    "riskLevel": "MEDIUM"
  },
  "inputs": {
    "path": "demo/output.pptx",
    "content": "..."
  }
}
```

说明：

- `event` 枚举：`pre_execution` | `pre_step` | `post_step` | `post_execution`
- `step`/`inputs` 字段仅在 step 相关事件中提供

### 8.3 Hook 响应格式（decision）

HTTP 200 响应体为 JSON：

```json
{
  "decision": "ALLOW"
}
```

其中 `decision` 支持：`ALLOW` | `DENY` | `PAUSE`。

### 8.4 超时与失败策略

当 HTTP hook 调用发生超时或异常时，将应用 `--governance-hook-fail-mode`（默认 `DENY`）。

---

## 9. 版本与兼容性

- 本协议建议纳入 `docs/COMPATIBILITY_CONTRACT.md` 的“对外契约”范围
- Hook payload 字段扩展遵循“对象扩展向后兼容”原则
