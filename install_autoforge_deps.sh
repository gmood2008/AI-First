#!/bin/bash
# AutoForge 依赖安装脚本

echo "=========================================="
echo "安装 AutoForge 依赖"
echo "=========================================="
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3"
    exit 1
fi

echo "📦 安装依赖包..."
python3 -m pip install --upgrade pip --quiet
python3 -m pip install openai pyyaml httpx pydantic --quiet

echo ""
echo "✅ 依赖安装完成！"
echo ""
echo "已安装的包："
python3 -m pip list | grep -E "(openai|yaml|httpx|pydantic)" || echo "检查中..."
echo ""
echo "=========================================="
echo "下一步："
echo "=========================================="
echo ""
echo "1. 设置 DeepSeek API Key:"
echo "   export DEEPSEEK_API_KEY=your_key_here"
echo ""
echo "2. 生成能力:"
echo "   ./forge create '你的需求' --provider deepseek"
echo ""
