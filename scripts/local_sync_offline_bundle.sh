#!/usr/bin/env bash
set -euo pipefail

# Sync offline distribution artifacts between two local folders.
# Usage:
#   scripts/local_sync_offline_bundle.sh \
#     --src "/path/to/ai-first-runtime-master" \
#     --dst "/Users/daniel/AI项目/Aegis/ai-first-runtime" \
#     --mode bundle
#
# Modes:
#   bundle  : sync dist/bundles/*.tar.gz and related dist wheels
#   assets  : sync plaintext assets (capabilities/, packs/, specs/facades)
#   docs    : sync curated docs
#

SRC=""
DST=""
MODE="bundle"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --src)
      SRC="$2"; shift 2;;
    --dst)
      DST="$2"; shift 2;;
    --mode)
      MODE="$2"; shift 2;;
    *)
      echo "Unknown argument: $1"; exit 2;;
  esac
done

if [[ -z "$SRC" || -z "$DST" ]]; then
  echo "Missing --src or --dst" >&2
  exit 2
fi

mkdir -p "$DST"

rsync_common=(
  -avh
  --delete
  --exclude ".git/"
  --exclude ".venv/"
  --exclude "__pycache__/"
  --exclude ".pytest_cache/"
)

case "$MODE" in
  bundle)
    mkdir -p "$DST/dist/bundles" "$DST/dist"
    rsync "${rsync_common[@]}" "$SRC/dist/bundles/" "$DST/dist/bundles/" || true
    rsync "${rsync_common[@]}" "$SRC/dist/" "$DST/dist/" --include "*.whl" --exclude "*" || true
    ;;
  assets)
    mkdir -p "$DST"
    rsync "${rsync_common[@]}" "$SRC/capabilities/" "$DST/capabilities/"
    rsync "${rsync_common[@]}" "$SRC/packs/" "$DST/packs/"
    mkdir -p "$DST/specs"
    rsync "${rsync_common[@]}" "$SRC/specs/facades/" "$DST/specs/facades/"
    ;;
  docs)
    mkdir -p "$DST/docs"
    rsync "${rsync_common[@]}" "$SRC/ARCHITECTURE.md" "$DST/ARCHITECTURE.md" || true
    rsync "${rsync_common[@]}" "$SRC/QUICKSTART_EXTERNAL_INTEGRATION.md" "$DST/QUICKSTART_EXTERNAL_INTEGRATION.md" || true
    rsync "${rsync_common[@]}" "$SRC/docs/" "$DST/docs/" \
      --include "INTERNAL_PYPI_DISTRIBUTION_SOP.md" \
      --include "partner_technical_evaluation.md" \
      --include "INTEGRATION_GUIDE.md" \
      --include "EXTERNAL_CAPABILITY_INTEGRATION.md" \
      --exclude "*"
    ;;
  *)
    echo "Unknown --mode: $MODE (expected: bundle|assets|docs)" >&2
    exit 2
    ;;
esac

echo "SYNC_DONE mode=$MODE"
