# Governance Platform API - 平台级治理主权 API

## 定位声明

这不是一个"后台管理模块"，而是 **AI-First Runtime 的平台级治理主权 API（Sovereign Control Plane）**。

该 API 决定 Capability 的生死、冻结、降级与审计地位。

**哲学**：
- Proposal ≠ Execution
- 事实 ≠ 判断
- 没有治理 API，AI-First 只是工具；有了它，才是秩序系统

## 架构：4 个领域

### Domain A: Signal Ingestion (事实层)

**职责**：只记录事实，不判断、不聚合、不删除

**模块**：
- `signals/models.py` - Signal 数据模型
- `signals/signal_bus.py` - Signal Bus（只追加）
- `signals/repository.py` - Signal Repository（Event Sourcing）

**禁止事项**：
- ❌ update / delete
- ❌ 在这里计算健康度
- ❌ 自动触发生命周期变更

### Domain B: Governance Evaluation (裁决生成层)

**职责**：将 Signal 转换为 GovernanceProposal，只能"建议"，不能"执行"

**模块**：
- `evaluation/proposal.py` - GovernanceProposal 模型
- `evaluation/health_authority.py` - Health Authority（只读评估）
- `evaluation/rules.py` - 评估规则

**规则**：
- Reliability < 80% → Proposal(FIX)
- HUMAN_REJECTED 占比 > 50% → Proposal(SPLIT or UPGRADE_RISK)
- ROLLBACK_TRIGGERED 高频 → Proposal(FREEZE)

### Domain C: Lifecycle Authority (主权执行层)

**职责**：唯一允许改变 Capability 状态的模块

**模块**：
- `lifecycle/state_machine.py` - 状态机（严格转换表）
- `lifecycle/lifecycle_service.py` - Lifecycle Service（唯一可改变状态）
- `lifecycle/enforcement.py` - GovernanceViolation 强制执行

**状态机**：
```
PROPOSED → ACTIVE → DEGRADING → FROZEN → DEPRECATED
```

**Runtime 强制契约**：
- Runtime 执行前必须调用 `enforce_lifecycle_state()`
- 如果状态是 `FROZEN` 或 `DEPRECATED`，抛出 `GovernanceViolation`

### Domain D: Governance Audit (治理账本)

**职责**：形成跨系统、可追溯、不可篡改的治理因果链

**模块**：
- `audit/audit_log.py` - Audit Log（不可篡改）
- `audit/queries.py` - 审计查询

**记录内容**：
- Capability 状态变更
- Proposal 批准 / 拒绝
- 关联 Signal IDs
- （预留）permission_package_id（K-OS）

## 平台级 API

### GovernanceAPI 类

```python
from governance.api import GovernanceAPI

api = GovernanceAPI()
```

### API 方法

#### 1. POST /governance/signals

```python
signal_id = api.append_signal(
    capability_id="net.api.example",
    signal_type=SignalType.ROLLBACK_TRIGGERED,
    severity=SignalSeverity.HIGH,
    source=SignalSource.WORKFLOW,
    metadata={"workflow_id": "wf_123"}
)
```

#### 2. POST /governance/evaluate

```python
proposals = api.evaluate(
    capability_id="net.api.example",
    window_hours=24
)
```

#### 3. POST /governance/lifecycle/freeze

```python
api.freeze_capability(
    capability_id="net.api.example",
    proposal_id="prop_123",  # 可选
    approved_by="admin_user",
    reason="Security concern"
)
```

#### 4. GET /governance/lifecycle/{capability_id}

```python
state_info = api.get_lifecycle_state("net.api.example")
# 返回: {"capability_id": "...", "state": "FROZEN", "is_executable": False}
```

#### 5. GET /governance/audit/events

```python
events = api.get_audit_events(
    capability_id="net.api.example",
    limit=100
)
```

## Runtime 集成

### RuntimeEngine 集成

```python
from runtime.engine import RuntimeEngine
from runtime.registry import CapabilityRegistry
from governance.lifecycle.lifecycle_service import LifecycleService
from governance.signals.signal_bus import SignalBus

# 初始化治理组件
signal_bus = SignalBus()
state_machine = LifecycleStateMachine()
lifecycle_service = LifecycleService(state_machine, signal_bus)

# 创建 RuntimeEngine（带治理）
registry = CapabilityRegistry()
engine = RuntimeEngine(
    registry=registry,
    lifecycle_service=lifecycle_service,
    signal_bus=signal_bus
)

# FROZEN 能力会被自动拒绝（抛出 GovernanceViolation）
result = engine.execute("frozen.capability", {}, context)
# result.status == ExecutionStatus.ERROR
```

