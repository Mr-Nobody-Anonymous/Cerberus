"""
Adapter for PenClaw (penclaw) — REAL adapter.

Extends SandboxedAdapter: policy gate + sandboxed CLI execution +
evidence logging.

PenClaw is an AI-powered penetration testing CLI (Node.js,
bin: ./dist/cli/index.js per package.json) for static analysis,
dynamic scanning, and secret detection. This adapter runs the
built CLI in the sandbox; if the dist bundle is not built it
reports exactly that.
"""

import asyncio
import logging
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from cyberai.orchestrator.adapters.base import (
    AdapterCapability,
    AdapterResult,
    SandboxedAdapter,
)
from cyberai.security.sandbox import run_subprocess

logger = logging.getLogger(__name__)

ORIGINAL_NAME = "PenClaw"
_ADAPTER_DIR = Path(__file__).resolve().parent
PENCLAW_ENTRY = _ADAPTER_DIR / "dist" / "cli" / "index.js"


class Adapter(SandboxedAdapter):
    """Real adapter that runs the PenClaw CLI in the sandbox."""

    name = "penclaw"
    version = "0.2.0"
    description = "Static/dynamic analysis via Node CLI (real adapter)"

    def __init__(self, config=None):
        super().__init__(config)
        self._python = sys.executable or shutil.which("python")

    # ------------------------------------------------------------- health
    async def health_check(self):
        node = shutil.which("node")
        if not node:
            return {"status": "UNAVAILABLE", "message": "Node.js not found",
                    "details": {}}
        if not PENCLAW_ENTRY.exists():
            return {"status": "WARN",
                    "message": "dist/cli/index.js not built. "
                               "Run: cd adapters/penclaw && npm install && npm run build",
                    "details": {"entry": str(PENCLAW_ENTRY), "node": node}}
        return {"status": "AVAILABLE",
                "message": "PenClaw entry point present",
                "details": {"python": self._python,
                            "entry": str(PENCLAW_ENTRY)}}

    async def capabilities(self):
        return [
            AdapterCapability("static_analysis", "Static analysis via PenClaw"),
            AdapterCapability("dynamic_scanning", "Dynamic scanning via PenClaw"),
            AdapterCapability("secret_detection", "Secret detection via PenClaw"),
        ]

    # ----------------------------------------------------------- execution
    async def _do_execute(self, task):
        action = task.get("action", "unknown")
        target = task.get("target", {})
        host = target.get("host") or target.get("id", "")
        params = task.get("parameters", {})
        if not host:
            return AdapterResult(False, error="No target host specified",
                                 metadata={"tool": self.name, "action": action})

        health = await self.health_check()
        if health["status"] != "AVAILABLE":
            return AdapterResult(False, error=health["message"],
                                 metadata={"tool": self.name, "action": action,
                                           "target_host": host,
                                           "health": health["status"]})

        node = shutil.which("node")
        cmd = [node, str(PENCLAW_ENTRY), "scan", "--target", host]
        exec_result = await asyncio.to_thread(
            run_subprocess, cmd,
            timeout=params.get("timeout", 120),
            network_allowed=self._net_allowed(target),
            cwd=str(_ADAPTER_DIR))
        findings, evidence = self._normalize(host, action, exec_result)
        return AdapterResult(
            exec_result.success, output=exec_result.stdout,
            error=exec_result.error, evidence=evidence,
            metadata={"tool": self.name, "original": ORIGINAL_NAME,
                      "action": action, "target_host": host,
                      "command": cmd, "returncode": exec_result.returncode,
                      "timed_out": exec_result.timed_out, "findings": findings})

    async def collect_results(self):
        return AdapterResult(True, metadata={"tool": self.name})

    async def shutdown(self):
        logger.info("Shutting down %s adapter", self.name)

    # ------------------------------------------------------------- helpers
    def _net_allowed(self, target):
        return any(a in target.get("allowed_actions", [])
                   for a in ("exploitation", "verification", "scan", "recon"))

    def _normalize(self, host, action, r):
        evidence = {"type": "tool_response", "tool": self.name,
                    "target_host": host, "action": action,
                    "stdout": r.stdout[:2000], "stderr": r.stderr[:1000],
                    "returncode": r.returncode, "timed_out": r.timed_out}
        if r.success:
            findings = [{"description": f"PenClaw {action} ok vs {host}",
                         "confidence": 0.6, "source": self.name}]
        else:
            findings = [{"description": f"PenClaw {action} failed vs {host}",
                         "confidence": 0.0, "source": self.name}]
        return findings, evidence
