# 使用 DeepSeek 快速开始

## 🚀 3 步开始使用 DeepSeek

### 步骤 1: 设置 DeepSeek API Key

```bash
export DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

### 步骤 2: 生成 GitHub API 能力

```bash
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --provider deepseek \
  --reference docs/github_api_reference.md
```

### 步骤 3: 查看生成结果

```bash
cat capabilities/validated/generated/net.github.get_repo.yaml
cat src/runtime/stdlib/generated/net_github_get_repo.py
```

---

## 📝 完整命令（使用 DeepSeek）

### 生成 GitHub API 能力

```bash
# 设置 API Key
export DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 生成能力
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --provider deepseek \
  --reference docs/github_api_reference.md \
  --verbose
```

### 或使用便捷脚本

```bash
# 运行脚本（会自动提示输入 API Key）
./generate_github_with_deepseek.sh
```

---

## 🔧 自动检测模式（推荐）

如果设置了 `DEEPSEEK_API_KEY`，AutoForge 会自动使用 DeepSeek，无需指定 `--provider`：

```bash
export DEEPSEEK_API_KEY=your_key

# 自动使用 DeepSeek
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --reference docs/github_api_reference.md
```

---

## 📋 所有支持的命令

### create 命令

```bash
# 基础使用
./forge create "你的需求" --provider deepseek

# 带参考文档
./forge create "你的需求" \
  --reference ./docs/api.md \
  --provider deepseek

# TDD 模式
./forge create "你的需求" \
  --test-first \
  --provider deepseek
```

### update 命令

```bash
./forge update net.github.get_repo \
  "新需求" \
  --provider deepseek
```

---

## 💡 提示

1. **自动检测**：设置 `DEEPSEEK_API_KEY` 后，默认会自动使用 DeepSeek
2. **明确指定**：使用 `--provider deepseek` 明确指定
3. **模型映射**：DeepSeek 会自动将 OpenAI 模型名映射到 `deepseek-chat`

---

**现在可以使用 DeepSeek 生成能力了！🎉**
