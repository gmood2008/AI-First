"""
Load Skill Facade specs from directory and register (PROPOSED by default).
"""

import yaml
from pathlib import Path
from typing import Optional

from specs.skill_facade import SkillFacadeSpec
from runtime.registry.skill_facade_registry import SkillFacadeRegistry, FacadeState


def load_facades_from_directory(
    registry: SkillFacadeRegistry,
    directory: Path,
    activate: bool = False,
    registered_by: Optional[str] = None,
) -> int:
    """
    Load YAML facade specs from directory and register as PROPOSED.
    If activate=True, transition to ACTIVE after registration (for demo/dev).
    """
    directory = Path(directory)
    if not directory.exists() or not directory.is_dir():
        return 0

    count = 0
    for path in directory.glob("*.yaml"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            spec = SkillFacadeSpec.from_yaml(content)
            registry.register_facade(spec, registered_by=registered_by)
            count += 1
            if activate:
                registry.transition_state(
                    spec.name,
                    spec.version,
                    FacadeState.ACTIVE,
                    changed_by=registered_by or "loader",
                    reason="Auto-activated by loader (demo)",
                )
        except Exception as e:
            # Log but do not fail entire load
            import logging
            logging.getLogger(__name__).warning("Failed to load facade %s: %s", path.name, e)
    return count
