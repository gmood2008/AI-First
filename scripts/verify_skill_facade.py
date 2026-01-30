#!/usr/bin/env python3
"""
Skill Facade 完整验证脚本。

用法（在项目根目录）:
  pip install -e .              # 安装依赖（含 pyyaml），注意 -e 后要有空格和点
  python3 scripts/verify_skill_facade.py   # macOS 上请用 python3（无 python 时）

验证内容:
  1. 加载 specs/facades/*.yaml 的 SkillFacadeSpec
  2. 注册并激活 Facade
  3. get_facade_by_trigger("分析财报") 命中
  4. resolve_nl("extract tables from pdf", facade_registry) 命中与路由
"""

import sys
from pathlib import Path

# 项目根 = 本文件所在目录的上一级
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def check_deps():
    """确保 pyyaml 可用。"""
    try:
        import yaml  # noqa: F401
    except ModuleNotFoundError:
        print("缺少依赖：当前 Python 未安装 pyyaml。")
        print("请用「安装时用的同一个 Python」执行下面两条（不要复制 # 开头的行）：")
        print("  pip install -e .")
        print("  python3 scripts/verify_skill_facade.py")
        print("若仍报错，可显式指定 Python，例如：")
        print("  python3.11 -m pip install -e .")
        print("  python3.11 scripts/verify_skill_facade.py")
        sys.exit(1)


def main():
    check_deps()

    from src.specs.skill_facade import SkillFacadeSpec
    from src.runtime.registry.skill_facade_registry import (
        SkillFacadeRegistry,
        FacadeState,
    )
    from src.runtime.facade_loader import load_facades_from_directory
    from src.runtime.facade_router import resolve_nl

    facades_dir = PROJECT_ROOT / "specs" / "facades"
    if not facades_dir.exists():
        print(f"错误: 未找到 Facade 目录 {facades_dir}")
        sys.exit(1)

    # 1. 加载 Spec
    registry = SkillFacadeRegistry(db_path=PROJECT_ROOT / ".ai-first" / "skill_facade_verify.db")
    n = load_facades_from_directory(
        registry,
        facades_dir,
        activate=True,
        registered_by="verify_script",
    )
    print(f"已加载并激活 {n} 个 Facade")

    # 2. get_facade_by_trigger("分析财报")
    facade_cn = registry.get_facade_by_trigger("分析财报")
    assert facade_cn is not None, "get_facade_by_trigger('分析财报') 应命中"
    print(f"  get_facade_by_trigger('分析财报') -> {facade_cn.name}")

    # 3. resolve_nl("extract tables from pdf", facade_registry)
    route = resolve_nl("extract tables from pdf", registry)
    assert route is not None, "resolve_nl('extract tables from pdf') 应命中"
    print(f"  resolve_nl('extract tables from pdf') -> {route.route_type} ref={route.ref} facade={route.facade.name}")

    # 额外：列出所有 ACTIVE facades
    active = registry.list_facades(state=FacadeState.ACTIVE)
    print(f"当前 ACTIVE Facade 数量: {len(active)}")

    print("验证通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
