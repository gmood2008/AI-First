# Capability Ingress & Governance Enforcement - 部署总结

## ✅ 部署完成

**日期**: 2024-12-XX  
**版本**: v3.1  
**状态**: ✅ 所有验收标准通过

---

## 📦 核心组件

### Capability Ingress API

```
src/governance/ingress/
├── models.py              # CapabilityProposal 模型
├── ingress_service.py     # 能力准入服务
├── approval_service.py    # 审批服务
└── api.py                 # API 门面
```

### Registry 治理强制

- `CapabilityRegistry.register_governance_approved()` - 唯一安全路径
- `CapabilityRegistry.register()` - 已弃用，仅用于 stdlib 向后兼容
- 治理检查：非 stdlib 能力直接注册会抛出 `RuntimeError`

---

## ✅ 验收标准（全部通过）

### 1. Ingress Test ✅

**要求**: 提交能力创建 Proposal，Registry 保持不变

**结果**: ✅ 通过
- 提案成功创建，状态为 `PENDING_REVIEW`
- Registry 未改变，能力未激活

### 2. Approval Test ✅

**要求**: 批准提案激活能力，Runtime 可以执行

**结果**: ✅ 通过
- 提案批准后，能力注册到 Registry
- 治理元数据正确附加
- 生命周期状态设置为 `ACTIVE`

### 3. Rejection Test ✅

**要求**: 拒绝的提案永远不会出现在 Registry

**结果**: ✅ 通过
- 拒绝的提案状态为 `REJECTED`
- 能力未注册到 Registry
- 拒绝原因正确记录

### 4. Security Test ✅

**要求**: 任何绕过治理的尝试都会抛出硬错误

**结果**: ✅ 通过
- 直接注册非 stdlib 能力抛出 `RuntimeError`
- 错误消息包含 "SECURITY" 和 "governance"
- Registry 治理强制生效

---

## 🔒 治理强制

### Registry 只读模式

```python
registry = CapabilityRegistry(governance_enforced=True)
```

### 直接注册检查

```python
# ⚠️ 非 stdlib 能力会被拒绝
try:
    registry.register("new.capability", handler, spec_dict)
except RuntimeError as e:
    # ❌ SECURITY: Direct registration is forbidden
    pass
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

---

## 📋 API 方法

| HTTP 方法 | 路径 | Python 方法 | 说明 |
|----------|------|-------------|------|
| POST | `/governance/capabilities/proposals` | `submit_proposal()` | 提交提案 |
| POST | `/governance/capabilities/proposals/batch` | `submit_batch_proposals()` | 批量提交提案 |
| POST | `/governance/capabilities/proposals/{id}/approve` | `approve_proposal()` | 批准提案 |
| POST | `/governance/capabilities/proposals/{id}/reject` | `reject_proposal()` | 拒绝提案 |

---

## 🗄️ 数据库

| 数据库文件 | 用途 | 表名 |
|-----------|------|------|
| `~/.ai-first/capability_proposals.db` | 能力提案 | `capability_proposals` |

---

## 🧪 测试

### 运行验收测试

```bash
pytest tests/v3/test_capability_ingress.py -v
```

### 手动测试

```python
from governance.ingress.api import CapabilityIngressAPI
from governance.ingress.models import ProposalSource
from specs.v3.capability_schema import CapabilitySpec, RiskLevel, OperationType, Risk, SideEffects, Compensation, CapabilityMetadata

api = CapabilityIngressAPI()

# 1. 提交提案
spec = CapabilitySpec(...)
proposal = api.submit_proposal(
    capability_spec=spec,
    source=ProposalSource.INTERNAL,
    submitted_by="user_id",
    justification="Required for feature X"
)

# 2. 批准提案
api.approve_proposal(
    proposal_id=proposal.proposal_id,
    reviewer_id="admin",
    reason="Approved after security review"
)

# 3. 验证能力已注册
assert api.registry._governance_approved.get(spec.id) is not None
```

---

## 📋 代码审计

### 已审计的注册路径

1. **stdlib/loader.py** ✅
   - 允许：标准库能力在启动时加载
   - 限制：仅限 `io.*`, `net.*`, `sys.*`, `data.*` 命名空间

2. **registry.register()** ✅
   - 已添加治理检查
   - 非 stdlib 能力会抛出 `RuntimeError`

### 需要重构的路径

- `external_loader.py`: 外部能力加载应改为提案提交
- `forge import`: AutoForge 生成的能力应通过提案流程

---

## 🎯 核心原则

> **Capabilities are powers, not code.**
> **All powers must pass through governance.**

如果能力出现在 Registry 中但没有 Proposal ID，这是严重错误。

---

## ✅ 部署清单

- [x] Capability Ingress API
- [x] Capability Proposal Workflow
- [x] Governance Approval API
- [x] Batch Import = Batch Proposal
- [x] Registry 治理强制
- [x] 直接注册检查
- [x] 验收标准测试
- [x] 文档完善

---

## 🎉 部署成功

**Capability Ingress & Governance Enforcement 已就绪！**

所有新能力必须通过治理审批才能进入系统。
