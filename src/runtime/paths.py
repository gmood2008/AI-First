from __future__ import annotations

import os
import sysconfig
from pathlib import Path
from typing import Optional


def _installed_share_root() -> Optional[Path]:
    data_root = sysconfig.get_paths().get("data")
    if not data_root:
        return None
    p = Path(data_root) / "share" / "ai-first-runtime"
    return p if p.exists() else None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def assets_root() -> Path:
    installed = _installed_share_root()
    if installed is not None:
        return installed

    env_root = os.environ.get("AI_FIRST_ASSETS_DIR")
    if env_root:
        p = Path(env_root)
        if p.exists():
            return p

    return repo_root()


def stdlib_specs_dir() -> Path:
    return assets_root() / "capabilities" / "validated" / "stdlib"


def external_specs_dir() -> Path:
    return assets_root() / "capabilities" / "validated" / "external"


def packs_dir() -> Path:
    return assets_root() / "packs"


def facades_dir() -> Path:
    return assets_root() / "specs" / "facades"