### UndoManager 集成

```python
# UndoManager.rollback() 会自动发射 ROLLBACK_TRIGGERED 信号
undone = undo_manager.rollback(steps=1, signal_bus=signal_bus)
```

## 验收标准

### 1. Signal Test ✅

模拟 workflow rollback → governance_signals 有 ROLLBACK_TRIGGERED

```python
api.append_signal(
    capability_id="test.capability",
    signal_type=SignalType.ROLLBACK_TRIGGERED,
    severity=SignalSeverity.HIGH,
    source=SignalSource.WORKFLOW
)

signals = api.signal_bus.get_signals(
    capability_id="test.capability",
    signal_type=SignalType.ROLLBACK_TRIGGERED
)
assert len(signals) > 0
```

### 2. Health Test ✅

注入 10 条失败 signal → HealthAuthority 生成 Proposal(FREEZE)

```python
for i in range(10):
    api.append_signal(
        capability_id="test.capability",
        signal_type=SignalType.EXECUTION_FAILED,
        severity=SignalSeverity.HIGH,
        source=SignalSource.RUNTIME
    )

proposals = api.evaluate("test.capability", window_hours=24)
freeze_proposals = [p for p in proposals if p.proposal_type.value == "FREEZE"]
assert len(freeze_proposals) > 0
```

### 3. Governance Test ✅

Lifecycle 冻结 capability → Runtime 立即拒绝执行

```python
api.freeze_capability(
    capability_id="test.capability",
    proposal_id=None,
    approved_by="admin",
    reason="Test freeze"
)

result = engine.execute("test.capability", {}, context)
assert result.status == ExecutionStatus.ERROR
assert "FROZEN" in result.error_message
```

## 治理完整性保证

1. **Signal 只记录事实** - 不判断、不聚合、不删除
2. **Proposal 只是建议** - 不直接执行，必须通过 LifecycleService
3. **只有 LifecycleService 可以改变状态** - 所有状态转换必须通过它
4. **Runtime 强制服从** - 执行前检查，FROZEN/DEPRECATED 立即拒绝
5. **所有操作可审计** - 每个操作都记录在 Audit Log

## 使用示例

### 完整工作流

```python
from governance.api import GovernanceAPI
from governance.signals.models import SignalType, SignalSeverity, SignalSource

api = GovernanceAPI()

# 1. Runtime 上报失败信号
api.append_signal(
    capability_id="net.api.example",
    signal_type=SignalType.EXECUTION_FAILED,
    severity=SignalSeverity.HIGH,
    source=SignalSource.RUNTIME
)

# 2. Health Authority 评估并生成 Proposal
proposals = api.evaluate("net.api.example", window_hours=24)

# 3. 批准 Proposal 并执行
if proposals:
    proposal = proposals[0]
    api.approve_proposal(
        proposal_id=proposal.proposal_id,
        approved_by="admin",
        reason="Approved after review"
    )

# 4. 查询状态
state_info = api.get_lifecycle_state("net.api.example")
print(f"State: {state_info['state']}, Executable: {state_info['is_executable']}")

# 5. 查询审计记录
audit_events = api.get_audit_events(capability_id="net.api.example")
for event in audit_events:
    print(f"{event.timestamp}: {event.event_type} by {event.actor}")
```

## 数据库

治理系统使用 SQLite：

- `~/.ai-first/governance_signals.db` - Signal 记录
- `~/.ai-first/lifecycle.db` - 生命周期状态
- `~/.ai-first/governance_proposals.db` - 治理提案
- `~/.ai-first/governance_audit.db` - 审计记录

## 测试

运行验收测试：

```bash
pytest tests/v3/test_governance_platform_api.py -v
```

## 重要提醒

写代码时，请始终问自己：

> "这一步是在记录事实、生成裁决，还是在行使主权？"

如果答案不清楚，说明设计错了。

**这是 Runtime 的"宪法法院"。**
