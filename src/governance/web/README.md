# Reference Web Governance Console

## 核心原则

> **If the Web Console disappears,**
> **the Governance System must still fully function.**

这是一个 Reference Client，类似 Kubernetes Dashboard，而不是 Admin Panel。

## 架构

```
┌─────────────────────────────────────┐
│   Reference Web Console (UI)        │
│   - 只显示数据                       │
│   - 只调用 API                       │
│   - 可删除                           │
└──────────────┬──────────────────────┘
               │ HTTP API Calls
               ▼
┌─────────────────────────────────────┐
│   Governance Platform API v3        │
│   - 所有逻辑在这里                   │
│   - 状态机、校验、权限判断            │
│   - 不可删除                         │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Runtime Engine                    │
│   - 执行能力                         │
│   - 服从治理决策                     │
└─────────────────────────────────────┘
```

## 运行

```bash
# 启动 Web Console 服务器
python3 src/governance/web/server.py

# 访问
http://localhost:8080
```

## 功能

### V1: Observatory（只读）

- ✅ Capability Health Map
- ✅ Risk Level Distribution
- ✅ Signal Timeline
- ✅ Capability Demand Radar

**约束**:
- ❌ 不允许任何写操作
- ❌ 不允许隐藏数据
- ❌ 所有数据来自 API

### V2: Decision Room（审批）

- ✅ Proposal Queue
- ✅ Proposal Detail（Evidence / Diff）
- ✅ Approve / Reject（带 comment）

**约束**:
- UI 不得决定审批逻辑
- UI 只调用 `/approve` 和 `/reject`
- 审批完成后，UI 必须显示生成的 GDR

### V3: Ecosystem Ops（运营指标）

- ✅ Capability Adoption
- ✅ Lifecycle Funnel
- ✅ Failure / Rollback Rate

**约束**:
- ❌ 不允许 UI 中创建 Capability
- ❌ 不允许 UI 中导入第三方能力
- ❌ 不允许 UI 中直接修改 Risk / Policy

## 禁止事项

❌ UI 直接写 Registry  
❌ UI 计算 Health / Risk  
❌ UI 决定 Capability 状态  
❌ UI 绕过 Proposal 流程  

## 删除 UI 后

如果删除整个 `src/governance/web/` 目录：

- ✅ Governance API 仍然完整
- ✅ 可以用 curl / Postman 完成所有治理动作
- ✅ 可以用 CLI 工具完成所有治理动作
- ✅ 可以用第三方 UI 完成所有治理动作

## 价值

UI 的价值只有一个：

> 让人类第一次"看见"AI 行为背后的权力结构。

不要多做。  
不要聪明。  
不要加权力。  

把秩序跑通。
