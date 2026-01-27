# AutoForge 用户体验设计文档

## 🎯 设计理念

AutoForge 的用户体验设计遵循以下核心原则：

1. **零学习曲线** - 用户无需学习复杂语法，用自然语言即可
2. **即时反馈** - 每个步骤都有清晰的进度提示
3. **错误友好** - 错误信息不仅说明问题，还提供解决方案
4. **渐进式披露** - 基础功能简单，高级功能可选
5. **可预测性** - 用户能清楚知道会发生什么

---

## 📱 用户旅程

### 阶段 1: 发现 (Discovery)

**用户目标：** 了解 AutoForge 能做什么

**体验设计：**
- 清晰的命令帮助信息
- 示例命令展示
- 快速开始指南

```bash
$ forge create --help

Usage: forge create [OPTIONS] REQUIREMENT

Create a new capability from natural language requirement

Examples:
  forge create "获取比特币价格"
  forge create "发送 Slack 消息" --id "net.slack.send"
  forge create "读取文件" --dry-run

Options:
  --id TEXT          Capability ID (auto-generated if not provided)
  --workspace PATH    Workspace root directory
  --context JSON      Additional context as JSON string
  --dry-run          Preview without saving files
  --verbose          Show detailed progress
  --model TEXT       LLM model to use (default: gpt-4o-mini)
  --retries INTEGER  Maximum retries for validation (default: 3)
```

### 阶段 2: 首次使用 (First Use)

**用户目标：** 成功创建第一个能力

**体验设计：**
- 自动检测环境（API 密钥）
- 友好的错误提示
- 清晰的下一步指引

```bash
$ forge create "获取比特币价格"

⚠️  Warning: OPENAI_API_KEY not set.
   Set it with: export OPENAI_API_KEY=your_key_here

Continue anyway? [y/N]: n
```

### 阶段 3: 日常使用 (Daily Use)

**用户目标：** 高效创建多个能力

**体验设计：**
- 快速执行（默认不显示详细信息）
- 批量操作支持
- 结果清晰展示

```bash
$ forge create "获取比特币价格"

================================================================================
🔨 AutoForge - Converting Natural Language to Capability
================================================================================

📝 Requirement: 获取比特币价格

✅ Capability Forged Successfully!
================================================================================

📋 Capability Information:
   ID: net.crypto.get_price
   Name: Get Price Crypto
   Risk Level: LOW
   Operation Type: NETWORK
   Supports Undo: No

📁 Generated Files:
   📄 Spec:      capabilities/validated/generated/net.crypto.get_price.yaml
   🐍 Handler:   src/runtime/stdlib/generated/net_crypto_get_price.py
   🧪 Test:      tests/generated/test_net_crypto_get_price.py

🚀 Next Steps:
   1. Review the generated code:
      cat src/runtime/stdlib/generated/net_crypto_get_price.py
   2. Run tests:
      pytest tests/generated/test_net_crypto_get_price.py
   3. Commit to Git:
      git add capabilities/validated/generated/net.crypto.get_price.yaml ...
      git commit -m 'feat: add net.crypto.get_price capability'
```

### 阶段 4: 高级使用 (Advanced Use)

**用户目标：** 处理复杂场景和调试

**体验设计：**
- 详细模式（--verbose）
- 预览模式（--dry-run）
- 自定义配置

```bash
$ forge create "复杂需求" --verbose --retries 5

📊 Starting pipeline...
   Phase 1: Parsing requirement...
   ✓ Extracted action: complex_action
   ✓ Extracted target: complex_target
   ...
```

---

## 🎨 交互设计细节

### 1. 进度指示

**设计原则：** 用户应该始终知道系统在做什么

**实现：**
- 使用 emoji 图标增强可读性
- 分阶段显示进度
- 显示耗时信息

```
🔨 Starting AutoForge pipeline...
📝 Phase 1: Parsing requirement...     [正在执行]
🔧 Phase 2: Generating specification... [等待]
✅ Phase 3: Validating specification... [完成]
💻 Phase 4: Generating handler code... [等待]
🧪 Phase 5: Generating test code...     [等待]
```

