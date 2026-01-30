#!/usr/bin/env python3

import argparse
import re
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def _extract_bundle_path(output: str) -> Path | None:
    m = re.search(r"^BUNDLE_CREATED=(.+)$", output, flags=re.MULTILINE)
    if not m:
        return None
    return Path(m.group(1)).expanduser().resolve()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Release pipeline for offline-bundle-first distribution: smoke -> build wheel -> bundle (.tar.gz) -> optional local sync"
    )
    parser.add_argument(
        "--sync-dst",
        default=None,
        help="Optional local folder to sync bundle artifacts into (e.g. /Users/daniel/AI项目/Aegis/ai-first-runtime)",
    )
    parser.add_argument(
        "--no-smoke",
        action="store_true",
        help="Skip smoke_wheel_install (not recommended)",
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]

    if not args.no_smoke:
        smoke = _run([sys.executable, "scripts/smoke_wheel_install.py"], cwd=repo)
        sys.stdout.write(smoke.stdout)

    bundle = _run([sys.executable, "scripts/make_offline_bundle.py"], cwd=repo)
    sys.stdout.write(bundle.stdout)

    bundle_path = _extract_bundle_path(bundle.stdout)
    if bundle_path is None:
        raise SystemExit("Failed to parse BUNDLE_CREATED from make_offline_bundle.py output")

    if args.sync_dst:
        dst = Path(args.sync_dst).expanduser().resolve()
        # Sync bundle + docs/assets using provided rsync wrapper
        sync_cmd = [
            "bash",
            "scripts/local_sync_offline_bundle.sh",
            "--src",
            str(repo),
            "--dst",
            str(dst),
            "--mode",
            "bundle",
        ]
        sync = _run(sync_cmd, cwd=repo)
        sys.stdout.write(sync.stdout)

    print(f"RELEASE_OFFLINE_BUNDLE={bundle_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
