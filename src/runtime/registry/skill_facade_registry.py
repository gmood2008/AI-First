"""
Skill Facade Registry - Semantic entry layer; no risk, no Capability dependency.

Design:
- register_facade() → PROPOSED only; ACTIVE only via transition_state (governance).
- list_facades() / get_facade_by_trigger() for retrieval and route info only.
- Facade does not participate in risk calculation; does not depend on CapabilityRegistry.
"""

import sqlite3
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from contextlib import closing
from enum import Enum

from specs.skill_facade import SkillFacadeSpec


# =========================
# Lifecycle
# =========================

class FacadeState(str, Enum):
    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    DEPRECATED = "DEPRECATED"


# =========================
# Exceptions
# =========================

class SkillFacadeRegistryError(Exception):
    pass


class FacadeNotFoundError(SkillFacadeRegistryError):
    pass


class FacadeStateTransitionError(SkillFacadeRegistryError):
    pass


# =========================
# Skill Facade Registry
# =========================

class SkillFacadeRegistry:
    """
    Skill Facade Registry.

    - register_facade() → PROPOSED only; activation via transition_state (governance).
    - list_facades() / get_facade_by_trigger() for retrieval and route info.
    - No risk; no dependency on CapabilityRegistry.
    """

    _TRANSITIONS: Dict[FacadeState, List[FacadeState]] = {
        FacadeState.PROPOSED: [FacadeState.ACTIVE, FacadeState.DEPRECATED],
        FacadeState.ACTIVE: [FacadeState.FROZEN, FacadeState.DEPRECATED],
        FacadeState.FROZEN: [FacadeState.ACTIVE, FacadeState.DEPRECATED],
        FacadeState.DEPRECATED: [],
    }

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path.home() / ".ai-first" / "skill_facade_registry.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._facades: Dict[str, Dict[str, Any]] = {}
        self._load_all()

    def _init_db(self) -> None:
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS facades (
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    spec TEXT NOT NULL,
                    state TEXT NOT NULL,
                    registered_at TEXT NOT NULL,
                    registered_by TEXT,
                    proposal_id TEXT,
                    approval_id TEXT,
                    metadata TEXT,
                    PRIMARY KEY (name, version)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facade_state ON facades(state)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facade_name ON facades(name)")
            conn.commit()

    def _load_all(self) -> None:
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute("SELECT * FROM facades"):
                key = f"{row['name']}@{row['version']}"
                self._facades[key] = {
                    "name": row["name"],
                    "version": row["version"],
                    "spec": SkillFacadeSpec.from_dict(json.loads(row["spec"])),
                    "state": FacadeState(row["state"]),
                    "registered_at": datetime.fromisoformat(row["registered_at"]),
                    "registered_by": row["registered_by"],
                    "proposal_id": row["proposal_id"],
                    "approval_id": row["approval_id"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                }

    def register_facade(
        self,
        spec: SkillFacadeSpec,
        registered_by: Optional[str] = None,
        proposal_id: Optional[str] = None,
    ) -> None:
        """
        Register a facade. Always as PROPOSED; ACTIVE only via transition_state.
        """
        key = f"{spec.name}@{spec.version}"
        if key in self._facades:
            raise SkillFacadeRegistryError(f"Facade already exists: {key}")

        now = datetime.now().isoformat()
        record = {
            "name": spec.name,
            "version": spec.version,
            "spec": spec,
            "state": FacadeState.PROPOSED,
            "registered_at": datetime.fromisoformat(now),
            "registered_by": registered_by,
            "proposal_id": proposal_id,
            "approval_id": None,
            "metadata": {},
        }

        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO facades
                (name, version, spec, state, registered_at, registered_by, proposal_id, approval_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                spec.name,
                spec.version,
                json.dumps(spec.to_dict()),
                FacadeState.PROPOSED.value,
                now,
                registered_by,
                proposal_id,
                None,
                json.dumps({}),
            ))
            conn.commit()

        self._facades[key] = record

    def transition_state(
        self,
        name: str,
        version: str,
        new_state: FacadeState,
        changed_by: str,
        reason: str,
        approval_id: Optional[str] = None,
    ) -> None:
        key = f"{name}@{version}"
        if key not in self._facades:
            raise FacadeNotFoundError(key)

        current = self._facades[key]["state"]
        if new_state not in self._TRANSITIONS[current]:
            raise FacadeStateTransitionError(
                f"Invalid transition {current.value} → {new_state.value}"
            )

        meta = self._facades[key]["metadata"]
        meta["last_transition"] = {
            "from": current.value,
            "to": new_state.value,
            "by": changed_by,
            "reason": reason,
            "approval_id": approval_id,
            "timestamp": datetime.now().isoformat(),
        }

        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("""
                UPDATE facades
                SET state = ?, approval_id = ?, metadata = ?
                WHERE name = ? AND version = ?
            """, (new_state.value, approval_id, json.dumps(meta), name, version))
            conn.commit()

        self._facades[key]["state"] = new_state
        self._facades[key]["approval_id"] = approval_id
        self._facades[key]["metadata"] = meta

    def activate_facade(
        self,
        name: str,
        version: str,
        changed_by: str,
        reason: str,
        approval_id: Optional[str] = None,
    ) -> None:
        self.transition_state(
            name=name,
            version=version,
            new_state=FacadeState.ACTIVE,
            changed_by=changed_by,
            reason=reason,
            approval_id=approval_id,
        )

    def freeze_facade(
        self,
        name: str,
        version: str,
        changed_by: str,
        reason: str,
        approval_id: Optional[str] = None,
    ) -> None:
        self.transition_state(
            name=name,
            version=version,
            new_state=FacadeState.FROZEN,
            changed_by=changed_by,
            reason=reason,
            approval_id=approval_id,
        )

    def deprecate_facade(
        self,
        name: str,
        version: str,
        changed_by: str,
        reason: str,
        approval_id: Optional[str] = None,
    ) -> None:
        self.transition_state(
            name=name,
            version=version,
            new_state=FacadeState.DEPRECATED,
            changed_by=changed_by,
            reason=reason,
            approval_id=approval_id,
        )

    def list_facades(
        self,
        state: Optional[FacadeState] = None,
        name: Optional[str] = None,
    ) -> List[SkillFacadeSpec]:
        result = [
            rec["spec"]
            for rec in self._facades.values()
            if (state is None or rec["state"] == state)
        ]
        if name is not None:
            result = [s for s in result if s.name == name]
        return result

    def get_facade(self, name: str, version: Optional[str] = None) -> Optional[SkillFacadeSpec]:
        matches = [r for r in self._facades.values() if r["name"] == name]
        if not matches:
            return None
        if version:
            for r in matches:
                if r["version"] == version:
                    return r["spec"]
            return None
        latest = max(matches, key=lambda r: r["version"])
        return latest["spec"]

    def get_facade_record(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        matches = [r for r in self._facades.values() if r["name"] == name]
        if not matches:
            return None

        if version:
            for r in matches:
                if r["version"] == version:
                    return r
            return None

        latest = max(matches, key=lambda r: r["version"])
        return latest

    def get_facade_state(self, name: str, version: Optional[str] = None) -> Optional[FacadeState]:
        rec = self.get_facade_record(name=name, version=version)
        return rec["state"] if rec else None

    def get_facade_by_trigger(self, text: str) -> Optional[SkillFacadeSpec]:
        """
        Match natural language input to an ACTIVE facade by triggers.
        Uses normalized substring match: text and triggers are lowercased/stripped;
        first facade with any trigger contained in text, or text contained in trigger, wins.
        """
        if not text or not isinstance(text, str):
            return None
        normalized = text.strip().lower()
        if not normalized:
            return None

        active = [r for r in self._facades.values() if r["state"] == FacadeState.ACTIVE]
        for rec in active:
            spec = rec["spec"]
            for trigger in spec.triggers:
                t = trigger.strip().lower()
                if t in normalized or normalized in t:
                    return spec
        return None

    def match(self, text: str) -> Optional[SkillFacadeSpec]:
        """Alias for get_facade_by_trigger for routing code."""
        return self.get_facade_by_trigger(text)

    def is_facade_active(self, name: str, version: Optional[str] = None) -> bool:
        if version:
            key = f"{name}@{version}"
            return key in self._facades and self._facades[key]["state"] == FacadeState.ACTIVE
        return any(
            r["name"] == name and r["state"] == FacadeState.ACTIVE
            for r in self._facades.values()
        )
