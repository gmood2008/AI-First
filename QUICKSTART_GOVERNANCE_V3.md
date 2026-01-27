# Governance Platform v3 - 快速启动指南

## 🚀 快速开始

### 1. 通过 API（推荐）

```python
from governance.api_v3 import GovernanceAPIV3

# 初始化 API
api = GovernanceAPIV3()

# 获取所有能力
capabilities = api.get_capabilities()

# 获取能力健康度
health = api.get_capability_health("io.fs.read_file")

# 获取提案列表
proposals = api.get_proposals(status="PENDING")

# 批准提案
decision = api.approve_proposal(
    proposal_id="prop_123",
    decided_by="admin",
    rationale="Approved after review"
)
```

### 2. 通过 curl

```bash
# 获取所有能力
curl http://localhost:8080/api/governance/capabilities

# 获取能力健康度
curl http://localhost:8080/api/governance/capabilities/test.capability/health

# 获取提案列表
curl http://localhost:8080/api/governance/proposals?status=PENDING

# 批准提案
curl -X POST http://localhost:8080/api/governance/proposals/prop_123/approve \
  -H "Content-Type: application/json" \
  -d '{"decided_by": "admin", "rationale": "Approved"}'
```

### 3. 通过 Web Console（参考实现）

```bash
# 启动服务器
python3 src/governance/web/server.py

# 访问
http://localhost:8080
```

## 📋 核心原则

1. **API 主权** - 所有逻辑在 API 层
2. **只读为主，仅签名可写** - UI 只能查看和审批
3. **UI 可删除** - 删除 UI 后，治理系统仍然完整

## ✅ 验证

运行验收测试：

```bash
pytest tests/v3/test_governance_v3_runtime_enforcement.py -v
```

## 📚 文档

- [完整实现文档](docs/GOVERNANCE_V3_COMPLETE.md)
- [OpenAPI 文档](docs/governance-api-openapi.yaml)
- [部署总结](GOVERNANCE_V3_DEPLOYMENT.md)
