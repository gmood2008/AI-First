from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml

from .semver import SemVer, satisfies


@dataclass(frozen=True)
class CapabilityRef:
    capability_id: str
    constraint: str = ""


@dataclass(frozen=True)
class CapabilityVersion:
    capability_id: str
    version: SemVer
    spec: Dict[str, Any]


class CapabilityNotFoundError(KeyError):
    pass


class CapabilityVersionIndex:
    def __init__(self) -> None:
        self._by_id: Dict[str, List[CapabilityVersion]] = {}

    def add(self, cap: CapabilityVersion) -> None:
        versions = self._by_id.setdefault(cap.capability_id, [])
        versions.append(cap)
        versions.sort(key=lambda c: c.version)

    def has(self, capability_id: str) -> bool:
        return capability_id in self._by_id

    def list_versions(self, capability_id: str) -> List[SemVer]:
        return [c.version for c in self._by_id.get(capability_id, [])]

    def resolve(self, capability_id: str, constraint: str = "") -> CapabilityVersion:
        if capability_id not in self._by_id:
            raise CapabilityNotFoundError(capability_id)

        candidates = [c for c in self._by_id[capability_id] if satisfies(c.version, constraint)]
        if not candidates:
            raise CapabilityNotFoundError(f"{capability_id} (constraint={constraint})")

        return max(candidates, key=lambda c: c.version)


class VersionedCapabilityLoader:
    def __init__(self, specs_roots: Iterable[Path]):
        self._roots = [Path(p) for p in specs_roots]
        self._index = CapabilityVersionIndex()

    @property
    def index(self) -> CapabilityVersionIndex:
        return self._index

    def build_index(self) -> None:
        for root in self._roots:
            if not root.exists():
                continue
            for path in root.rglob("*.yaml"):
                spec = self._read_yaml(path)
                if not isinstance(spec, dict):
                    continue
                meta = spec.get("meta") or {}
                cap_id = meta.get("id")
                ver = meta.get("version")
                if not cap_id or not ver:
                    continue
                self._index.add(CapabilityVersion(capability_id=str(cap_id), version=SemVer.parse(str(ver)), spec=spec))

    def resolve(self, capability_id: str, constraint: str = "") -> CapabilityVersion:
        return self._index.resolve(capability_id, constraint)

    def resolve_with_dependencies(
        self,
        root: CapabilityRef,
    ) -> List[CapabilityVersion]:
        resolved: List[CapabilityVersion] = []
        visiting: set[Tuple[str, str]] = set()
        visited: set[Tuple[str, str]] = set()

        def dfs(ref: CapabilityRef) -> None:
            key = (ref.capability_id, ref.constraint)
            if key in visited:
                return
            if key in visiting:
                raise RuntimeError(f"Dependency cycle detected at {ref.capability_id}")
            visiting.add(key)

            cap = self.resolve(ref.capability_id, ref.constraint)
            deps = _parse_dependencies(cap.spec)
            for dep in deps:
                dfs(dep)

            visiting.remove(key)
            visited.add(key)
            resolved.append(cap)

        dfs(root)
        return resolved

    def _read_yaml(self, path: Path) -> Any:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)


def _parse_dependencies(spec: Dict[str, Any]) -> List[CapabilityRef]:
    meta = spec.get("meta") or {}
    deps = meta.get("dependencies") or []
    result: List[CapabilityRef] = []

    if isinstance(deps, list):
        for d in deps:
            if isinstance(d, str):
                cap_id, constraint = _split_ref(d)
                result.append(CapabilityRef(capability_id=cap_id, constraint=constraint))
            elif isinstance(d, dict):
                cap_id = d.get("id") or d.get("capability_id")
                constraint = d.get("version") or d.get("constraint") or ""
                if cap_id:
                    result.append(CapabilityRef(capability_id=str(cap_id), constraint=str(constraint)))

    return result


def _split_ref(raw: str) -> Tuple[str, str]:
    s = (raw or "").strip()
    if "@" not in s:
        return s, ""
    cap_id, c = s.split("@", 1)
    return cap_id.strip(), c.strip()
