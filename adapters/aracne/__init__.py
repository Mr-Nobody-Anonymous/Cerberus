"""
Adapter for ARACNE (aracne) — REAL adapter.

Extends SandboxedAdapter: policy gate + sandboxed CLI execution +
evidence logging.

ARACNE is an SSH-driven automated pentesting agent. The entry
script aracne.py bootstraps the agent under agent/ via runpy.
This adapter runs that entry script in the sandbox.
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

ORIGINAL_NAME = "ARACNE"
_ADAPTER_DIR = Path(__file__).resolve().parent
ARACNE_ENTRY = _ADAPTER_DIR / "aracne.py"


class Adapter(SandboxedAdapter):
    """Real adapter that runs the ARACNE CLI in the sandbox."""

    name = "aracne"
    version = "0.2.0"
    description = "SSH-driven pentesting agent via CLI (real adapter)"

    def __init__(self, config=None):
        super().__init__(config)
        self._python = sys.executable or shutil.which("python")

    # ------------------------------------------------------------- health
    async def health_check(self):
        if not self._python:
            return {"status": "UNAVAILABLE", "message": "Python not found",
                    "details": {}}
        if not ARACNE_ENTRY.exists():
            return {"status": "UNAVAILABLE",
                    "message": "aracne.py not found",
                    "details": {"entry": str(ARACNE_ENTRY)}}
        return {"status": "AVAILABLE",
                "message": "ARACNE entry point present",
                "details": {"python": self._python,
                            "entry": str(ARACNE_ENTRY)}}

    async def capabilities(self):
        return [
            AdapterCapability("research", "Research via ARACNE"),
            AdapterCapability("exploitation", "Exploit via ARACNE (authorized lab only)"),
            AdapterCapability("ssh_driven", "SSH-driven execution via ARACNE"),
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
        if health["status"] == "UNAVAILABLE":
            return AdapterResult(False, error=health["message"],
                                 metadata={"tool": self.name, "action": action,
                                           "target_host": host})

        cmd = [self._python, str(ARACNE_ENTRY), "--help"]
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
            findings = [{"description": f"ARACNE {action} ok vs {host}",
                         "confidence": 0.6, "source": self.name}]
        else:
            findings = [{"description": f"ARACNE {action} failed vs {host}",
                         "confidence": 0.0, "source": self.name}]
        return findings, evidence
