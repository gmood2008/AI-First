# 能力审核入库与第三方能力集成

## 一、能力审核入库流程

### 当前实现

#### 1. 能力生成阶段（AutoForge）

```bash
# 使用 AutoForge 生成能力
./forge create "从 GitHub API 获取仓库信息" --id "net.github.get_repo"
```

**生成的文件：**
- `capabilities/validated/generated/net.github.get_repo.yaml` - 能力规范
- `src/runtime/stdlib/generated/net_github_get_repo.py` - Handler 实现
- `tests/generated/test_net_github_get_repo.py` - 测试代码

#### 2. 自动验证阶段

**位置**: `src/forge/auto/validator.py`

```python
class SpecValidator:
    def validate_and_fix(self, spec: CapabilitySpec) -> CapabilitySpec:
        """
        验证并自动修复规范
        
        验证项：
        1. 风险级别一致性检查
        2. 写入操作必须有补偿策略
        3. DELETE 操作必须是 HIGH+ 风险
        4. 规范完整性检查
        """
        for attempt in range(self.max_retries):
            issues = self._validate(spec)
            if not issues:
                return spec  # 验证通过
            
            # 自动修复问题
            spec = self._fix_issues(spec, issues)
        
        raise ValueError("验证失败")
```

**验证规则：**
- ✅ 风险级别与操作类型匹配
- ✅ 写入操作必须有 `compensation.supported = true`
- ✅ DELETE 操作必须是 HIGH 或 CRITICAL 风险
- ✅ 所有必需字段存在

#### 3. 入库流程（当前：手动）

**当前方式：**
```bash
# 1. 生成能力（已在 generated 目录）
./forge create "需求描述" --id "capability.id"

# 2. 手动审核生成的文件
# - 检查 YAML 规范
# - 检查 Handler 代码
# - 运行测试

# 3. 测试通过后，手动移动到 stdlib 目录
mv capabilities/validated/generated/net.github.get_repo.yaml \
   capabilities/validated/stdlib/net_github_get_repo.yaml

# 4. 更新 loader.py 注册映射（如果需要）
# 在 src/runtime/stdlib/loader.py 中添加：
# "net.github.get_repo": GetRepoHandler,
```

### 改进方案：自动化审核入库

#### 方案 1: 添加审核命令

```python
# src/forge/auto/reviewer.py
class CapabilityReviewer:
    """
    能力审核器
    
    功能：
    1. 检查规范完整性
    2. 运行测试套件
    3. 代码质量检查
    4. 安全审计
    5. 生成审核报告
    """
    
    def review(self, capability_id: str) -> ReviewResult:
        """
        审核能力
        
        返回：
        - passed: bool - 是否通过
        - issues: List[str] - 问题列表
        - score: float - 质量评分
        """
        pass
    
    def approve(self, capability_id: str) -> bool:
        """
        批准入库
        
        操作：
        1. 移动文件到 stdlib 目录
        2. 更新注册映射
        3. 生成变更日志
        """
        pass
```

**使用方式：**
```bash
# 审核能力
./forge review net.github.get_repo

# 自动入库（如果审核通过）
./forge approve net.github.get_repo

# 或一键审核并入库
./forge review --auto-approve net.github.get_repo
```

#### 方案 2: 集成到 CI/CD

```yaml
# .github/workflows/capability-review.yml
name: Capability Review

on:
  pull_request:
    paths:
      - 'capabilities/validated/generated/**'

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Review Capability
        run: |
          ./forge review ${{ github.event.pull_request.changed_files }}
      - name: Run Tests
        run: pytest tests/generated/
      - name: Security Audit
        run: ./forge audit ${{ github.event.pull_request.changed_files }}
```

---

## 二、第三方能力集成（如 Claude Skill）

### 当前实现

#### 1. MCP 协议集成（Claude Desktop）

**位置**: `docs/INTEGRATION_GUIDE.md`

**配置方式：**
```json
// ~/.claude/agent_config.json
{
  "name": "AI-First Runtime",
  "tools": [
    {
      "type": "mcp",
      "name": "airun",
      "command": [
        "python3",
        "/path/to/ai-first-runtime/src/runtime/mcp/server_v2.py"
      ]
    }
  ]
}
```

