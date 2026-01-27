#!/bin/bash
# 使用 DeepSeek API 生成 GitHub 能力

set -e

echo "=========================================="
echo "使用 DeepSeek 生成 GitHub API 能力"
echo "=========================================="
echo ""

# 检查 API Key
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "⚠️  警告: DEEPSEEK_API_KEY 未设置"
    echo ""
    read -p "请输入你的 DeepSeek API Key: " api_key
    export DEEPSEEK_API_KEY="$api_key"
    echo ""
fi

echo "✅ 使用 DeepSeek API"
echo ""

# 生成能力
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --provider deepseek \
  --reference docs/github_api_reference.md \
  --verbose

echo ""
echo "=========================================="
echo "✅ 生成完成！"
echo "=========================================="
echo ""
echo "生成的文件："
echo "  - capabilities/validated/generated/net.github.get_repo.yaml"
echo "  - src/runtime/stdlib/generated/net_github_get_repo.py"
echo "  - tests/generated/test_net_github_get_repo.py"
echo ""
