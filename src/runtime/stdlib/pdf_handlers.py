"""
PDF capability handlers (io.pdf.* namespace).

Implements io.pdf.extract_table for financial report workflow.
"""

from pathlib import Path
from typing import Any, Dict, List

from ..handler import ActionHandler
from ..types import ActionOutput, SecurityError


def _resolve_path(path_str: str, context: Any) -> Path:
    """Resolve path within workspace."""
    workspace_root = context.workspace_root
    full_path = (workspace_root / path_str).resolve()
    if not str(full_path).startswith(str(workspace_root.resolve())):
        raise SecurityError(f"Path '{path_str}' escapes workspace boundary")
    return full_path


def _parse_page_range(page_range: str, num_pages: int) -> List[int]:
    """Parse page_range string to list of 0-based page indices."""
    if not page_range or page_range == "all":
        return list(range(num_pages))
    indices = []
    for part in page_range.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            start, end = int(a.strip()) - 1, int(b.strip())  # 1-based to 0-based
            indices.extend(range(start, min(end, num_pages)))
        else:
            indices.append(int(part) - 1)
    return sorted(set(i for i in indices if 0 <= i < num_pages))


class PdfExtractTableHandler(ActionHandler):
    """Handler for io.pdf.extract_table."""

    def execute(self, params: Dict[str, Any], context: Any) -> ActionOutput:
        pdf_path = params["pdf_path"]
        page_range = params.get("page_range", "all")
        table_detection_mode = params.get("table_detection_mode", "auto")

        full_path = _resolve_path(pdf_path, context)
        if not full_path.exists():
            return ActionOutput(
                result={"extracted_tables": [], "success": False, "error_message": f"PDF not found: {pdf_path}"},
                undo_closure=None,
                description="io.pdf.extract_table: PDF not found",
            )

        try:
            import pdfplumber
        except ImportError:
            return ActionOutput(
                result={
                    "extracted_tables": [],
                    "success": False,
                    "error_message": "pdfplumber is required for io.pdf.extract_table. Install with: pip install pdfplumber",
                },
                undo_closure=None,
                description="io.pdf.extract_table: missing pdfplumber",
            )

        try:
            with pdfplumber.open(full_path) as pdf:
                num_pages = len(pdf.pages)
                pages_to_use = _parse_page_range(page_range, num_pages)
                extracted_tables = []
                for i in pages_to_use:
                    page = pdf.pages[i]
                    tables = page.extract_tables()
                    for table in tables or []:
                        if not table:
                            continue
                        rows = [list(r) for r in table if r]
                        if not rows:
                            continue
                        headers = [str(h) if h is not None else f"_col{j}" for j, h in enumerate(rows[0])]
                        out_rows = []
                        for row in rows[1:]:
                            out_rows.append(dict(zip(headers, [v for v in row] + [None] * (len(headers) - len(row)))))
                        if not out_rows and len(rows) == 1:
                            out_rows = [dict(zip(headers, rows[0]))]
                        extracted_tables.append({"page": i + 1, "rows": out_rows, "headers": headers})

            return ActionOutput(
                result={"extracted_tables": extracted_tables, "success": True},
                undo_closure=None,
                description=f"io.pdf.extract_table: extracted {len(extracted_tables)} table(s) from {pdf_path}",
            )
        except Exception as e:
            return ActionOutput(
                result={"extracted_tables": [], "success": False, "error_message": str(e)},
                undo_closure=None,
                description="io.pdf.extract_table: extraction failed",
            )
