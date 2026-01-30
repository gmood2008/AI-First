from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from registry.pack_registry import PackRegistry
from specs.capability_pack import CapabilityPackSpec, PackState


def load_packs_from_directory(
    registry: PackRegistry,
    directory: Path,
    activate: bool = False,
    registered_by: Optional[str] = None,
) -> int:
    directory = Path(directory)
    if not directory.exists() or not directory.is_dir():
        return 0

    count = 0
    for path in directory.glob("**/pack.yaml"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                continue

            spec = CapabilityPackSpec.from_dict(data)
            registry.register_pack(spec, registered_by=registered_by or "loader")
            count += 1

            if activate:
                registry.transition_state(
                    pack_id=spec.pack_id,
                    version=spec.version,
                    new_state=PackState.ACTIVE,
                    changed_by=registered_by or "loader",
                    reason="Auto-activated by loader (demo)",
                )
        except Exception:
            import logging

            logging.getLogger(__name__).warning("Failed to load pack %s", str(path))

    return count
