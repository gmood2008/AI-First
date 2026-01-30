from __future__ import annotations

from typing import Any, Dict, List

from ..adapters import AdapterRuntimeConfig, AdapterRuntimeWrapper
from ..handler import ActionHandler


def _get_allowed_domains(contracts: Dict[str, Any]) -> List[str]:
    raw = contracts.get("allowed_domains")
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if str(x).strip()]
    if isinstance(raw, str):
        return [p.strip() for p in raw.split(",") if p.strip()]
    return []


def _get_sidecar_base_url(contracts: Dict[str, Any]) -> str:
    v = contracts.get("sidecar_base_url")
    if not v or not isinstance(v, str):
        raise ValueError("sidecar_base_url is required in contracts")
    return v


class WebBrowserNavigateHandler(ActionHandler):
    def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        url = params["url"]
        wait_until = params.get("wait_until")

        contracts = self.contracts
        base_url = _get_sidecar_base_url(contracts)
        allowed_domains = _get_allowed_domains(contracts)
        timeout = float(contracts.get("timeout_seconds", 20))
        if not allowed_domains:
            raise ValueError("allowed_domains must be configured")

        wrapper = AdapterRuntimeWrapper(
            AdapterRuntimeConfig(
                base_url=base_url,
                timeout_seconds=timeout,
                allowed_domains=allowed_domains,
            )
        )

        result = wrapper.navigate(url=str(url), wait_until=str(wait_until) if wait_until else None)
        return {"success": True, **result}


class WebBrowserSnapshotHandler(ActionHandler):
    def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        url = params["url"]

        contracts = self.contracts
        base_url = _get_sidecar_base_url(contracts)
        allowed_domains = _get_allowed_domains(contracts)
        timeout = float(contracts.get("timeout_seconds", 20))
        if not allowed_domains:
            raise ValueError("allowed_domains must be configured")

        wrapper = AdapterRuntimeWrapper(
            AdapterRuntimeConfig(
                base_url=base_url,
                timeout_seconds=timeout,
                allowed_domains=allowed_domains,
            )
        )

        result = wrapper.snapshot(url=str(url))
        return {"success": True, **result}
