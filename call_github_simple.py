#!/usr/bin/env python3
"""
直接调用生成的 GitHub handler（简化版）
"""
import sys
import json
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# 直接导入生成的 handler
from runtime.stdlib.generated.net_github_get_repo import GetRepoHandler
from runtime.types import ExecutionContext

def main():
    print("=" * 70)
    print("🚀 直接调用 GitHub Handler")
    print("=" * 70)
    print()
    
    # 创建符合 v3 格式的 spec
    spec_dict = {
        "meta": {
            "id": "net.github.get_repo",
            "name": "Get Repository Info Github",
            "description": "Capability to get repository info on github",
            "version": "1.0.0",
        },
        "contracts": {
            "risk": {
                "level": "LOW",
                "justification": "Read-only operation",
            },
            "side_effects": {
                "reversible": True,
                "scope": "network",
            },
            "compensation": {
                "supported": True,
                "strategy": "automatic",
            },
        },
        "behavior": {
            "operation_type": "NETWORK",
        },
        "interface": {
            "inputs": {
                "owner": {
                    "type": "string",
                    "description": "Repository owner",
                    "required": True,
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name",
                    "required": True,
                },
            },
            "outputs": {
                "repository_info": {
                    "type": "string",
                },
                "metadata": {
                    "type": "string",
                },
            },
        },
    }
    
    # 创建 handler 实例
    handler = GetRepoHandler(spec_dict)
    
    # 创建执行上下文
    workspace = project_root / "workspace"
    workspace.mkdir(exist_ok=True)
    
    context = ExecutionContext(
        user_id="test_user",
        workspace_root=workspace,
        session_id="test_session",
        confirmation_callback=None,
        undo_enabled=True,
    )
    
    # 准备参数
    params = {
        "owner": "microsoft",
        "repo": "vscode"
    }
    
    print(f"📝 调用参数:")
    print(json.dumps(params, indent=2, ensure_ascii=False))
    print()
    print("🔄 执行中...")
    print()
    
    try:
        # 执行 handler
        result = handler.execute(params, context)
        
        # 显示结果
        print("=" * 70)
        print("✅ 执行成功!")
        print()
        print("📤 输出结果:")
        print(json.dumps(result.result, indent=2, ensure_ascii=False))
        print()
        print(f"📝 描述: {result.description}")
        
        if result.undo_closure:
            print("↩️  支持撤销操作")
        
    except Exception as e:
        print("=" * 70)
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 70)

if __name__ == "__main__":
    main()
