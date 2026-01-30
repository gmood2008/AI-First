import json
from pathlib import Path

from runtime.audit.exporter import export_audit_jsonl
from runtime.audit.logger import AuditLogger


def test_export_audit_jsonl_roundtrip(tmp_path: Path) -> None:
    db = tmp_path / "audit.db"
    out = tmp_path / "out.jsonl"

    logger = AuditLogger(db_path=str(db))
    logger.log_action(
        session_id="s1",
        user_id="u1",
        capability_id="awe.proposal",
        action_type="decision",
        params={"intent": "x"},
        result={"plan": "y"},
        status="success",
        side_effects=[],
        requires_confirmation=False,
        was_confirmed=None,
        undo_available=False,
    )

    logger.shutdown()

    n = export_audit_jsonl(db_path=db, out_path=out)
    assert n >= 1

    lines = out.read_text(encoding="utf-8").splitlines()
    rec = json.loads(lines[-1])

    assert rec["session_id"] == "s1"
    assert rec["capability_id"] == "awe.proposal"
    assert rec["params_json"]["intent"] == "x"
    assert rec["result_json"]["plan"] == "y"
