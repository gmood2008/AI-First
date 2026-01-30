# aegis-demo

This pack provides a minimal, stdlib-only workflow for Aegis integration testing.

## Included

- Workflow: `aegis_financial_summary_ppt`
- Capabilities:
  - `io.fs.write_file`
  - `io.fs.read_file`
  - `io.fs.list_dir`

## Notes

- Artifacts are written under the workflow workspace (e.g. `workspace/demo/*`).
- Governance PAUSE/DENY is demonstrated via `airun bridge exec-workflow --enable-governance-hooks`.
