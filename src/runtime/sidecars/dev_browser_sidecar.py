from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx


def _env_float(name: str, default: float) -> float:
    import os

    v = os.getenv(name)
    if v is None or v.strip() == "":
        return default
    return float(v)


def _env_list(name: str, default: Optional[List[str]] = None) -> List[str]:
    import os

    v = os.getenv(name)
    if v is None or v.strip() == "":
        return list(default or [])
    parts = [p.strip() for p in v.split(",")]
    return [p for p in parts if p]


def _is_allowed_domain(host: str, allowlist: List[str]) -> bool:
    host = (host or "").lower().strip(".")
    if not host:
        return False

    for rule in allowlist:
        r = (rule or "").lower().strip().strip(".")
        if not r:
            continue
        if r == host:
            return True
        if r.startswith("*."):
            suffix = r[2:]
            if suffix and (host == suffix or host.endswith("." + suffix)):
                return True
    return False


def _validate_url(url: str, allowlist: List[str]) -> str:
    if not url or not isinstance(url, str):
        raise ValueError("url is required")

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("only http/https URLs are allowed")
    if not parsed.netloc:
        raise ValueError("url must include host")

    host = parsed.hostname or ""
    if not _is_allowed_domain(host, allowlist):
        raise ValueError("host is not in allowlist")

    return url


def _read_json_body(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    raw = handler.rfile.read(length) if length > 0 else b"{}"
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise ValueError("invalid json") from e
    if not isinstance(data, dict):
        raise ValueError("json body must be an object")
    return data


def _write_json(handler: BaseHTTPRequestHandler, status: int, payload: Dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class DevBrowserHandler(BaseHTTPRequestHandler):
    server_version = "DevBrowserSidecar/0.1"

    def do_POST(self) -> None:
        allowlist = getattr(self.server, "allowed_domains", [])
        timeout_seconds = getattr(self.server, "timeout_seconds", 20.0)

        try:
            if self.path not in {"/navigate", "/snapshot"}:
                _write_json(self, 404, {"error": "not_found"})
                return

            body = _read_json_body(self)
            url = _validate_url(str(body.get("url") or ""), allowlist)

            with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
                resp = client.get(url, headers={"User-Agent": "ai-first-dev-browser/0.1"})

            if self.path == "/navigate":
                _write_json(
                    self,
                    200,
                    {
                        "ok": True,
                        "url": url,
                        "final_url": str(resp.url),
                        "status_code": resp.status_code,
                    },
                )
                return

            text = resp.text
            snippet = text[:5000]
            _write_json(
                self,
                200,
                {
                    "ok": True,
                    "url": url,
                    "final_url": str(resp.url),
                    "status_code": resp.status_code,
                    "content_type": resp.headers.get("Content-Type"),
                    "html": snippet,
                },
            )

        except Exception as e:
            _write_json(
                self,
                400,
                {
                    "ok": False,
                    "error": type(e).__name__,
                    "message": str(e),
                },
            )

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    allowed_domains = _env_list("DEV_BROWSER_ALLOWED_DOMAINS", default=[])
    timeout_seconds = _env_float("DEV_BROWSER_TIMEOUT_SECONDS", 20.0)

    httpd = ThreadingHTTPServer((args.host, args.port), DevBrowserHandler)
    httpd.allowed_domains = allowed_domains
    httpd.timeout_seconds = timeout_seconds
    httpd.serve_forever()


if __name__ == "__main__":
    main()
