# 本地双目录同步机制（离线分发/升级）

当内部团队暂时不走 Internal PyPI，而是你本机两个目录之间“拷贝/同步交付”，推荐使用 `rsync` 机制。

---

## 1. 目标

- 你维护：源码仓库目录（例如）
  - `/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master`
- 对方接收：离线交付目录（例如）
  - `/Users/daniel/AI项目/Aegis/ai-first-runtime`

同步目标可以分为三类：

- **bundle**：同步 `dist/bundles/*.tar.gz`（离线交付包）与 wheel
- **assets**：同步明文资产（`capabilities/`、`packs/`、`specs/facades/`）
- **docs**：同步关键文档

---

## 2. 使用脚本（推荐）

仓库已提供脚本：`scripts/local_sync_offline_bundle.sh`

### 2.1 同步离线包（推荐交付方式）

```bash
bash scripts/local_sync_offline_bundle.sh \
  --src "/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master" \
  --dst "/Users/daniel/AI项目/Aegis/ai-first-runtime" \
  --mode bundle
```

### 2.2 同步明文资产

```bash
bash scripts/local_sync_offline_bundle.sh \
  --src "/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master" \
  --dst "/Users/daniel/AI项目/Aegis/ai-first-runtime" \
  --mode assets
```

### 2.3 同步关键文档

```bash
bash scripts/local_sync_offline_bundle.sh \
  --src "/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master" \
  --dst "/Users/daniel/AI项目/Aegis/ai-first-runtime" \
  --mode docs
```

---

## 3. 建议的升级节奏

- 日常升级：
  - 你发布新 wheel / 生成新 tar.gz
  - `--mode bundle` 同步
  - 对方解压/安装新版本，并跑一次 smoke

- 资产快速验证（不发版）：
  - `--mode assets` 同步
  - 对方设置 `AI_FIRST_ASSETS_DIR` 指向同步目录

---

## 4. 风险提示

- `rsync --delete` 会删除目标目录中脚本同步范围内的“多余文件”，避免脏文件导致误用。
- 如果对方目录里有业务方自定义内容，建议放在同步脚本未覆盖的路径中，或拆分到独立目录。
