#!/usr/bin/env python3
"""
测试外部能力集成功能
"""
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def test_adapter_framework():
    """测试适配器框架"""
    print("=" * 70)
    print("🧪 测试适配器框架")
    print("=" * 70)
    print()
    
    try:
        from runtime.adapters import create_adapter, ClaudeSkillAdapter, HTTPAPIAdapter
        
        print("1️⃣ 测试适配器工厂函数...")
        # 测试创建适配器
        claude_config = {
            "capability_id": "test.claude.skill",
            "skill_id": "skill_123",
            "api_key_env": "CLAUDE_API_KEY"
        }
        
        # 注意：这里不会真正创建，因为需要 API key
        print(f"   ✅ 适配器模块导入成功")
        print(f"   ✅ create_adapter 函数可用")
        print()
        
        print("2️⃣ 测试适配器类...")
        print(f"   ✅ ClaudeSkillAdapter: {ClaudeSkillAdapter}")
        print(f"   ✅ HTTPAPIAdapter: {HTTPAPIAdapter}")
        print()
        
        return True
    
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_skill_converter():
    """测试能力转换器"""
    print("=" * 70)
    print("🧪 测试能力转换器")
    print("=" * 70)
    print()
    
    try:
        from forge.auto.skill_converter import SkillConverter
        
        converter = SkillConverter()
        
        print("1️⃣ 测试 Claude Skill 转换...")
        skill_def = {
            "id": "skill_123",
            "name": "Test Skill",
            "description": "A test skill",
            "input_schema": {
                "properties": {
                    "input": {
                        "type": "string",
                        "description": "Input parameter"
                    }
                },
                "required": ["input"]
            },
            "output_schema": {
                "properties": {
                    "result": {
                        "type": "string",
                        "description": "Output result"
                    }
                }
            }
        }
        
        adapter_config = {
            "skill_id": "skill_123",
            "api_key_env": "CLAUDE_API_KEY"
        }
        
        spec = converter.convert_claude_skill(
            skill_definition=skill_def,
            capability_id="external.claude.test_skill",
            adapter_config=adapter_config
        )
        
        print(f"   ✅ 转换成功")
        print(f"   📋 能力 ID: {spec.id}")
        print(f"   📝 名称: {spec.name}")
        print(f"   📦 参数数量: {len(spec.parameters)}")
        print()
        
        print("2️⃣ 测试 Handler 代码生成...")
        handler_code = converter.generate_handler_wrapper(
            spec=spec,
            adapter_type="claude_skill",
            adapter_config=adapter_config
        )
        
        print(f"   ✅ Handler 代码生成成功")
        print(f"   📏 代码长度: {len(handler_code)} 字符")
        print()
        
        return True
    
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_external_loader():
    """测试外部能力加载器"""
    print("=" * 70)
    print("🧪 测试外部能力加载器")
    print("=" * 70)
    print()
    
    try:
        from runtime.external_loader import load_external_capability_proposals
        from pathlib import Path
        
        # 创建测试目录和文件
        test_dir = Path("capabilities/validated/external")
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建测试 YAML 文件
        test_yaml = test_dir / "test_external_capability.yaml"
        test_yaml.write_text("""id: external.test.capability
name: Test External Capability
description: A test external capability
operation_type: NETWORK
risk:
  level: MEDIUM
  justification: Test capability
side_effects:
  reversible: false
  scope: external
adapter:
  type: http_api
  config:
    endpoint_url: https://api.example.com/test
    method: POST
    auth_type: none
""")
        
        print("1️⃣ 测试加载外部能力 Proposal...")
        proposals = load_external_capability_proposals(test_dir)
        print(f"   ✅ proposals 数量: {len(proposals)}")
        
        # 清理测试文件
        test_yaml.unlink()
        
        print()
        return True
    
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("🚀 外部能力集成功能测试")
    print("=" * 70)
    print()
    
    results = []
    
    # 测试 1: 适配器框架
    results.append(("适配器框架", test_adapter_framework()))
    print()
    
    # 测试 2: 能力转换器
    results.append(("能力转换器", test_skill_converter()))
    print()
    
    # 测试 3: 外部加载器
    results.append(("外部加载器", test_external_loader()))
    print()
    
    # 总结
    print("=" * 70)
    print("📊 测试结果总结")
    print("=" * 70)
    print()
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"   {name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    print()
    if all_passed:
        print("✅ 所有测试通过！")
    else:
        print("⚠️  部分测试失败，请检查错误信息")
    
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
