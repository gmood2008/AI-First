from __future__ import annotations

import argparse
from pathlib import Path

from runtime.audit.exporter import export_audit_jsonl


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, help="Path to audit.db")
    parser.add_argument("--out", required=True, help="Output jsonl path")
    parser.add_argument("--session", default=None, help="Optional session_id filter")
    args = parser.parse_args()

    count = export_audit_jsonl(db_path=Path(args.db), out_path=Path(args.out), session_id=args.session)
    print(f"exported {count} records to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
