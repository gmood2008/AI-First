# Skill Facade Spec v1.0 — 实现说明

## 定位

Skill Facade 是「人类/LLM 友好」的能力入口描述层，将自然语言请求稳定、可治理地路由到 Capability / Workflow / Pack。Facade 只做入口，不执行、不持风险、不参与审批。

## 已实现内容

### 1. SkillFacadeSpec v1.0

- **路径**: `src/specs/skill_facade.py`
- **字段**: `name`, `version`, `description`, `triggers`, `examples`, `routes` (primary/fallback), `constraints`, `metadata`
- **序列化**: Pydantic，支持 `from_dict` / `from_yaml` / `to_yaml`，无执行逻辑

### 2. SkillFacadeRegistry

- **路径**: `src/runtime/registry/skill_facade_registry.py`
- **能力**:
  - `register_facade(spec)` → 仅 PROPOSED
  - `transition_state(name, version, new_state, ...)` → 治理驱动 PROPOSED → ACTIVE
  - `list_facades(state=None)`, `get_facade_by_trigger(text)`, `match(text)`
- **原则**: 不参与风险计算、不依赖 CapabilityRegistry，仅检索与提供路由信息

### 3. Runtime 路由增强

- **Facade 路由**: `src/runtime/facade_router.py`
  - `resolve_nl(text, facade_registry)` → `ResolvedRoute(route_type, ref, facade)`
  - `resolve_and_validate(text, facade_registry, pack_registry)` → 校验 pack ACTIVE 后返回路由
- **MCP 集成**: `src/runtime/mcp/server_v2.py`
  - 启动时从 `specs/facades/` 加载 Facade，并 `activate=True` 激活
  - `call_tool` 时：先 `resolve_nl(capability_id, facade_registry)`；若命中则返回 `status: facade_resolved` 及 `route_type`/`ref`，不执行能力

### 4. 示例 Facade

- **pdf** (Claude Skill 对标): `specs/facades/pdf.yaml`
  - 触发: "处理 PDF", "提取 PDF 表格", "extract tables from pdf" 等
  - 路由: primary → workflow `financial_report`, fallback → pack `document-processing-pack`
- **financial-analyst**: `specs/facades/financial-analyst.yaml`
  - 触发: "分析财报", "生成金融报告", "financial report" 等
  - 路由: primary → workflow `financial_report`, fallback → pack `financial-analyst`

### 5. CapabilityRegistry 与包结构

- `CapabilityRegistry` 已迁入 `src/runtime/registry/capability_registry.py`
- `from runtime.registry import CapabilityRegistry, SkillFacadeRegistry` 统一从 `src/runtime/registry/__init__.py` 导出，保持向后兼容

## 完成标志对照

| 要求 | 状态 |
|------|------|
| SkillFacadeSpec v1.0 可被加载 | ✅ `from_dict` / `from_yaml` |
| Facade 可被列出、冻结、下线 | ✅ `list_facades` + `transition_state` (FROZEN/DEPRECATED) |
| 自然语言输入可命中 Facade | ✅ `get_facade_by_trigger` / `match`，MCP 中先解析再执行 |
| Claude 的 pdf skill 可被等价替代 | ✅ pdf facade 示例 + 触发词 |
| Financial Skill Suite 可通过 Facade 触发 | ✅ financial-analyst facade 示例 |

## 本地完整验证

### 1. 安装依赖

在项目根目录执行（需联网）：

```bash
pip install -e .    # 注意：-e 与点号之间要有空格，即 -e .
# 或仅安装运行验证所需依赖：
pip install pyyaml pydantic
```

跑 pytest 时建议安装开发依赖：

```bash
pip install -e ".[dev]"
```

### 2. 运行验证脚本

```bash
cd /path/to/ai-first-runtime-master
python3 scripts/verify_skill_facade.py
```

若系统只有 `python3` 没有 `python`，请用 `python3`。`pip install -e .` 时注意 `-e` 后要有空格和点。

预期输出示例：

- `已加载并激活 N 个 Facade`
- `get_facade_by_trigger('分析财报') -> financial-analyst`
- `resolve_nl('extract tables from pdf') -> workflow ref=financial_report facade=pdf`
- `验证通过。`

### 3. 运行 pytest

```bash
pytest tests/v3/test_skill_facade.py -v
```

用例包括：YAML 加载 Spec、注册并激活 Facade、`get_facade_by_trigger` 命中、`resolve_nl` 命中与路由。

---

## 禁止事项（已遵守）

- Facade 不直接引用 Capability ID
- Facade 中不定义 risk / approval / 执行 prompt
- 治理保留在 Pack / Workflow / Capability 层
