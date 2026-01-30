from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .intent import Proposal


class HandshakeRequiredError(RuntimeError):
    pass


@dataclass
class ProposalHandshakeGate:
    proposal: Proposal
    approved: bool = False
    approval_note: str = ""

    def approve(self, note: str = "") -> None:
        self.approved = True
        self.approval_note = note

    def reject(self, note: str = "") -> None:
        self.approved = False
        self.approval_note = note

    def require_approved(self) -> None:
        if not self.approved:
            raise HandshakeRequiredError("proposal not approved")
