# AI-First Governance Console

## 概述

Governance Console 是 AI-First 生态系统的权威层（Authority Layer），负责：

- 决定能力是否健康或危险
- 提出演进或降级建议
- 在整个 Runtime 中强制执行硬执行禁令

所有执行层必须无条件遵守治理决策。

## 架构：4 个权力中心

### 1. Signal Bus - 传感器

**角色**: 治理事件源（不是调试日志）

**功能**:
- 被动记录系统发出的所有摩擦和失败信号
- 只追加写入（不可变）
- 信号可重放

**支持的信号类型**:
- `CAPABILITY_NOT_FOUND`
- `POLICY_DENIED`
- `ROLLBACK_TRIGGERED`
- `HUMAN_REJECTED`
- `GOVERNANCE_REJECTED`
- `LIFECYCLE_CHANGED`
- `HEALTH_DEGRADED`
- `EXECUTION_FAILED`
- `EXECUTION_SUCCESS`

### 2. Health Authority - 法官

**角色**: 评估信号并决定应该提出什么建议

**约束**:
- 不能改变能力状态
- 不能直接调用 LifecycleManager
- 不能接触 Registry

**输出**: 仅输出 `GovernanceProposal` 对象

**提案类型**:
- `FIX` - 修复可靠性问题
- `SPLIT` - 拆分为更小的能力
- `UPGRADE_RISK` - 提高风险级别
- `FREEZE` - 冻结能力

**核心规则**:
- 可靠性分数 < 80% → `FIX` 提案
- 人工干预率 > 50% → `SPLIT` 或 `UPGRADE_RISK` 提案
- 重复回滚 → `FREEZE` 提案

### 3. Lifecycle Manager - 执行器

**角色**: 唯一可以改变能力生命周期状态的组件

**状态**:
- `PROPOSED` → `ACTIVE` → `DEGRADING` → `FROZEN` → `DEPRECATED`

**硬规则**:
- 实现明确的状态转换表
- 无效转换必须引发错误
- `DEPRECATED` 是终端状态
- `FROZEN` 状态的能力必须被 Runtime 硬拒绝

### 4. Governance Console UI - 界面

**角色**: 人类操作台（不是可观测性仪表板）

**视图**:
- Health Leaderboard - 健康排行榜
- Proposal Queue - 提案队列
- Signal Stream - 信号流

## 使用方式

### CLI 工具

```bash
# 查看健康排行榜
python3 src/cli/governance.py leaderboard

# 查看提案队列
python3 src/cli/governance.py proposals

# 批准提案
python3 src/cli/governance.py approve <proposal_id> --reason "Reason here"

# 拒绝提案
python3 src/cli/governance.py reject <proposal_id> --reason "Reason here"

# 冻结能力
python3 src/cli/governance.py freeze <capability_id> --reason "Reason here"

# 解冻能力
python3 src/cli/governance.py unfreeze <capability_id> --reason "Reason here"

# 查看信号流
python3 src/cli/governance.py signals --capability-id <capability_id>
```

### Python API

```python
from governance import (
    SignalBus, LifecycleManager, HealthAuthority, GovernanceConsole
)

# 初始化
signal_bus = SignalBus()
lifecycle_manager = LifecycleManager(signal_bus)
health_authority = HealthAuthority(signal_bus, lifecycle_manager)
console = GovernanceConsole(signal_bus, lifecycle_manager, health_authority)

# 查看健康排行榜
leaderboard = console.get_health_leaderboard(limit=20)

# 查看提案队列
proposals = console.get_proposal_queue()

# 批准提案
console.approve_proposal(
    proposal_id="prop_123",
    admin_id="admin_user",
    reason="Approved after review"
)

# 冻结能力
console.freeze_capability(
    capability_id="net.api.dangerous",
    admin_id="admin_user",
    reason="Security concern"
)
```

## 治理完整性保证

### 边界强制执行

1. **HealthAuthority 只读**
   - 不能直接改变能力状态
   - 只能生成提案

2. **只有 LifecycleManager 可以改变状态**
   - 所有状态转换必须通过 LifecycleManager
   - 无效转换会引发 `StateTransitionError`

3. **FROZEN 状态硬拒绝**
   - Runtime 在执行前检查生命周期状态
   - FROZEN 能力返回 `NOT_FOUND` 状态
   - 发出 `GOVERNANCE_REJECTED` 信号

4. **所有治理操作可审计**
   - 每个生命周期更改都发出信号
   - 每个提案都有原因和证据
   - 所有管理员操作都记录在信号中

## 集成到 Runtime

治理系统已集成到 RuntimeEngine 和 MCP Server：

```python
from runtime.engine import RuntimeEngine
from runtime.registry import CapabilityRegistry
from governance import SignalBus, LifecycleManager

# 初始化治理组件
signal_bus = SignalBus()
lifecycle_manager = LifecycleManager(signal_bus)

# 创建 RuntimeEngine（带治理）
registry = CapabilityRegistry()
engine = RuntimeEngine(
    registry=registry,
    lifecycle_manager=lifecycle_manager,
    signal_bus=signal_bus
)

# FROZEN 能力会被自动拒绝
result = engine.execute("frozen.capability", {}, context)
# result.status == ExecutionStatus.NOT_FOUND
```

## 测试

运行完整性测试：

```bash
pytest tests/v3/test_governance_integrity.py -v
```

测试覆盖：
- HealthAuthority 只读验证
- LifecycleManager 状态转换
- Runtime 硬拒绝 FROZEN 能力
- 信号重放
- 提案工作流

## 数据库位置

治理系统使用 SQLite 数据库：

- 信号: `~/.ai-first/governance.db`
- 生命周期: `~/.ai-first/lifecycle.db`
- 提案: `~/.ai-first/governance_proposals.db`

## 未来扩展

- Web UI 界面
- 自动提案执行（需要配置）
- 更复杂的健康评分算法
- 能力依赖关系分析
- 批量操作支持
