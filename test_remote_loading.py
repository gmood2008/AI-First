#!/usr/bin/env python3
"""
测试远程加载功能 - 从 GitHub 加载能力
"""
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from runtime.registry import CapabilityRegistry
from runtime.stdlib.loader import load_stdlib
from runtime.remote_loader import RemoteSpecLoader

def main():
    print("=" * 70)
    print("🧪 测试远程加载功能")
    print("=" * 70)
    print()
    
    # 测试 1: 直接测试远程加载器
    print("1️⃣ 测试远程加载器...")
    loader = RemoteSpecLoader()
    
    # 列出可用能力
    available = loader.list_available_specs()
    print(f"   📦 GitHub 上可用能力: {len(available)} 个")
    print(f"   示例: {', '.join(available[:5])}")
    print()
    
    # 加载一个能力
    print("2️⃣ 从 GitHub 加载能力: io.fs.read_file")
    spec = loader.load_spec("io.fs.read_file")
    if spec:
        print(f"   ✅ 加载成功")
        print(f"   📋 ID: {spec.get('meta', {}).get('id', 'N/A')}")
        print(f"   📝 描述: {spec.get('meta', {}).get('description', 'N/A')[:60]}...")
    else:
        print(f"   ❌ 加载失败")
    print()
    
    # 测试 2: 测试 stdlib loader 的远程加载
    print("3️⃣ 测试 stdlib loader（混合本地和远程）...")
    print()
    
    # 创建一个临时目录，只包含部分文件
    import tempfile
    import shutil
    
    temp_dir = Path(tempfile.mkdtemp())
    print(f"   临时目录: {temp_dir}")
    
    # 复制一个文件到临时目录（模拟部分本地文件）
    stdlib_dir = project_root / "capabilities" / "validated" / "stdlib"
    if stdlib_dir.exists() and (stdlib_dir / "io_fs_read_file.yaml").exists():
        shutil.copy(stdlib_dir / "io_fs_read_file.yaml", temp_dir / "io_fs_read_file.yaml")
        print(f"   ✅ 复制了 1 个本地文件")
    
    # 尝试加载（应该从本地加载一个，从 GitHub 加载其他的）
    registry = CapabilityRegistry()
    try:
        # 注意：这会尝试加载所有 20 个能力
        # 如果本地只有 1 个，其他 19 个会从 GitHub 加载
        loaded = load_stdlib(registry, temp_dir)
        print(f"   ✅ 加载了 {loaded} 个能力")
        print(f"   📦 注册表中的能力: {len(registry.list_capabilities())} 个")
    except Exception as e:
        print(f"   ⚠️  加载过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        print(f"   🗑️  清理临时目录")
    
    print()
    print("=" * 70)
    print("✅ 测试完成")
    print("=" * 70)
    print()
    print("💡 使用说明:")
    print("   - 如果本地找不到能力 spec，系统会自动从 GitHub 加载")
    print("   - 远程加载的能力会被缓存，提高性能")
    print("   - 支持离线模式：如果网络不可用，只使用本地能力")

if __name__ == "__main__":
    main()
