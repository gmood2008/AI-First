# 生成 GitHub API 能力指南

## 🎯 需求
从 GitHub API 获取仓库信息，需要 OAuth token

## 🚀 生成方法

### 方法 1: 使用 CLI 命令（推荐）

#### 使用 DeepSeek（推荐）

```bash
# 1. 确保已安装依赖
pip install openai pyyaml httpx

# 2. 设置 DeepSeek API Key
export DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 3. 生成能力（自动检测 DeepSeek）
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --reference docs/github_api_reference.md

# 或明确指定 DeepSeek
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --provider deepseek \
  --reference docs/github_api_reference.md
```

#### 使用 OpenAI

```bash
# 1. 确保已安装依赖
pip install openai pyyaml httpx

# 2. 设置 OpenAI API Key
export OPENAI_API_KEY=your_openai_api_key_here

# 3. 生成能力
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --provider openai \
  --reference docs/github_api_reference.md
```

### 方法 2: 使用 Python 脚本

```bash
# 运行生成脚本
python3 generate_github_capability.py
```

### 方法 3: 在 Cursor AI 中

直接在 Cursor 的 AI 聊天窗口说：
```
请使用 AutoForge 生成一个能力：从 GitHub API 获取仓库信息，需要 OAuth token
```

## 📋 生成的文件

生成后会在以下位置创建文件：

1. **规范文件**
   - `capabilities/validated/generated/net.github.get_repo.yaml`
   - 包含完整的能力定义

2. **处理器代码**
   - `src/runtime/stdlib/generated/net_github_get_repo.py`
   - 包含实际的 API 调用逻辑

3. **测试代码**
   - `tests/generated/test_net_github_get_repo.py`
   - 包含 pytest 测试用例

## 📝 示例输出

我已经创建了示例文件，展示生成的结果结构：

- `examples/generated_github_capability_example.yaml` - 规范示例
- `examples/generated_github_handler_example.py` - 处理器代码示例

## 🔧 使用生成的能力

### 1. 安装依赖

```bash
pip install httpx
```

### 2. 运行测试

```bash
pytest tests/generated/test_net_github_get_repo.py -v
```

### 3. 在代码中使用

```python
from runtime.engine import RuntimeEngine
from runtime.types import ExecutionContext
from pathlib import Path

# 初始化运行时
engine = RuntimeEngine(...)
context = ExecutionContext(
    user_id="user1",
    workspace_root=Path("/tmp"),
    session_id="session1"
)

# 调用能力
result = engine.execute(
    "net.github.get_repo",
    {
        "owner": "octocat",
        "repo": "Hello-World",
        "token": "your_github_token"
    },
    context
)

print(result.outputs)
```

## 📚 参考文档

我已经创建了 GitHub API 参考文档：
- `docs/github_api_reference.md`

这个文档会被 AutoForge 使用，帮助生成更准确的代码。

## ⚠️ 注意事项

1. **需要 LLM API Key**
   - DeepSeek: `export DEEPSEEK_API_KEY=your_key`（推荐）
   - OpenAI: `export OPENAI_API_KEY=your_key`
   - AutoForge 会自动检测可用的 API Key

2. **需要安装依赖**
   - `pip install openai pyyaml httpx`

3. **GitHub Token**
   - 需要有效的 GitHub OAuth token
   - 可以在 GitHub Settings -> Developer settings -> Personal access tokens 创建

4. **选择提供商**
   - 使用 `--provider deepseek` 明确指定 DeepSeek
   - 使用 `--provider openai` 明确指定 OpenAI
   - 使用 `--provider auto` 或省略（自动检测）

## 🎉 开始生成

### 使用 DeepSeek（推荐）

```bash
# 设置 DeepSeek API Key
export DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 生成能力
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --provider deepseek \
  --reference docs/github_api_reference.md
```

### 使用 OpenAI

```bash
# 设置 OpenAI API Key
export OPENAI_API_KEY=your_openai_api_key_here

# 生成能力
./forge create "从 GitHub API 获取仓库信息，需要 OAuth token" \
  --id "net.github.get_repo" \
  --provider openai \
  --reference docs/github_api_reference.md
```

或者查看示例文件了解生成结果的结构！

**查看 [DeepSeek 配置指南](DEEPSEEK_SETUP.md) 了解更多详情。**
