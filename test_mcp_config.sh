#!/bin/bash
# 测试 MCP Server 配置

echo "=========================================="
echo "🔍 测试 MCP Server 配置"
echo "=========================================="
echo ""

PROJECT_ROOT="/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master"
SPECS_DIR="$PROJECT_ROOT/capabilities/validated/stdlib"
PYTHON_BIN="$PROJECT_ROOT/venv/bin/python3"
SERVER_SCRIPT="$PROJECT_ROOT/src/runtime/mcp/server_v2.py"

echo "1️⃣ 检查目录结构..."
echo "   项目根目录: $PROJECT_ROOT"
if [ -d "$PROJECT_ROOT" ]; then
    echo "   ✅ 项目目录存在"
else
    echo "   ❌ 项目目录不存在"
    exit 1
fi

echo ""
echo "2️⃣ 检查 specs 目录..."
echo "   Specs 目录: $SPECS_DIR"
if [ -d "$SPECS_DIR" ]; then
    echo "   ✅ Specs 目录存在"
    echo "   目录内容:"
    ls -la "$SPECS_DIR" | tail -n +2 | awk '{print "      " $0}'
else
    echo "   ❌ Specs 目录不存在"
    echo "   💡 创建目录..."
    mkdir -p "$SPECS_DIR"
    echo "   ✅ 已创建"
fi

echo ""
echo "3️⃣ 检查 Python 环境..."
if [ -f "$PYTHON_BIN" ]; then
    echo "   ✅ Python 存在: $PYTHON_BIN"
    PYTHON_VERSION=$("$PYTHON_BIN" --version 2>&1)
    echo "   版本: $PYTHON_VERSION"
else
    echo "   ❌ Python 不存在: $PYTHON_BIN"
    exit 1
fi

echo ""
echo "4️⃣ 检查 Server 脚本..."
if [ -f "$SERVER_SCRIPT" ]; then
    echo "   ✅ Server 脚本存在: $SERVER_SCRIPT"
else
    echo "   ❌ Server 脚本不存在: $SERVER_SCRIPT"
    exit 1
fi

echo ""
echo "5️⃣ 检查环境变量配置..."
export AI_FIRST_SPECS_DIR="$SPECS_DIR"
export PYTHONPATH="$PROJECT_ROOT/src"

if [ -n "$AI_FIRST_SPECS_DIR" ]; then
    echo "   ✅ AI_FIRST_SPECS_DIR: $AI_FIRST_SPECS_DIR"
else
    echo "   ⚠️  AI_FIRST_SPECS_DIR 未设置"
fi

if [ -n "$PYTHONPATH" ]; then
    echo "   ✅ PYTHONPATH: $PYTHONPATH"
else
    echo "   ⚠️  PYTHONPATH 未设置"
fi

echo ""
echo "6️⃣ 测试导入（快速检查）..."
cd "$PROJECT_ROOT" || exit 1
if "$PYTHON_BIN" -c "import sys; sys.path.insert(0, 'src'); from runtime.mcp.specs_resolver import resolve_specs_dir; print('✅ Specs resolver 可以导入')" 2>&1; then
    echo "   ✅ 模块导入成功"
else
    echo "   ⚠️  模块导入失败（可能需要安装依赖）"
fi

echo ""
echo "=========================================="
echo "📋 Chatbox 配置信息"
echo "=========================================="
echo ""
echo "命令字段："
echo "$PYTHON_BIN $SERVER_SCRIPT"
echo ""
echo "环境变量字段（每行一个）："
echo "AI_FIRST_SPECS_DIR=$SPECS_DIR"
echo "PYTHONPATH=$PROJECT_ROOT/src"
echo ""
echo "=========================================="
echo "✅ 配置检查完成"
echo "=========================================="
