#!/bin/bash
# 测试 Claude Skill 导入功能

echo "=========================================="
echo "🧪 测试 Claude Skill 导入"
echo "=========================================="
echo ""

# 创建测试用的 Claude Skill 定义
cat > /tmp/test_claude_skill.json << 'EOF'
{
  "id": "skill_test_123",
  "name": "Test Skill",
  "description": "A test Claude Skill for integration",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Query string"
      },
      "max_results": {
        "type": "integer",
        "description": "Maximum number of results",
        "default": 10
      }
    },
    "required": ["query"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "results": {
        "type": "array",
        "description": "Search results"
      },
      "count": {
        "type": "integer",
        "description": "Number of results"
      }
    }
  }
}
EOF

echo "1️⃣ 创建测试 Skill 定义文件: /tmp/test_claude_skill.json"
echo ""

echo "2️⃣ 测试导入（dry-run 模式）..."
echo "----------------------------------------"
cd /Users/daniel/AI项目/云端同步项目/ai-first-runtime-master

./forge import \
  --from-claude-skill /tmp/test_claude_skill.json \
  --id "external.claude.test_skill" \
  --dry-run \
  2>&1 | head -50

echo ""
echo "=========================================="
echo "✅ 测试完成"
echo "=========================================="
echo ""
echo "💡 如果看到生成的 YAML 和代码，说明导入功能正常"
echo "💡 使用 --dry-run 可以预览，去掉该参数会实际保存文件"
