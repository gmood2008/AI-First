# DeepSeek 快速开始指南

## ✅ 环境已就绪

所有代码已修改完成，现在可以使用 DeepSeek API 了！

---

## 🚀 3 步开始使用

### 步骤 1: 激活虚拟环境

```bash
source venv/bin/activate
```

### 步骤 2: 设置 DeepSeek API Key

```bash
export DEEPSEEK_API_KEY=your_real_deepseek_api_key_here
```

**获取 DeepSeek API Key：**
1. 访问 https://platform.deepseek.com
2. 注册/登录账号
3. 在 API Keys 页面创建新的 API Key
4. 复制 API Key

### 步骤 3: 生成 GitHub API 能力

```bash
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --provider deepseek \
  --reference docs/github_api_reference.md
```

---

## 📝 完整命令示例

### 使用 DeepSeek 生成 GitHub 能力

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 设置 DeepSeek API Key
export DEEPSEEK_API_KEY=your_real_deepseek_api_key_here

# 3. 生成能力
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --provider deepseek \
  --reference docs/github_api_reference.md \
  --verbose
```

### 自动检测模式（推荐）

如果设置了 `DEEPSEEK_API_KEY`，可以省略 `--provider`：

```bash
export DEEPSEEK_API_KEY=your_key

# 自动使用 DeepSeek
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --reference docs/github_api_reference.md
```

---

## 🔧 已修复的问题

✅ **导入路径问题** - 已修复  
✅ **虚拟环境支持** - forge 脚本自动激活 venv  
✅ **DeepSeek 支持** - 完全集成  
✅ **依赖安装** - 已安装所有必要依赖  

---

## 💡 使用提示

1. **forge 脚本自动处理虚拟环境**
   - 无需手动激活 `venv`
   - 直接运行 `./forge` 即可

2. **自动检测 DeepSeek**
   - 设置 `DEEPSEEK_API_KEY` 后自动使用
   - 无需每次都指定 `--provider deepseek`

3. **在 Cursor 中设置环境变量**
   - Cursor Settings -> Environment Variables
   - 添加 `DEEPSEEK_API_KEY`

---

## 🎯 现在就开始

```bash
# 设置真实的 DeepSeek API Key
export DEEPSEEK_API_KEY=your_real_deepseek_api_key_here

# 生成 GitHub API 能力
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --provider deepseek \
  --reference docs/github_api_reference.md
```

---

## 📚 相关文档

- [DeepSeek 配置指南](DEEPSEEK_SETUP.md)
- [使用 DeepSeek 指南](USING_DEEPSEEK.md)
- [生成 GitHub 能力指南](GENERATE_GITHUB_CAPABILITY.md)

---

**环境已就绪，使用真实的 DeepSeek API Key 即可开始生成能力！🚀**
