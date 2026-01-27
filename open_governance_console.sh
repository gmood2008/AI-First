#!/bin/bash

# 快速打开 Governance Console

echo "================================================================================
🌐 打开 Governance Console
================================================================================
"

cd "$(dirname "$0")"

# 检查服务器是否已运行
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "✅ 服务器已在运行"
    PID=$(lsof -ti:8080)
    echo "   进程 ID: $PID"
else
    echo "🚀 启动服务器..."
    python3 src/governance/web/server.py > /tmp/governance_console.log 2>&1 &
    PID=$!
    echo $PID > /tmp/governance_console.pid
    sleep 2
    
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ 服务器启动成功 (PID: $PID)"
    else
        echo "❌ 服务器启动失败"
        echo "查看日志: cat /tmp/governance_console.log"
        exit 1
    fi
fi

echo ""
echo "================================================================================
📋 访问地址
================================================================================
"
echo "🌐 http://localhost:8080"
echo ""
echo "在浏览器中打开上述地址即可查看 Governance Console"
echo ""
echo "================================================================================
📋 功能说明
================================================================================
"
echo "V1: Observatory（只读）"
echo "  - Capability Health Map - 能力健康度地图"
echo "  - Risk Level Distribution - 风险级别分布"
echo "  - Signal Timeline - 信号时间线"
echo "  - Capability Demand Radar - 能力需求雷达"
echo ""
echo "V2: Decision Room（审批）"
echo "  - Proposal Queue - 提案队列"
echo "  - Proposal Detail - 提案详情"
echo "  - Approve / Reject - 批准/拒绝"
echo ""
echo "V3: Ecosystem Ops（运营指标）"
echo "  - Capability Adoption - 能力采用率"
echo "  - Lifecycle Funnel - 生命周期漏斗"
echo ""
echo "================================================================================
🛑 停止服务器
================================================================================
"
echo "停止服务器: kill $PID"
echo "或运行: ./stop_governance_console.sh"
echo ""

# 尝试自动打开浏览器（macOS）
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🌐 正在打开浏览器..."
    open http://localhost:8080 2>/dev/null || echo "请手动在浏览器中打开: http://localhost:8080"
fi
