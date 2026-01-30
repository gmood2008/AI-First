# Chatbox 中配置 AI-First MCP（编辑 MCP Server）

按下面填写后点「测试」，通过再点「保存」。

---

## 名称

```
AI-First
```
（或任意名称，必填）

---

## 类型

选择：**本地 (stdio)**

---

## 命令（一行，中间用空格）

**必须写在一行里**，且**命令开头不能有任何多余字符**（如 `[object Object]`、`br`、换行等），否则会报 `spawn ENOENT`。

正确写法（建议从本仓库文件 `scripts/chatbox_mcp_command.txt` 里复制，避免粘贴进网页时带进 HTML）：

```
/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/venv/bin/python3 /Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/src/runtime/mcp/server_v2.py
```

- 若**没有 venv**，改成你本机已安装依赖的 Python，例如：  
  `/usr/local/bin/python3.11 /Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/src/runtime/mcp/server_v2.py`
- 不要写成两行；若从网页/文档复制后命令前出现 `[object Object] br` 等，**务必删掉**再保存。

---

## 环境变量（每行一个 KEY=VALUE）

```
AI_FIRST_SPECS_DIR=/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/capabilities/validated/stdlib
PYTHONPATH=/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/src
```

- 若 Chatbox 是「键值对」形式，则：  
  `AI_FIRST_SPECS_DIR` = `/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/capabilities/validated/stdlib`  
  `PYTHONPATH` = `/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/src`

---

## 若仍报错

1. **spawn [object ENOENT / 请确保您已安装以下命令: [object**  
   - 说明「命令」字段**开头被写入了多余内容**（如 `[object Object]`、`br`），系统在找名为 `[object` 的可执行文件所以报 ENOENT。  
   - 处理：在 Chatbox 里**清空命令框**，然后**只粘贴**下面这一整行（可从 `scripts/chatbox_mcp_command.txt` 打开复制）：  
     `/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/venv/bin/python3 /Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/src/runtime/mcp/server_v2.py`  
   - 不要从网页或富文本里复制，以免带进隐藏字符。

2. **Connection closed / 导入 runtime 失败**  
   - 已在本仓库修复：`server_v2.py` 会把项目 `src` 加入 `sys.path`，不依赖 Chatbox 是否传 `PYTHONPATH`。  
   - 请确认用的是**当前仓库最新代码**再点「测试」。

3. **找不到 venv**  
   - 命令里不要用 `venv/bin/python3`，改成系统或其它环境里的 Python，例如：  
     `which python3.11` 或 `which python3` 得到的路径。

4. **No module named 'yaml' / 'mcp'**  
   - 用该 Python 先安装依赖：  
     `pip install -e .` 或 `pip install pyyaml mcp`，再在 Chatbox 里用同一解释器路径。

5. **Specs directory not found**  
   - 确认目录存在：  
     `ls /Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/capabilities/validated/stdlib`  
   - 若不存在：  
     `mkdir -p /Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/capabilities/validated/stdlib`
