#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _read_lines(path: Path) -> List[str]:
    return path.read_text(encoding="utf-8", errors="ignore").splitlines()


def _is_list_line(line: str) -> bool:
    return bool(re.match(r"^\s*([-*+]|\d+\.)\s+", line))


def lint_markdown(path: Path) -> List[str]:
    errors: List[str] = []
    lines = _read_lines(path)

    in_fence = False
    fence_line_no = -1
    fence_lang = ""

    in_list_block = False
    list_block_start_line = -1

    i = 0
    while i < len(lines):
        line = lines[i]
        ln = i + 1

        m = re.match(r"^(\s*)(```+)(.*)$", line)
        if m:
            info = (m.group(3) or "").strip()
            if not in_fence:
                in_fence = True
                fence_line_no = ln
                fence_lang = info

                if not fence_lang:
                    errors.append(f"MD040 fenced-code-language: {path}: line {ln}")

                if i - 1 >= 0:
                    prev = lines[i - 1]
                    if prev.strip() != "":
                        errors.append(f"MD031 blanks-around-fences: {path}: line {ln} (missing blank line before)")

            else:
                in_fence = False

                if i + 1 < len(lines):
                    nxt = lines[i + 1]
                    if nxt.strip() != "":
                        errors.append(f"MD031 blanks-around-fences: {path}: line {ln} (missing blank line after)")

            # Fence boundary terminates any list block
            in_list_block = False
            list_block_start_line = -1

            i += 1
            continue

        if in_fence:
            i += 1
            continue

        is_list_line = _is_list_line(line)

        if is_list_line:
            # Entering a list block: enforce blank line before list
            if not in_list_block:
                list_block_start_line = ln
                if i - 1 >= 0 and lines[i - 1].strip() != "":
                    errors.append(
                        f"MD032 blanks-around-lists: {path}: line {ln} (missing blank line before list)"
                    )
                in_list_block = True
            i += 1
            continue

        # Not a list line
        if line.strip() == "":
            # Blank line ends list block (and also satisfies 'after list')
            in_list_block = False
            list_block_start_line = -1
            i += 1
            continue

        # Normal content line
        if in_list_block:
            # List block ended but next content is not separated by blank line
            start_ln = list_block_start_line if list_block_start_line > 0 else ln
            errors.append(
                f"MD032 blanks-around-lists: {path}: line {start_ln} (missing blank line after list)"
            )
            in_list_block = False
            list_block_start_line = -1

        i += 1

    if in_fence:
        errors.append(f"Unclosed fenced code block starting at line {fence_line_no}: {path}")

    return errors


def main() -> int:
    root = _project_root()

    targets = [
        root / "docs" / "EXTERNAL_CAPABILITY_INTEGRATION.md",
    ]

    errors: List[str] = []
    for t in targets:
        if not t.exists():
            errors.append(f"markdown lint target missing: {t}")
            continue
        errors.extend(lint_markdown(t))

    if errors:
        for e in errors:
            print(f"❌ {e}")
        print(f"\nMarkdown lint failed: {len(errors)} error(s).")
        return 3

    print("✅ Markdown lint passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
