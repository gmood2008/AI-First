# Internal PyPI 分发与升级 SOP（AI‑First Runtime）

本 SOP 面向公司内部不同项目团队，目标是：

- 以 **Python wheel** 形式分发 AI‑First Runtime（作为能力底座）
- 让消费方可通过 **版本号** 进行升级/回滚（而不是拷贝源码）

---

## 1. 推荐交付物

- **运行时包**：`ai-first-runtime`
  - 安装后可直接使用 `airun`（CLI）/ MCP Server / Python SDK
- **内置资产（随 wheel 一并交付）**
  - `capabilities/validated/stdlib/*.yaml`
  - `capabilities/validated/external/*.yaml`
  - `packs/**`
  - `specs/facades/*.yaml`

> 资产在安装后位于 `share/ai-first-runtime/...`，运行时会自动发现。

---

## 2. 发布方（能力底座团队）发布流程

### 2.1 版本策略

- 建议使用 SemVer：`MAJOR.MINOR.PATCH`
- 建议内部消费默认：`~=MAJOR.MINOR.0`（自动接收补丁）
- 破坏性变更只在 MAJOR 递增

### 2.2 构建 wheel

在仓库根目录执行：

```bash
python -m pip install -U pip setuptools wheel
python -m pip wheel . -w dist
```

产物：`dist/*.whl`

### 2.3 发布到 Internal PyPI（制品库）

根据你们公司制品库实现（Nexus/Artifactory/GitLab Package Registry）选择上传方式。

常见流程（示例）：

```bash
python -m pip install -U twine
python -m twine upload --repository-url <INTERNAL_PYPI_URL> dist/*.whl
```

> 认证信息建议使用 token / 环境变量注入，不要写入仓库。

### 2.4 发布后验证（强制）

运行 smoke：

```bash
python scripts/smoke_wheel_install.py
```

验收标准：

- wheel 安装后 `resolve_specs_dir()` 能定位到打包资产目录
- stdlib 能成功加载（输出 `STDLIB_LOADED`）

---

## 3. 消费方（业务项目团队）集成方式

### 3.1 requirements / Poetry 依赖

推荐：

- 保守（固定版本）：

```txt
ai-first-runtime==0.1.0
```

- 自动接收补丁（推荐内部使用）：

```txt
ai-first-runtime~=0.1.0
```

### 3.2 升级/回滚

- 升级：调整版本号（或 `pip install -U`）
- 回滚：回退版本号（或指定旧版本重新安装）

---

## 4. 支持边界（建议对内明确）

- **底座团队负责**：
  - `RuntimeEngine` / `WorkflowEngine` / `Audit` / `Undo` 的稳定性与兼容性
  - 资产发现与加载（`capabilities/packs/facades`）

- **业务团队负责**：
  - 自己的 workflow/pack/facade 设计（除非纳入底座统一维护）
  - 业务侧外部系统的凭据管理与合规

---

## 5. 常见问题

### 5.1 业务方需要自定义能力库或覆盖 assets

可以通过环境变量指定：

- `AI_FIRST_ASSETS_DIR=/path/to/assets_root`

其目录结构应包含：

- `capabilities/validated/stdlib/`
- `packs/`
- `specs/facades/`

### 5.2 specs 找不到

优先检查：

- 是否设置了 `AI_FIRST_SPECS_DIR`（会覆盖默认行为）
- wheel 是否正确包含 assets（跑 smoke 验证）

---

## 6. 相关文档

- `docs/partner_technical_evaluation.md`
- `ARCHITECTURE.md`
- `docs/INTEGRATION_GUIDE.md`
- `docs/EXTERNAL_CAPABILITY_INTEGRATION.md`
