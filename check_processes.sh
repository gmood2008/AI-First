#!/bin/bash
# 快速检查 AI-First MCP Server 进程状态

echo "=========================================="
echo "🔍 AI-First MCP Server 进程状态检查"
echo "=========================================="
echo ""

# 检查新版本进程
echo "📌 新版本进程 (ai-first-runtime-master):"
NEW_PIDS=$(ps aux | grep "ai-first-runtime-master.*server_v2.py" | grep -v grep | awk '{print $2}')
if [ -z "$NEW_PIDS" ]; then
    echo "  ⚠️  未运行"
    echo "  💡 提示: 请在 Chatbox 中连接 MCP Server"
else
    NEW_COUNT=$(echo "$NEW_PIDS" | wc -l | tr -d ' ')
    echo "  ✅ 运行中 ($NEW_COUNT 个进程)"
    echo "$NEW_PIDS" | while read pid; do
        ps -p "$pid" -o pid,etime,pcpu,pmem,command 2>/dev/null | tail -1 | awk '{printf "    PID: %-8s  运行时间: %-12s  CPU: %5s%%  MEM: %5s%%\n", $1, $2, $3, $4}'
    done
fi

echo ""

# 检查旧版本进程
echo "📌 旧版本进程 (ai-first-runtime-2.0.0):"
OLD_PIDS=$(ps aux | grep "ai-first-runtime-2.0.0.*server_v2.py" | grep -v grep | awk '{print $2}')
if [ -z "$OLD_PIDS" ]; then
    echo "  ✅ 已清理"
else
    OLD_COUNT=$(echo "$OLD_PIDS" | wc -l | tr -d ' ')
    echo "  ⚠️  发现 $OLD_COUNT 个旧进程（建议清理）"
    echo "$OLD_PIDS" | while read pid; do
        ps -p "$pid" -o pid,etime,pcpu,pmem 2>/dev/null | tail -1 | awk '{printf "    PID: %-8s  运行时间: %-12s  CPU: %5s%%  MEM: %5s%%\n", $1, $2, $3, $4}'
    done
    echo ""
    echo "  💡 清理命令: ./cleanup_old_processes.sh"
fi

echo ""
echo "=========================================="
