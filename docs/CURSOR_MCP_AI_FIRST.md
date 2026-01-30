# Cursor 中配置 ai-first MCP

## 当前状态检查

Cursor 项目下 MCP 状态在：  
`~/.cursor/projects/<project-id>/mcps/user-ai-first-runtime/STATUS.md`  
若显示 "The MCP server errored"，按下面步骤排查。

## 1. 确保 specs 目录存在

MCP 启动时会解析 `AI_FIRST_SPECS_DIR` 或查找兄弟目录 `ai-first-specs`。本地没有 specs 时，使用项目内空目录即可：

```bash
# 在项目根目录
mkdir -p capabilities/validated/stdlib
```

项目已包含 `capabilities/validated/stdlib/`（可为空）。

## 2. 本地测试 MCP 能否启动

在项目根目录执行（先设置环境变量再运行脚本）：

```bash
export AI_FIRST_SPECS_DIR="$(pwd)/capabilities/validated/stdlib"
export PYTHONPATH="$(pwd)/src"
python3 scripts/test_mcp_startup.py
```

若输出 `OK: Server 创建成功`，说明同一套环境在 Cursor 里也应能启动 MCP。

## 3. Cursor MCP 配置

在 Cursor 中：**Settings → MCP → 添加 / 编辑 ai-first-runtime**。

### 方式 A：使用项目内 Python（推荐）

- **Command**（命令）：用安装过依赖的 Python 解释器运行 `server_v2.py`，例如：

  ```text
  /usr/local/bin/python3.11 /Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/src/runtime/mcp/server_v2.py
  ```

  若用 venv，则：

  ```text
  /Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/venv/bin/python3 /Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/src/runtime/mcp/server_v2.py
  ```

- **Env**（环境变量，若有该字段则填）：

  ```text
  AI_FIRST_SPECS_DIR=/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/capabilities/validated/stdlib
  PYTHONPATH=/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/src
  ```

把路径换成你本机实际的项目根路径。

### 方式 B：Cursor MCP 的 JSON 配置示例

若 Cursor 使用 JSON 配置 MCP，可参考（路径请按本机修改）：

```json
{
  "mcpServers": {
    "ai-first-runtime": {
      "command": "/usr/local/bin/python3.11",
      "args": [
        "/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/src/runtime/mcp/server_v2.py"
      ],
      "env": {
        "AI_FIRST_SPECS_DIR": "/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/capabilities/validated/stdlib",
        "PYTHONPATH": "/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/src"
      }
    }
  }
}
```

## 4. 常见错误与处理

| 现象 | 处理 |
|------|------|
| FileNotFoundError: specs directory not found | 设置 `AI_FIRST_SPECS_DIR` 为已存在的目录（如 `capabilities/validated/stdlib`），或先 `mkdir -p capabilities/validated/stdlib` |
| ModuleNotFoundError: No module named 'mcp' | 安装 MCP 依赖：`pip install mcp`，或使用已安装该依赖的 Python/venv |
| ModuleNotFoundError: No module named 'runtime' | 设置 `PYTHONPATH` 为项目下的 `src` 目录（绝对路径） |
| zsh: command not found: python | Cursor 启动命令里用 `python3` 或完整路径（如 `/usr/local/bin/python3.11`） |

## 5. 验证

1. 保存 MCP 配置后，在 Cursor 中查看 MCP 状态是否变为正常。
2. 在对话或 Composer 中尝试调用 ai-first 提供的工具（如 `io.fs.read_file` 等），能列出并调用即表示配置成功。
