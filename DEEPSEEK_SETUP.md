# DeepSeek API 配置指南

## 🚀 快速开始

### 步骤 1: 设置 DeepSeek API Key

```bash
export DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

### 步骤 2: 使用 DeepSeek 生成能力

```bash
# 自动检测（推荐）
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --reference docs/github_api_reference.md

# 或明确指定 DeepSeek
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --provider deepseek \
  --reference docs/github_api_reference.md
```

## 📋 完整示例

### 生成 GitHub API 能力（使用 DeepSeek）

```bash
# 1. 设置 API Key
export DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 2. 生成能力
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --provider deepseek \
  --reference docs/github_api_reference.md \
  --verbose
```

## 🔧 配置说明

### 自动检测模式（默认）

AutoForge 会自动检测可用的 API Key：

1. 如果设置了 `DEEPSEEK_API_KEY`，使用 DeepSeek
2. 如果设置了 `OPENAI_API_KEY`，使用 OpenAI
3. 如果两者都设置了，优先使用 DeepSeek

### 明确指定提供商

```bash
# 使用 DeepSeek
./forge create "你的需求" --provider deepseek

# 使用 OpenAI
./forge create "你的需求" --provider openai

# 自动检测（默认）
./forge create "你的需求" --provider auto
```

## 📝 模型映射

DeepSeek 使用以下模型映射：

| OpenAI 模型 | DeepSeek 模型 |
|------------|--------------|
| gpt-4o-mini | deepseek-chat |
| gpt-4o | deepseek-chat |
| gpt-4 | deepseek-chat |
| gpt-3.5-turbo | deepseek-chat |

默认使用 `deepseek-chat` 模型。

## 🎯 使用示例

### 示例 1: 基础使用

```bash
export DEEPSEEK_API_KEY=your_key
./forge create "获取比特币价格" --id "net.crypto.get_price"
```

### 示例 2: 带参考文档

```bash
export DEEPSEEK_API_KEY=your_key
./forge create "调用公司 API" \
  --reference ./docs/api.md \
  --provider deepseek
```

### 示例 3: TDD 模式

```bash
export DEEPSEEK_API_KEY=your_key
./forge create "处理 CSV 文件" \
  --test-first \
  --provider deepseek
```

### 示例 4: 更新能力

```bash
export DEEPSEEK_API_KEY=your_key
./forge update net.crypto.get_price \
  "添加缓存机制" \
  --provider deepseek
```

## ⚙️ 环境变量

### DeepSeek

```bash
export DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

### OpenAI（如果同时使用）

```bash
export OPENAI_API_KEY=your_openai_api_key_here
```

## 🔍 验证配置

### 检查 API Key

```bash
# 检查 DeepSeek
echo $DEEPSEEK_API_KEY

# 检查 OpenAI
echo $OPENAI_API_KEY
```

### 测试连接

运行一个简单的生成命令来测试：

```bash
./forge create "测试" --dry-run --provider deepseek
```

## 💡 最佳实践

1. **使用自动检测模式**
   - 设置 `DEEPSEEK_API_KEY` 后，默认会自动使用 DeepSeek
   - 无需每次都指定 `--provider deepseek`

2. **在脚本中设置**
   ```bash
   #!/bin/bash
   export DEEPSEEK_API_KEY=your_key
   ./forge create "你的需求"
   ```

3. **在 Cursor 中设置**
   - Cursor Settings -> Environment Variables
   - 添加 `DEEPSEEK_API_KEY`

## 🐛 故障排除

### 问题 1: 提示 "DEEPSEEK_API_KEY not set"

**解决：**
```bash
export DEEPSEEK_API_KEY=your_key_here
```

### 问题 2: 仍然使用 OpenAI

**解决：**
```bash
# 明确指定提供商
./forge create "你的需求" --provider deepseek

# 或检查环境变量
echo $DEEPSEEK_API_KEY
```

### 问题 3: API 调用失败

**解决：**
- 检查 API Key 是否正确
- 检查网络连接
- 查看 DeepSeek API 文档确认端点

## 📚 相关文档

- [DeepSeek API 文档](https://platform.deepseek.com/api-docs/)
- [AutoForge 用户指南](docs/AUTOFORGE_USER_GUIDE.md)
- [快速开始](QUICKSTART_AUTOFORGE.md)

---

**现在可以使用 DeepSeek API 来生成能力了！🚀**
