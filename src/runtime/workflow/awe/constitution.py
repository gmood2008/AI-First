from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class ConstitutionDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


@dataclass(frozen=True)
class ConstitutionResult:
    decision: ConstitutionDecision
    reason: str = ""
    rule_id: Optional[str] = None


class ConstitutionViolation(RuntimeError):
    pass


class ConstitutionEngine:
    def __init__(
        self,
        mode: str = "lenient",
        snippets_path: Optional[Path] = None,
    ) -> None:
        self.mode = mode
        self._snippets_path = Path(snippets_path) if snippets_path else None

        self._rules: List[Dict[str, Any]] = []
        self._default_decision: ConstitutionDecision = ConstitutionDecision.ALLOW

        if self._snippets_path and self._snippets_path.exists():
            self._load(self._snippets_path)
        else:
            self._load_defaults(mode)

    def check(
        self,
        *,
        capability_id: str,
        principal: Optional[str] = None,
        side_effects: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ConstitutionResult:
        side_effects = side_effects or []
        context = context or {}

        for rule in self._rules:
            if not self._rule_matches(rule, capability_id=capability_id, principal=principal, side_effects=side_effects):
                continue

            action = str(rule.get("action") or "ALLOW").upper()
            decision = ConstitutionDecision(action)
            return ConstitutionResult(
                decision=decision,
                reason=str(rule.get("reason") or ""),
                rule_id=str(rule.get("id")) if rule.get("id") is not None else None,
            )

        return ConstitutionResult(decision=self._default_decision, reason="")

    def enforce(
        self,
        *,
        capability_id: str,
        principal: Optional[str] = None,
        side_effects: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        result = self.check(
            capability_id=capability_id,
            principal=principal,
            side_effects=side_effects,
            context=context,
        )
        if result.decision == ConstitutionDecision.DENY:
            raise ConstitutionViolation(result.reason or f"Denied by constitution: {capability_id}")

    def _load(self, path: Path) -> None:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Invalid constitution snippets")

        default = str(raw.get("default") or "ALLOW").upper()
        self._default_decision = ConstitutionDecision(default)

        rules = raw.get("rules") or []
        if not isinstance(rules, list):
            raise ValueError("Invalid constitution rules")

        self._rules = [r for r in rules if isinstance(r, dict)]

    def _load_defaults(self, mode: str) -> None:
        if mode == "strict":
            self._default_decision = ConstitutionDecision.ALLOW
            self._rules = [
                {
                    "id": "strict-deny-filesystem-write",
                    "capabilities": ["io.*"],
                    "side_effects_any": ["filesystem_write"],
                    "action": "DENY",
                    "reason": "strict mode: filesystem_write is forbidden",
                },
                {
                    "id": "strict-deny-network-write",
                    "capabilities": ["net.*"],
                    "side_effects_any": ["network_write"],
                    "action": "DENY",
                    "reason": "strict mode: network_write is forbidden",
                },
            ]
            return

        self._default_decision = ConstitutionDecision.ALLOW
        self._rules = []

    def _rule_matches(
        self,
        rule: Dict[str, Any],
        *,
        capability_id: str,
        principal: Optional[str],
        side_effects: List[str],
    ) -> bool:
        principals = rule.get("principals")
        if principals is not None:
            if not principal:
                return False
            if not self._any_match_pattern(principals, principal):
                return False

        caps = rule.get("capabilities")
        if caps is not None:
            if not self._any_match_pattern(caps, capability_id):
                return False

        se_any = rule.get("side_effects_any")
        if se_any is not None:
            if not any(s in side_effects for s in se_any):
                return False

        se_all = rule.get("side_effects_all")
        if se_all is not None:
            if not all(s in side_effects for s in se_all):
                return False

        return True

    @staticmethod
    def _any_match_pattern(patterns: Any, value: str) -> bool:
        if isinstance(patterns, str):
            patterns = [patterns]
        if not isinstance(patterns, list):
            return False

        return any(ConstitutionEngine._match_pattern(str(p), value) for p in patterns)

    @staticmethod
    def _match_pattern(pattern: str, value: str) -> bool:
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return value.startswith(pattern[:-1])
        return pattern == value
