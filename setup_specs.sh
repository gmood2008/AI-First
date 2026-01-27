#!/bin/bash
# 设置 ai-first-specs 标准库

echo "=========================================="
echo "🔧 设置 AI-First Specs 标准库"
echo "=========================================="
echo ""

PROJECT_ROOT="/Users/daniel/AI项目/云端同步项目/ai-first-runtime-master"
SPECS_REPO="/Users/daniel/AI项目/云端同步项目/ai-first-specs"
SPECS_DIR="$SPECS_REPO/capabilities/validated/stdlib"
TARGET_DIR="$PROJECT_ROOT/capabilities/validated/stdlib"

echo "📋 配置信息:"
echo "  项目根目录: $PROJECT_ROOT"
echo "  Specs 仓库: $SPECS_REPO"
echo "  Specs 目录: $SPECS_DIR"
echo "  目标目录: $TARGET_DIR"
echo ""

# 检查 specs 仓库是否存在
if [ ! -d "$SPECS_REPO" ]; then
    echo "❌ ai-first-specs 仓库不存在"
    echo ""
    echo "💡 正在克隆仓库..."
    cd "$(dirname "$SPECS_REPO")" || exit 1
    git clone https://github.com/gmood2008/ai-first-specs.git
    if [ $? -eq 0 ]; then
        echo "✅ 仓库克隆成功"
    else
        echo "❌ 仓库克隆失败"
        exit 1
    fi
fi

# 检查 stdlib 目录
if [ ! -d "$SPECS_DIR" ]; then
    echo "❌ stdlib 目录不存在: $SPECS_DIR"
    exit 1
fi

# 统计文件数量
YAML_COUNT=$(find "$SPECS_DIR" -name "*.yaml" 2>/dev/null | wc -l | tr -d ' ')
echo "📦 找到 $YAML_COUNT 个标准库 YAML 文件"
echo ""

# 选项 1: 创建符号链接（推荐）
echo "选择配置方式:"
echo "  1. 创建符号链接（推荐，节省空间）"
echo "  2. 复制文件到项目目录"
echo "  3. 仅设置环境变量（不修改文件系统）"
echo ""
read -p "请选择 (1-3) [默认: 1]: " choice
choice=${choice:-1}

case $choice in
    1)
        echo ""
        echo "🔗 创建符号链接..."
        if [ -L "$TARGET_DIR" ]; then
            echo "  ⚠️  符号链接已存在，删除旧链接..."
            rm "$TARGET_DIR"
        elif [ -d "$TARGET_DIR" ] && [ "$(ls -A $TARGET_DIR 2>/dev/null)" ]; then
            echo "  ⚠️  目标目录已存在且有内容，备份为 stdlib.backup..."
            mv "$TARGET_DIR" "${TARGET_DIR}.backup"
        fi
        
        mkdir -p "$(dirname "$TARGET_DIR")"
        ln -s "$SPECS_DIR" "$TARGET_DIR"
        
        if [ $? -eq 0 ]; then
            echo "  ✅ 符号链接创建成功"
            echo "  $TARGET_DIR -> $SPECS_DIR"
        else
            echo "  ❌ 符号链接创建失败"
            exit 1
        fi
        ;;
    2)
        echo ""
        echo "📋 复制文件..."
        mkdir -p "$TARGET_DIR"
        cp -r "$SPECS_DIR"/*.yaml "$TARGET_DIR/" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "  ✅ 文件复制成功"
            echo "  📦 复制了 $(ls -1 "$TARGET_DIR"/*.yaml 2>/dev/null | wc -l | tr -d ' ') 个文件"
        else
            echo "  ❌ 文件复制失败"
            exit 1
        fi
        ;;
    3)
        echo ""
        echo "📝 环境变量配置:"
        echo ""
        echo "在 Chatbox 或 shell 中设置:"
        echo "  export AI_FIRST_SPECS_DIR=$SPECS_DIR"
        echo ""
        echo "或在 Chatbox 环境变量字段中添加:"
        echo "  AI_FIRST_SPECS_DIR=$SPECS_DIR"
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "✅ 设置完成"
echo "=========================================="
echo ""
echo "📋 验证配置:"
echo "  标准库路径: $SPECS_DIR"
echo "  YAML 文件数: $YAML_COUNT"
echo ""
echo "💡 下一步:"
echo "  1. 如果使用符号链接或复制，MCP Server 会自动找到标准库"
echo "  2. 如果使用环境变量，确保在 Chatbox 中设置了 AI_FIRST_SPECS_DIR"
echo "  3. 重启 MCP Server 以加载新的标准库能力"
