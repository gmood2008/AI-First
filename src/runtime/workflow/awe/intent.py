from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .domain import Task, Workflow


class IntentStatus(str, Enum):
    PROPOSED = "PROPOSED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


class ClarificationRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    questions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Proposal(BaseModel):
    model_config = ConfigDict(extra="allow")

    intent: str
    plan_markdown: str
    workflow: Optional[Workflow] = None
    tasks: List[Task] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntentParseResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: IntentStatus
    proposal: Optional[Proposal] = None
    clarification: Optional[ClarificationRequest] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def require_proposal(self) -> Proposal:
        if self.status != IntentStatus.PROPOSED or self.proposal is None:
            raise ValueError("proposal not available")
        return self.proposal

    def require_clarification(self) -> ClarificationRequest:
        if self.status != IntentStatus.NEEDS_CLARIFICATION or self.clarification is None:
            raise ValueError("clarification not available")
        return self.clarification
