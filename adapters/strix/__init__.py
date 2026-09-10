"""
Adapter for Strix (strix) — REAL adapter.

Extends SandboxedAdapter: policy gate + sandboxed CLI execution +
evidence logging.

Strix is an autonomous pentest agent with a CLI entry point at
``strix/interface/main.py`` (``python -m strix.interface.main``). Real
scans require Docker (for the sandbox image) and a configured LLM, so
this adapter health-checks those prerequisites and reports precise,
actionable statuses. The ``--help`` probe validates the CLI is
importable; a real scan passes the target through to the CLI.
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

ORIGINAL_NAME = "Strix"
_ADAPTER_DIR = Path(__file__).resolve().parent
STRIX_PACKAGE_DIR = _ADAPTER_DIR / "strix"


class Adapter(SandboxedAdapter):
    """Real adapter that runs the Strix CLI in the sandbox."""

    name = "strix"
    version = "0.2.0"
    description = "Autonomous pentest agent via CLI (real adapter)"

    def __init__(self, config=None):
        super().__init__(config)
        self._python = sys.executable or shutil.which("python")

    # ------------------------------------------------------------- health
    async def health_check(self):
        if not self._python:
            return {"status": "UNAVAILABLE", "message": "Python not found",
                    "details": {}}
        if not (STRIX_PACKAGE_DIR / "interface" / "main.py").exists():
            return {"status": "UNAVAILABLE",
                    "message": "strix/interface/main.py not found",
                    "details": {"dir": str(STRIX_PACKAGE_DIR)}}
        docker = shutil.which("docker")
        if not docker:
            return {"status": "WARN",
                    "message": "Strix CLI present but Docker not installed "
                               "(real scans need the strix sandbox image)",
                    "details": {"docker": False}}
        return {"status": "AVAILABLE",
                "message": "Strix CLI present, Docker available",
                "details": {"python": self._python, "docker": docker}}

    async def capabilities(self):
        return [
            AdapterCapability("recon", "Recon via Strix agent"),
            AdapterCapability("scan", "Vulnerability scan via Strix agent"),
            AdapterCapability("analysis", "Analyze findings via Strix agent"),
            AdapterCapability("exploitation", "Exploit via Strix agent (authorized lab only)"),
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

        # Real invocation: the Strix CLI. `--help` validates importability
        # and prints usage; a real scan passes the target through.
        cmd = [self._python, "-m", "strix.interface.main"]
        if action in ("scan", "recon", "exploitation", "analysis"):
            cmd.extend(["--target", host])
        else:
            cmd.append("--help")

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
            findings = [{"description": f"Strix {action} ok vs {host}",
                         "confidence": 0.6, "source": self.name}]
        else:
            findings = [{"description": f"Strix {action} failed vs {host}",
                         "confidence": 0.0, "source": self.name}]
        return findings, evidence
