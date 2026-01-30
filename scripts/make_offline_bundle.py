#!/usr/bin/env python3

import argparse
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    subprocess.check_call(cmd, cwd=str(cwd) if cwd else None)


def _copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _copy_tree_if_exists(src_dir: Path, dst_dir: Path) -> None:
    if not src_dir.exists():
        return
    dst_dir.parent.mkdir(parents=True, exist_ok=True)
    if dst_dir.exists():
        shutil.rmtree(dst_dir)
    shutil.copytree(src_dir, dst_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an offline bundle (tar.gz) for internal distribution")
    parser.add_argument(
        "--out",
        default=None,
        help="Output directory for bundle (default: <repo>/dist/bundles)",
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    out_dir = Path(args.out).expanduser().resolve() if args.out else (repo / "dist" / "bundles")
    out_dir.mkdir(parents=True, exist_ok=True)

    dist_dir = repo / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    # Build wheel into dist/
    _run([sys.executable, "-m", "pip", "wheel", ".", "-w", str(dist_dir)], cwd=repo)

    wheels = sorted(dist_dir.glob("ai_first_runtime-*.whl"))
    if not wheels:
        wheels = sorted(dist_dir.glob("ai_first_runtime_core-*.whl"))
    if not wheels:
        wheels = sorted(dist_dir.glob("*.whl"))
    if not wheels:
        raise SystemExit("No wheel produced under dist/")

    wheel_path = wheels[-1]

    # Bundle staging dir
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle_name = f"ai-first-runtime-offline-bundle_{ts}"
    staging = Path(tempfile.mkdtemp(prefix=bundle_name + "_"))
    bundle_root = staging / bundle_name

    (bundle_root / "wheels").mkdir(parents=True, exist_ok=True)
    shutil.copy2(wheel_path, bundle_root / "wheels" / wheel_path.name)

    # Plaintext assets for review/customization
    assets_root = bundle_root / "assets"
    _copy_tree_if_exists(repo / "capabilities", assets_root / "capabilities")
    _copy_tree_if_exists(repo / "packs", assets_root / "packs")
    _copy_tree_if_exists(repo / "specs" / "facades", assets_root / "specs" / "facades")

    # Minimal install + verify scripts
    _copy_if_exists(repo / "scripts" / "smoke_wheel_install.py", bundle_root / "scripts" / "smoke_wheel_install.py")

    # Docs (copy a curated set)
    _copy_if_exists(repo / "docs" / "INTERNAL_PYPI_DISTRIBUTION_SOP.md", bundle_root / "docs" / "INTERNAL_PYPI_DISTRIBUTION_SOP.md")
    _copy_if_exists(repo / "docs" / "partner_technical_evaluation.md", bundle_root / "docs" / "partner_technical_evaluation.md")
    _copy_if_exists(repo / "docs" / "INTEGRATION_GUIDE.md", bundle_root / "docs" / "INTEGRATION_GUIDE.md")
    _copy_if_exists(repo / "docs" / "EXTERNAL_CAPABILITY_INTEGRATION.md", bundle_root / "docs" / "EXTERNAL_CAPABILITY_INTEGRATION.md")
    _copy_if_exists(repo / "docs" / "COMPATIBILITY_CONTRACT.md", bundle_root / "docs" / "COMPATIBILITY_CONTRACT.md")
    _copy_if_exists(repo / "docs" / "AEGIS_AWE_INTEGRATION_RESPONSE.md", bundle_root / "docs" / "AEGIS_AWE_INTEGRATION_RESPONSE.md")
    _copy_if_exists(repo / "docs" / "AEGIS_GOVERNANCE_HOOKS_CONTRACT.md", bundle_root / "docs" / "AEGIS_GOVERNANCE_HOOKS_CONTRACT.md")
    _copy_if_exists(repo / "docs" / "AEGIS_WORKFLOW_EXECUTION_HISTORY_CONTRACT.md", bundle_root / "docs" / "AEGIS_WORKFLOW_EXECUTION_HISTORY_CONTRACT.md")
    _copy_if_exists(repo / "docs" / "AEGIS_AUTOFORGE_CALL_STRATEGY.md", bundle_root / "docs" / "AEGIS_AUTOFORGE_CALL_STRATEGY.md")
    _copy_if_exists(repo / "ARCHITECTURE.md", bundle_root / "ARCHITECTURE.md")
    _copy_if_exists(repo / "QUICKSTART_EXTERNAL_INTEGRATION.md", bundle_root / "QUICKSTART_EXTERNAL_INTEGRATION.md")

    # Schemas (for Aegis ingest validation)
    _copy_if_exists(
        repo / "schemas" / "aegis" / "bridge_exec_workflow_output.schema.json",
        bundle_root / "schemas" / "aegis" / "bridge_exec_workflow_output.schema.json",
    )

    # Instructions
    readme = bundle_root / "README_OFFLINE_INSTALL.md"
    readme.write_text(
        """# AI-First Runtime 离线交付包使用说明\n\n本压缩包用于无法直接访问 Internal PyPI 的场景，适合‘本地拷贝给对方’的交付方式。\n\n## 1. 包内结构\n\n- wheels/\n  - ai_first_runtime-<version>-py3-none-any.whl\n- scripts/\n  - smoke_wheel_install.py\n- assets/\n  - capabilities/\n  - packs/\n  - specs/facades/\n- docs/\n  - INTERNAL_PYPI_DISTRIBUTION_SOP.md\n  - partner_technical_evaluation.md\n  - INTEGRATION_GUIDE.md\n  - EXTERNAL_CAPABILITY_INTEGRATION.md\n  - COMPATIBILITY_CONTRACT.md\n  - AEGIS_AWE_INTEGRATION_RESPONSE.md\n  - AEGIS_GOVERNANCE_HOOKS_CONTRACT.md\n  - AEGIS_WORKFLOW_EXECUTION_HISTORY_CONTRACT.md\n  - AEGIS_AUTOFORGE_CALL_STRATEGY.md\n- schemas/\n  - aegis/bridge_exec_workflow_output.schema.json\n- ARCHITECTURE.md\n- QUICKSTART_EXTERNAL_INTEGRATION.md\n\n## 2. 离线安装（推荐使用 venv）\n\n```bash\npython3 -m venv .venv\nsource .venv/bin/activate\npython -m pip install -U pip\npython -m pip install wheels/ai_first_runtime-*.whl\n```\n\n## 3. 明文资产（assets/）用途\n\n默认情况下，运行时会优先使用 wheel 内置的 `share/ai-first-runtime` 资产。\n\n如需让运行时改为使用本包内的明文资产（便于查看/对比/二开），可设置：\n\n```bash\nexport AI_FIRST_ASSETS_DIR=\"$(pwd)/assets\"\n```\n\n其目录结构应包含：\n- `capabilities/validated/stdlib/`\n- `packs/`\n- `specs/facades/`\n\n## 4. 验证安装（可选，但推荐）\n\n```bash\npython scripts/smoke_wheel_install.py\n```\n\n若输出包含 `RESOLVED_SPECS_DIR= .../share/ai-first-runtime/...` 与 `✅ smoke_wheel_install passed`，说明资产随 wheel 安装且可用。\n""",
        encoding="utf-8",
    )

    # Create tar.gz
    tar_path = out_dir / f"{bundle_name}.tar.gz"
    if tar_path.exists():
        tar_path.unlink()

    _run(["tar", "-czf", str(tar_path), "-C", str(staging), bundle_name])

    print(f"BUNDLE_CREATED={tar_path}")

    # Cleanup staging dir
    shutil.rmtree(staging)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
