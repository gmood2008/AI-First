#!/bin/bash
# AutoForge 环境设置脚本

set -e

echo "=========================================="
echo "AutoForge 环境设置"
echo "=========================================="
echo ""

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# 检查虚拟环境
if [ -d "venv" ]; then
    echo "✅ 发现虚拟环境: venv/"
    echo "激活虚拟环境..."
    source venv/bin/activate
    echo "✅ 虚拟环境已激活"
else
    echo "⚠️  未找到虚拟环境，创建新的虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate
    echo "✅ 虚拟环境已创建并激活"
fi

echo ""
echo "📦 安装/更新依赖..."
python3 -m pip install --upgrade pip --quiet
python3 -m pip install openai pyyaml httpx pydantic --quiet

echo ""
echo "✅ 依赖安装完成！"
echo ""

# 检查依赖
echo "🔍 检查依赖..."
python3 -c "
import sys
try:
    import openai
    print('✅ openai:', openai.__version__)
except ImportError as e:
    print('❌ openai:', e)
    sys.exit(1)

try:
    import yaml
    print('✅ pyyaml: 已安装')
except ImportError as e:
    print('❌ pyyaml:', e)
    sys.exit(1)

try:
    import httpx
    print('✅ httpx:', httpx.__version__)
except ImportError as e:
    print('❌ httpx:', e)
    sys.exit(1)

try:
    import pydantic
    print('✅ pydantic:', pydantic.__version__)
except ImportError as e:
    print('❌ pydantic:', e)
    sys.exit(1)
"

echo ""
echo "=========================================="
echo "✅ 环境设置完成！"
echo "=========================================="
echo ""
echo "📝 使用说明："
echo ""
echo "1. 激活虚拟环境（如果还没激活）："
echo "   source venv/bin/activate"
echo ""
echo "2. 设置 DeepSeek API Key："
echo "   export DEEPSEEK_API_KEY=your_deepseek_api_key_here"
echo ""
echo "3. 生成 GitHub API 能力："
echo "   ./forge create '从 GitHub API 获取仓库信息，需要 OAuth token' \\"
echo "     --id 'net.github.get_repo' \\"
echo "     --provider deepseek \\"
echo "     --reference docs/github_api_reference.md"
echo ""
echo "💡 提示：每次使用前记得激活虚拟环境！"
echo ""
