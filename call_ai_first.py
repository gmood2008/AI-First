#!/usr/bin/env python3
"""
调用 AI-First 能力的示例脚本
"""
import sys
import json
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from runtime.registry import CapabilityRegistry
from runtime.engine import RuntimeEngine
from runtime.types import ExecutionContext
from runtime.stdlib.loader import load_stdlib

def main():
    print("=" * 70)
    print("🚀 AI-First Runtime - 能力调用示例")
    print("=" * 70)
    print()
    
    # 1. 设置路径
    specs_dir = project_root / "capabilities" / "validated" / "stdlib"
    generated_dir = project_root / "capabilities" / "validated" / "generated"
    workspace = project_root / "workspace"
    workspace.mkdir(exist_ok=True)
    
    # 2. 创建注册表并加载能力
    print("📦 加载能力...")
    registry = CapabilityRegistry()
    
    # 加载标准库（如果存在）
    if specs_dir.exists():
        try:
            loaded = load_stdlib(registry, specs_dir)
            print(f"   ✅ 已加载 {loaded} 个标准库能力")
        except Exception as e:
            print(f"   ⚠️  标准库加载失败: {e}")
    
    # 加载生成的能力（直接导入 handler）
    if generated_dir.exists():
        try:
            from runtime.handler import load_spec_from_yaml
            import yaml
            
            yaml_files = list(generated_dir.glob("*.yaml"))
            loaded_count = 0
            
            for yaml_file in yaml_files:
                try:
                    # 加载 spec
                    spec_dict = load_spec_from_yaml(yaml_file)
                    capability_id = spec_dict.get("id")
                    
                    if not capability_id:
                        print(f"   ⚠️  {yaml_file.name} 缺少 id 字段")
                        continue
                    
                    # 获取 handler 路径
                    handler_path = spec_dict.get("handler")
                    if not handler_path:
                        print(f"   ⚠️  {yaml_file.name} 缺少 handler 路径")
                        continue
                    
                    # 动态导入 handler
                    try:
                        handler_module = __import__(handler_path, fromlist=[""])
                        
                        # 查找 Handler 类（通常是 {Name}Handler）
                        handler_class = None
                        for attr_name in dir(handler_module):
                            attr = getattr(handler_module, attr_name)
                            if (isinstance(attr, type) and 
                                attr_name.endswith("Handler") and 
                                hasattr(attr, "execute") and
                                attr != __import__("runtime.handler", fromlist=["ActionHandler"]).ActionHandler):
                                handler_class = attr
                                break
                        
                        if handler_class:
                            # 转换 spec 格式（v3 格式需要 meta 字段）
                            # 如果 spec_dict 没有 meta，创建一个兼容的格式
                            if "meta" not in spec_dict:
                                spec_dict_v3 = {
                                    "meta": {
                                        "id": capability_id,
                                        "name": spec_dict.get("name", capability_id),
                                        "description": spec_dict.get("description", ""),
                                        "version": spec_dict.get("metadata", {}).get("version", "1.0.0"),
                                    },
                                    **spec_dict
                                }
                            else:
                                spec_dict_v3 = spec_dict
                            
                            # 创建 handler 实例（可能需要 spec）
                            try:
                                handler = handler_class(spec_dict_v3)
                            except Exception as e:
                                # 如果失败，尝试无参数初始化
                                try:
                                    handler = handler_class()
                                except:
                                    raise e
                            
                            registry.register(capability_id, handler, spec_dict)
                            loaded_count += 1
                            print(f"   ✅ 已加载: {capability_id}")
                        else:
                            print(f"   ⚠️  在 {handler_path} 中找不到 Handler 类")
                    except ImportError as e:
                        print(f"   ⚠️  无法导入 handler {handler_path}: {e}")
                    except Exception as e:
                        print(f"   ⚠️  加载 {yaml_file.name} 失败: {e}")
                        import traceback
                        traceback.print_exc()
                        
                except Exception as e:
                    print(f"   ⚠️  处理 {yaml_file.name} 失败: {e}")
            
            if loaded_count > 0:
                print(f"   ✅ 共加载 {loaded_count} 个生成的能力")
        except Exception as e:
            print(f"   ⚠️  生成能力加载失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 3. 列出可用能力
    capabilities = registry.list_capabilities()
    print(f"\n📚 可用能力数量: {len(capabilities)}")
    
    if not capabilities:
        print("   ⚠️  没有找到可用能力")
        print("\n💡 提示:")
        print("   - 确保 capabilities/validated/stdlib 或 generated 目录中有 YAML 文件")
        print("   - 或者使用 AutoForge 生成新能力: ./forge create \"你的需求\"")
        return
    
    # 显示前几个能力
    print("\n可用能力列表:")
    for i, cap_id in enumerate(capabilities[:10], 1):
        print(f"   {i}. {cap_id}")
    if len(capabilities) > 10:
        print(f"   ... 还有 {len(capabilities) - 10} 个能力")
    
    # 4. 尝试调用 GitHub 能力（如果存在）
    github_cap = "net.github.get_repo"
    if github_cap in capabilities:
        print(f"\n🔧 测试调用能力: {github_cap}")
        print("-" * 70)
        
        # 创建执行引擎
        engine = RuntimeEngine(registry)
        
        # 创建执行上下文
        context = ExecutionContext(
            user_id="test_user",
            workspace_root=workspace,
            session_id="test_session",
            confirmation_callback=None,  # 不需要确认
            undo_enabled=True,
        )
        
        # 准备参数
        params = {
            "owner": "microsoft",
            "repo": "vscode"
        }
        
        print(f"📝 参数: {json.dumps(params, indent=2, ensure_ascii=False)}")
        print()
        
        try:
            # 执行能力
            result = engine.execute(github_cap, params, context)
            
            # 显示结果
            print("=" * 70)
            if result.is_success():
                print("✅ 执行成功!")
                print(f"\n📤 输出结果:")
                print(json.dumps(result.outputs, indent=2, ensure_ascii=False))
                
                if result.undo_available:
                    print(f"\n↩️  支持撤销操作")
            else:
                print(f"❌ 执行失败: {result.status.value}")
                if result.error_message:
                    print(f"\n💬 错误信息: {result.error_message}")
            
            print(f"\n⏱️  执行时间: {result.execution_time_ms:.2f}ms")
            
        except Exception as e:
            print(f"❌ 执行出错: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"\n💡 提示: 没有找到 {github_cap} 能力")
        print("   可以使用以下命令生成:")
        print(f'   ./forge create "从 GitHub API 获取仓库信息" --id "{github_cap}"')
    
    print("\n" + "=" * 70)
    print("✅ 完成")
    print("=" * 70)

if __name__ == "__main__":
    main()
