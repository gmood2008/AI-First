import pytest

from runtime.workflow.awe import DeterministicIntentParser, HandshakeRequiredError, IntentStatus, ProposalHandshakeGate


def test_intent_parser_returns_clarification_for_short_intent() -> None:
    p = DeterministicIntentParser(min_intent_len=12)
    r = p.parse(intent="hi")
    assert r.status == IntentStatus.NEEDS_CLARIFICATION
    c = r.require_clarification()
    assert len(c.questions) >= 1


def test_intent_parser_returns_proposal_for_clear_intent() -> None:
    p = DeterministicIntentParser(min_intent_len=5)
    r = p.parse(intent="generate a report for TSLA")
    assert r.status == IntentStatus.PROPOSED
    proposal = r.require_proposal()
    assert "Proposal" in proposal.plan_markdown
    assert proposal.intent == "generate a report for TSLA"
    assert proposal.workflow is not None
    assert proposal.workflow.metadata["intent"] == "generate a report for TSLA"


def test_handshake_gate_blocks_until_approved() -> None:
    p = DeterministicIntentParser(min_intent_len=5)
    r = p.parse(intent="do something deterministic")
    proposal = r.require_proposal()

    gate = ProposalHandshakeGate(proposal=proposal)

    with pytest.raises(HandshakeRequiredError):
        gate.require_approved()

    gate.approve(note="ok")
    gate.require_approved()
