"""
Facade Router: Natural language → SkillFacadeRegistry.match → Resolved route.

Integrates with existing execution: resolve NL to workflow or pack,
then caller enters workflow/pack execution and governance.
"""

from typing import Optional, NamedTuple, List, TYPE_CHECKING

from specs.skill_facade import SkillFacadeSpec
from runtime.registry.skill_facade_registry import SkillFacadeRegistry

if TYPE_CHECKING:
    from registry.pack_registry import PackRegistry


class ResolvedRoute(NamedTuple):
    """Result of resolving natural language via facade."""
    route_type: str  # "workflow" | "pack"
    ref: str         # workflow name or pack id/name
    facade: SkillFacadeSpec
    allowed_workflows: Optional[List[str]] = None


def resolve_nl(
    text: str,
    facade_registry: SkillFacadeRegistry,
    pack_registry: Optional["PackRegistry"] = None,
) -> Optional[ResolvedRoute]:
    """
    Resolve natural language input to a route (workflow or pack).

    - Match text against ACTIVE facades via triggers.
    - Return primary route (workflow or pack); no execution here.
    - If route is workflow and pack_registry given, caller should check
      workflow's pack is ACTIVE (see resolve_and_validate below).
    """
    facade = facade_registry.match(text)
    if not facade:
        return None

    primary = facade.routes.primary
    return ResolvedRoute(
        route_type=primary.type.value,
        ref=primary.ref,
        facade=facade,
        allowed_workflows=None,
    )


def resolve_and_validate(
    text: str,
    facade_registry: SkillFacadeRegistry,
    pack_registry: Optional["PackRegistry"] = None,
) -> Optional[ResolvedRoute]:
    """
    Resolve NL to route and validate constraints.

    - If route is workflow and facade.constraints.requires_pack_active:
      find a pack that includes this workflow and check pack is ACTIVE.
    - If route is pack: check pack is ACTIVE when pack_registry is given.
    - Returns None if validation fails (e.g. pack not ACTIVE).
    """
    route = resolve_nl(text, facade_registry, pack_registry)
    if not route or not pack_registry:
        return route

    if route.route_type == "workflow" and route.facade.constraints.requires_pack_active:
        # Find an ACTIVE pack that includes this workflow
        from specs.capability_pack import PackState
        for rec in pack_registry.list_packs(state=PackState.ACTIVE):
            if route.ref in (rec.includes.workflows or []):
                return route
        # No ACTIVE pack contains this workflow → treat as not routable
        return None

    if route.route_type == "pack":
        # Check pack is ACTIVE (ref may be pack_id or pack name)
        pack = None
        if pack_registry.is_pack_executable(route.ref):
            pack = pack_registry.get_pack(route.ref)
        else:
            from specs.capability_pack import PackState
            # Find any ACTIVE pack by name
            for p in pack_registry.list_packs(state=PackState.ACTIVE, pack_name=route.ref):
                pack = p
                break
            if pack is None:
                return None

        # Enforce: when routing to a pack, only workflows inside that pack are allowed.
        allowed = list(pack.includes.workflows or []) if pack else []
        return ResolvedRoute(
            route_type=route.route_type,
            ref=route.ref,
            facade=route.facade,
            allowed_workflows=allowed,
        )

    return route
