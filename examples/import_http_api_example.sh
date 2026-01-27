#!/bin/bash
# 示例：导入 HTTP API 为 AI-First 能力

echo "=========================================="
echo "📥 导入 HTTP API 示例"
echo "=========================================="
echo ""

# 创建示例 API 定义
echo "示例: 导入 Slack API"
echo "----------------------------------------"
echo ""
echo "1. 创建 API 定义文件 (slack_api.json):"
cat << 'JSON'
{
  "name": "Send Slack Message",
  "description": "Send a message to a Slack channel",
  "endpoint_url": "https://slack.com/api/chat.postMessage",
  "method": "POST",
  "parameters": {
    "channel": {
      "type": "string",
      "description": "Slack channel ID or name",
      "required": true
    },
    "text": {
      "type": "string",
      "description": "Message text",
      "required": true
    },
    "thread_ts": {
      "type": "string",
      "description": "Thread timestamp (optional)",
      "required": false
    }
  },
  "auth_type": "bearer",
  "auth_config": {
    "token_env": "SLACK_BOT_TOKEN"
  }
}
JSON

echo ""
echo "2. 导入命令:"
echo './forge import --from-http-api slack_api.json \\'
echo '  --id "external.slack.send_message"'
echo ""

echo "=========================================="
echo "✅ 导入完成后，能力将保存在:"
echo "   - capabilities/validated/external/external.slack.send_message.yaml"
echo ""
echo "💡 运行时启动时会自动加载并注册该能力"
echo "=========================================="
