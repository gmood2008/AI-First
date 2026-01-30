# 明文资产模式接入指南（深度集成场景）

本指南面向“对方采用明文资产（YAML/pack/facade）模式，而非完全依赖 wheel 内置资产”的集成方式。

---

## 1. 结论：推荐的组合方式

即使对方选择“明文资产模式”，也强烈建议：

- **运行时代码**：仍通过 `pip install ai-first-runtime`（wheel）管理版本
- **运行时资产**：通过 `AI_FIRST_ASSETS_DIR=<assets_root>` 指向对方维护/同步的明文资产目录

原因：

- 代码升级/回滚通过版本号可控
- 资产可独立调整，便于深度集成与差异化
- 二者解耦后更易定位问题（是代码问题还是资产问题）

---

## 2. 资产目录结构（assets_root）

对方的 `assets_root` 目录必须包含（相对路径）：

- `capabilities/validated/stdlib/`
- `capabilities/validated/external/`（如需要）
- `packs/`
- `specs/facades/`

示例：

```text
assets_root/
  capabilities/
    validated/
      stdlib/
        *.yaml
      external/
        *.yaml
  packs/
    <pack-id>/
      pack.yaml
      workflows/
        *.yaml
  specs/
    facades/
      *.yaml
```

---

## 3. 启用明文资产模式

在对方环境中设置：

```bash
export AI_FIRST_ASSETS_DIR=/absolute/path/to/assets_root
```

说明：

- 运行时会优先使用 wheel 内置的 `share/ai-first-runtime` 资产；
- 但当 `AI_FIRST_ASSETS_DIR` 指向存在的目录时，会改用该目录作为资产根。

---

## 4. 版本与兼容性策略（非常关键）

明文资产模式的核心风险是：“资产变化导致运行时代码不兼容”。为了让升级可以同步且可控，建议对方采用 **版本组合锁定**：

- **代码版本**：`ai-first-runtime==X.Y.Z`
- **资产版本**：一个可追溯版本（Git commit / tag / zip 的版本号）

推荐做法：

- 在资产根目录放一个版本文件（由对方或底座团队生成），例如：
  - `assets_root/ASSETS_VERSION.txt`
  - 或 `assets_root/assets.manifest.json`

并在对方 CI 中记录：

- 本次上线的 `runtime_version`
- 本次上线的 `assets_version`

---

## 5. 升级/回滚 SOP（明文资产模式）

### 5.1 升级代码（runtime）

```bash
python -m pip install --upgrade "ai-first-runtime==X.Y.Z"
```

### 5.2 升级资产（assets_root）

- 通过 Git pull / rsync / 解压覆盖更新 `assets_root`
- 更新后跑一次最小验证（见 6）

### 5.3 回滚

- 回滚代码：重新安装旧版本 wheel
- 回滚资产：切回旧的 assets commit/tag 或恢复旧目录快照

建议回滚优先级：

- 如果是功能性问题且与资产相关，先回滚资产
- 如果是运行时行为变化，回滚代码版本

---

## 6. 最小验证（推荐对方 CI 强制执行）

在对方项目中跑两类验证：

- **代码安装验证**：确认 runtime 可 import
- **资产加载验证**：确认 `AI_FIRST_ASSETS_DIR` 生效且能加载 stdlib/packs/facades

如果对方拿的是离线 bundle，可直接使用 bundle 内的 smoke 脚本。

---

## 7. 本地双目录同步（离线交付/升级同步）

如果你们在同一台机器上维护两个目录（例如你这边的源码仓库与对方集成目录），推荐使用：

- `docs/LOCAL_FOLDER_SYNC_GUIDE.md`
- `scripts/local_sync_offline_bundle.sh`

常用：

- `--mode assets`：同步明文资产目录
- `--mode bundle`：同步离线 tar.gz 交付包

---

## 8. 推荐边界（建议对内明确）

- 底座团队负责：
  - 代码版本兼容性承诺（SemVer）
  - 资产 schema 的演进策略（CapabilitySpec / pack.yaml / facade spec）

- 深度集成团队负责：
  - 明文资产的维护与变更评审
  - 与业务系统的集成与凭据合规
