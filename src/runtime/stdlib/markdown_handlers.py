from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from ..handler import ActionHandler


def _split_markdown(md: str, split_by: str) -> List[str]:
    text = md.replace("\r\n", "\n").replace("\r", "\n")
    if split_by == "horizontal_rule":
        parts = re.split(r"\n\s*---+\s*\n", text)
        return [p.strip() for p in parts if p.strip()]

    chunks: List[str] = []
    current: List[str] = []
    for line in text.split("\n"):
        if line.startswith("# "):
            if current:
                chunks.append("\n".join(current).strip())
                current = []
            current.append(line)
        else:
            current.append(line)
    if current:
        chunks.append("\n".join(current).strip())
    return [c for c in chunks if c]


def _parse_chunk(chunk: str) -> Dict[str, Any]:
    lines = [l.rstrip() for l in chunk.split("\n")]
    heading = ""
    content: List[Dict[str, Any]] = []

    i = 0
    if lines and lines[0].startswith("# "):
        heading = lines[0][2:].strip()
        i = 1

    bullets: List[str] = []
    paragraph_lines: List[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        text = " ".join([x.strip() for x in paragraph_lines if x.strip()]).strip()
        if text:
            content.append({"type": "paragraph", "text": text})
        paragraph_lines = []

    def flush_bullets() -> None:
        nonlocal bullets
        if bullets:
            content.append({"type": "bullet_list", "bullets": bullets})
        bullets = []

    for line in lines[i:]:
        if not line.strip():
            flush_bullets()
            flush_paragraph()
            continue

        m = re.match(r"^\s*[-*]\s+(.*)$", line)
        if m:
            flush_paragraph()
            bullets.append(m.group(1).strip())
            continue

        flush_bullets()
        paragraph_lines.append(line.strip())

    flush_bullets()
    flush_paragraph()

    if not heading:
        heading = "Slide"

    if not content:
        content = [{"type": "paragraph", "text": ""}]

    return {"heading": heading, "content": content}


class MarkdownToSlidesHandler(ActionHandler):
    def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        self.validate_params(params)

        md = params.get("md_content")
        if not isinstance(md, str):
            raise ValueError("md_content must be a string")

        rules = params.get("parsing_rules") or {}
        if not isinstance(rules, dict):
            raise ValueError("parsing_rules must be an object")

        split_by = rules.get("split_by", "h1")
        if split_by not in {"h1", "horizontal_rule"}:
            raise ValueError("parsing_rules.split_by must be 'h1' or 'horizontal_rule'")

        extract_images = rules.get("extract_images", False)
        if extract_images not in {True, False}:
            raise ValueError("parsing_rules.extract_images must be boolean")
        if extract_images:
            raise ValueError("input_constraints.forbid_external_urls violated")

        chunks = _split_markdown(md, split_by)
        slides = [_parse_chunk(c) for c in chunks]

        metadata = {
            "split_by": split_by,
            "source": (context.metadata or {}).get("source") if hasattr(context, "metadata") else None,
        }

        return {"structured_slides": slides, "metadata": metadata}
