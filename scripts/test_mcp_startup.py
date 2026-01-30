#!/usr/bin/env python3
"""
测试 MCP Server 能否在本地成功初始化（不跑 stdio 主循环）。
用于排查 Cursor 中 ai-first MCP 报错。

用法（项目根目录）:
  export AI_FIRST_SPECS_DIR="$(pwd)/capabilities/validated/stdlib"
  export PYTHONPATH="$(pwd)/src"
  python3 scripts/test_mcp_startup.py
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))


def main():
    try:
        import yaml  # noqa: F401
    except ModuleNotFoundError:
        print("当前 Python 未安装 pyyaml。请用安装过依赖的解释器运行，例如：")
        print("  python3.11 scripts/test_mcp_startup.py")
        print("或先：pip install -e .")
        return 1

    specs_dir = os.environ.get("AI_FIRST_SPECS_DIR")
    if not specs_dir:
        print("未设置 AI_FIRST_SPECS_DIR。请先执行：")
        print('  export AI_FIRST_SPECS_DIR="' + str(PROJECT_ROOT / "capabilities" / "validated" / "stdlib") + '"')
        print('  export PYTHONPATH="' + str(PROJECT_ROOT / "src") + '"')
        return 1
    p = Path(specs_dir)
    if not p.exists():
        print(f"目录不存在: {p}")
        print("可创建空目录: mkdir -p capabilities/validated/stdlib")
        return 1
    if not p.is_dir():
        print(f"不是目录: {p}")
        return 1

    print("正在创建 MCP Server 实例...")
    try:
        from runtime.mcp.server_v2 import create_server
        server = create_server(specs_dir=Path(specs_dir))
        print("OK: Server 创建成功")
        print(f"  specs_dir: {server.specs_dir}")
        print(f"  tools: {len(server.tool_definitions)}")
        print(f"  facades: {len(server.facade_registry.list_facades())}")
        return 0
    except FileNotFoundError as e:
        print("FileNotFoundError:", e)
        return 1
    except Exception as e:
        print("Error:", type(e).__name__, e)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
