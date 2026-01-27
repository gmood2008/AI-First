# AI-First MCP Server 进程管理指南

## 当前状态

- ✅ **新版本进程**: 1 个 (ai-first-runtime-master)
- ⚠️ **旧版本进程**: 11 个 (ai-first-runtime-2.0.0)

## 快速清理命令

### 方法 1: 使用清理脚本（推荐）

```bash
./cleanup_old_processes.sh
```

### 方法 2: 一键清理所有旧版本进程

```bash
# 查找并终止所有旧版本进程
ps aux | grep "ai-first-runtime-2.0.0.*server_v2.py" | grep -v grep | awk '{print $2}' | xargs kill
```

### 方法 3: 强制终止（如果普通 kill 无效）

```bash
ps aux | grep "ai-first-runtime-2.0.0.*server_v2.py" | grep -v grep | awk '{print $2}' | xargs kill -9
```

## 查看进程状态

### 查看所有 AI-First 进程

```bash
ps aux | grep "server_v2.py" | grep -v grep
```

### 只查看新版本进程

```bash
ps aux | grep "ai-first-runtime-master.*server_v2.py" | grep -v grep
```

### 只查看旧版本进程

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

## 进程管理最佳实践

### 1. 定期清理

建议在更新配置后清理旧进程：

```bash
# 添加到 ~/.zshrc 或 ~/.bashrc
alias cleanup-ai-first='ps aux | grep "ai-first-runtime-2.0.0.*server_v2.py" | grep -v grep | awk "{print \$2}" | xargs kill 2>/dev/null; echo "✅ 已清理旧版本进程"'
```

### 2. 检查进程健康

```bash
# 检查新版本进程是否正常运行
ps aux | grep "ai-first-runtime-master.*server_v2.py" | grep -v grep && echo "✅ 新版本运行中" || echo "❌ 新版本未运行"
```

### 3. 重启新版本进程

如果需要重启新版本进程：

```bash
# 1. 终止当前新版本进程
ps aux | grep "ai-first-runtime-master.*server_v2.py" | grep -v grep | awk '{print $2}' | xargs kill

# 2. 在 Chatbox 中重新连接（会自动启动新进程）
```

## 常见问题

### Q: 为什么有这么多旧进程？

A: 可能是 Chatbox 多次尝试连接旧配置导致的。建议：
1. 更新 Chatbox 配置到新路径
2. 清理所有旧进程
3. 重启 Chatbox

### Q: 如何防止旧进程再次启动？

A: 
1. 确保 Chatbox 配置已更新到新路径
2. 删除或重命名旧版本的 server_v2.py（如果不再需要）
3. 定期运行清理脚本

### Q: 进程占用资源过多怎么办？

A: 
- 检查是否有僵尸进程：`ps aux | grep defunct`
- 使用 `top` 或 `htop` 查看资源占用
- 考虑限制 Chatbox 的连接数

## 监控脚本

创建一个监控脚本，定期检查进程状态：

```bash
#!/bin/bash
# monitor_ai_first.sh

NEW_COUNT=$(ps aux | grep "ai-first-runtime-master.*server_v2.py" | grep -v grep | wc -l | tr -d ' ')
OLD_COUNT=$(ps aux | grep "ai-first-runtime-2.0.0.*server_v2.py" | grep -v grep | wc -l | tr -d ' ')

echo "📊 AI-First MCP Server 进程状态"
echo "  新版本: $NEW_COUNT 个"
echo "  旧版本: $OLD_COUNT 个"

if [ "$OLD_COUNT" -gt 0 ]; then
    echo "⚠️  建议清理 $OLD_COUNT 个旧版本进程"
fi
```
