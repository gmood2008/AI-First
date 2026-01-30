from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class CheckStep:
    name: str
    argv: List[str]
    optional: bool = False


def _which(cmd: str) -> Optional[str]:
    venv_exe = Path(__file__).resolve().parents[1] / ".venv" / "bin" / cmd
    if venv_exe.exists() and venv_exe.is_file():
        return str(venv_exe)
    return shutil.which(cmd)


def _python_executable() -> str:
    venv_python = Path(__file__).resolve().parents[1] / ".venv" / "bin" / "python"
    if venv_python.exists() and venv_python.is_file():
        return str(venv_python)
    return sys.executable


def _run(step: CheckStep) -> int:
    exe = step.argv[0]
    resolved_exe = _which(exe)
    if resolved_exe is None:
        if step.optional:
            print(f"[SKIP] {step.name}: '{exe}' not found")
            return 0
        print(f"[FAIL] {step.name}: '{exe}' not found")
        return 127

    argv = [resolved_exe, *step.argv[1:]]

    print(f"[RUN]  {step.name}: {' '.join(argv)}")
    proc = subprocess.run(argv)
    if proc.returncode == 0:
        print(f"[PASS] {step.name}")
        return 0

    if step.optional:
        print(f"[WARN] {step.name} failed (optional). rc={proc.returncode}")
        return 0

    print(f"[FAIL] {step.name} rc={proc.returncode}")
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full test suite (may fail if unrelated legacy tests are broken)",
    )
    args = parser.parse_args()

    python_exe = _python_executable()

    pytest_argv: List[str]
    if args.full:
        pytest_argv = [python_exe, "-m", "pytest"]
    else:
        awe_tests = sorted(str(p) for p in Path("tests").glob("test_awe_*.py"))
        if not awe_tests:
            print("[FAIL] pytest: no AWE tests found matching tests/test_awe_*.py")
            return 4
        pytest_argv = [
            python_exe,
            "-m",
            "pytest",
            "-q",
            *awe_tests,
        ]

    steps = [
        CheckStep(name="ruff", argv=["ruff", "check", "src", "tests", "scripts"], optional=True),
        CheckStep(name="mypy", argv=["mypy", "src"], optional=True),
        CheckStep(name="pytest", argv=pytest_argv, optional=False),
    ]

    rc = 0
    for step in steps:
        step_rc = _run(step)
        if step_rc != 0:
            rc = step_rc
            break

    if rc == 0:
        print("[OK] self-check completed")
    else:
        print(f"[ERR] self-check failed rc={rc}")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
