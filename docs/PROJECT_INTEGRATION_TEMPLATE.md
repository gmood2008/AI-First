# 项目接入模板（AI‑First Runtime）

本文档是给内部项目团队的“复制即用”接入模板。

---

## 1. 适用场景

- 你们希望在项目中使用 AI‑First Runtime 作为“能力执行底座”（CLI / MCP / SDK）。
- 你们希望后续可通过版本号升级/回滚，而不是拷贝源码。

---

## 2. 安装方式（推荐优先级）

### 2.1 内部 PyPI（推荐）

#### A. 稳定模式（固定版本）

```txt
ai-first-runtime==0.1.0
```

#### B. 内部推荐模式（自动接收补丁）

```txt
ai-first-runtime~=0.1.0
```

说明：

- `~=0.1.0` 会自动接收 `0.1.x` 的补丁升级（bugfix/资产修正），避免“升级不同步”。
- `MINOR`/`MAJOR` 仍建议显式评估后升级。

### 2.2 离线交付包（tar.gz）

适用于无法访问 Internal PyPI 的场景。

- 解压你收到的 `ai-first-runtime-offline-bundle_*.tar.gz`
- 按包内 `README_OFFLINE_INSTALL.md` 安装

---

## 3. 初始化与验证（最小闭环）

### 3.1 创建隔离环境

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
```

### 3.2 安装

- 内部 PyPI：

```bash
python -m pip install ai-first-runtime~=0.1.0
```

- 离线包：

```bash
python -m pip install wheels/ai_first_runtime-*.whl
```

### 3.3 运行 smoke（推荐）

如果你拿到离线包，或你在做升级评估，请执行：

```bash
python scripts/smoke_wheel_install.py
```

验收标准：

- 输出包含 `RESOLVED_SPECS_DIR= .../share/ai-first-runtime/...`
- 输出 `✅ smoke_wheel_install passed`

---

## 4. 资产覆盖（可选，二开/查看/临时修复）

默认情况下，运行时会优先使用 wheel 内置的 `share/ai-first-runtime` 资产。

如需使用你们自己的资产目录（例如 fork 后自定义 packs/facades/stdlib yaml），设置：

```bash
export AI_FIRST_ASSETS_DIR=/absolute/path/to/assets_root
```

目录结构要求：

- `capabilities/validated/stdlib/`
- `capabilities/validated/external/`（如需要）
- `packs/`
- `specs/facades/`

建议：

- 资产覆盖用于 PoC/灰度/紧急修复。
- 需要长期生效的变更，应回收至底座团队并通过发版同步。

---

## 5. 升级与回滚（版本驱动）

### 5.1 升级

- 固定版本：修改版本号并重新安装

```bash
python -m pip install --upgrade "ai-first-runtime==0.1.2"
```

- 自动补丁：

```bash
python -m pip install --upgrade "ai-first-runtime~=0.1.0"
```

### 5.2 回滚

```bash
python -m pip install --force-reinstall "ai-first-runtime==0.1.0"
```

---

## 6. 推荐团队内约定（强烈建议）

- 依赖策略：默认使用 `~=0.1.0`（补丁自动同步）。
- CI 规则：升级后必须跑一次 smoke 或最小 workflow 验证。
- 支持边界：资产/能力的“生产可用版本”以底座团队发版为准。
