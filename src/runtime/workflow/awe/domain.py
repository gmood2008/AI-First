from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Link(BaseModel):
    model_config = ConfigDict(extra="allow")

    source: str
    target: str
    kind: str = Field(default="depends_on")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    model_config = ConfigDict(extra="allow")

    task_id: str
    kind: str = Field(default="action")
    title: Optional[str] = None
    capability_id: Optional[str] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)

    sub_tasks: List["Task"] = Field(default_factory=list)

    metadata: Dict[str, Any] = Field(default_factory=dict)


class Workflow(BaseModel):
    model_config = ConfigDict(extra="allow")

    workflow_id: str
    version: str = Field(default="1.0.0")
    title: Optional[str] = None

    tasks: List[Task] = Field(default_factory=list)
    links: List[Link] = Field(default_factory=list)

    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workflow":
        return cls.model_validate(data)

    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        return cls.model_json_schema()
