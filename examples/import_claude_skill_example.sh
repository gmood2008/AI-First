#!/bin/bash
# 示例：导入 Claude Skill 为 AI-First 能力

echo "=========================================="
echo "📥 导入 Claude Skill 示例"
echo "=========================================="
echo ""

# 示例 1: 从 URL 导入
echo "示例 1: 从 Claude API URL 导入"
echo "----------------------------------------"
echo ""
echo "命令:"
echo './forge import --from-claude-skill "https://api.anthropic.com/v1/skills/skill_123" \\'
echo '  --id "external.claude.data_analysis" \\'
echo '  --api-key "\$CLAUDE_API_KEY"'
echo ""

# 示例 2: 从 JSON 文件导入
echo "示例 2: 从本地 JSON 文件导入"
echo "----------------------------------------"
echo ""
echo "1. 创建 Claude Skill 定义文件 (skill.json):"
cat << 'JSON'
{
  "id": "skill_123",
  "name": "Data Analysis",
  "description": "Analyze data and generate insights",
  "input_schema": {
    "type": "object",
    "properties": {
      "data": {
        "type": "string",
        "description": "Data to analyze"
      },
      "analysis_type": {
        "type": "string",
        "description": "Type of analysis",
        "enum": ["summary", "trends", "anomalies"]
      }
    },
    "required": ["data"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "insights": {
        "type": "string",
        "description": "Analysis insights"
      },
      "confidence": {
        "type": "number",
        "description": "Confidence score"
      }
    }
  }
}
JSON

echo ""
echo "2. 导入命令:"
echo './forge import --from-claude-skill skill.json \\'
echo '  --id "external.claude.data_analysis"'
echo ""

echo "=========================================="
echo "✅ 导入完成后，能力将保存在:"
echo "   - capabilities/validated/external/external.claude.data_analysis.yaml"
echo "   - src/runtime/stdlib/generated/external_claude_data_analysis.py"
echo "   - tests/generated/test_external_claude_data_analysis.py"
echo ""
echo "💡 运行时启动时会自动加载 external/ 目录中的能力"
echo "=========================================="
