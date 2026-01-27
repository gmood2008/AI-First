#!/bin/bash
# AutoForge Usage Examples
# 
# This script demonstrates various ways to use AutoForge

set -e

echo "=========================================="
echo "AutoForge Usage Examples"
echo "=========================================="
echo ""

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY not set"
    echo "   Set it with: export OPENAI_API_KEY=your_key_here"
    echo ""
    echo "Examples will show --dry-run mode (preview only)"
    DRY_RUN="--dry-run"
else
    echo "✅ OPENAI_API_KEY is set"
    echo ""
    DRY_RUN=""
fi

echo "Example 1: Basic usage - Get Bitcoin price"
echo "--------------------------------------------"
forge create "获取 CoinGecko 的比特币价格" $DRY_RUN --id "net.crypto.get_bitcoin_price"
echo ""

echo "Example 2: Network operation - Send Slack message"
echo "--------------------------------------------"
forge create "发送消息到 Slack 频道" $DRY_RUN --id "net.slack.send_message" --verbose
echo ""

echo "Example 3: File operation - Read file"
echo "--------------------------------------------"
forge create "读取本地文件内容" $DRY_RUN --id "io.fs.read_file"
echo ""

echo "Example 4: File operation - Write file"
echo "--------------------------------------------"
forge create "写入内容到本地文件" $DRY_RUN --id "io.fs.write_file"
echo ""

echo "Example 5: With context"
echo "--------------------------------------------"
forge create "获取 GitHub 仓库信息" \
    --id "net.github.get_repo" \
    --context '{"workspace": "my-workspace", "default_branch": "main"}' \
    $DRY_RUN
echo ""

echo "Example 6: Preview mode (always dry-run)"
echo "--------------------------------------------"
forge create "创建新的数据库记录" --dry-run
echo ""

echo "=========================================="
echo "All examples completed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Review generated files"
echo "  2. Run tests: pytest tests/generated/"
echo "  3. Commit to Git"
echo ""
