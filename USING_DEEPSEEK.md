# 使用 DeepSeek 生成能力 - 完整指南

## 🚀 快速开始（3 步）

### 步骤 1: 设置环境

```bash
# 运行环境设置脚本（会自动创建/激活虚拟环境并安装依赖）
./setup_autoforge.sh
```

### 步骤 2: 设置 DeepSeek API Key

```bash
export DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

### 步骤 3: 生成能力

```bash
# 使用包装器脚本（自动处理虚拟环境）
./forge_wrapper.sh create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --provider deepseek \
  --reference docs/github_api_reference.md
```

---

## 📋 完整命令示例

### 生成 GitHub API 能力

```bash
# 1. 确保虚拟环境已激活
source venv/bin/activate

# 2. 设置 API Key
export DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 3. 生成能力
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --provider deepseek \
  --reference docs/github_api_reference.md \
  --verbose
```

### 使用便捷脚本

```bash
# 使用包装器（推荐，自动处理虚拟环境）
./forge_wrapper.sh create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --provider deepseek \
  --reference docs/github_api_reference.md
```

---

## 🔧 环境设置

### 方法 1: 使用设置脚本（推荐）

```bash
./setup_autoforge.sh
```

这个脚本会：
- ✅ 检查/创建虚拟环境
- ✅ 激活虚拟环境
- ✅ 安装所有依赖
- ✅ 验证安装

### 方法 2: 手动设置

```bash
# 1. 创建虚拟环境（如果还没有）
python3 -m venv venv

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 安装依赖
pip install openai pyyaml httpx pydantic
```

---

## 💡 使用建议

### 推荐工作流

1. **每次使用前激活虚拟环境**
   ```bash
   source venv/bin/activate
   ```

2. **使用包装器脚本（自动处理）**
   ```bash
   ./forge_wrapper.sh create "你的需求"
   ```

3. **设置 API Key**
   ```bash
   export DEEPSEEK_API_KEY=your_key
   ```

### 在 Cursor 中设置

1. 打开 Cursor 设置
2. 搜索 "Environment Variables"
3. 添加：
   - `DEEPSEEK_API_KEY` = `your_deepseek_api_key`

---

## 🎯 完整示例

### 生成 GitHub API 能力（完整流程）

```bash
# 1. 设置环境（首次使用）
./setup_autoforge.sh

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 设置 API Key
export DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 4. 生成能力
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --provider deepseek \
  --reference docs/github_api_reference.md \
  --verbose

# 5. 查看生成的文件
cat capabilities/validated/generated/net.github.get_repo.yaml
cat src/runtime/stdlib/generated/net_github_get_repo.py
```

---

## 🐛 故障排除

### 问题 1: ModuleNotFoundError: No module named 'openai'

**解决：**
```bash
# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install openai pyyaml httpx pydantic
```

### 问题 2: 命令找不到

**解决：**
```bash
# 使用包装器脚本
./forge_wrapper.sh create "你的需求"

# 或确保在项目根目录
cd /Users/daniel/AI项目/云端同步项目/ai-first-runtime-master
```

### 问题 3: DEEPSEEK_API_KEY not set

**解决：**
```bash
export DEEPSEEK_API_KEY=your_key_here
```

---

## 📚 相关文档

- [DeepSeek 配置指南](DEEPSEEK_SETUP.md)
- [快速开始](QUICKSTART_DEEPSEEK.md)
- [生成 GitHub 能力指南](GENERATE_GITHUB_CAPABILITY.md)

---

**现在可以开始使用 DeepSeek 生成能力了！🚀**
