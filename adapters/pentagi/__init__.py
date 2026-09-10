"""
Adapter for PentAGI (pentagi) — REAL adapter.

Extends SandboxedAdapter: policy gate + real REST/GraphQL invocation +
evidence logging.

PentAGI is a Docker-hosted autonomous pentesting agent exposing a
REST/GraphQL API on port 8443 (see INTEGRATION.md). This adapter talks
to that API over HTTP when the service is up, and reports a precise,
actionable WARN when it is not — never a fabricated result.
"""

import asyncio
import logging
import os
import socket
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import request as urlrequest
from urllib.error import URLError

from cyberai.orchestrator.adapters.base import (
    AdapterCapability,
    AdapterResult,
    SandboxedAdapter,
)

logger = logging.getLogger(__name__)

ORIGINAL_NAME = "PentAGI"
ORIGINAL_REPOSITORY = "https://github.com/vxcontrol/pentagi"

_ADAPTER_DIR = Path(__file__).resolve().parent
API_URL_ENV = "PENTAGI_API_URL"
API_TOKEN_ENV = "PENTAGI_API_TOKEN"
DEFAULT_API_URL = "http://localhost:8443"
DEFAULT_PORT = 8443
HTTP_TIMEOUT_SECONDS = 30


class Adapter(SandboxedAdapter):
    """Real adapter that drives PentAGI over its REST/GraphQL API."""

    name = "pentagi"
    version = "0.2.0"
    description = "Autonomous pentesting agent via REST/GraphQL API (real adapter)"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._api_url = os.environ.get(API_URL_ENV, DEFAULT_API_URL).rstrip("/")
        self._api_token = os.environ.get(API_TOKEN_ENV, "")

    # ------------------------------------------------------------- health
    async def health_check(self) -> Dict[str, Any]:
        """Probe the PentAGI API port and report precisely."""
        port = self._port_from_url()
        listening = await asyncio.to_thread(self._port_listening, port)
        if listening:
            return {
                "status": "AVAILABLE",
                "message": f"PentAGI API reachable at {self._api_url}",
                "details": {"url": self._api_url, "port": port},
            }
        return {
            "status": "WARN",
            "message": "PentAGI service not running (port not listening). "
                       "Start it with: cd adapters/pentagi && docker compose up -d",
            "details": {
                "url": self._api_url,
                "port": port,
                "source_present": _ADAPTER_DIR.exists(),
                "integration": "REST/GraphQL API (Docker)",
            },
        }

    async def capabilities(self) -> List[AdapterCapability]:
        return [
            AdapterCapability("research", "Research via PentAGI agent"),
            AdapterCapability("analysis", "Analyze target findings"),
            AdapterCapability("exploitation", "Exploit weaknesses (authorized lab only)"),
            AdapterCapability("reporting", "Generate assessment report"),
        ]

    # ----------------------------------------------------------- execution
    async def _do_execute(self, task: Dict[str, Any]) -> AdapterResult:
        action = task.get("action", "unknown")
        target = task.get("target", {})
        host = target.get("host") or target.get("id", "")
        params = task.get("parameters", {})
        if not host:
            return AdapterResult(
                False, error="No target host specified",
                metadata={"tool": self.name, "action": action})

        health = await self.health_check()
        if health["status"] != "AVAILABLE":
            return AdapterResult(
                False,
                error=f"PentAGI service unavailable: {health['message']}",
                metadata={"tool": self.name, "original": ORIGINAL_NAME,
                          "action": action, "target_host": host,
                          "health": health["status"]},
            )

        payload = {
            "action": action,
            "target": host,
            "parameters": params,
        }
        status, body = await asyncio.to_thread(
            self._http_post_json, f"{self._api_url}/api/v1/tasks", payload)

        findings = [{
            "description": f"PentAGI {action} on {host}: HTTP {status}",
            "confidence": 0.6 if status == 200 else 0.0,
            "source": self.name,
        }]
        evidence = [{
            "type": "api_response", "tool": self.name,
            "target_host": host, "action": action,
            "http_status": status, "body": str(body)[:2000],
        }]
        return AdapterResult(
            status == 200,
            output=body if isinstance(body, str) else str(body),
            error=None if status == 200 else f"HTTP {status}",
            evidence=evidence,
            metadata={"tool": self.name, "original": ORIGINAL_NAME,
                      "action": action, "target_host": host,
                      "http_status": status, "findings": findings},
        )

    async def collect_results(self) -> AdapterResult:
        return AdapterResult(
            True, metadata={"tool": self.name,
                            "note": "PentAGI results are synchronous in this adapter"})

    async def shutdown(self) -> None:
        logger.info("Shutting down %s adapter", self.name)

    # ------------------------------------------------------------- helpers
    def _port_from_url(self) -> int:
        try:
            from urllib.parse import urlparse
            return urlparse(self._api_url).port or DEFAULT_PORT
        except ValueError:
            return DEFAULT_PORT

    @staticmethod
    def _port_listening(port: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                return s.connect_ex(("127.0.0.1", port)) == 0
        except OSError:
            return False

    def _http_post_json(self, url: str, payload: Dict[str, Any]):
        """POST JSON via urllib (no external deps). Returns (status, body)."""
        import json

        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"
        req = urlrequest.Request(url, data=data, headers=headers, method="POST")
        try:
            with urlrequest.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace")
        except URLError as exc:
            return 0, f"connection failed: {exc}"
        except OSError as exc:
            return 0, f"request failed: {exc}"
