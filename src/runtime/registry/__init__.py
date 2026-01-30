"""
Runtime registry components.

- CapabilityRegistry: capability ID -> handler (existing).
- SkillFacadeRegistry: semantic entry layer; routes NL to workflow/pack.
"""

from .capability_registry import CapabilityRegistry
from .skill_facade_registry import (
    SkillFacadeRegistry,
    FacadeState,
    SkillFacadeRegistryError,
    FacadeNotFoundError,
    FacadeStateTransitionError,
)

__all__ = [
    "CapabilityRegistry",
    "SkillFacadeRegistry",
    "FacadeState",
    "SkillFacadeRegistryError",
    "FacadeNotFoundError",
    "FacadeStateTransitionError",
]
