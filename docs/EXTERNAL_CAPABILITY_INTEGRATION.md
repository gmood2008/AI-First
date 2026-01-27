# 第三方能力集成指南

## 概述

AI-First Runtime 现在支持将第三方能力（Claude Skills、OpenAI Functions、HTTP APIs 等）转换为 AI-First 能力，实现反向集成。

## 架构设计

```
第三方能力 (Claude Skill / OpenAI Function / HTTP API)
    ↓
适配器 (Adapter)
    ↓
AI-First Handler 包装器
    ↓
能力注册表 (Registry)
    ↓
运行时引擎 (RuntimeEngine)
```

## 支持的适配器类型

### 1. Claude Skill 适配器

将 Claude Skill 转换为 AI-First 能力。

**使用方式：**
```bash
# 从 URL 导入
./forge import --from-claude-skill "https://api.anthropic.com/v1/skills/skill_123" \
  --id "external.claude.data_analysis" \
  --api-key "$CLAUDE_API_KEY"

# 从 JSON 文件导入
./forge import --from-claude-skill skill.json \
  --id "external.claude.data_analysis"
```

**生成的 YAML 示例：**
```yaml
id: external.claude.data_analysis
name: Data Analysis
description: Analyze data and generate insights
operation_type: NETWORK
risk:
  level: MEDIUM
  justification: External API call via Claude Skill
side_effects:
  reversible: false
  scope: external
adapter:
  type: claude_skill
  config:
    skill_id: skill_123
    api_key_env: CLAUDE_API_KEY
    base_url: https://api.anthropic.com/v1
```

### 2. HTTP API 适配器

将任何 HTTP API 转换为 AI-First 能力。

**使用方式：**
```bash
./forge import --from-http-api api_definition.json \
  --id "external.slack.send_message"
```

**API 定义文件格式：**
```json
{
  "name": "Send Slack Message",
  "description": "Send a message to a Slack channel",
  "endpoint_url": "https://slack.com/api/chat.postMessage",
  "method": "POST",
  "parameters": {
    "channel": {
      "type": "string",
      "description": "Slack channel ID",
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

### 3. OpenAI Function 适配器

将 OpenAI Function 转换为 AI-First 能力（开发中）。

## 实现细节

### 适配器框架

**基础类：** `src/runtime/adapters/base.py`
- `ExternalCapabilityAdapter`: 所有适配器的基类
- `AdapterConfig`: 适配器配置数据类

**具体适配器：**
- `ClaudeSkillAdapter`: `src/runtime/adapters/claude_skill.py`
- `HTTPAPIAdapter`: `src/runtime/adapters/http_api.py`
- `OpenAIFunctionAdapter`: `src/runtime/adapters/openai_function.py`

### 能力转换器

**位置：** `src/forge/auto/skill_converter.py`

**功能：**
- 将第三方能力定义转换为 AI-First 规范
- 生成 Handler 包装器代码
- 生成测试代码

### 外部能力加载器

**位置：** `src/runtime/external_loader.py`

**功能：**
- 自动扫描 `capabilities/validated/external/` 目录
- 加载外部能力 YAML 文件
- 使用适配器创建 Handler
- 注册到能力注册表

### 动态注册

**位置：** `src/runtime/registry.py`

**方法：** `register_external()`

```python
registry.register_external(
    capability_id="external.claude.my_skill",
    adapter_type="claude_skill",
    adapter_config={
        "skill_id": "skill_123",
        "api_key_env": "CLAUDE_API_KEY"
    }
)
```

## 工作流程

### 1. 导入第三方能力

```bash
# 导入 Claude Skill
./forge import --from-claude-skill skill.json \
  --id "external.claude.my_skill" \
  --output "capabilities/validated/external"
```

**生成的文件：**
- `capabilities/validated/external/external.claude.my_skill.yaml` - 能力规范
- `src/runtime/stdlib/generated/external_claude_my_skill.py` - Handler 包装器
- `tests/generated/test_external_claude_my_skill.py` - 测试代码

### 2. 自动加载

运行时启动时，MCP Server 会自动：
1. 扫描 `capabilities/validated/external/` 目录
2. 读取 YAML 文件中的适配器配置
3. 创建适配器实例
4. 生成 Handler 包装器
5. 注册到能力注册表

### 3. 使用能力

导入的能力可以像普通 AI-First 能力一样使用：

```python
# 通过运行时引擎
result = engine.execute("external.claude.my_skill", {
    "data": "some data",
    "analysis_type": "summary"
}, context)

