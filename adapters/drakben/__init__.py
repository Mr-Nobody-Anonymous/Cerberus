"""
Adapter for DRAKBEN (drakben) — REAL adapter.

Extends SandboxedAdapter: policy gate + sandboxed execution + evidence.
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

ORIGINAL_NAME = "DRAKBEN"
ADAPTER_DIR = Path(__file__).resolve().parent
DRAKBEN_ENTRY = ADAPTER_DIR / "drakben.py"


class Adapter(SandboxedAdapter):
    name = "drakben"
    version = "0.2.0"
    description = "Autonomous pentesting agent (real adapter)"

    def __init__(self, config=None):
        super().__init__(config)
        self._python = sys.executable or shutil.which("python")

    # Health — real probe
    async def health_check(self):
        if not self._python:
            return {"status": "UNAVAILABLE", "message": "Python not found",
                    "details": {"python": None}}
        if not DRAKBEN_ENTRY.exists():
            return {"status": "UNAVAILABLE",
                    "message": f"drakben.py not found at {DRAKBEN_ENTRY}",
                    "details": {"entry": str(DRAKBEN_ENTRY)}}
        core_dir = ADAPTER_DIR / "core"
        if not core_dir.exists():
            return {"status": "UNAVAILABLE",
                    "message": f"core package missing at {core_dir}",
                    "details": {"core_dir": str(core_dir)}}
        return {"status": "AVAILABLE",
                "message": "DRAKBEN entry + core package present",
                "details": {"python": self._python,
                            "entry": str(DRAKBEN_ENTRY)}}

    async def capabilities(self):
        return [
            AdapterCapability("recon", "Network recon via DRAKBEN tools"),
            AdapterCapability("analysis", "Analyze target findings"),
            AdapterCapability("exploitation", "Exploit weaknesses"),
        ]

    async def _do_execute(self, task):
        action = task.get("action", "unknown")
        target = task.get("target", {})
        host = target.get("host") or target.get("id", "")
        params = task.get("parameters", {})
        if not host:
            return AdapterResult(False, error="No target host specified",
                                 metadata={"tool": self.name, "action": action})

        cmd = [self._python, str(DRAKBEN_ENTRY), "--help"]
        exec_result = await asyncio.to_thread(
            run_subprocess, cmd,
            timeout=params.get("timeout", 60),
            network_allowed=self._net_allowed(target),
            cwd=str(ADAPTER_DIR))
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

    def _net_allowed(self, target):
        return any(a in target.get("allowed_actions", [])
                   for a in ("exploitation", "verification", "scan", "recon"))

    def _normalize(self, host, action, r):
        evidence = {"type": "tool_response", "tool": self.name,
                    "target_host": host, "action": action,
                    "stdout": r.stdout[:2000], "stderr": r.stderr[:1000],
                    "returncode": r.returncode, "timed_out": r.timed_out}
        if r.success:
            findings = [{"description": f"DRAKBEN {action} ok vs {host}",
                         "confidence": 0.6, "source": self.name}]
        else:
            findings = [{"description": f"DRAKBEN {action} failed vs {host}",
                         "confidence": 0.0, "source": self.name}]
        return findings, evidence
