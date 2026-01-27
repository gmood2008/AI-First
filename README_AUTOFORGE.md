# AutoForge 使用指南 - DeepSeek 版本

## ✅ 环境已就绪

依赖已安装完成！现在可以使用 DeepSeek 生成能力了。

---

## 🚀 立即开始（2 步）

### 步骤 1: 设置 DeepSeek API Key

```bash
export DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

### 步骤 2: 生成 GitHub API 能力

```bash
# 使用 forge 命令（自动处理虚拟环境）
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --provider deepseek \
  --reference docs/github_api_reference.md
```

---

## 📝 完整命令

### 基础使用

```bash
# 激活虚拟环境（如果还没激活）
source venv/bin/activate

# 设置 API Key
export DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 生成能力
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --provider deepseek \
  --reference docs/github_api_reference.md \
  --verbose
```

### 预览模式（不保存文件）

```bash
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --provider deepseek \
  --reference docs/github_api_reference.md \
  --dry-run
```

---

## 🔧 已安装的依赖

✅ openai: 2.15.0  
✅ pyyaml: 已安装  
✅ httpx: 0.28.1  
✅ pydantic: 2.12.5  

---

## 💡 使用提示

1. **forge 脚本已自动处理虚拟环境**
   - 无需手动激活 `venv`
   - 直接运行 `./forge` 即可

2. **自动检测 DeepSeek**
   - 如果设置了 `DEEPSEEK_API_KEY`，默认使用 DeepSeek
   - 无需每次都指定 `--provider deepseek`

3. **在 Cursor 中使用**
   - 可以在 Cursor 的终端直接运行命令
   - 或在 AI 聊天窗口说："请使用 AutoForge 生成..."

---

## 🎯 现在就开始

```bash
# 设置 API Key
export DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 生成能力
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --provider deepseek \
  --reference docs/github_api_reference.md
```

---

**环境已就绪，可以开始生成了！🚀**