**工作原理：**
1. Claude Desktop 启动 MCP Server
2. Server 暴露所有 AI-First 能力为 MCP Tools
3. Claude 可以调用这些能力

#### 2. 能力转换（当前：手动）

**问题：** 如何将 Claude Skill 或其他第三方能力转换为 AI-First 能力？

**当前方式：** 手动创建 YAML 规范和 Handler

### 改进方案：自动转换第三方能力

#### 方案 1: Claude Skill 转换器

```python
# src/forge/auto/skill_converter.py
class ClaudeSkillConverter:
    """
    Claude Skill 转换器
    
    将 Claude Skill 定义转换为 AI-First 能力规范
    """
    
    def convert_skill(self, skill_definition: dict) -> CapabilitySpec:
        """
        转换 Claude Skill 为 AI-First 能力
        
        Args:
            skill_definition: Claude Skill JSON 定义
        
        Returns:
            CapabilitySpec 对象
        """
        # 1. 解析 Skill 定义
        # 2. 映射到 AI-First 规范格式
        # 3. 生成 Handler 包装器
        # 4. 生成测试代码
        pass
    
    def create_handler_wrapper(self, skill: dict) -> str:
        """
        创建 Handler 包装器
        
        包装器会：
        1. 调用 Claude Skill API
        2. 转换参数格式
        3. 处理响应
        4. 实现撤销逻辑（如果可能）
        """
        pass
```

**使用方式：**
```bash
# 从 Claude Skill 创建能力
./forge import --from-claude-skill skill.json --id "claude.skill.name"

# 或从 URL 导入
./forge import --from-claude-skill https://api.claude.ai/skills/123 --id "claude.skill.name"
```

#### 方案 2: 通用第三方能力适配器

```python
# src/runtime/adapters/external_adapter.py
class ExternalCapabilityAdapter:
    """
    外部能力适配器
    
    支持：
    - Claude Skills
    - OpenAI Functions
    - LangChain Tools
    - Custom HTTP APIs
    """
    
    def __init__(self, adapter_type: str, config: dict):
        """
        Args:
            adapter_type: "claude_skill", "openai_function", "langchain_tool", "http_api"
            config: 适配器配置
        """
        self.adapter_type = adapter_type
        self.config = config
    
    def create_handler(self, external_def: dict) -> ActionHandler:
        """
        创建适配器 Handler
        
        Handler 会：
        1. 接收 AI-First 格式的参数
        2. 转换为外部 API 格式
        3. 调用外部 API
        4. 转换响应为 AI-First 格式
        """
        pass
```

**配置示例：**
```yaml
# capabilities/validated/external/claude_skill_example.yaml
meta:
  id: external.claude.skill_example
  version: 1.0.0
  description: "Claude Skill 示例（通过适配器）"

adapter:
  type: claude_skill
  config:
    skill_id: "skill_123"
    api_key_env: "CLAUDE_API_KEY"
    base_url: "https://api.claude.ai"

interface:
  inputs:
    query:
      type: string
      description: "查询内容"
  outputs:
    result:
      type: string
      description: "Skill 返回结果"
```

#### 方案 3: 动态能力注册

```python
# src/runtime/registry.py (扩展)
class CapabilityRegistry:
    def register_external(
        self,
        capability_id: str,
        adapter_type: str,
        adapter_config: dict
    ):
        """
        注册外部能力
        
        无需本地 Handler，通过适配器动态调用
        """
        from runtime.adapters import create_adapter
        
        adapter = create_adapter(adapter_type, adapter_config)
        handler = adapter.create_handler(adapter_config)
        
        self.register(capability_id, handler)
```

**使用方式：**
```python
# 运行时注册 Claude Skill
registry = CapabilityRegistry()

registry.register_external(
    capability_id="external.claude.my_skill",
    adapter_type="claude_skill",
    adapter_config={
        "skill_id": "skill_123",
        "api_key": os.getenv("CLAUDE_API_KEY")
    }
)
```

---

## 三、完整工作流程

### 场景 1: 创建新能力并审核入库

