# 远程能力加载功能

## 概述

AI-First Runtime 现在支持从 GitHub 云端动态加载能力规范（specs）。如果本地找不到某个能力的 YAML 文件，系统会自动尝试从 [ai-first-specs](https://github.com/gmood2008/ai-first-specs) 仓库加载。

## 功能特性

- ✅ **自动回退**: 本地找不到时自动从 GitHub 加载
- ✅ **缓存机制**: 加载的能力会被缓存，避免重复请求
- ✅ **离线支持**: 网络不可用时只使用本地能力
- ✅ **透明使用**: 对用户和代码完全透明，无需额外配置

## 工作原理

### 加载顺序

1. **本地优先**: 首先检查本地 `capabilities/validated/stdlib/` 目录
2. **远程回退**: 如果本地文件不存在，从 GitHub 加载
3. **缓存使用**: 远程加载的能力会被缓存，后续直接使用缓存

### 实现细节

```python
# 在 stdlib/loader.py 中
if spec_path.exists():
    # 从本地加载
    spec_dict = yaml.safe_load(open(spec_path))
else:
    # 从 GitHub 加载
    spec_dict = load_capability_from_github(capability_id)
```

## 使用示例

### 基本使用

无需任何额外配置，系统会自动使用远程加载：

```python
from runtime.registry import CapabilityRegistry
from runtime.stdlib.loader import load_stdlib
from pathlib import Path

registry = CapabilityRegistry()
specs_dir = Path("capabilities/validated/stdlib")

# 如果本地只有部分文件，缺失的会自动从 GitHub 加载
load_stdlib(registry, specs_dir)
```

### 直接使用远程加载器

```python
from runtime.remote_loader import RemoteSpecLoader

loader = RemoteSpecLoader()

# 列出 GitHub 上的所有能力
available = loader.list_available_specs()
print(f"可用能力: {available}")

# 加载特定能力
spec = loader.load_spec("io.fs.read_file")
```

### 自定义配置

```python
from runtime.remote_loader import RemoteSpecLoader

# 使用自定义仓库和分支
loader = RemoteSpecLoader(
    repo="your-org/your-specs-repo",
    branch="main",
    specs_path="capabilities/validated/stdlib",
    timeout=15.0
)
```

## 配置选项

### 环境变量

可以通过环境变量控制远程加载行为：

```bash
# 禁用远程加载（仅使用本地）
export AI_FIRST_DISABLE_REMOTE_LOADING=true

# 自定义 GitHub 仓库
export AI_FIRST_SPECS_REPO=your-org/your-repo
export AI_FIRST_SPECS_BRANCH=main
```

### 代码配置

```python
from runtime.remote_loader import RemoteSpecLoader

# 创建自定义加载器
loader = RemoteSpecLoader(
    repo="custom/repo",
    branch="dev",
    timeout=20.0
)
```

## 性能考虑

### 缓存机制

- 远程加载的能力会被缓存在内存中
- 同一会话中重复加载同一能力不会触发网络请求
- 缓存可以通过 `loader.clear_cache()` 清除

### 网络优化

- 默认超时时间：10 秒
- 支持并发加载（未来版本）
- 失败时优雅降级到本地能力

## 故障排查

### 问题：无法从 GitHub 加载

**可能原因：**
1. 网络连接问题
2. GitHub API 限流
3. 仓库路径错误

**解决方案：**
```python
# 检查网络连接
import httpx
response = httpx.get("https://api.github.com", timeout=5.0)

# 检查仓库是否存在
loader = RemoteSpecLoader()
available = loader.list_available_specs()  # 应该返回能力列表
```

### 问题：加载速度慢

**优化建议：**
1. 使用本地符号链接（推荐）
2. 定期同步 GitHub 仓库到本地
3. 增加缓存使用

## 最佳实践

### 1. 开发环境

使用符号链接指向本地克隆的仓库：

```bash
ln -s ../ai-first-specs/capabilities/validated/stdlib \
      capabilities/validated/stdlib
```

### 2. 生产环境

定期同步仓库，避免运行时网络依赖：

```bash
cd ai-first-specs
git pull origin main
```

### 3. 离线环境

确保所有需要的能力都在本地，禁用远程加载：

```bash
export AI_FIRST_DISABLE_REMOTE_LOADING=true
```

## API 参考

### RemoteSpecLoader

```python
class RemoteSpecLoader:
    def __init__(
        self,
        repo: str = "gmood2008/ai-first-specs",
        branch: str = "main",
        specs_path: str = "capabilities/validated/stdlib",
        timeout: float = 10.0
    )
    
    def list_available_specs() -> list[str]
    def load_spec(capability_id: str, use_cache: bool = True) -> Optional[Dict]
    def load_specs_batch(capability_ids: list[str]) -> Dict[str, Dict]
    def clear_cache()
```

## 相关文档

- [标准库能力列表](../README.md#standard-library)
- [能力规范格式](../docs/CAPABILITY_SPEC.md)
- [MCP Server 配置](../CHATBOX_MCP_CONFIG_UPDATED.md)
