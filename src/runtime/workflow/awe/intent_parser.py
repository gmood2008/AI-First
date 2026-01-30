from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .domain import Task, Workflow
from .intent import ClarificationRequest, IntentParseResult, IntentStatus, Proposal


class IntentParser(Protocol):
    def parse(self, *, intent: str) -> IntentParseResult:
        raise NotImplementedError


@dataclass
class DeterministicIntentParser:
    min_intent_len: int = 12

    def parse(self, *, intent: str) -> IntentParseResult:
        normalized = (intent or "").strip()
        if len(normalized) < self.min_intent_len:
            return IntentParseResult(
                status=IntentStatus.NEEDS_CLARIFICATION,
                clarification=ClarificationRequest(
                    questions=[
                        "你的目标是什么？请用一句话描述期望产出。",
                        "是否有必须使用/禁止使用的 capability 或数据源？",
                    ],
                    metadata={"reason": "intent_too_short"},
                ),
            )

        if "?" in normalized or "？" in normalized:
            return IntentParseResult(
                status=IntentStatus.NEEDS_CLARIFICATION,
                clarification=ClarificationRequest(
                    questions=[
                        "你希望我优先解决哪个问题/输出哪个产物？",
                        "是否允许产生副作用（写文件/网络请求/执行命令）？",
                    ],
                    metadata={"reason": "intent_contains_question"},
                ),
            )

        task = Task(
            task_id="t1",
            kind="composite",
            title="Execute approved plan",
            metadata={"source": "deterministic_parser"},
        )

        wf = Workflow(
            workflow_id="awe.workflow.proposed",
            title="Proposed Workflow",
            tasks=[task],
            links=[],
            metadata={"intent": normalized},
        )

        plan_md = "\n".join(
            [
                "# Proposal",
                "",
                f"**Intent**: {normalized}",
                "",
                "## Plan",
                "1. Clarify any missing constraints (if needed).",
                "2. Run shadow mode to preview side effects.",
                "3. Ask for user handshake.",
                "4. Execute tasks with rollback enabled.",
            ]
        )

        return IntentParseResult(
            status=IntentStatus.PROPOSED,
            proposal=Proposal(
                intent=normalized,
                plan_markdown=plan_md,
                workflow=wf,
                tasks=[task],
                metadata={"parser": "deterministic"},
            ),
        )
