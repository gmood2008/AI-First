# 第三方能力集成快速开始

## 🎯 功能概述

AI-First Runtime 现在支持将第三方能力（Claude Skills、HTTP APIs 等）转换为 AI-First 能力，实现反向集成。

## 🚀 快速开始

### 1. 导入 Claude Skill

```bash
# 从 JSON 文件导入
./forge import --from-claude-skill skill.json \
  --id "external.claude.my_skill"

# 从 URL 导入
./forge import --from-claude-skill "https://api.anthropic.com/v1/skills/skill_123" \
  --id "external.claude.my_skill" \
  --api-key "$CLAUDE_API_KEY"
```

### 2. 导入 HTTP API

```bash
# 创建 API 定义文件
cat > api.json << 'EOF'
{
  "name": "Send Slack Message",
  "endpoint_url": "https://slack.com/api/chat.postMessage",
  "method": "POST",
  "parameters": {
    "channel": {"type": "string", "required": true},
    "text": {"type": "string", "required": true}
  },
  "auth_type": "bearer",
  "auth_config": {"token_env": "SLACK_BOT_TOKEN"}
}
EOF

# 导入
./forge import --from-http-api api.json \
  --id "external.slack.send_message"
```

### 3. 自动加载

运行时启动时会自动加载 `capabilities/validated/external/` 目录中的能力：

```bash
# MCP Server 启动时会自动加载
python3 src/runtime/mcp/server_v2.py
```

## 📋 完整示例

### 示例：集成 Slack API

**步骤 1: 创建 API 定义**

```json
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
    }
  },
  "auth_type": "bearer",
  "auth_config": {
    "token_env": "SLACK_BOT_TOKEN"
  }
}
```

**步骤 2: 导入**

```bash
./forge import --from-http-api slack_api.json \
  --id "external.slack.send_message" \
  --output "capabilities/validated/external"
```

**步骤 3: 使用**

导入后，能力会自动注册到运行时，可以通过 MCP Server 调用：

```python
# 在 Claude Desktop 或其他 MCP 客户端中
# 可以直接调用 external.slack.send_message
```

## 🔧 配置说明

### Claude Skill 配置

```yaml
adapter:
  type: claude_skill
  config:
    skill_id: "skill_123"
    api_key_env: "CLAUDE_API_KEY"  # 从环境变量获取
    base_url: "https://api.anthropic.com/v1"
```

### HTTP API 配置

```yaml
adapter:
  type: http_api
  config:
    endpoint_url: "https://api.example.com/endpoint"
    method: "POST"
    auth_type: "bearer"  # none, bearer, api_key, basic
    auth_config:
      token_env: "API_TOKEN"
```

## 📁 文件结构

导入后生成的文件：

```
capabilities/validated/external/
└── external.claude.my_skill.yaml    # 能力规范（含适配器配置）

src/runtime/stdlib/generated/
└── external_claude_my_skill.py       # Handler 包装器

tests/generated/
└── test_external_claude_my_skill.py   # 测试代码
```

## ✅ 验证

### 检查导入是否成功

```bash
# 查看生成的规范
cat capabilities/validated/external/external.claude.my_skill.yaml

# 运行测试
pytest tests/generated/test_external_claude_my_skill.py
```

### 检查运行时加载

```python
from runtime.registry import CapabilityRegistry
from runtime.external_loader import load_external_capabilities
from pathlib import Path

registry = CapabilityRegistry()
external_dir = Path("capabilities/validated/external")
load_external_capabilities(registry, external_dir)

# 检查是否注册
if "external.claude.my_skill" in registry:
    print("✅ 能力已注册")
```

## 🎯 使用场景

1. **集成现有 API**: 将公司内部 API 快速接入 AI-First
2. **Claude Skills**: 复用已有的 Claude Skill
3. **第三方服务**: 集成 Slack、GitHub、Jira 等服务
4. **快速原型**: 无需编写完整 Handler，直接使用适配器

## 📚 相关文档

- [完整集成指南](./docs/EXTERNAL_CAPABILITY_INTEGRATION.md)
- [能力审核入库](./docs/CAPABILITY_REVIEW_AND_INTEGRATION.md)
- [示例脚本](./examples/import_claude_skill_example.sh)

## 💡 提示

- API Key 应通过环境变量传递，不要硬编码
- 外部能力通常不支持撤销操作
- 建议设置合理的超时时间
- 导入后记得运行测试验证功能
