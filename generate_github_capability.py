#!/usr/bin/env python3
"""
使用 AutoForge 生成 GitHub API 能力
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from forge.auto.pipeline import AutoForge

def main():
    print("=" * 80)
    print("🔨 AutoForge - 生成 GitHub API 能力")
    print("=" * 80)
    print()
    
    # 检查 API Key
    import os
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  警告: OPENAI_API_KEY 未设置")
        print("   请设置: export OPENAI_API_KEY=your_key_here")
        api_key = input("\n请输入你的 OpenAI API Key (或按 Enter 跳过): ").strip()
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        else:
            print("❌ 需要 API Key 才能继续")
            return 1
    
    # 初始化 AutoForge
    print("📦 初始化 AutoForge...")
    autoforge = AutoForge(model="gpt-4o-mini", max_retries=3)
    print("✅ 初始化完成")
    print()
    
    # 需求
    requirement = "从 GitHub API 获取仓库信息，需要 OAuth token"
    capability_id = "net.github.get_repo"
    
    # 参考文档
    reference_file = "docs/github_api_reference.md"
    references = [reference_file] if Path(reference_file).exists() else None
    
    print(f"📝 需求: {requirement}")
    print(f"🆔 能力 ID: {capability_id}")
    if references:
        print(f"📚 参考文档: {', '.join(references)}")
    print()
    print("🔨 开始生成...")
    print()
    
    try:
        # 生成能力
        result = autoforge.forge_capability(
            requirement=requirement,
            capability_id=capability_id,
            references=references
        )
        
        print()
        print("=" * 80)
        print("✅ 生成成功！")
        print("=" * 80)
        print()
        
        # 显示能力信息
        print("📋 能力信息:")
        print(f"   ID: {result.capability_id}")
        print(f"   名称: {result.spec.name}")
        print(f"   描述: {result.spec.description}")
        print(f"   风险等级: {result.spec.risk.level.value}")
        print(f"   操作类型: {result.spec.operation_type.value}")
        print(f"   支持撤销: {'是' if result.spec.compensation.supported else '否'}")
        print()
        
        # 显示参数
        if result.spec.parameters:
            print("📥 参数:")
            for param in result.spec.parameters:
                print(f"   • {param.name} ({param.type}): {param.description}")
            print()
        
        # 显示依赖
        if result.dependencies:
            print("📦 检测到的依赖:")
            for dep in sorted(result.dependencies):
                print(f"   • {dep}")
            print()
        
        # 保存文件
        workspace = Path.cwd()
        
        # 创建目录
        (workspace / result.spec_path).parent.mkdir(parents=True, exist_ok=True)
        (workspace / result.handler_path).parent.mkdir(parents=True, exist_ok=True)
        (workspace / result.test_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 保存文件
        (workspace / result.spec_path).write_text(result.spec_yaml, encoding='utf-8')
        (workspace / result.handler_path).write_text(result.handler_code, encoding='utf-8')
        (workspace / result.test_path).write_text(result.test_code, encoding='utf-8')
        
        print("📁 生成的文件:")
        print(f"   📄 规范: {result.spec_path}")
        print(f"   🐍 处理器: {result.handler_path}")
        print(f"   🧪 测试: {result.test_path}")
        print()
        
        # 显示文件内容预览
        print("=" * 80)
        print("📄 规范文件预览 (前 20 行):")
        print("=" * 80)
        spec_lines = result.spec_yaml.split('\n')[:20]
        for line in spec_lines:
            print(line)
        if len(result.spec_yaml.split('\n')) > 20:
            print("...")
        print()
        
        print("=" * 80)
        print("🐍 处理器代码预览 (前 30 行):")
        print("=" * 80)
        handler_lines = result.handler_code.split('\n')[:30]
        for line in handler_lines:
            print(line)
        if len(result.handler_code.split('\n')) > 30:
            print("...")
        print()
        
        print("=" * 80)
        print("🚀 下一步:")
        print("=" * 80)
        print(f"   1. 查看完整规范: cat {result.spec_path}")
        print(f"   2. 查看完整代码: cat {result.handler_path}")
        print(f"   3. 查看测试代码: cat {result.test_path}")
        if result.dependencies:
            deps = " ".join(sorted(result.dependencies))
            print(f"   4. 安装依赖: pip install {deps}")
        print(f"   5. 运行测试: pytest {result.test_path} -v")
        print()
        
        return 0
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ 生成失败")
        print("=" * 80)
        print(f"错误: {e}")
        print()
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
