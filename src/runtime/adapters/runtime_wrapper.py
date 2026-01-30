from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx


class AdapterRuntimeError(RuntimeError):
    pass


@dataclass(frozen=True)
class AdapterRuntimeConfig:
    base_url: str
    timeout_seconds: float
    allowed_domains: List[str]


class AdapterRuntimeWrapper:
    def __init__(self, config: AdapterRuntimeConfig):
        self._config = config
        parsed = urlparse(config.base_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("base_url must be http or https")
        if not parsed.netloc:
            raise ValueError("base_url must include host")
        if config.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")

    def navigate(self, url: str, wait_until: Optional[str] = None) -> Dict[str, Any]:
        safe_url = self._validate_target_url(url)
        payload: Dict[str, Any] = {"url": safe_url}
        if wait_until is not None:
            payload["wait_until"] = wait_until
        return self._post_json("/navigate", payload)

    def snapshot(self, url: str) -> Dict[str, Any]:
        safe_url = self._validate_target_url(url)
        return self._post_json("/snapshot", {"url": safe_url})

    def _post_json(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        base = self._config.base_url.rstrip("/")
        endpoint = f"{base}{path}"
        try:
            with httpx.Client(timeout=self._config.timeout_seconds) as client:
                resp = client.post(endpoint, json=payload)
                resp.raise_for_status()
                data = resp.json()
                if not isinstance(data, dict):
                    raise AdapterRuntimeError("sidecar response must be a json object")
                return data
        except httpx.TimeoutException as e:
            raise AdapterRuntimeError("sidecar call timed out") from e
        except httpx.HTTPError as e:
            raise AdapterRuntimeError(f"sidecar http error: {e}") from e
        except ValueError as e:
            raise AdapterRuntimeError("sidecar returned invalid json") from e

    def _validate_target_url(self, url: str) -> str:
        if not url or not isinstance(url, str):
            raise ValueError("url is required")

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("only http/https URLs are allowed")
        if not parsed.netloc:
            raise ValueError("url must include host")

        host = parsed.hostname or ""
        if not self._is_allowed_domain(host):
            raise ValueError("host is not in allowlist")

        return url

    def _is_allowed_domain(self, host: str) -> bool:
        host = host.lower().strip(".")
        if not host:
            return False

        for rule in self._config.allowed_domains:
            r = (rule or "").lower().strip()
            if not r:
                continue
            r = r.strip(".")
            if r == host:
                return True
            if r.startswith("*."):
                suffix = r[2:]
                if suffix and (host == suffix or host.endswith("." + suffix)):
                    return True

        return False
