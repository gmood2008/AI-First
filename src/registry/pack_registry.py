"""
AI-First Runtime v3.1 - Pack Registry (Governance Corrected)

Design Principles (ENFORCED):
1. Proposal-only registration (no implicit activation)
2. State transitions ONLY via governance
3. ACTIVE is the ONLY executable state
4. Stable identity via pack_id (not name)
5. Registry = Law Enforcement, not Decision Maker
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from src.specs.capability_pack import (
    CapabilityPackSpec,
    PackState,
)
from src.specs.v3.capability_schema import RiskLevel
from src.runtime.registry import CapabilityRegistry


# =========================
# Exceptions
# =========================

class PackRegistryError(Exception):
    pass


class PackNotFoundError(PackRegistryError):
    pass


class InvalidPackError(PackRegistryError):
    pass


class PackStateTransitionError(PackRegistryError):
    pass


# =========================
# Risk Utilities (v3.1)
# =========================

_RISK_ORDER = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.CRITICAL: 3,
}


def risk_ge(a: RiskLevel, b: RiskLevel) -> bool:
    """Return True if a >= b in risk severity."""
    return _RISK_ORDER[a] >= _RISK_ORDER[b]


# =========================
# Pack Registry
# =========================

class PackRegistry:
    """
    Capability Pack Registry (Governance-Enforced)

    ⚠️ v3.x ASSUMPTION:
    - Single-writer
    - Registry is authoritative
    - All governance decisions come from Governance API
    """

    _TRANSITIONS: Dict[PackState, List[PackState]] = {
        PackState.PROPOSED: [PackState.ACTIVE, PackState.DEPRECATED],
        PackState.ACTIVE: [PackState.FROZEN, PackState.DEPRECATED],
        PackState.FROZEN: [PackState.ACTIVE, PackState.DEPRECATED],
        PackState.DEPRECATED: [],
    }

    def __init__(
        self,
        db_path: Optional[Path] = None,
        capability_registry: Optional[CapabilityRegistry] = None,
    ):
        if db_path is None:
            db_path = Path.home() / ".ai-first" / "pack_registry.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.capability_registry = capability_registry
        self._init_db()

        # In-memory cache (single-writer assumption)
        self._packs: Dict[str, Dict[str, Any]] = {}
        self._load_all()

    # =========================
    # Database
    # =========================

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS packs (
                    pack_id TEXT NOT NULL,
                    pack_name TEXT NOT NULL,
                    pack_version TEXT NOT NULL,
                    pack_spec TEXT NOT NULL,
                    state TEXT NOT NULL,
                    registered_at TEXT NOT NULL,
                    registered_by TEXT NOT NULL,
                    proposal_id TEXT,
                    approval_id TEXT,
                    metadata TEXT,
                    PRIMARY KEY (pack_id, pack_version)
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_pack_state ON packs(state)"
            )
            conn.commit()

    def _load_all(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute("SELECT * FROM packs"):
                key = f"{row['pack_id']}@{row['pack_version']}"
                self._packs[key] = {
                    "pack_id": row["pack_id"],
                    "pack_name": row["pack_name"],
                    "pack_version": row["pack_version"],
                    "pack_spec": json.loads(row["pack_spec"]),
                    "state": PackState(row["state"]),
                    "registered_at": datetime.fromisoformat(row["registered_at"]),
                    "registered_by": row["registered_by"],
                    "proposal_id": row["proposal_id"],
                    "approval_id": row["approval_id"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                }

    # =========================
    # Registration
    # =========================

    def register_pack(
        self,
        pack_spec: CapabilityPackSpec,
        registered_by: Optional[str] = None,
        proposal_id: Optional[str] = None,
    ) -> None:
        """
        Register a Pack Proposal.

        ❗ ALWAYS registers as PROPOSED.
        Activation MUST happen via transition_state().
        """
        self._validate_pack(pack_spec)

        key = f"{pack_spec.pack_id}@{pack_spec.version}"
        if key in self._packs:
            raise PackRegistryError(f"Pack already exists: {key}")

        now = datetime.now().isoformat()

        record = {
            "pack_id": pack_spec.pack_id,
            "pack_name": pack_spec.name,
            "pack_version": pack_spec.version,
            "pack_spec": pack_spec.to_dict(),
            "state": PackState.PROPOSED.value,
            "registered_at": now,
            "registered_by": registered_by,
            "proposal_id": proposal_id,
            "approval_id": None,
            "metadata": {},
        }

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO packs
                (pack_id, pack_name, pack_version, pack_spec, state,
                 registered_at, registered_by, proposal_id, approval_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record["pack_id"],
                record["pack_name"],
                record["pack_version"],
                json.dumps(record["pack_spec"]),
                record["state"],
                record["registered_at"],
                record["registered_by"],
                record["proposal_id"],
                record["approval_id"],
                json.dumps(record["metadata"]),
            ))
            conn.commit()

        self._packs[key] = {
            **record,
            "state": PackState.PROPOSED,
            "registered_at": datetime.fromisoformat(now),
        }

    # =========================
    # Validation
    # =========================

    def _validate_pack(self, pack: CapabilityPackSpec) -> None:
        if not self.capability_registry:
            return

        max_cap_risk = RiskLevel.LOW

        for cid in pack.includes.capabilities:
            if not self.capability_registry.has_capability(cid):
                raise InvalidPackError(f"Capability not found: {cid}")

            spec = self.capability_registry.get_spec(cid)
            if spec and "risk" in spec:
                cap_risk = RiskLevel(spec["risk"]["level"])
                if not risk_ge(pack.risk_profile.max_risk, cap_risk):
                    max_cap_risk = cap_risk

        if not risk_ge(pack.risk_profile.max_risk, max_cap_risk):
            raise InvalidPackError(
                f"Pack max_risk {pack.risk_profile.max_risk.value} "
                f"< capability risk {max_cap_risk.value}"
            )

        # Workflow risk envelopes: ensure referenced workflow IDs are valid.
        # When WorkflowSpec gains a risk_level field, enforce pack max_risk >= workflow risk.
        for wid in (pack.includes.workflows or []):
            if not wid or not str(wid).strip():
                raise InvalidPackError("Pack includes empty workflow ID")

    # =========================
    # Queries
    # =========================

    def get_pack(
        self,
        pack_id: str,
        version: Optional[str] = None,
    ) -> Optional[CapabilityPackSpec]:
        matches = [
            p for p in self._packs.values()
            if p["pack_id"] == pack_id
        ]

        if not matches:
            return None

        if version:
            for p in matches:
                if p["pack_version"] == version:
                    return CapabilityPackSpec.from_dict(p["pack_spec"])
            return None

        latest = max(matches, key=lambda p: p["pack_version"])
        return CapabilityPackSpec.from_dict(latest["pack_spec"])

    def get_pack_record(
        self,
        pack_ref: str,
        version: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        # Prefer exact pack_id match
        matches = [
            p for p in self._packs.values()
            if p["pack_id"] == pack_ref
        ]
        if not matches:
            matches = [
                p for p in self._packs.values()
                if p["pack_name"] == pack_ref
            ]
        if not matches:
            return None

        if version:
            for p in matches:
                if p["pack_version"] == version:
                    return p
            return None

        latest = max(matches, key=lambda p: p["pack_version"])
        return latest

    def get_pack_state(
        self,
        pack_ref: str,
        version: Optional[str] = None,
    ) -> Optional[PackState]:
        rec = self.get_pack_record(pack_ref=pack_ref, version=version)
        return rec["state"] if rec else None

    def list_packs(
        self,
        state: Optional[PackState] = None,
        pack_name: Optional[str] = None,
    ) -> List[CapabilityPackSpec]:
        result = [
            CapabilityPackSpec.from_dict(p["pack_spec"])
            for p in self._packs.values()
            if state is None or p["state"] == state
        ]
        if pack_name is not None:
            result = [spec for spec in result if spec.name == pack_name]
        return result

    # =========================
    # Governance (State Changes)
    # =========================

    def transition_state(
        self,
        pack_id: str,
        version: str,
        new_state: PackState,
        changed_by: str,
        reason: str,
        proposal_id: Optional[str] = None,
        approval_id: Optional[str] = None,
    ) -> None:
        key = f"{pack_id}@{version}"
        if key not in self._packs:
            raise PackNotFoundError(key)

        current = self._packs[key]["state"]
        if new_state not in self._TRANSITIONS[current]:
            raise PackStateTransitionError(
                f"Invalid transition {current.value} → {new_state.value}"
            )

        meta = self._packs[key]["metadata"]
        meta["last_transition"] = {
            "from": current.value,
            "to": new_state.value,
            "by": changed_by,
            "reason": reason,
            "proposal_id": proposal_id,
            "approval_id": approval_id,
            "timestamp": datetime.now().isoformat(),
        }

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE packs
                SET state = ?, approval_id = ?, metadata = ?
                WHERE pack_id = ? AND pack_version = ?
            """, (
                new_state.value,
                approval_id,
                json.dumps(meta),
                pack_id,
                version,
            ))
            conn.commit()

        self._packs[key]["state"] = new_state
        self._packs[key]["approval_id"] = approval_id
        self._packs[key]["metadata"] = meta

    # =========================
    # Runtime Gate
    # =========================

    def is_pack_executable(
        self,
        pack_id: str,
        version: Optional[str] = None,
    ) -> bool:
        pack = self.get_pack(pack_id, version)
        if not pack:
            return False

        key = f"{pack.pack_id}@{pack.version}"
        return self._packs[key]["state"] == PackState.ACTIVE
