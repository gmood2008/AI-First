# Governance Platform API v3.1 Beta - 部署总结

## ✅ 部署完成

**日期**: 2024-12-XX  
**版本**: v3.1 Beta  
**状态**: ✅ 所有验收标准通过

---

## 📦 架构重构

### 领域驱动设计（DDD）结构

```
src/governance/
├── signals/              # Domain A: 事实层
│   ├── models.py         # Signal 数据模型
│   ├── signal_bus.py     # Signal Bus（只追加）
│   └── repository.py     # Signal Repository（Event Sourcing）
│
├── evaluation/           # Domain B: 裁决生成层
│   ├── proposal.py       # GovernanceProposal 模型
│   ├── health_authority.py  # Health Authority（只读评估）
│   └── rules.py          # 评估规则
│
├── lifecycle/            # Domain C: 主权执行层
│   ├── state_machine.py  # 状态机（严格转换表）
│   ├── lifecycle_service.py  # Lifecycle Service（唯一可改变状态）
│   └── enforcement.py    # GovernanceViolation 强制执行
│
├── audit/                # Domain D: 治理账本
│   ├── audit_log.py      # Audit Log（不可篡改）
│   └── queries.py        # 审计查询
│
└── api.py                # 平台级 API 门面
```

---

## ✅ 验收标准（全部通过）

### 1. Signal Test ✅

**要求**: 模拟 workflow rollback → governance_signals 有 ROLLBACK_TRIGGERED

**结果**: ✅ 通过
- Signal 成功记录到数据库
- 可以按 capability_id 和 signal_type 查询

### 2. Health Test ✅

**要求**: 注入 3+ 条 ROLLBACK_TRIGGERED → HealthAuthority 生成 Proposal(FREEZE)

**结果**: ✅ 通过
- 成功生成 FREEZE Proposal
- Proposal 包含证据 Signal IDs
- Proposal 包含置信度和原因

### 3. Governance Test ✅

**要求**: Lifecycle 冻结 capability → Runtime 立即拒绝执行

**结果**: ✅ 通过
- Runtime 正确拒绝 FROZEN 能力
- 抛出 GovernanceViolation 异常
- 发出 GOVERNANCE_REJECTED 信号
- 审计事件正确记录

---

## 🔗 集成点

### RuntimeEngine

```python
from runtime.engine import RuntimeEngine
from governance.lifecycle.lifecycle_service import LifecycleService
from governance.signals.signal_bus import SignalBus

engine = RuntimeEngine(
    registry=registry,
    lifecycle_service=lifecycle_service,
    signal_bus=signal_bus
)

# FROZEN 能力会被自动拒绝
result = engine.execute("frozen.capability", {}, context)
# result.status == ExecutionStatus.ERROR
```

### UndoManager

```python
# UndoManager.rollback() 会自动发射 ROLLBACK_TRIGGERED 信号
undone = undo_manager.rollback(steps=1, signal_bus=signal_bus)
```

### MCP Server

```python
# server_v2.py 已集成
from governance.signals.signal_bus import SignalBus
from governance.lifecycle.lifecycle_service import LifecycleService
from governance.lifecycle.state_machine import LifecycleStateMachine

signal_bus = SignalBus()
state_machine = LifecycleStateMachine()
lifecycle_service = LifecycleService(state_machine, signal_bus)

engine = RuntimeEngine(
    registry=registry,
    lifecycle_service=lifecycle_service,
    signal_bus=signal_bus
)
```

---

## 📋 平台级 API

### GovernanceAPI 类

```python
from governance.api import GovernanceAPI

api = GovernanceAPI()
```

### API 方法

