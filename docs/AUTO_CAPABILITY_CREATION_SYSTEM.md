# 自动化能力创建与注册系统设计

## 🎯 系统目标

实现一个**端到端自动化**的能力创建和注册机制，系统可以：
1. **理解需求**：通过自然语言描述或问题
2. **网络搜索**：自动搜索相关信息补充需求
3. **生成规范**：自动创建符合 AI-First 原则的 YAML 规范
4. **验证规范**：自动验证规范的正确性
5. **生成实现**：自动生成 Handler 代码
6. **自动注册**：自动注册到运行时系统
7. **完整流程**：全自动化，无需人工干预

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│              自动化能力创建系统 (Auto Forge)                  │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
│  需求理解模块   │  │  信息补充模块   │  │  规范生成模块   │
│ Requirement   │  │ Info Enrichment│  │ Spec Generator │
│ Understanding  │  │                │  │                │
└───────┬────────┘  └───────┬────────┘  └───────┬────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
│  规范验证模块   │  │  代码生成模块   │  │  自动注册模块   │
│ Spec Validator │  │ Code Generator  │  │ Auto Register   │
└───────┬────────┘  └───────┬────────┘  └───────┬────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                    ┌───────▼────────┐
                    │  运行时系统     │
                    │ Runtime System │
                    └────────────────┘
```

---

## 📋 核心模块设计

### 1. 需求理解模块 (Requirement Understanding)

**功能：**
- 解析自然语言需求
- 提取关键信息（操作类型、输入输出、副作用等）
- 识别需求中的模糊点，触发信息补充

**输入：**
```python
{
    "requirement": "我需要一个能力来发送 Slack 消息",
    "context": {
        "user_id": "user123",
        "domain": "communication"
    }
}
```

**输出：**
```python
{
    "parsed_requirement": {
        "action": "send_message",
        "target": "slack",
        "inputs": ["message", "channel"],
        "outputs": ["status", "message_id"],
        "side_effects": ["network_write"],
        "confidence": 0.85,
        "missing_info": ["slack_api_format", "authentication_method"]
    }
}
```

### 2. 信息补充模块 (Info Enrichment)

**功能：**
- 网络搜索补充缺失信息
- 查询现有能力库，避免重复
- 查找最佳实践和示例

**实现方式：**
```python
async def enrich_requirement(parsed_req):
    # 1. 网络搜索
    search_results = await web_search(
        f"{parsed_req['action']} {parsed_req['target']} API"
    )
    
    # 2. 检查现有能力
    existing = check_existing_capabilities(parsed_req['action'])
    
    # 3. 查找相关文档
    docs = find_related_docs(parsed_req['target'])
    
    return {
        "api_info": extract_api_info(search_results),
        "existing_capabilities": existing,
        "best_practices": extract_best_practices(docs)
    }
```

### 3. 规范生成模块 (Spec Generator)

**功能：**
- 使用增强的 LLM Prompt 生成规范
- 结合网络搜索结果和最佳实践
- 确保符合 AI-First 原则

**增强的 Prompt：**
```python
ENHANCED_GENERATOR_PROMPT = """
你是一个严格的能力规范生成器。

用户需求：{requirement}

补充信息：
- API 文档：{api_info}
- 现有类似能力：{existing_capabilities}
- 最佳实践：{best_practices}

请生成一个严格符合 AI-First 原则的能力规范：
1. 原子性：只做一件事
2. 类型严格：所有输入输出都有明确类型
3. 可逆性：明确的撤销策略
4. 副作用透明：声明所有副作用

输出 JSON 格式的规范...
"""
```

### 4. 规范验证模块 (Spec Validator)

**功能：**
- 使用现有的 Critic 进行验证
- 如果验证失败，自动修复并重试
- 多轮验证直到通过

**流程：**
```python
async def validate_with_retry(spec, max_retries=3):
    for attempt in range(max_retries):
        result = critic.critique(spec)
        if result.passed:
            return spec
        
        # 自动修复
        fixed_spec = auto_fix_spec(spec, result.issues)
        spec = fixed_spec
    
    raise ValidationError("Failed to validate after retries")
