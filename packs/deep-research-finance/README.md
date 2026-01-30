# Deep Research Finance Pack

## Overview

This pack provides a deterministic, governable Deep Research workflow for financial reporting.

- Workflow ID: `deep_research_financial_report`
- Primary output artifacts (workspace-relative):
  - `.ai-first/artifacts/deep-research-finance/market.json`
  - `.ai-first/artifacts/deep-research-finance/news.json`
  - `.ai-first/artifacts/deep-research-finance/report.md`
  - `.ai-first/artifacts/deep-research-finance/report.pdf`
  - `.ai-first/artifacts/deep-research-finance/manifest.json`

## Data Sources (Sidecar)

This pack expects an HTTP sidecar providing deterministic endpoints:

- `GET http://127.0.0.1:8787/finance/yahoo?symbol=...` -> JSON market snapshot
- `GET http://127.0.0.1:8787/search/google?q=...` -> JSON search results
- `POST http://127.0.0.1:8787/io/pdf_export` (body: markdown) -> base64 PDF bytes (text/plain)

A mock implementation exists at `scripts/mock_deep_research_sidecar.py`.

## How to Run (Smoke)

1. Start sidecar:

```bash
source .venv/bin/activate
python scripts/mock_deep_research_sidecar.py
```

1. Run the smoke workflow:

```bash
source .venv/bin/activate
python scripts/run_deep_research_smoke.py
```

Each smoke run uses a unique workspace folder under `workspace/<run_id>/`.

## Notes

- Market/news snapshots are stored as **pretty-printed JSON**.
- `manifest.json` includes `run_id/session_id` and SHA256 checksums for all key artifacts.
