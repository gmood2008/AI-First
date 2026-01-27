# AutoForge 快速体验指南

## 🚀 在 Cursor 中体验自动化能力生成

### 前置准备

1. **确保已安装依赖**
```bash
# 在项目根目录执行
pip install openai pyyaml pydantic
```

2. **设置 OpenAI API Key**
```bash
export OPENAI_API_KEY=your_api_key_here
```

或者在 Cursor 中设置环境变量。

---

## 📝 方法一：直接使用 Python 脚本（推荐）

### 步骤 1: 创建测试脚本

在项目根目录创建 `test_autoforge_quick.py`：

```python
#!/usr/bin/env python3
"""快速体验 AutoForge"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from forge.auto.pipeline import AutoForge

def main():
    # 初始化 AutoForge
    autoforge = AutoForge(model="gpt-4o-mini", max_retries=3)
    
    # 示例 1: 简单需求
    print("=" * 80)
    print("示例 1: 获取比特币价格")
    print("=" * 80)
    
    requirement = "获取 CoinGecko 的比特币价格"
    result = autoforge.forge_capability(
        requirement=requirement,
        capability_id="net.crypto.get_price"
    )
    
    print(f"\n✅ 生成成功！")
    print(f"能力 ID: {result.capability_id}")
    print(f"风险等级: {result.spec.risk.level.value}")
    print(f"\n生成的文件:")
    print(f"  - {result.spec_path}")
    print(f"  - {result.handler_path}")
    print(f"  - {result.test_path}")
    
    # 保存文件（可选）
    save = input("\n是否保存文件到磁盘？[y/N]: ")
    if save.lower() == 'y':
        workspace = Path.cwd()
        (workspace / result.spec_path).parent.mkdir(parents=True, exist_ok=True)
        (workspace / result.handler_path).parent.mkdir(parents=True, exist_ok=True)
        (workspace / result.test_path).parent.mkdir(parents=True, exist_ok=True)
        
        (workspace / result.spec_path).write_text(result.spec_yaml)
        (workspace / result.handler_path).write_text(result.handler_code)
        (workspace / result.test_path).write_text(result.test_code)
        
        print("✅ 文件已保存！")

if __name__ == "__main__":
    main()
```

### 步骤 2: 运行脚本

在 Cursor 终端中执行：

```bash
python3 test_autoforge_quick.py
```

---

## 📝 方法二：使用 CLI 命令

### 步骤 1: 创建 forge 命令别名

在项目根目录创建 `forge` 脚本：

```bash
#!/bin/bash
# forge 命令包装器

cd "$(dirname "$0")"
python3 tools/forge/cli.py "$@"
```

### 步骤 2: 赋予执行权限

```bash
chmod +x forge
```

### 步骤 3: 使用命令

```bash
# 预览模式（不保存文件）
./forge create "获取 CoinGecko 的比特币价格" --dry-run

# 实际生成
./forge create "获取 CoinGecko 的比特币价格" --id "net.crypto.get_price"

# 带参考文档
./forge create "调用公司 OA API" \
  --reference ./docs/api_docs.md \
  --id "net.oa.get_user"

# TDD 模式
./forge create "处理 CSV 文件" --test-first
```

---

## 📝 方法三：在 Cursor 中使用 AI 助手

### 直接对话体验

在 Cursor 的 AI 聊天窗口中，你可以直接说：

```
请使用 AutoForge 创建一个能力：获取 CoinGecko 的比特币价格
```

或者：

```
帮我生成一个能力，需求是：从 GitHub API 获取仓库信息，需要 OAuth token
```

---

## 🎯 完整体验流程

### 1. 基础体验（5 分钟）

```bash
# 1. 设置 API Key
export OPENAI_API_KEY=your_key_here

# 2. 运行快速测试
python3 test_autoforge_quick.py

# 3. 查看生成的文件
cat capabilities/validated/generated/net.crypto.get_price.yaml
cat src/runtime/stdlib/generated/net_crypto_get_price.py
```

### 2. 进阶体验（10 分钟）

```bash
# 1. 使用参考文档
echo "# CoinGecko API
GET https://api.coingecko.com/api/v3/simple/price
Params: ids=bitcoin, vs_currencies=usd" > docs/coingecko_api.md

./forge create "获取比特币价格" \
  --reference docs/coingecko_api.md \
  --id "net.crypto.get_price"

# 2. TDD 模式
./forge create "处理 CSV 文件" --test-first

# 3. 更新现有能力
./forge update net.crypto.get_price \
  "添加缓存机制，缓存时间 5 分钟" \
  --preview
```

### 3. 完整工作流（20 分钟）

```bash
# 1. 创建能力
./forge create "从 Slack API 发送消息" \
  --reference docs/slack_api.md \
  --id "net.slack.send_message"

# 2. 查看依赖
# (在输出中自动显示)

# 3. 安装依赖
pip install httpx

# 4. 运行测试
pytest tests/generated/test_net_slack_send_message.py

# 5. 查看生成的代码
code src/runtime/stdlib/generated/net_slack_send_message.py
```

---

## 🔍 验证生成结果

### 检查生成的文件

```bash
# 查看规范
cat capabilities/validated/generated/net.crypto.get_price.yaml

# 查看处理器代码
cat src/runtime/stdlib/generated/net_crypto_get_price.py

# 查看测试代码
cat tests/generated/test_net_crypto_get_price.py
```

### 验证代码质量

```bash
# 语法检查
python3 -m py_compile src/runtime/stdlib/generated/net_crypto_get_price.py

# 运行测试
pytest tests/generated/test_net_crypto_get_price.py -v
```

---

## 💡 常见问题

### Q: 提示 "OPENAI_API_KEY not set"

**解决：**
```bash
export OPENAI_API_KEY=your_key_here
```

或在 Cursor 设置中添加环境变量。

### Q: 导入错误 "No module named 'forge'"

**解决：**
```bash
# 确保在项目根目录
cd /Users/daniel/AI项目/云端同步项目/ai-first-runtime-master

# 使用 Python 路径
PYTHONPATH=src:tools python3 tools/forge/cli.py create "你的需求"
```

### Q: 生成失败，提示验证错误

**解决：**
```bash
# 使用 --verbose 查看详细信息
./forge create "你的需求" --verbose

# 增加重试次数
./forge create "你的需求" --retries 5
```

---

## 🎨 推荐体验场景

### 场景 1: 简单 API 调用
```bash
./forge create "从 CoinGecko 获取比特币价格"
```

### 场景 2: 文件操作
```bash
./forge create "读取 CSV 文件并转换为 JSON"
```

### 场景 3: 带参考文档
```bash
# 先创建参考文档
cat > docs/api_example.md << EOF
# API 文档示例
Endpoint: GET /api/v1/data
Auth: Bearer token
EOF

./forge create "调用 API 获取数据" --reference docs/api_example.md
```

### 场景 4: TDD 模式
```bash
./forge create "处理用户输入验证" --test-first
```

---

## 📚 下一步

- 阅读 [完整用户指南](docs/AUTOFORGE_USER_GUIDE.md)
- 查看 [优化功能文档](docs/AUTOFORGE_OPTIMIZATIONS.md)
- 参考 [模板库](docs/AUTOFORGE_PROMPTS_LIBRARY.md)

---

**开始体验 AutoForge 的强大功能吧！🚀**