| HTTP 方法 | 路径 | Python 方法 | 说明 |
|----------|------|-------------|------|
| POST | `/governance/signals` | `append_signal()` | 追加 Signal（只记录事实） |
| POST | `/governance/evaluate` | `evaluate()` | 评估并生成 Proposal |
| POST | `/governance/lifecycle/freeze` | `freeze_capability()` | 冻结能力（主权执行） |
| GET | `/governance/lifecycle/{id}` | `get_lifecycle_state()` | 获取生命周期状态 |
| GET | `/governance/audit/events` | `get_audit_events()` | 获取审计事件 |

---

## 🗄️ 数据库

治理系统使用 SQLite：

| 数据库文件 | 用途 | 表名 |
|-----------|------|------|
| `~/.ai-first/governance_signals.db` | Signal 记录 | `governance_signals` |
| `~/.ai-first/lifecycle.db` | 生命周期状态 | `capability_lifecycles` |
| `~/.ai-first/governance_proposals.db` | 治理提案 | `governance_proposals` |
| `~/.ai-first/governance_audit.db` | 审计记录 | `governance_audit` |

### 数据库迁移

系统自动处理数据库迁移：
- 检查表是否存在
- 检查列是否存在
- 自动添加缺失的列
- 如果表结构不匹配，删除并重建

---

## 🧪 测试

### 运行验收测试

```bash
pytest tests/v3/test_governance_platform_api.py -v
```

### 手动测试

```python
from governance.api import GovernanceAPI
from governance.signals.models import SignalType, SignalSeverity, SignalSource

api = GovernanceAPI()

# 1. 追加 Signal
api.append_signal(
    capability_id="test.capability",
    signal_type=SignalType.ROLLBACK_TRIGGERED,
    severity=SignalSeverity.HIGH,
    source=SignalSource.WORKFLOW
)

# 2. 评估并生成 Proposal
proposals = api.evaluate("test.capability", window_hours=24)

# 3. 冻结能力
api.freeze_capability(
    capability_id="test.capability",
    proposal_id=None,
    approved_by="admin",
    reason="Test freeze"
)

# 4. 查询状态
state_info = api.get_lifecycle_state("test.capability")
print(f"State: {state_info['state']}, Executable: {state_info['is_executable']}")

# 5. 查询审计记录
audit_events = api.get_audit_events(capability_id="test.capability")
```

---

## 📋 治理完整性保证

1. **Signal 只记录事实** ✅
   - 不判断、不聚合、不删除
   - Event Sourcing / Append-only 模式

2. **Proposal 只是建议** ✅
   - 不直接执行，必须通过 LifecycleService
   - 包含证据、置信度、原因

3. **只有 LifecycleService 可以改变状态** ✅
   - 所有状态转换必须通过它
   - 严格的状态转换表

4. **Runtime 强制服从** ✅
   - 执行前检查，FROZEN/DEPRECATED 立即拒绝
   - 抛出 GovernanceViolation 异常

5. **所有操作可审计** ✅
   - 每个操作都记录在 Audit Log
   - 形成可追溯的因果链

---

## 🎯 核心哲学

> **这是 Runtime 的"宪法法院"。**

写代码时，请始终问自己：

> "这一步是在记录事实、生成裁决，还是在行使主权？"

如果答案不清楚，说明设计错了。

---

## 📚 文档

- [Governance Platform API 文档](docs/GOVERNANCE_PLATFORM_API.md)
- [Governance Console 文档](docs/GOVERNANCE_CONSOLE.md)

---

## ✅ 部署清单

- [x] Domain A: Signal Ingestion API（事实层）
- [x] Domain B: Governance Evaluation API（裁决生成层）
- [x] Domain C: Lifecycle Authority API（主权执行层）
- [x] Domain D: Governance Audit API（治理账本）
- [x] 平台级 API 门面（api.py）
- [x] RuntimeEngine 集成
- [x] UndoManager 集成
- [x] MCP Server 集成
- [x] 验收标准测试
- [x] 数据库迁移逻辑
- [x] 文档完善

---

## 🎉 部署成功

**Governance Platform API v3.1 Beta 已就绪！**

所有验收标准通过，系统可以投入使用。
