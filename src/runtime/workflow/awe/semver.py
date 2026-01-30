from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class SemVer:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, v: str) -> "SemVer":
        parts = (v or "").strip().split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid semver: {v}")
        return cls(major=int(parts[0]), minor=int(parts[1]), patch=int(parts[2]))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def satisfies(version: SemVer, constraint: str) -> bool:
    c = (constraint or "").strip()
    if not c:
        return True

    if c.startswith("^"):
        base = SemVer.parse(c[1:])
        if version.major != base.major:
            return False
        return version >= base

    if c.startswith(">="):
        base = SemVer.parse(c[2:])
        return version >= base

    return version == SemVer.parse(c)