```bash
# 1. 生成能力
./forge create "发送 Slack 消息" --id "net.slack.send_message"

# 2. 审核
./forge review net.slack.send_message
# 输出：
# ✅ 规范验证通过
# ✅ 测试通过 (5/5)
# ✅ 代码质量评分: 8.5/10
# ⚠️  建议：添加更多错误处理

# 3. 批准入库
./forge approve net.slack.send_message
# 操作：
# - 移动到 stdlib 目录
# - 更新注册映射
# - 生成变更日志
```

### 场景 2: 集成 Claude Skill

```bash
# 1. 导入 Claude Skill
./forge import \
  --from-claude-skill https://api.claude.ai/skills/123 \
  --id "external.claude.data_analysis" \
  --adapter claude_skill

# 2. 自动生成：
# - YAML 规范（带适配器配置）
# - Handler 包装器
# - 测试代码

# 3. 测试
pytest tests/generated/test_external_claude_data_analysis.py

# 4. 注册到运行时
# 运行时启动时自动加载 external 目录的能力
```

---

## 四、实现优先级

### 高优先级（已实现）

- ✅ AutoForge 能力生成
- ✅ 自动验证和修复
- ✅ MCP Server 集成（Claude Desktop）

### 中优先级（建议实现）

- 🔄 审核命令 (`forge review`)
- 🔄 自动入库 (`forge approve`)
- 🔄 外部能力适配器框架

### 低优先级（未来扩展）

- ⏳ CI/CD 集成
- ⏳ 能力市场/注册表
- ⏳ 版本管理和回滚

---

## 五、代码示例

### 审核器实现示例

```python
# src/forge/auto/reviewer.py
class CapabilityReviewer:
    def review(self, capability_id: str) -> ReviewResult:
        # 1. 加载规范
        spec_path = f"capabilities/validated/generated/{capability_id}.yaml"
        spec = load_spec_from_yaml(spec_path)
        
        # 2. 规范验证
        validator = SpecValidator()
        validated_spec = validator.validate_and_fix(spec)
        
        # 3. 代码质量检查
        handler_path = f"src/runtime/stdlib/generated/{capability_id.replace('.', '_')}.py"
        code_score = self._check_code_quality(handler_path)
        
        # 4. 运行测试
        test_path = f"tests/generated/test_{capability_id.replace('.', '_')}.py"
        test_results = self._run_tests(test_path)
        
        # 5. 安全审计
        security_issues = self._security_audit(spec, handler_path)
        
        return ReviewResult(
            passed=all([
                validated_spec is not None,
                code_score >= 7.0,
                test_results.passed,
                len(security_issues) == 0
            ]),
            issues=security_issues,
            score=code_score
        )
```

### 适配器实现示例

```python
# src/runtime/adapters/claude_skill_adapter.py
class ClaudeSkillAdapter:
    def create_handler(self, skill_config: dict) -> ActionHandler:
        class ClaudeSkillHandler(ActionHandler):
            def __init__(self, spec_dict):
                super().__init__(spec_dict)
                self.skill_id = skill_config["skill_id"]
                self.api_key = skill_config["api_key"]
                self.client = ClaudeClient(api_key=self.api_key)
            
            def execute(self, params: dict, context: Any) -> ActionOutput:
                # 转换参数格式
                skill_params = self._convert_params(params)
                
                # 调用 Claude Skill API
                result = self.client.call_skill(
                    skill_id=self.skill_id,
                    params=skill_params
                )
                
                # 转换响应格式
                outputs = self._convert_outputs(result)
                
                return ActionOutput(
                    result=outputs,
                    description=f"Executed Claude Skill: {self.skill_id}",
                    undo_closure=None  # 外部能力通常不可撤销
                )
        
        return ClaudeSkillHandler
```

---

## 六、总结

### 当前状态

1. **能力审核入库**：
   - ✅ 自动验证已实现
   - ⚠️  审核流程需要手动
   - ⚠️  入库需要手动移动文件

2. **第三方能力集成**：
   - ✅ MCP 协议支持（Claude Desktop）
   - ⚠️  缺少自动转换工具
   - ⚠️  缺少适配器框架

### 建议改进

1. **实现审核命令** (`forge review`)
2. **实现自动入库** (`forge approve`)
3. **实现适配器框架** (支持 Claude Skill、OpenAI Functions 等)
4. **添加 CI/CD 集成**

这些功能将大大提升能力管理的效率和第三方集成的便利性。