```

### 5. 代码生成模块 (Code Generator)

**功能：**
- 根据规范自动生成 Handler 代码
- 生成测试代码
- 生成文档注释

**生成模板：**
```python
HANDLER_TEMPLATE = """
class {HandlerName}(ActionHandler):
    \"\"\"Handler for {capability_id}\"\"\"
    
    def execute(self, params: Dict[str, Any], context: Any) -> ActionOutput:
        # 参数提取
        {param_extraction}
        
        # 实现逻辑
        {implementation_logic}
        
        # 返回结果
        return {{
            {output_mapping}
        }}
    
    def _create_undo_closure(self, ...):
        # 撤销逻辑
        {undo_logic}
"""
```

### 6. 自动注册模块 (Auto Register)

**功能：**
- 保存 YAML 规范到 validated 目录
- 保存 Handler 代码到 stdlib 目录
- 更新 loader.py 注册映射
- 触发运行时重新加载

**注册流程：**
```python
async def auto_register(capability_spec, handler_code):
    # 1. 保存规范
    spec_path = save_spec(capability_spec)
    
    # 2. 保存 Handler
    handler_path = save_handler(handler_code)
    
    # 3. 更新 loader.py
    update_loader_registry(capability_spec['meta']['id'], handler_class_name)
    
    # 4. 验证注册
    verify_registration(capability_spec['meta']['id'])
    
    return {
        "spec_path": spec_path,
        "handler_path": handler_path,
        "registered": True
    }
```

---

## 🚀 完整工作流程

```python
async def auto_create_capability(requirement: str, context: dict):
    """
    自动化创建能力的完整流程
    """
    
    # 步骤 1: 理解需求
    print("📝 步骤 1: 解析需求...")
    parsed_req = await understand_requirement(requirement, context)
    
    # 步骤 2: 信息补充
    if parsed_req['missing_info']:
        print("🔍 步骤 2: 搜索补充信息...")
        enrichment = await enrich_requirement(parsed_req)
        parsed_req.update(enrichment)
    
    # 步骤 3: 生成规范
    print("📋 步骤 3: 生成能力规范...")
    spec = await generate_spec(parsed_req)
    
    # 步骤 4: 验证规范
    print("✅ 步骤 4: 验证规范...")
    validated_spec = await validate_with_retry(spec)
    
    # 步骤 5: 生成代码
    print("💻 步骤 5: 生成 Handler 代码...")
    handler_code = await generate_handler(validated_spec)
    
    # 步骤 6: 生成测试
    print("🧪 步骤 6: 生成测试代码...")
    test_code = await generate_tests(validated_spec, handler_code)
    
    # 步骤 7: 自动注册
    print("📦 步骤 7: 自动注册...")
    registration_result = await auto_register(validated_spec, handler_code)
    
    # 步骤 8: 运行测试
    print("🔬 步骤 8: 运行测试...")
    test_result = await run_tests(test_code)
    
    if test_result.passed:
        print("✅ 能力创建成功！")
        return {
            "success": True,
            "capability_id": validated_spec['meta']['id'],
            "spec_path": registration_result['spec_path'],
            "handler_path": registration_result['handler_path']
        }
    else:
        print("❌ 测试失败，需要人工审查")
        return {
            "success": False,
            "errors": test_result.errors
        }
```

---

## 🔧 实现细节

### 1. 网络搜索集成

```python
async def web_search(query: str) -> List[Dict]:
    """
    使用搜索引擎 API 搜索相关信息
    """
    # 可以使用：
    # - Google Custom Search API
    # - Bing Search API
    # - DuckDuckGo API
    # - 或者使用 LLM 的搜索能力（如 Claude with web access）
    
    results = await search_api.search(query, max_results=5)
    return [
        {
            "title": r.title,
            "url": r.url,
            "snippet": r.snippet,
            "content": r.content  # 如果可获取
        }
        for r in results
    ]
```

### 2. 自动修复机制

```python
def auto_fix_spec(spec: Dict, issues: List[Dict]) -> Dict:
    """
    根据验证问题自动修复规范
    """
    fixed_spec = spec.copy()
    
    for issue in issues:
        if issue['category'] == 'atomicity':
            # 如果不够原子，尝试拆分
            fixed_spec = split_capability(fixed_spec)
        
        elif issue['category'] == 'types':
            # 如果类型不明确，使用 LLM 推断类型
            fixed_spec = infer_types(fixed_spec)
        
        elif issue['category'] == 'reversibility':
            # 如果缺少撤销策略，生成撤销策略
            fixed_spec = generate_undo_strategy(fixed_spec)
    
    return fixed_spec
```

### 3. Handler 代码生成

```python
async def generate_handler(spec: Dict) -> str:
    """
    根据规范生成 Handler 代码
    """
    prompt = f"""
    根据以下能力规范，生成 Python Handler 代码：
    
    {yaml.dump(spec)}
    
    要求：
    1. 继承自 ActionHandler
    2. 实现 execute 方法
    3. 实现撤销逻辑（如果适用）
    4. 包含完整的类型注解
    5. 包含错误处理
    6. 符合 Python 最佳实践
    
    只返回代码，不要返回其他内容。
    """
    
    code = await llm.generate_code(prompt)
    return code
