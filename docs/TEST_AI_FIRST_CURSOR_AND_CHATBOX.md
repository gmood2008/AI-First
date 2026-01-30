# AI-First 功能测试：Cursor 与 Chatbox

在 Cursor 和 Chatbox 中分别验证 ai-first MCP 的**能力调用**与**Skill Facade 语义路由**。

---

## 前置条件

1. **Cursor**：`~/.cursor/mcp.json` 中已配置 `ai-first-runtime`，且 MCP 状态正常（无报错）。
2. **Chatbox**：已配置 AI-First MCP（命令、环境变量正确），点「测试」通过并已保存。
3. 本仓库已安装依赖：`pip install -e .`（或至少 `pyyaml`、`mcp` 等）。

---

## 一、Cursor 中测试

### 1. 确认 MCP 已连接

- 打开 Cursor **Settings → MCP**，确认 `ai-first-runtime` 为绿色/正常。
- 或在 Composer / Chat 中，看是否能看到与 ai-first 相关的工具（名称里可能带 `io.`、`sys.` 等）。

### 2. 测试「列出能力 / 工具」

在 **Composer** 或 **Chat** 中输入（任选一种说法）：

- “列出 ai-first 提供的所有工具。”
- “List all tools from the ai-first MCP server.”

**预期**：能列出若干工具，例如 `io.fs.read_file`、`io.fs.write_file`、`sys.undo` 等（具体以你当前加载的 specs 为准）。

### 3. 测试「能力调用」

在对话中请求执行一个**只读**能力，例如：

- “用 ai-first 读一下当前项目根目录下的 README.md 内容。”
- “Call the ai-first tool io.fs.read_file to read the file README.md in the project root.”

**预期**：AI 会调用 ai-first 的读文件工具，并返回文件内容或结构化结果。

### 4. 测试「Skill Facade 语义路由」（ai-first 独有）

请求用**自然语言/触发词**触发 Facade，而不是直接传 capability id：

- “用 ai-first 执行「分析财报」。”
- “Call the ai-first tool with name 「extract tables from pdf」 and no arguments.”

**预期**：返回内容里包含 `facade_resolved`、`route_type`（如 `workflow`）、`ref`（如 `financial_report`）、`facade_name`（如 `pdf` 或 `financial-analyst`），且**不会**真的去读 PDF，只做路由说明。

---

## 二、Chatbox 中测试

### 1. 确认 MCP 已连接

- 在 Chatbox 的 MCP 配置里点「测试」，应显示连接成功。
- 若 Chatbox 有「工具列表」或「已连接服务」等入口，确认能看到 ai-first 相关工具。

### 2. 测试「列出能力 / 工具」（含财报分析工具）

在对话里输入：

- “列出 ai-first 提供的所有工具。”
- “List all MCP tools from ai-first.”

**预期**：能列出 ai-first 暴露的工具，**必须包含财报分析相关**：
- `io.pdf.extract_table`（从 PDF 提取表格）
- `math.pandas.calculate`（Pandas 指标计算）
- 以及 `io.fs.read_file`、`io.fs.write_file`、`sys.undo` 等。

**若看不到 `io.pdf.extract_table` / `math.pandas.calculate`**：请将环境变量 `AI_FIRST_SPECS_DIR` 指向**本仓库**的 specs 目录，例如：
`/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/capabilities/validated/stdlib`  
（或你本机上的 `ai-first-runtime-master/capabilities/validated/stdlib`）。MCP 工具列表与该目录下的 YAML 一一对应，只有该目录包含 `io_pdf_extract_table.yaml` 和 `math_pandas_calculate.yaml` 时，财报分析工具才会出现在列表中。

### 3. 测试「能力调用」

在对话里请求执行一个只读能力，例如：

- “用 ai-first 读一下项目里的 README.md。”
- “使用 ai-first 的 io.fs.read_file 读取 README.md。”

**预期**：AI 通过 ai-first 调用读文件，并展示内容或结果。

### 4. 测试「Skill Facade 语义路由」

用自然语言/触发词作为「工具名」来触发：

- “用 ai-first 执行「分析财报」。”
- “调用 ai-first，工具名用「extract tables from pdf」，不传参数。”

**预期**：返回中包含 `facade_resolved`、`route_type`、`ref`、`facade_name`，表示命中 Facade 并解析到 workflow/pack，而不是执行具体 capability。

---

## 三、本地 CLI 快速自检（可选）

在**项目根目录**执行，用于确认服务能启动、Facade 能加载，再去做 Cursor/Chatbox 测试：

```bash
# 1. 依赖与 Facade 校验
python3 scripts/verify_skill_facade.py

# 2. MCP 服务能否创建（需同目录下 capabilities/validated/stdlib 存在）
export AI_FIRST_SPECS_DIR="$(pwd)/capabilities/validated/stdlib"
export PYTHONPATH="$(pwd)/src"
python3 scripts/test_mcp_startup.py
```

两项都通过后再在 Cursor / Chatbox 里做上述界面测试。

---

## 四、结果对照表

| 测试项           | Cursor 预期                    | Chatbox 预期                   |
|------------------|--------------------------------|--------------------------------|
| MCP 连接         | 设置里 ai-first 正常           | 测试按钮通过                   |
| 列出工具         | 能列出 io./sys. 等工具         | 能列出 ai-first 工具           |
| **财报分析工具** | 列表中含 io.pdf.extract_table、math.pandas.calculate | 同上（依赖 AI_FIRST_SPECS_DIR 指向本仓库 capabilities/validated/stdlib） |
| 能力调用         | 能读文件并返回内容             | 能读文件并返回内容             |
| Skill Facade     | 返回含 facade_resolved 的路由  | 返回含 facade_resolved 的路由  |

若某一步失败，可先跑第三节的 CLI 自检，再检查 Cursor/Chatbox 的 MCP 配置（命令、环境变量、Python 路径）是否与文档一致。