# 通过 MCP Server (Claude Desktop)
# Claude 可以直接调用该能力
```

## 配置选项

### Claude Skill 适配器

```yaml
adapter:
  type: claude_skill
  config:
    skill_id: "skill_123"           # Claude Skill ID
    api_key: "sk-..."                # API Key (可选，优先使用环境变量)
    api_key_env: "CLAUDE_API_KEY"   # 环境变量名
    base_url: "https://api.anthropic.com/v1"  # API Base URL
    timeout: 30.0                    # 请求超时时间
```

### HTTP API 适配器

```yaml
adapter:
  type: http_api
  config:
    endpoint_url: "https://api.example.com/endpoint"
    method: "POST"                   # GET, POST, PUT, DELETE
    headers:                         # 自定义请求头
      Content-Type: "application/json"
    auth_type: "bearer"              # none, bearer, api_key, basic
    auth_config:
      token_env: "API_TOKEN"         # 从环境变量获取 token
    timeout: 30.0
```

## 示例

### 示例 1: 导入 Claude Skill

```bash
# 1. 创建 Skill 定义文件
cat > my_skill.json << 'EOF'
{
  "id": "skill_123",
  "name": "Text Summarizer",
  "description": "Summarize long text",
  "input_schema": {
    "properties": {
      "text": {"type": "string", "description": "Text to summarize"},
      "max_length": {"type": "integer", "description": "Max summary length"}
    },
    "required": ["text"]
  }
}
EOF

# 2. 导入
./forge import --from-claude-skill my_skill.json \
  --id "external.claude.text_summarizer"

# 3. 测试
pytest tests/generated/test_external_claude_text_summarizer.py
```

### 示例 2: 导入 HTTP API

```bash
# 1. 创建 API 定义
cat > github_api.json << 'EOF'
{
  "name": "Create GitHub Issue",
  "endpoint_url": "https://api.github.com/repos/{owner}/{repo}/issues",
  "method": "POST",
  "parameters": {
    "owner": {"type": "string", "required": true},
    "repo": {"type": "string", "required": true},
    "title": {"type": "string", "required": true},
    "body": {"type": "string", "required": false}
  },
  "auth_type": "bearer",
  "auth_config": {
    "token_env": "GITHUB_TOKEN"
  }
}
EOF

# 2. 导入
./forge import --from-http-api github_api.json \
  --id "external.github.create_issue"

# 3. 使用
# 运行时启动后，可以通过 MCP 调用该能力
```

## 限制和注意事项

### 1. 撤销支持

大多数外部能力**不支持撤销操作**，因为：
- 外部 API 通常不提供撤销接口
- 操作可能已经产生外部影响

### 2. 错误处理

适配器会捕获外部 API 错误并转换为 AI-First 格式：
- HTTP 错误 → `RuntimeError`
- 超时 → `TimeoutError`
- 认证失败 → `AuthenticationError`

### 3. 性能考虑

- 外部 API 调用有网络延迟
- 建议设置合理的超时时间
- 考虑实现缓存机制（未来版本）

### 4. 安全性

- API Key 应通过环境变量传递，不要硬编码
- 使用 `api_key_env` 配置项指定环境变量名
- 敏感信息会被审计日志自动脱敏

## 故障排查

### 问题：导入失败

**可能原因：**
1. API Key 未设置
2. 网络连接问题
3. 定义文件格式错误

**解决方案：**
```bash
# 检查 API Key
echo $CLAUDE_API_KEY

# 检查网络
curl https://api.anthropic.com/v1/skills

# 验证 JSON 格式
python3 -m json.tool skill.json
```

### 问题：运行时找不到外部能力

**检查：**
1. YAML 文件是否在 `capabilities/validated/external/` 目录
2. YAML 文件是否包含 `adapter` 配置
3. 适配器类型是否正确

**验证：**
```python
from runtime.external_loader import load_external_capabilities
from runtime.registry import CapabilityRegistry
from pathlib import Path

registry = CapabilityRegistry()
external_dir = Path("capabilities/validated/external")
load_external_capabilities(registry, external_dir)

print(f"Loaded capabilities: {registry.list_capabilities()}")
```

## 未来扩展

### 计划支持

- ✅ Claude Skill
- ✅ HTTP API
- 🔄 OpenAI Function
- ⏳ LangChain Tools
- ⏳ gRPC Services
- ⏳ GraphQL APIs

### 增强功能

- ⏳ 自动参数映射
- ⏳ 响应缓存
- ⏳ 批量操作支持
- ⏳ 能力组合（Chain）

## 相关文档

- [能力审核入库](./CAPABILITY_REVIEW_AND_INTEGRATION.md)
- [项目关系说明](./PROJECT_RELATIONSHIP.md)
- [MCP Server 配置](../CHATBOX_MCP_CONFIG_UPDATED.md)
