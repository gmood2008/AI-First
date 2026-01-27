# Chatbox MCP Server 配置

## 更新后的配置信息

### 基本信息
- **名称**: AI-First
- **类型**: 本地 (stdio)
- **命令**: 见下方

### 命令配置

将以下命令复制到 Chatbox 的"命令"字段：

```
/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/venv/bin/python3 /Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/src/runtime/mcp/server_v2.py
```

### 环境变量（可选）

如果需要设置环境变量，可以在"环境变量"字段中添加：

```
PYTHONPATH=/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/src
```

或者如果需要使用 DeepSeek：

```
DEEPSEEK_API_KEY=your_deepseek_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

### 配置步骤

1. 打开 Chatbox
2. 进入 MCP Server 配置
3. 编辑 "AI-First" 服务器
4. 将上面的命令复制到"命令"字段
5. （可选）添加环境变量
6. 点击"测试"验证连接
7. 点击"保存"

### 验证配置

配置完成后，可以通过以下方式验证：

1. 点击"测试"按钮
2. 检查是否显示连接成功
3. 尝试调用 AI-First 的能力

### 路径说明

- **旧路径**: `/Users/daniel/AI项目/AI-First/ai-first-runtime-2.0.0/`
- **新路径**: `/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/`

### 注意事项

- 确保虚拟环境已激活或使用完整路径
- 确保 `server_v2.py` 文件存在
- 如果遇到权限问题，检查文件是否可执行
- 如果使用相对路径，确保工作目录正确
