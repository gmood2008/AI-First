#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    subprocess.check_call(cmd, cwd=str(cwd) if cwd else None, env=env)


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    dist_dir = repo / "dist"

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)

    # Build wheel
    # We intentionally use pip wheel (no extra build deps required)
    _run([sys.executable, "-m", "pip", "wheel", ".", "-w", str(dist_dir)], cwd=repo)

    wheels = sorted(dist_dir.glob("ai_first_runtime-*.whl"))
    if not wheels:
        wheels = sorted(dist_dir.glob("ai_first_runtime_core-*.whl"))
    if not wheels:
        wheels = sorted(dist_dir.glob("*.whl"))
    if not wheels:
        raise SystemExit("No wheel produced under dist/")

    wheel_path = wheels[-1]

    # Create isolated venv
    with tempfile.TemporaryDirectory(prefix="aifirst_smoke_") as td:
        td_path = Path(td)
        venv_dir = td_path / "venv"
        _run([sys.executable, "-m", "venv", str(venv_dir)])

        py = venv_dir / "bin" / "python"
        pip = venv_dir / "bin" / "pip"

        _run([str(pip), "install", "--upgrade", "pip", "setuptools", "wheel"])
        _run([str(pip), "install", str(wheel_path)])

        # Smoke checks:
        # 1) packaged stdlib specs dir is resolvable
        # 2) stdlib can be loaded from that dir
        code = r'''
from runtime.mcp.specs_resolver import resolve_specs_dir
from runtime.stdlib.loader import load_stdlib
from runtime.registry import CapabilityRegistry

specs_dir = resolve_specs_dir()
print("RESOLVED_SPECS_DIR=", specs_dir)

reg = CapabilityRegistry()
count = load_stdlib(reg, specs_dir)
print("STDLIB_LOADED=", count)
'''
        env = os.environ.copy()
        env.pop("AI_FIRST_SPECS_DIR", None)
        env.pop("AI_FIRST_ASSETS_DIR", None)
        _run([str(py), "-c", code], env=env)

    print("✅ smoke_wheel_install passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
