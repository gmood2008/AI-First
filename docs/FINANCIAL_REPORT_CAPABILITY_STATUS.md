# 财报分析能力现状

## 一句话结论

**入口、流程与三个 Capability 均已具备**：可以说「分析财报」并走完「从 PDF 提取表格 → 用 Pandas 计算 → 写报告」的流水线。`io.pdf.extract_table` 与 `math.pandas.calculate` 已实现并接入 stdlib 加载。

---

## 已有部分 ✅

| 层级 | 内容 | 位置 |
|------|------|------|
| **Skill Facade（入口）** | 自然语言「分析财报」「生成金融报告」→ 路由到 workflow / pack | `specs/facades/financial-analyst.yaml`、`pdf.yaml` |
| **Pack 定义** | financial-analyst-pack，包含 workflow 与能力列表 | `packs/financial-analyst/pack.yaml` |
| **Workflow 定义** | financial_report：extract_tables → calculate_metrics → render_report | `packs/financial-analyst/financial_report.yaml` |
| **Capability** | `io.pdf.extract_table`、`math.pandas.calculate`、`io.fs.write_file` | stdlib 已实现并注册 |

在 Cursor/Chatbox 里说「分析财报」或调用对应工具名，会得到 **facade_resolved**，并看到 `route_type: workflow`、`ref: financial_report`，说明**入口和路由**是通的。

---

## 三个 Capability 现状 ✅

Workflow `financial_report` 依赖三个能力，均已实现：

| Capability | 用途 | 现状 |
|------------|------|------|
| `io.pdf.extract_table` | 从 PDF 提取表格 | ✅ Spec：`capabilities/validated/stdlib/io_pdf_extract_table.yaml`；Handler：`src/runtime/stdlib/pdf_handlers.py`（依赖 pdfplumber） |
| `math.pandas.calculate` | 用 Pandas 做指标计算 | ✅ Spec：`capabilities/validated/stdlib/math_pandas_calculate.yaml`；Handler：`src/runtime/stdlib/pandas_handlers.py`（依赖 pandas） |
| `io.fs.write_file` | 写出分析报告文件 | ✅ 已有；支持 `path` 与 `file_path` 参数兼容 workflow |

---

## 依赖与 Spec 目录

- **运行时依赖**：`requirements.txt` 已增加 `pdfplumber>=0.10.0`、`pandas>=2.0`。安装：`pip install -e .` 或 `pip install pdfplumber pandas`。
- **Spec 目录**：MCP 会优先解析 `AI_FIRST_SPECS_DIR`；未设置时，会回退到项目内 `capabilities/validated/stdlib`（若存在），其中包含 `io_pdf_extract_table.yaml` 与 `math_pandas_calculate.yaml`。

---

## 当前可做的验证

- **Facade / 路由**：在 Cursor 或 Chatbox 中说「用 ai-first 执行：分析财报」，应返回 `facade_resolved`、`ref: financial_report`。  
- **单能力**：可单独测 `io.pdf.extract_table`、`math.pandas.calculate`、`io.fs.write_file`。  
- **完整 workflow**：在 Pack 为 ACTIVE、Workflow 可被调用的前提下，可从「分析财报」入口端到端跑通：PDF 路径 → 提取表格 → 计算指标 → 写出报告。
