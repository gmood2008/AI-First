from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from specs.v3.workflow_schema import WorkflowSpec


class WorkflowSpecNotFoundError(Exception):
    pass


def _convert_pack_workflow_yaml_to_workflow_spec_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    workflow_id = data.get("workflow_id")
    metadata = data.get("metadata") or {}
    if workflow_id and "workflow_id" not in metadata:
        metadata = {**metadata, "workflow_id": workflow_id}

    return {
        "name": data.get("name") or workflow_id,
        "version": data.get("version", "1.0.0"),
        "description": data.get("description", ""),
        "steps": data.get("steps", []),
        "initial_state": data.get("initial_state", {}),
        "metadata": metadata,
        "policy": data.get("policy", []),
        "global_compensation_steps": data.get("global_compensation_steps", []),
        "max_execution_time_seconds": data.get("max_execution_time_seconds", 3600),
        "enable_auto_rollback": data.get("enable_auto_rollback", True),
    }


def load_workflow_spec_by_id(
    workflow_id: str,
    packs_root: Optional[Path] = None,
) -> WorkflowSpec:
    if not workflow_id or not isinstance(workflow_id, str):
        raise WorkflowSpecNotFoundError("workflow_id is required")

    if packs_root is None:
        packs_root = Path(__file__).resolve().parents[3] / "packs"

    packs_root = Path(packs_root)
    if not packs_root.exists():
        raise WorkflowSpecNotFoundError(f"packs root not found: {packs_root}")

    candidates = list(packs_root.glob(f"**/{workflow_id}.yaml"))
    if not candidates:
        raise WorkflowSpecNotFoundError(f"workflow spec not found for id: {workflow_id}")

    path = candidates[0]
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise WorkflowSpecNotFoundError(f"invalid workflow spec yaml: {path}")

    spec_dict = _convert_pack_workflow_yaml_to_workflow_spec_dict(raw)
    return WorkflowSpec.model_validate(spec_dict)
