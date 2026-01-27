#!/bin/bash

# 停止 Governance Console 服务器

echo "================================================================================
🛑 停止 Governance Console 服务器
================================================================================
"

# 查找并停止进程
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    PID=$(lsof -ti:8080)
    echo "找到运行中的服务器 (PID: $PID)"
    kill $PID 2>/dev/null
    sleep 1
    
    if ps -p $PID > /dev/null 2>&1; then
        echo "强制停止..."
        kill -9 $PID 2>/dev/null
    fi
    
    echo "✅ 服务器已停止"
else
    echo "⚠️  没有运行中的服务器"
fi

# 清理 PID 文件
rm -f /tmp/governance_console.pid

echo ""