```

### 4. 测试代码生成

```python
async def generate_tests(spec: Dict, handler_code: str) -> str:
    """
    生成测试代码
    """
    prompt = f"""
    为以下 Handler 生成完整的 pytest 测试：
    
    规范：{yaml.dump(spec)}
    代码：{handler_code}
    
    要求：
    1. 测试正常情况
    2. 测试边界情况
    3. 测试错误情况
    4. 测试撤销功能（如果适用）
    5. 测试类型验证
    
    使用 pytest 和 pytest-asyncio。
    """
    
    test_code = await llm.generate_code(prompt)
    return test_code
```

---

## 📊 系统优势

### 1. **完全自动化**
- 从需求到注册，全程无需人工干预
- 自动处理错误和重试

### 2. **智能增强**
- 网络搜索补充信息
- 自动修复验证问题
- 生成高质量代码

### 3. **质量保证**
- 多轮验证确保规范正确
- 自动生成测试代码
- 运行测试验证实现

### 4. **可扩展性**
- 模块化设计，易于扩展
- 支持自定义生成模板
- 支持多种代码生成策略

---

## 🎯 使用示例

### 示例 1: 简单需求

```python
# 用户输入
requirement = "我需要一个能力来发送 Slack 消息"

# 系统自动处理
result = await auto_create_capability(
    requirement=requirement,
    context={"user_id": "user123"}
)

# 输出
{
    "success": True,
    "capability_id": "comm.slack.send_message",
    "spec_path": "capabilities/validated/stdlib/comm_slack_send_message.yaml",
    "handler_path": "src/runtime/stdlib/comm_handlers.py"
}
```

### 示例 2: 复杂需求（需要信息补充）

```python
# 用户输入
requirement = "我需要一个能力来调用 OpenAI API 生成图片"

# 系统自动：
# 1. 解析需求
# 2. 发现缺少 API 格式信息 → 网络搜索
# 3. 生成规范
# 4. 验证规范
# 5. 生成代码
# 6. 注册

result = await auto_create_capability(requirement, context)
```

### 示例 3: 批量创建

```python
requirements = [
    "发送邮件",
    "创建 GitHub Issue",
    "查询数据库",
    "上传文件到 S3"
]

results = await batch_create_capabilities(requirements)
```

---

## 🔒 安全与质量控制

### 1. **人工审查点**
- 高风险操作（如删除、系统执行）需要人工确认
- 测试失败的能力需要人工审查
- 自动修复超过 3 次的能力需要人工介入

### 2. **质量检查**
- 代码复杂度检查
- 安全漏洞扫描
- 性能基准测试

### 3. **回滚机制**
- 如果新能力导致问题，自动回滚
- 保留所有版本的规范和代码

---

## 📈 未来扩展

### 1. **多语言支持**
- 支持从多种自然语言生成能力
- 自动翻译规范描述

### 2. **能力组合**
- 自动识别可以组合的能力
- 生成组合能力的规范

### 3. **智能推荐**
- 根据使用模式推荐新能力
- 自动发现缺失的能力

### 4. **社区贡献**
- 自动提交到能力仓库
- 社区审查和合并

---

## 🛠️ 实现优先级

### Phase 1: 核心功能（MVP）
1. ✅ 需求理解模块
2. ✅ 规范生成模块（基于现有 generator）
3. ✅ 规范验证模块（基于现有 critic）
4. ✅ 代码生成模块
5. ✅ 自动注册模块

### Phase 2: 增强功能
1. ⏳ 网络搜索集成
2. ⏳ 自动修复机制
3. ⏳ 测试代码生成
4. ⏳ 批量创建支持

### Phase 3: 高级功能
1. ⏳ 智能推荐
2. ⏳ 能力组合
3. ⏳ 社区集成
4. ⏳ 多语言支持

---

## 📝 总结

这个自动化系统将实现：

1. **从需求到能力的全自动转换**
2. **智能信息补充和增强**
3. **高质量代码自动生成**
4. **完整的质量保证流程**
5. **无缝的注册和集成**

**核心价值：**
- 🚀 **速度**：从需求到可用能力，分钟级完成
- 🎯 **质量**：自动验证和测试，确保质量
- 🔄 **迭代**：自动修复和重试，持续优化
- 📈 **扩展**：无限扩展能力，无需人工编码
