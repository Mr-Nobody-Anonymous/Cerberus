#!/usr/bin/env python3
"""
Mock lab target — a tiny HTTP service used when Docker is unavailable.

Serves a deliberately "vulnerable-looking" but harmless web app so the
CERBERUS platform (agents, tools, UI, demos, tests) has something real
to talk to in offline environments.

Usage:
    python mock_target.py --host 127.0.0.1 --port 8080 --name juice-shop
"""

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


PAGES = {
    "/": "<html><body><h1>Mock Lab Target</h1>"
          "<p>Intentionally vulnerable-looking mock app for offline labs.</p>"
          "<a href='/api/users'>users</a> <a href='/admin'>admin</a></body></html>",
    "/admin": "<html><body><h1>Admin Console</h1>"
              "<p>TODO: remove default credentials admin:admin</p></body></html>",
    "/login": "<html><body><h1>Login</h1><form>user:<input/>pass:<input type=password/></form></body></html>",
    "/api/users": json.dumps([
        {"id": 1, "user": "admin", "email": "admin@lab.local"},
        {"id": 2, "user": "dev", "email": "dev@lab.local"},
    ]),
    "/api/config": json.dumps({
        "debug": True,
        "version": "1.0-mock",
        "stack": ["mock", "python-http"],
    }),
    "/robots.txt": "User-agent: *\nDisallow: /admin\nDisallow: /api/config\n",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "MockLab/1.0"

    def _send(self, code: int, body: bytes, ctype: str = "text/html; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Powered-By", "MockLab")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in PAGES:
            val = PAGES[path]
            ctype = "application/json" if isinstance(val, str) and val.startswith(("[", "{")) else "text/html; charset=utf-8"
            self._send(200, val.encode(), ctype)
        elif path == "/health":
            self._send(200, json.dumps({"status": "UP", "name": self.server.lab_name}).encode(),
                       "application/json")
        else:
            self._send(404, b'{"error": "not found"}', "application/json")

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        _ = self.rfile.read(length) if length else b""
        self._send(200, b'{"ok": true, "note": "mock accepts everything"}',
                   "application/json")

    def log_message(self, fmt, *args):  # silence per-request logging
        pass


class MockServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, addr, name):
        super().__init__(addr, Handler)
        self.lab_name = name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--name", default="mock-target")
    args = ap.parse_args()

    srv = MockServer((args.host, args.port), args.name)
    print(f"[mock-target] '{args.name}' listening on http://{args.host}:{args.port}",
          flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    sys.exit(main())
