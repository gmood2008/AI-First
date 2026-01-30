#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _iter_py_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for p in root.rglob("*.py"):
        if "/.venv/" in str(p) or "/venv/" in str(p) or "/.git/" in str(p):
            continue
        files.append(p)
    return files


def _fail(errors: List[str]) -> int:
    for e in errors:
        print(f"❌ {e}")
    print(f"\nGovernance lint failed: {len(errors)} error(s).")
    return 2


def _check_no_register_external_calls(project_root: Path) -> List[str]:
    errors: List[str] = []

    src_root = project_root / "src"
    if not src_root.exists():
        return ["src/ directory not found"]

    allow_file = src_root / "runtime" / "registry" / "capability_registry.py"

    for py in _iter_py_files(src_root):
        text = _read_text(py)

        if py == allow_file:
            continue

        if "register_external(" in text or ".register_external(" in text:
            errors.append(f"Forbidden use of register_external in {py.relative_to(project_root)}")

    return errors


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml
    except ModuleNotFoundError:
        raise RuntimeError("pyyaml is required to run governance_lint")

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("yaml root must be a mapping")
    return data


def _extract_route_types(facade: Dict[str, Any]) -> List[Tuple[str, str]]:
    routes = facade.get("routes") or {}
    if not isinstance(routes, dict):
        return []

    out: List[Tuple[str, str]] = []
    for slot in ("primary", "fallback"):
        r = routes.get(slot)
        if isinstance(r, dict):
            t = r.get("type")
            if isinstance(t, str):
                out.append((slot, t))
    return out


def _check_facades_route_type_allowlist(project_root: Path) -> List[str]:
    errors: List[str] = []
    facades_dir = project_root / "specs" / "facades"
    if not facades_dir.exists():
        return errors

    allowed = {"workflow", "pack"}
    for y in sorted(facades_dir.glob("*.yaml")):
        facade = _load_yaml(y)
        for slot, t in _extract_route_types(facade):
            tt = t.strip().lower()
            if tt and tt not in allowed:
                errors.append(
                    f"Facade route type must be one of {sorted(list(allowed))} in {y.relative_to(project_root)} ({slot})"
                )
    return errors


def _check_authoritative_suites_present(project_root: Path) -> List[str]:
    errors: List[str] = []

    required_files = [
        project_root / "specs" / "facades" / "financial-analyst.yaml",
        project_root / "specs" / "facades" / "pdf.yaml",
        project_root / "packs" / "financial-analyst" / "pack.yaml",
        project_root / "packs" / "financial-analyst" / "financial_report.yaml",
        project_root / "specs" / "facades" / "web-research.yaml",
        project_root / "packs" / "web-research" / "pack.yaml",
        project_root / "packs" / "web-research" / "web_research.yaml",
        project_root / "src" / "runtime" / "sidecars" / "dev_browser_sidecar.py",
    ]

    for p in required_files:
        if not p.exists():
            errors.append(f"Authoritative suite file missing: {p.relative_to(project_root)}")

    return errors


def _check_facades_no_capability_route(project_root: Path) -> List[str]:
    errors: List[str] = []
    facades_dir = project_root / "specs" / "facades"
    if not facades_dir.exists():
        return errors

    for y in sorted(facades_dir.glob("*.yaml")):
        facade = _load_yaml(y)
        for slot, t in _extract_route_types(facade):
            if t.strip().lower() == "capability":
                errors.append(
                    f"Forbidden facade route type=capability in {y.relative_to(project_root)} ({slot})"
                )
    return errors


def main() -> int:
    project_root = _project_root()

    errors: List[str] = []
    errors.extend(_check_no_register_external_calls(project_root))
    errors.extend(_check_facades_no_capability_route(project_root))
    errors.extend(_check_facades_route_type_allowlist(project_root))
    errors.extend(_check_authoritative_suites_present(project_root))

    if errors:
        return _fail(errors)

    print("✅ Governance lint passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
