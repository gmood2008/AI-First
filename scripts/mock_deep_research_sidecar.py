#!/usr/bin/env python3

import base64
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: str, content_type: str = "application/json"):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)

        if parsed.path == "/finance/yahoo":
            symbol = (qs.get("symbol") or [""])[0]
            payload = {
                "provider": "mock_yahoo",
                "symbol": symbol,
                "price": 123.45,
                "pe": 27.1,
                "currency": "USD",
                "retrieved_at": "mock",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False))
            return

        if parsed.path == "/search/google":
            q = (qs.get("q") or [""])[0]
            payload = {
                "engine": "mock_google",
                "query": q,
                "retrieved_at": "mock",
                "results": [
                    {
                        "title": "Mock headline",
                        "url": "https://example.com/mock",
                        "snippet": "Mock snippet for deep research.",
                    }
                ],
            }
            self._send(200, json.dumps(payload, ensure_ascii=False))
            return

        self._send(404, json.dumps({"error": "not_found"}))

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length > 0 else b""

        if parsed.path == "/io/pdf_export":
            markdown = body.decode("utf-8", errors="ignore")
            pdf_bytes = ("%PDF-1.4\n% Mock PDF\n" + markdown[:200] + "\n%%EOF\n").encode("utf-8")
            b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            self._send(200, b64, content_type="text/plain")
            return

        self._send(404, json.dumps({"error": "not_found"}))

    def log_message(self, format, *args):
        return


def main():
    server = HTTPServer(("127.0.0.1", 8787), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
