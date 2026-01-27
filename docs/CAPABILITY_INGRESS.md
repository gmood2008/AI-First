# Capability Ingress & Governance Enforcement

## 核心原则

> **Capabilities are powers, not code.**
> **All powers must pass through governance.**

能力是权力，不是代码。所有权力必须通过治理。

## 架构

### Capability Ingress API

所有新能力必须通过 `CapabilityIngressAPI` 进入系统。

```
新能力（内部/第三方/AutoForge）
    ↓
CapabilityIngressService.submit_proposal()
    ↓
CapabilityProposal (PENDING_REVIEW)
    ↓
人工审批
    ↓
CapabilityApprovalService.approve_proposal()
    ↓
Registry.register_governance_approved()
    ↓
能力激活（ACTIVE）
```

### 禁止事项

❌ **Registry 直接写入**
- 禁止从第三方、Runtime、UI、Agent 直接写入 Registry
- Registry 写入只能通过治理批准路径

❌ **批量导入 = 批量激活**
- 禁止批量导入并立即激活
- 批量导入 = 批量提案，需要逐个审批

❌ **UI 直接创建能力**
- UI 可以提交提案、审核提案
- UI 不能直接创建能力或绕过提案流程

## API 使用

### 提交提案

```python
from governance.ingress.api import CapabilityIngressAPI
from governance.ingress.models import ProposalSource
from specs.v3.capability_schema import CapabilitySpec

api = CapabilityIngressAPI()

proposal = api.submit_proposal(
    capability_spec=spec,
    source=ProposalSource.INTERNAL,  # 或 THIRD_PARTY, AUTOFORGE
    submitted_by="user_id",
    justification="Required for feature X"
)
```

### 批量提交提案

```python
proposals = api.submit_batch_proposals(
    capability_specs=[spec1, spec2, spec3],
    source=ProposalSource.THIRD_PARTY,
    submitted_by="user_id",
    justification="Batch import from external source"
)
# 每个能力成为独立的 Proposal，需要逐个审批
```

### 批准提案

```python
api.approve_proposal(
    proposal_id=proposal.proposal_id,
    reviewer_id="admin",
    reason="Approved after security review"
)
# 能力被注册到 Registry，状态变为 ACTIVE
```

### 拒绝提案

```python
api.reject_proposal(
    proposal_id=proposal.proposal_id,
    reviewer_id="admin",
    rejection_reason="Security concerns"
)
# 能力永远不会进入 Registry
```

## Registry 治理强制

### 只读模式

Registry 默认启用治理强制：

```python
registry = CapabilityRegistry(governance_enforced=True)
```

### 直接注册（已弃用）

```python
# ⚠️ DEPRECATED: 仅用于向后兼容 stdlib 加载
registry.register(capability_id, handler, spec_dict)
# 对于非 stdlib 能力会抛出 RuntimeError
```

### 治理批准注册（唯一安全路径）

```python
# ✅ 唯一允许的新能力注册方式
registry.register_governance_approved(
    capability_id=capability_id,
    spec_dict=spec_dict,  # 必须包含 _governance 元数据
    approval_id=approval_id,
    handler=handler
)
```

## 验收标准

### ✅ Ingress Test

提交能力创建 Proposal，Registry 保持不变。

```python
proposal = api.submit_proposal(...)
assert proposal.status == ProposalStatus.PENDING_REVIEW
assert not api.registry.has_capability(proposal.capability_spec.id)
```

### ✅ Approval Test

批准提案激活能力，Runtime 可以执行。

```python
api.approve_proposal(proposal.proposal_id, reviewer_id="admin")
assert api.registry._governance_approved.get(capability_id) is not None
```

### ✅ Rejection Test

拒绝的提案永远不会出现在 Registry。

```python
api.reject_proposal(proposal.proposal_id, reviewer_id="admin", rejection_reason="...")
assert not api.registry.has_capability(capability_id)
```

### ✅ Security Test

任何绕过治理的尝试都会抛出硬错误。

```python
# 尝试直接注册（非 stdlib）
with pytest.raises(RuntimeError) as exc_info:
    registry.register("new.capability", handler, spec_dict)
assert "SECURITY" in str(exc_info.value)
assert "governance" in str(exc_info.value).lower()
```

## 代码审计

### 已审计的注册路径

1. **stdlib/loader.py** ✅
   - 允许：标准库能力在启动时加载
   - 限制：仅限 `io.*`, `net.*`, `sys.*`, `data.*` 命名空间

2. **external_loader.py** ⚠️
   - 需要重构：外部能力应通过提案流程

3. **registry.register()** ✅
   - 已添加治理检查
   - 非 stdlib 能力会抛出 RuntimeError

### 需要重构的路径

- `external_loader.py`: 外部能力加载应改为提案提交
- `forge import`: AutoForge 生成的能力应通过提案流程

## 设计原则

在治理模块中添加的注释：

```python
"""
Capabilities are powers, not code.
All powers must pass through governance.
"""
```

如果能力出现在 Registry 中但没有 Proposal ID，这是严重错误。

## 测试

运行验收测试：

```bash
pytest tests/v3/test_capability_ingress.py -v
```
