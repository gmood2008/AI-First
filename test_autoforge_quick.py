#!/usr/bin/env python3
"""
AutoForge 快速体验脚本

在 Cursor 中直接运行此脚本来体验 AutoForge 功能。
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

def check_environment():
    """检查环境配置"""
    print("=" * 80)
    print("🔍 环境检查")
    print("=" * 80)
    
    # 检查 API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  警告: OPENAI_API_KEY 未设置")
        print("   请设置: export OPENAI_API_KEY=your_key_here")
        print()
        response = input("是否继续？(可能需要手动输入 API Key) [y/N]: ")
        if response.lower() != 'y':
            return False
    else:
        print("✅ OPENAI_API_KEY 已设置")
    
    # 检查依赖
    try:
        import openai
        print("✅ openai 库已安装")
    except ImportError:
        print("❌ openai 库未安装")
        print("   请运行: pip install openai")
        return False
    
    try:
        import yaml
        print("✅ pyyaml 库已安装")
    except ImportError:
        print("⚠️  pyyaml 库未安装（可选）")
    
    print()
    return True

def quick_demo():
    """快速演示"""
    print("=" * 80)
    print("🚀 AutoForge 快速体验")
    print("=" * 80)
    print()
    
    if not check_environment():
        return
    
    try:
        from forge.auto.pipeline import AutoForge
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("   请确保在项目根目录运行此脚本")
        return
    
    # 初始化
    print("📦 初始化 AutoForge...")
    autoforge = AutoForge(model="gpt-4o-mini", max_retries=3)
    print("✅ 初始化完成")
    print()
    
    # 示例需求
    examples = [
        {
            "name": "获取比特币价格",
            "requirement": "获取 CoinGecko 的比特币价格",
            "id": "net.crypto.get_price"
        },
        {
            "name": "读取文件",
            "requirement": "读取本地文本文件内容",
            "id": "io.fs.read_file"
        },
        {
            "name": "发送消息",
            "requirement": "向 Slack 频道发送消息",
            "id": "net.slack.send_message"
        }
    ]
    
    print("📋 可用示例：")
    for i, ex in enumerate(examples, 1):
        print(f"  {i}. {ex['name']}: {ex['requirement']}")
    print()
    
    # 选择示例或自定义
    choice = input("选择示例 (1-3) 或输入 'c' 自定义: ").strip()
    
    if choice.lower() == 'c':
        requirement = input("输入你的需求: ").strip()
        capability_id = input("输入能力 ID (可选，直接回车自动生成): ").strip() or None
    elif choice in ['1', '2', '3']:
        ex = examples[int(choice) - 1]
        requirement = ex['requirement']
        capability_id = ex['id']
        print(f"\n✅ 选择: {ex['name']}")
        print(f"   需求: {requirement}")
        print(f"   ID: {capability_id}")
    else:
        print("❌ 无效选择")
        return
    
    print()
    print("=" * 80)
    print("🔨 开始生成能力...")
    print("=" * 80)
    print()
    
    try:
        # 生成能力
        result = autoforge.forge_capability(
            requirement=requirement,
            capability_id=capability_id
        )
        
        print()
        print("=" * 80)
        print("✅ 生成成功！")
        print("=" * 80)
        print()
        print(f"📋 能力信息:")
        print(f"   ID: {result.capability_id}")
        print(f"   名称: {result.spec.name}")
        print(f"   描述: {result.spec.description}")
        print(f"   风险等级: {result.spec.risk.level.value}")
        print(f"   操作类型: {result.spec.operation_type.value}")
        print(f"   支持撤销: {'是' if result.spec.compensation.supported else '否'}")
        print()
        
        if result.dependencies:
            print(f"📦 检测到的依赖:")
            for dep in sorted(result.dependencies):
                print(f"   • {dep}")
            print()
        
        print(f"📁 生成的文件:")
        print(f"   📄 规范: {result.spec_path}")
        print(f"   🐍 处理器: {result.handler_path}")
        print(f"   🧪 测试: {result.test_path}")
        print()
        
        # 询问是否保存
        save = input("是否保存文件到磁盘？[Y/n]: ").strip().lower()
        if save != 'n':
            workspace = Path.cwd()
            
            # 创建目录
            (workspace / result.spec_path).parent.mkdir(parents=True, exist_ok=True)
            (workspace / result.handler_path).parent.mkdir(parents=True, exist_ok=True)
            (workspace / result.test_path).parent.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            (workspace / result.spec_path).write_text(result.spec_yaml, encoding='utf-8')
            (workspace / result.handler_path).write_text(result.handler_code, encoding='utf-8')
            (workspace / result.test_path).write_text(result.test_code, encoding='utf-8')
            
            print()
            print("✅ 文件已保存！")
            print()
            print("🚀 下一步:")
            print(f"   1. 查看规范: cat {result.spec_path}")
            print(f"   2. 查看代码: cat {result.handler_path}")
            print(f"   3. 运行测试: pytest {result.test_path}")
            if result.dependencies:
                deps = " ".join(sorted(result.dependencies))
                print(f"   4. 安装依赖: pip install {deps}")
        else:
            print()
            print("💡 提示: 使用 --dry-run 模式可以预览而不保存")
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ 生成失败")
        print("=" * 80)
        print(f"错误: {e}")
        print()
        print("💡 建议:")
        print("   1. 检查 OPENAI_API_KEY 是否正确")
        print("   2. 检查网络连接")
        print("   3. 尝试使用 --verbose 查看详细信息")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    quick_demo()
