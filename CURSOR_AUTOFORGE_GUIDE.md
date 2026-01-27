# 在 Cursor 中体验 AutoForge

## 🎯 快速开始（3 步）

### 步骤 1: 设置环境变量

在 Cursor 的终端中执行：

```bash
export OPENAI_API_KEY=your_openai_api_key_here
```

或者在 Cursor 设置中添加环境变量：
- 打开 Cursor 设置
- 搜索 "Environment Variables"
- 添加 `OPENAI_API_KEY`

### 步骤 2: 运行快速体验脚本

```bash
python3 test_autoforge_quick.py
```

脚本会引导你完成整个体验过程。

### 步骤 3: 查看生成结果

生成的文件会保存在：
- `capabilities/validated/generated/` - 规范文件
- `src/runtime/stdlib/generated/` - 处理器代码
- `tests/generated/` - 测试代码

---

## 🚀 三种使用方式

### 方式 1: 快速体验脚本（最简单）

```bash
python3 test_autoforge_quick.py
```

**特点：**
- ✅ 交互式引导
- ✅ 自动检查环境
- ✅ 示例可选
- ✅ 一键体验

### 方式 2: CLI 命令（最灵活）

```bash
# 使用项目根目录的 forge 脚本
./forge create "你的需求"

# 示例
./forge create "获取 CoinGecko 的比特币价格" --id "net.crypto.get_price"
```

**特点：**
- ✅ 完整的命令行选项
- ✅ 支持所有高级功能
- ✅ 适合自动化脚本

### 方式 3: 在 Cursor AI 中直接对话

在 Cursor 的 AI 聊天窗口中：

```
请使用 AutoForge 创建一个能力：获取 CoinGecko 的比特币价格
```

或者：

```
帮我生成一个能力，需求是：从 GitHub API 获取仓库信息
```

**特点：**
- ✅ 自然语言交互
- ✅ 无需记忆命令
- ✅ AI 助手自动调用

---

## 📝 完整体验示例

### 示例 1: 基础能力生成

```bash
# 1. 运行体验脚本
python3 test_autoforge_quick.py

# 2. 选择示例 1（获取比特币价格）

# 3. 查看生成的文件
cat capabilities/validated/generated/net.crypto.get_price.yaml
cat src/runtime/stdlib/generated/net_crypto_get_price.py
```

### 示例 2: 使用 CLI 命令

```bash
# 预览模式（不保存）
./forge create "获取比特币价格" --dry-run

# 实际生成
./forge create "获取比特币价格" --id "net.crypto.get_price" --verbose

# 查看结果
ls -la capabilities/validated/generated/
ls -la src/runtime/stdlib/generated/
```

### 示例 3: 带参考文档

```bash
# 1. 创建参考文档
mkdir -p docs
cat > docs/coingecko_api.md << 'EOF'
# CoinGecko API 文档

## 获取价格
GET https://api.coingecko.com/api/v3/simple/price

参数:
- ids: 币种ID (如 bitcoin)
- vs_currencies: 计价货币 (如 usd)

示例:
GET /api/v3/simple/price?ids=bitcoin&vs_currencies=usd
EOF

# 2. 使用参考文档生成
./forge create "获取比特币价格" \
  --reference docs/coingecko_api.md \
  --id "net.crypto.get_price"
```

### 示例 4: TDD 模式

```bash
# 先生成测试，再生成实现
./forge create "处理 CSV 文件" --test-first

# 查看生成的测试
cat tests/generated/test_*.py
```

### 示例 5: 更新现有能力

```bash
# 1. 先创建一个能力
./forge create "获取价格" --id "net.crypto.get_price"

# 2. 更新它
./forge update net.crypto.get_price \
  "添加缓存机制，缓存时间 5 分钟" \
  --preview

# 3. 确认更新
./forge update net.crypto.get_price "添加缓存机制"
```

---

## 🔍 验证生成结果

### 检查文件结构

```bash
# 查看生成的所有文件
find . -path "*/generated/*" -type f

# 查看规范
cat capabilities/validated/generated/net.crypto.get_price.yaml

# 查看代码
cat src/runtime/stdlib/generated/net_crypto_get_price.py

# 查看测试
cat tests/generated/test_net_crypto_get_price.py
```

### 验证代码质量

```bash
# 语法检查
python3 -m py_compile src/runtime/stdlib/generated/net_crypto_get_price.py

# 运行测试（需要先安装依赖）
pip install httpx pytest
pytest tests/generated/test_net_crypto_get_price.py -v
```

---

## 💡 在 Cursor 中的最佳实践

### 1. 使用 Cursor 的 AI 助手

直接在聊天窗口说：
- "帮我创建一个获取比特币价格的能力"
- "使用 AutoForge 生成一个 Slack 消息发送能力"
- "创建一个文件读取能力，使用 TDD 模式"

### 2. 利用 Cursor 的代码补全

在终端中输入 `./forge` 后，Cursor 会自动补全命令选项。

### 3. 使用 Cursor 的文件预览

生成后，直接在 Cursor 中打开生成的文件查看：
- `capabilities/validated/generated/*.yaml`
- `src/runtime/stdlib/generated/*.py`
- `tests/generated/test_*.py`

### 4. 集成到工作流

在 Cursor 中创建任务：
1. 创建能力
2. 审查代码
3. 运行测试
4. 提交到 Git

---

## 🐛 常见问题

### Q: 提示 "No module named 'forge'"

**解决：**
```bash
# 确保在项目根目录
cd /Users/daniel/AI项目/云端同步项目/ai-first-runtime-master

# 使用 PYTHONPATH
PYTHONPATH=src:tools python3 tools/forge/cli.py create "你的需求"
```

### Q: API Key 未设置

**解决：**
```bash
# 方法 1: 环境变量
export OPENAI_API_KEY=your_key_here

# 方法 2: 在 Cursor 设置中添加
# Settings -> Environment Variables -> 添加 OPENAI_API_KEY
```

### Q: 生成失败

**解决：**
```bash
# 使用 --verbose 查看详细信息
./forge create "你的需求" --verbose

# 增加重试次数
./forge create "你的需求" --retries 5

# 使用更强大的模型
./forge create "你的需求" --model "gpt-4"
```

---

## 📚 相关文档

- [完整用户指南](docs/AUTOFORGE_USER_GUIDE.md)
- [优化功能文档](docs/AUTOFORGE_OPTIMIZATIONS.md)
- [模板库](docs/AUTOFORGE_PROMPTS_LIBRARY.md)
- [快速开始](QUICKSTART_AUTOFORGE.md)

---

## 🎉 开始体验

现在就运行：

```bash
python3 test_autoforge_quick.py
```

或者：

```bash
./forge create "获取 CoinGecko 的比特币价格"
```

**享受 AutoForge 的强大功能！🚀**