### 2. 错误处理

**设计原则：** 错误是学习的机会

**实现：**
- 错误分类（API、验证、解析等）
- 针对性的解决建议
- 可选的详细堆栈信息

```
❌ Error: Capability Generation Failed
================================================================================

💬 Error Message: Failed to generate valid spec after 3 attempts

💡 Suggestions:
  • Try rephrasing your requirement to be more specific
  • Use --verbose to see detailed validation issues
  • Check if your requirement involves destructive operations
  • Try increasing retries: --retries 5

💡 Run with --verbose for detailed error information
```

### 3. 成功反馈

**设计原则：** 成功应该明确且有用

**实现：**
- 清晰的成功标识
- 关键信息摘要
- 明确的下一步行动

```
✅ Capability Forged Successfully!

📋 Capability Information:
   ID: net.crypto.get_price
   Risk Level: LOW
   ...

🚀 Next Steps:
   1. Review the generated code
   2. Run tests
   3. Commit to Git
```

### 4. 预览模式

**设计原则：** 让用户先确认再保存

**实现：**
- `--dry-run` 模式
- 格式化输出
- 文件路径预览

```bash
$ forge create "需求" --dry-run

📋 Generated Spec (YAML):
================================================================================
id: net.crypto.get_price
name: Get Price Crypto
...

🐍 Generated Handler Code:
================================================================================
from runtime.handler import ActionHandler
...
```

---

## 🔄 用户反馈循环

### 快速反馈

- **即时验证** - 检查 API 密钥、参数格式
- **进度更新** - 每个阶段完成后立即显示
- **错误捕获** - 立即显示错误，不等到最后

### 延迟反馈

- **LLM 调用** - 显示"正在生成..."提示
- **文件保存** - 批量保存后统一显示结果
- **验证过程** - 显示验证步骤和结果

---

## 🎯 可访问性考虑

### 1. 命令行友好

- 支持所有常见 shell（bash, zsh, fish）
- 清晰的帮助信息
- 合理的默认值

### 2. 视觉辅助

- Emoji 图标（可选的，不影响功能）
- 颜色编码（错误=红色，成功=绿色）
- 结构化输出（表格、列表）

### 3. 国际化准备

- 支持中文需求描述
- 错误消息可本地化
- 文档多语言支持

---

## 📊 性能体验

### 1. 响应时间

- **即时反馈** < 100ms（参数验证、帮助信息）
- **LLM 调用** 5-30s（取决于模型和复杂度）
- **文件保存** < 1s

### 2. 超时处理

- LLM 调用超时：60s
- 自动重试：最多 3 次
- 用户可取消：Ctrl+C

### 3. 资源使用

- 内存占用：< 100MB
- 磁盘空间：每个能力约 10-50KB
- 网络：仅 LLM API 调用

---

## 🚀 未来改进方向

### 1. 交互式模式

```bash
$ forge create --interactive

? Enter your requirement: 
> 获取比特币价格

? Capability ID (press Enter for auto-generated):
> net.crypto.get_price

? Additional context (optional, JSON format):
> {"currency": "USD"}

? Generate test code? (Y/n):
> Y

Generating...
```

### 2. 批量模式

```bash
$ forge create --batch requirements.txt

Processing 10 requirements...
[1/10] ✓ net.crypto.get_price
[2/10] ✓ net.slack.send_message
...
```

### 3. Web UI（未来）

- 可视化编辑器
- 实时预览
- 拖拽式配置

---

## 📝 总结

AutoForge 的用户体验设计目标是：

1. **简单** - 一句话就能创建能力
2. **清晰** - 每个步骤都有反馈
3. **友好** - 错误有解决方案
4. **高效** - 快速完成常见任务
5. **灵活** - 支持高级用法

通过这些设计，我们希望用户能够：
- 在 5 分钟内完成首次使用
- 在 1 分钟内创建日常能力
- 在遇到问题时快速找到解决方案
