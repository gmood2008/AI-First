from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from contextlib import closing


def export_audit_jsonl(
    *,
    db_path: str | Path,
    out_path: str | Path,
    session_id: Optional[str] = None,
) -> int:
    db_path = Path(db_path)
    out_path = Path(out_path)

    query = "SELECT * FROM audit_log"
    params: list[Any] = []
    if session_id:
        query += " WHERE session_id = ?"
        params.append(session_id)
    query += " ORDER BY id ASC"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with closing(sqlite3.connect(str(db_path))) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params)

        with open(out_path, "w", encoding="utf-8") as f:
            for row in rows:
                record = _row_to_dict(row)
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1

    return count


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)

    for k in ["params_json", "result_json"]:
        v = d.get(k)
        if isinstance(v, str) and v:
            try:
                d[k] = json.loads(v)
            except Exception:
                pass

    if isinstance(d.get("side_effects"), str):
        d["side_effects"] = [s for s in d["side_effects"].split(",") if s]

    return d
