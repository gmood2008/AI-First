import json
import socket
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


@dataclass(frozen=True)
class GovernanceHttpConfig:
    hook_url: str
    timeout_ms: int = 2000
    fail_mode: str = "DENY"  # ALLOW | DENY | PAUSE


def _normalize_decision(value: Any) -> str:
    if value is None:
        return "ALLOW"
    text = str(value).upper().strip()
    if text in {"ALLOW", "DENY", "PAUSE", "PAUSED"}:
        return "PAUSE" if text in {"PAUSE", "PAUSED"} else text
    return "ALLOW"


def _request_json(url: str, payload: Dict[str, Any], timeout_seconds: float) -> Dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        body = resp.read().decode("utf-8")
        if not body.strip():
            return {}
        return json.loads(body)


def build_http_governance_hooks(config: GovernanceHttpConfig) -> Dict[str, Callable[..., Any]]:
    timeout_seconds = max(0.001, float(config.timeout_ms) / 1000.0)
    fail_decision = _normalize_decision(config.fail_mode)

    def _call_hook(event: str, **kwargs: Any) -> str:
        payload: Dict[str, Any] = {
            "event": event,
            "traceId": kwargs.get("trace_id"),
            "workflowId": kwargs.get("workflow_id"),
        }

        step = kwargs.get("step")
        if step is not None:
            payload["step"] = {
                "name": getattr(step, "name", None),
                "stepType": getattr(getattr(step, "step_type", None), "value", None),
                "capabilityId": getattr(step, "capability_name", None),
                "agentName": getattr(step, "agent_name", None),
                "riskLevel": getattr(getattr(step, "risk_level", None), "value", None),
            }

        resolved_inputs = kwargs.get("resolved_inputs")
        if resolved_inputs is not None:
            payload["inputs"] = resolved_inputs

        summary = kwargs.get("summary")
        if summary is not None:
            payload["summary"] = summary

        try:
            resp = _request_json(config.hook_url, payload, timeout_seconds)
            decision = _normalize_decision((resp or {}).get("decision"))
            return decision
        except (socket.timeout, TimeoutError):
            return fail_decision
        except Exception:
            return fail_decision

    def _pre_execution_hook(**kwargs: Any) -> str:
        return _call_hook("pre_execution", **kwargs)

    def _pre_step_hook(**kwargs: Any) -> str:
        return _call_hook("pre_step", **kwargs)

    def _post_step_hook(**kwargs: Any) -> None:
        _call_hook("post_step", **kwargs)
        return None

    def _post_execution_hook(**kwargs: Any) -> None:
        _call_hook("post_execution", **kwargs)
        return None

    return {
        "pre_execution": _pre_execution_hook,
        "pre_step": _pre_step_hook,
        "post_step": _post_step_hook,
        "post_execution": _post_execution_hook,
    }
