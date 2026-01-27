# Governance Platform v3 - 完整实现文档

## 核心原则（写在代码注释顶部）

```python
"""
If the Web Console disappears,
the Governance System must still fully function.
"""
```

## 架构图

```
┌─────────────────────────────────────────────────────────┐
│   Reference Web Governance Console (可删除)            │
│   - 只显示数据                                           │
│   - 只调用 API                                           │
│   - 不包含任何业务逻辑                                   │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP API Calls
                     ▼
┌─────────────────────────────────────────────────────────┐
│   Governance Platform API v3 (不可删除)                │
│   - 所有治理逻辑在这里                                   │
│   - 状态机、校验、权限判断                                │
│   - 完整的治理系统                                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│   Runtime Engine                                        │
│   - 执行能力                                             │
│   - 服从治理决策                                         │
│   - 立即拒绝 FROZEN/DEPRECATED 能力                     │
└─────────────────────────────────────────────────────────┘
```

## API 端点

### Capability Governance

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/capabilities` | 获取所有能力列表 |
| GET | `/capabilities/{id}` | 获取单个能力详情 |
| GET | `/capabilities/{id}/health` | 获取能力健康度（API 计算） |
| GET | `/capabilities/{id}/signals` | 获取能力信号（API 提供） |
| GET | `/capabilities/{id}/lifecycle` | 获取能力生命周期（API 提供） |

### Governance Proposals

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/proposals` | 获取提案列表 |
| GET | `/proposals/{id}` | 获取单个提案详情 |
| POST | `/proposals/{id}/approve` | 批准提案 |
| POST | `/proposals/{id}/reject` | 拒绝提案 |

### Governance Decision Record

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/decisions` | 获取所有决策记录 |
| GET | `/decisions/{id}` | 获取单个决策记录 |

### V1: Observatory (只读)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/capabilities/risk-distribution` | 获取风险分布 |
| GET | `/signals` | 获取信号时间线 |
| GET | `/demand/missing-capabilities` | 获取缺失能力列表 |

## 使用示例

### 通过 curl

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
  -d '{"decided_by": "admin", "rationale": "Approved after review"}'
```

### 通过 Python API

```python
from governance.api_v3 import GovernanceAPIV3

api = GovernanceAPIV3()

# 获取能力列表
capabilities = api.get_capabilities()

# 获取能力健康度
health = api.get_capability_health("io.fs.read_file")

# 获取提案列表
proposals = api.get_proposals(status="PENDING")

# 批准提案
decision = api.approve_proposal(
    proposal_id="prop_123",
    decided_by="admin",
    rationale="Approved"
)
```

### 通过 Web Console

```bash
# 启动服务器
python3 src/governance/web/server.py

# 访问
http://localhost:8080
```

## 验收标准

### ✅ API 验收

1. **冻结 Capability → Runtime 立即拒绝执行**
   - 返回明确错误码（非异常）
   - 这是 v3 是否成功的生死线

2. **Proposal 审批 → 状态正确变更**
   - 提案状态从 PENDING → APPROVED
   - 能力状态正确变更

3. **每个决策 → GDR 可查询**
   - 每个 approve/reject 都生成 GDR
   - GDR 包含完整信息
   - GDR 可查询

### ✅ UI 验收

1. **UI 删除 → Governance API 仍可完整运作**
   - 删除 `src/governance/web/` 目录
   - API 仍然完整
   - 可以用 curl / Postman 完成所有治理动作

2. **UI 只是"看见 + 签字"**
   - UI 不计算任何数据
   - UI 不决定任何逻辑
   - UI 只调用 API

## 禁止事项

如果做了以下任何一条，视为架构失败：

❌ UI 直接写 Registry  
❌ UI 计算 Health / Risk  
❌ UI 决定 Capability 状态  
❌ UI 绕过 Proposal 流程  

## 最终验证

**如果所有 UI 消失，治理是否仍能完全且安全地通过 API 运行？**

**答案：是 ✅**

- 所有逻辑在 API 层
- UI 只是参考实现
- 可以用 curl / Postman 完成所有治理动作
- 可以用 CLI 工具完成所有治理动作
- 可以用第三方 UI 完成所有治理动作

## 文件结构

```
src/governance/
├── api_v3.py              # Governance API v3（完整治理系统）
├── platform_api.py        # 平台 API 门面
├── observatory/           # V1: Observatory APIs（只读）
├── decision_room/         # V2: Decision Room APIs（人工治理）
├── ingress/               # Capability Ingress（能力准入）
├── signals/               # Signal Bus（事实层）
├── evaluation/            # Health Authority（裁决层）
├── lifecycle/             # Lifecycle Service（主权执行层）
├── audit/                 # Audit Log（治理账本）
└── web/                   # Reference Web Console（可删除）
    ├── server.py          # HTTP 服务器
    └── static/            # 静态文件（HTML/JS）

docs/
└── governance-api-openapi.yaml  # OpenAPI 文档

tests/v3/
└── test_governance_v3_runtime_enforcement.py  # 验收测试
```

## 价值声明

UI 的价值只有一个：

> 让人类第一次"看见"AI 行为背后的权力结构。

不要多做。  
不要聪明。  
不要加权力。  

把秩序跑通。
