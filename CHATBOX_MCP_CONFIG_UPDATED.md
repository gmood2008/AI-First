# Chatbox MCP Server 配置（已修复）

## 🔧 问题诊断

错误原因：MCP Server 找不到 `ai-first-specs` 目录。

## ✅ 解决方案

### 方案 1: 设置环境变量（推荐）

在 Chatbox 的"环境变量"字段中添加：

```
AI_FIRST_SPECS_DIR=/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/capabilities/validated/stdlib
```

### 方案 2: 使用完整配置

**命令字段：**
```
/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/venv/bin/python3 /Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/src/runtime/mcp/server_v2.py
```

**环境变量字段：**
```
AI_FIRST_SPECS_DIR=/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/capabilities/validated/stdlib
PYTHONPATH=/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/src
```

## 📋 完整配置信息

| 字段 | 值 |
|------|-----|
| **名称** | `AI-First` |
| **类型** | `本地 (stdio)` |
| **命令** | `/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/venv/bin/python3 /Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/src/runtime/mcp/server_v2.py` |
| **环境变量** | `AI_FIRST_SPECS_DIR=/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/capabilities/validated/stdlib`<br>`PYTHONPATH=/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/src` |

## 🔍 验证配置

配置完成后：

1. 点击"测试"按钮
2. 应该看到连接成功
3. 如果仍有错误，检查：
   - 环境变量路径是否正确
   - `capabilities/validated/stdlib` 目录是否存在
   - Python 虚拟环境是否正确

## 📁 目录结构说明

当前项目的 specs 目录结构：
```
ai-first-runtime-master/
├── capabilities/
│   └── validated/
│       ├── stdlib/          # 标准库能力（已创建）
│       └── generated/       # 自动生成的能力
│           └── net.github.get_repo.yaml
└── src/
    └── runtime/
        └── mcp/
            └── server_v2.py
```

## 🛠️ 故障排查

### 如果仍然报错

1. **检查目录是否存在**：
   ```bash
   ls -la /Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/capabilities/validated/stdlib
   ```

2. **手动创建目录**（如果需要）：
   ```bash
   mkdir -p /Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/capabilities/validated/stdlib
   ```

3. **验证环境变量**：
   在终端中测试：
   ```bash
   export AI_FIRST_SPECS_DIR=/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/capabilities/validated/stdlib
   echo $AI_FIRST_SPECS_DIR
   ```

4. **检查 Python 路径**：
   ```bash
   /Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/venv/bin/python3 --version
   ```

## 💡 提示

- 环境变量 `AI_FIRST_SPECS_DIR` 是必需的
- 如果 `stdlib` 目录为空也没关系，MCP Server 会扫描该目录
- 新生成的能力会放在 `capabilities/validated/generated/` 目录
