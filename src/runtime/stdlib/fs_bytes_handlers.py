from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

from ..handler import ActionHandler
from ..types import ActionOutput, SecurityError


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _resolve_path(path_str: str, context: Any) -> Path:
    workspace_root = Path(context.workspace_root)
    full_path = (workspace_root / path_str).resolve()
    if not str(full_path).startswith(str(workspace_root.resolve())):
        raise SecurityError(f"Path '{path_str}' escapes workspace boundary")
    return full_path


class WriteBytesHandler(ActionHandler):
    def execute(self, params: Dict[str, Any], context: Any) -> ActionOutput:
        self.validate_params(params)

        path_str = params.get("path")
        if not isinstance(path_str, str) or not path_str.strip():
            raise ValueError("path must be a non-empty string")

        content_b64 = params.get("content_base64")
        if not isinstance(content_b64, str) or not content_b64.strip():
            raise ValueError("content_base64 must be a non-empty string")

        overwrite = params.get("overwrite", False)
        if overwrite not in {True, False}:
            raise ValueError("overwrite must be boolean")

        create_dirs = params.get("create_dirs", False)
        if create_dirs not in {True, False}:
            raise ValueError("create_dirs must be boolean")

        max_bytes = int(self.contracts.get("max_bytes", 20 * 1024 * 1024))

        try:
            data = base64.b64decode(content_b64.encode("utf-8"), validate=True)
        except Exception as e:
            raise ValueError("content_base64 is not valid base64") from e

        if len(data) > max_bytes:
            raise ValueError("execution_constraints.max_bytes exceeded")

        full_path = _resolve_path(path_str.strip(), context)
        if create_dirs:
            full_path.parent.mkdir(parents=True, exist_ok=True)

        existed = full_path.exists()
        if existed and not overwrite:
            raise ValueError("file exists and overwrite=false")

        backup: Optional[bytes] = None
        if existed:
            backup = full_path.read_bytes()

        full_path.write_bytes(data)

        checksum = _sha256_bytes(data)

        def undo() -> None:
            if existed and backup is not None:
                full_path.write_bytes(backup)
            else:
                full_path.unlink(missing_ok=True)

        return ActionOutput(
            result={
                "file_path": str(full_path),
                "bytes_written": len(data),
                "checksum": checksum,
                "success": True,
            },
            undo_closure=undo,
            description=f"Wrote {len(data)} bytes to {path_str}",
        )
