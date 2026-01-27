# AI-First MCP Server 快速参考

## 🚀 快速命令

### 检查进程状态
```bash
./check_processes.sh
```

### 清理旧版本进程
```bash
./cleanup_old_processes.sh
```

### 一键清理（无确认）
```bash
ps aux | grep "ai-first-runtime-2.0.0.*server_v2.py" | grep -v grep | awk '{print $2}' | xargs kill
```

## 📋 Chatbox 配置

### 命令字段
```
/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/venv/bin/python3 /Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/src/runtime/mcp/server_v2.py
```

### 环境变量（可选）
```
PYTHONPATH=/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master/src
```

## 🔍 常用检查命令

### 查看所有 AI-First 进程
```bash
ps aux | grep "server_v2.py" | grep -v grep
```

### 只查看新版本
```bash
ps aux | grep "ai-first-runtime-master.*server_v2.py" | grep -v grep
```

### 只查看旧版本
```bash
ps aux | grep "ai-first-runtime-2.0.0.*server_v2.py" | grep -v grep
```

### 统计进程数量
```bash
# 新版本
ps aux | grep "ai-first-runtime-master.*server_v2.py" | grep -v grep | wc -l

# 旧版本
ps aux | grep "ai-first-runtime-2.0.0.*server_v2.py" | grep -v grep | wc -l
```

## 📚 相关文档

- `CHATBOX_MCP_CONFIG.md` - Chatbox 配置详细说明
- `PROCESS_MANAGEMENT.md` - 进程管理完整指南
- `cleanup_old_processes.sh` - 清理脚本
- `check_processes.sh` - 检查脚本

## ⚠️ 注意事项

1. **定期检查**: 建议每周运行一次 `./check_processes.sh`
2. **及时清理**: 发现旧进程立即清理，避免资源浪费
3. **配置更新**: 确保 Chatbox 使用新路径配置
4. **进程监控**: 正常情况下应该只有 1 个新版本进程运行

## 🆘 故障排查

### 新版本进程未运行
1. 检查 Chatbox 配置是否正确
2. 检查虚拟环境是否存在
3. 检查 server_v2.py 文件是否存在
4. 在 Chatbox 中重新连接 MCP Server

### 旧进程无法清理
```bash
# 强制终止
ps aux | grep "ai-first-runtime-2.0.0.*server_v2.py" | grep -v grep | awk '{print $2}' | xargs kill -9
```

### 进程占用资源过高
```bash
# 查看资源占用
ps aux | grep "server_v2.py" | grep -v grep | awk '{print $2, $3, $4, $11}'
```
