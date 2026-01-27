# Governance Platform V1 + V2 API 文档

## 概述

AI-First Governance Platform 提供两个版本的 API：

- **V1: Observatory APIs** - 只读治理可观测性
- **V2: Decision Room APIs** - 人工治理决策

## 核心原则

1. **API 主权** - 每个治理能力都通过 API 暴露
2. **只读为主，仅签名可写** - V1 100% 只读，V2 只有 approve/reject 可写
3. **不绕过 Runtime 安全措施** - 治理 API 可以控制 Runtime 行为，但不能绕过安全措施
4. **审计是强制性的** - 每个治理决策必须留下持久、可查询的记录

## V1: Observatory APIs (只读治理)

### A1. Capability Health Read Model

#### GET /governance/capabilities/health

获取所有能力的健康度。

**响应示例**:
```json
{
  "capability_id": {
    "capability_id": "io.fs.read_file",
    "current_state": "ACTIVE",
    "reliability_score": 95.5,
    "friction_score": 2.3,
    "last_incident_at": "2024-12-01T10:00:00",
    "last_state_change_at": "2024-12-01T09:00:00"
  }
}
```

#### GET /governance/capabilities/{id}/health

获取单个能力的健康度。

### A2. Risk & Registry Distribution APIs

#### GET /governance/capabilities/risk-distribution

获取风险分布。

**响应示例**:
```json
{
  "distribution": {
    "LOW": 10,
    "MEDIUM": 5,
    "HIGH": 2,
    "CRITICAL": 1
  },
  "total": 18,
  "by_risk": {
    "LOW": ["io.fs.read_file", "io.fs.exists"],
    "HIGH": ["io.fs.delete", "net.http.post"]
  }
}
```

#### GET /governance/capabilities/by-risk?risk={level}

按风险级别获取能力列表。

### A3. Signal Timeline API

#### GET /governance/signals

获取信号时间线。

**查询参数**:
- `capability_id`: 能力 ID（可选）
- `signal_type`: 信号类型（可选）
- `start_time`: 开始时间（可选）
- `end_time`: 结束时间（可选）
- `limit`: 最大返回数量（可选）

#### GET /governance/signals/timeline?capability_id={id}

获取能力的信号时间线（因果链）。

### A4. Capability Demand Radar API

#### GET /governance/demand/missing-capabilities

获取缺失能力列表。

**查询参数**:
- `window_hours`: 时间窗口（小时，默认 24）
- `min_frequency`: 最小频率（默认 1）

#### GET /governance/demand/hotspots

获取需求热点。

**查询参数**:
- `window_hours`: 时间窗口（小时，默认 24）
- `top_n`: 返回前 N 个热点（默认 10）

## V2: Decision Room APIs (人工治理)

### B1. Governance Proposal Model

提案模型字段：
- `proposal_id`: 提案 ID
- `proposal_type`: 提案类型（FIX / SPLIT / FREEZE / PROMOTE / DEPRECATE）
- `target_capability_id`: 目标能力 ID
- `triggering_evidence`: 触发证据（signals, metrics, references）
- `created_at`: 创建时间
- `created_by`: 创建者（system / admin / autoforge）
- `status`: 状态（PENDING / APPROVED / REJECTED / EXPIRED）

### B2. Proposal Lifecycle APIs

#### GET /governance/proposals

获取提案列表。

**查询参数**:
- `status`: 状态过滤（可选）
- `target_capability_id`: 能力 ID 过滤（可选）

#### GET /governance/proposals/{id}

获取单个提案。

#### POST /governance/proposals/{id}/approve

批准提案。

**请求体**:
```json
{
  "decided_by": "admin",
  "rationale": "Approved after security review"
}
```

**响应**: Governance Decision Record

#### POST /governance/proposals/{id}/reject

拒绝提案。

**请求体**:
```json
{
  "decided_by": "admin",
  "rationale": "Security concerns"
}
```

### B3. Governance Decision Record (GDR)

决策记录字段：
- `decision_id`: 决策 ID
- `proposal_id`: 提案 ID
- `decision`: 决策类型（APPROVE / REJECT）
- `decided_by`: 决策者
- `decided_at`: 决策时间
- `rationale`: 理由（必需）
- `affected_capabilities`: 受影响的能力列表
- `resulting_state_transition`: 结果状态转换（如果有）

#### GET /governance/decisions/{proposal_id}

获取决策记录。

#### GET /governance/decisions

获取所有决策记录。

### B4. Lifecycle Enforcement Hook

当提案结果导致状态变更时：

- **FREEZE** → 能力状态变为 FROZEN
- Runtime 必须立即拒绝执行
- 返回确定性错误

## 使用示例

### Python API

```python
from governance.platform_api import GovernancePlatformAPI

api = GovernancePlatformAPI()

# V1: 只读治理
health = api.get_capability_health("io.fs.read_file")
distribution = api.get_risk_distribution()
signals = api.get_signals(capability_id="io.fs.read_file")
missing = api.get_missing_capabilities()

# V2: 人工治理
proposals = api.get_proposals(status="PENDING")
decision = api.approve_proposal(
    proposal_id="prop_123",
    decided_by="admin",
    rationale="Approved"
)
gdr = api.get_decision_record("prop_123")
```

## 验收标准

### ✅ Signal → Proposal

模拟重复失败，HealthAuthority 生成 FIX proposal。

### ✅ Proposal → Decision

批准 FREEZE，GDR 创建。

### ✅ Decision → Runtime Enforcement

冻结的能力在执行时被拒绝。

## 最终验证问题

**如果所有 UI 消失，治理是否仍能完全且安全地通过 API 运行？**

**答案：是 ✅**

- V1 APIs 提供完整的只读可观测性
- V2 APIs 提供完整的人工治理决策
- 所有操作都通过 API 进行
- 所有决策都有审计记录
