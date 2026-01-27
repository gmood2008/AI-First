#!/bin/bash
# 清理旧版本的 AI-First MCP Server 进程

echo "=========================================="
echo "🧹 清理旧版本 AI-First MCP Server 进程"
echo "=========================================="
echo ""

# 查找旧版本进程
OLD_PIDS=$(ps aux | grep "ai-first-runtime-2.0.0.*server_v2.py" | grep -v grep | awk '{print $2}')

if [ -z "$OLD_PIDS" ]; then
    echo "✅ 没有找到旧版本进程"
    exit 0
fi

echo "📋 找到以下旧版本进程："
ps aux | grep "ai-first-runtime-2.0.0.*server_v2.py" | grep -v grep | awk '{printf "  PID: %-8s 启动时间: %s\n", $2, $9}'
echo ""

# 询问确认
read -p "是否要终止这些进程？(y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 已取消"
    exit 0
fi

# 终止进程
KILLED=0
for PID in $OLD_PIDS; do
    if kill "$PID" 2>/dev/null; then
        echo "✅ 已终止进程 PID: $PID"
        KILLED=$((KILLED + 1))
    else
        echo "⚠️  无法终止进程 PID: $PID (可能已结束)"
    fi
done

echo ""
echo "=========================================="
echo "✅ 清理完成！共终止 $KILLED 个进程"
echo "=========================================="
echo ""
echo "📌 当前运行的新版本进程："
ps aux | grep "ai-first-runtime-master.*server_v2.py" | grep -v grep || echo "  (无)"
