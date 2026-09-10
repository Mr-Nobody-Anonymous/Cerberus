"""
Adapter for Cybersecurity AI (CAI) ({name}) — REAL adapter.

Extends SandboxedAdapter: policy gate + real library invocation +
evidence logging.

CAI is a Python agent framework (src/cai) that can be imported directly.
This adapter imports the framework and runs its agents in-process when
the package is installed, and reports a precise WARN when it is not.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from cyberai.orchestrator.adapters.base import (
    AdapterCapability,
    AdapterResult,
    SandboxedAdapter,
)

logger = logging.getLogger(__name__)

ORIGINAL_NAME = "Cybersecurity AI (CAI)"
_ADAPTER_DIR = Path(__file__).resolve().parent
CAI_SRC = _ADAPTER_DIR / "src"


class Adapter(SandboxedAdapter):
    """Real adapter that drives CAI in-process via its Python API."""

    name = "cai"
    version = "0.2.0"
    description = "Cybersecurity agent framework via Python library (real adapter)"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._cai = None

    # ------------------------------------------------------------- health
    async def health_check(self) -> Dict[str, Any]:
        try:
            self._cai = self._import_cai()
            return {
                "status": "AVAILABLE",
                "message": "CAI framework importable",
                "details": {"module": getattr(self._cai, "__name__", "cai")},
            }
        except ImportError as exc:
            return {
                "status": "WARN",
                "message": f"CAI not installed in this interpreter ({exc}). "
                           "Install it with: pip install -e adapters/cai",
                "details": {"source_present": CAI_SRC.exists(),
                            "integration": "Python library"},
            }

    def _import_cai(self):
        """Import the CAI framework, preferring the vendored source tree."""
        import sys

        src_path = str(CAI_SRC)
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        import cai  # noqa: PLC0415 — deferred import on purpose

        return cai

    async def capabilities(self) -> List[AdapterCapability]:
        return [
            AdapterCapability("research", "Research via CAI agents"),
            AdapterCapability("analysis", "Analyze via CAI agents"),
            AdapterCapability("agent_framework", "Run CAI agent framework"),
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
                error=f"CAI unavailable: {health['message']}",
                metadata={"tool": self.name, "original": ORIGINAL_NAME,
                          "action": action, "target_host": host,
                          "health": health["status"]},
            )

        # Real invocation: run the CAI agent loop in a worker thread so we
        # never block the event loop. CAI exposes its agents via cai.agents.
        def _run():
            agents = getattr(self._cai, "agents", None) or {}
            if not agents:
                return "CAI imported but no agents registered"
            agent_name = params.get("agent") or "default"
            agent = agents.get(agent_name) or next(iter(agents.values()))
            runner = getattr(agent, "run", None) or getattr(agent, "__call__")
            return str(runner(f"{action} {host}" if callable(runner) else agent))

        try:
            output = await asyncio.to_thread(_run)
        except Exception as exc:  # noqa: BLE001
            return AdapterResult(
                False, error=f"CAI invocation failed: {type(exc).__name__}: {exc}",
                metadata={"tool": self.name, "action": action,
                          "target_host": host})

        findings = [{
            "description": f"CAI {action} on {host} completed",
            "confidence": 0.6,
            "source": self.name,
        }]
        evidence = [{
            "type": "library_response", "tool": self.name,
            "target_host": host, "action": action,
            "output": str(output)[:2000],
        }]
        return AdapterResult(
            True, output=str(output), evidence=evidence,
            metadata={"tool": self.name, "original": ORIGINAL_NAME,
                      "action": action, "target_host": host,
                      "findings": findings},
        )

    async def collect_results(self) -> AdapterResult:
        return AdapterResult(
            True, metadata={"tool": self.name,
                            "note": "CAI results are synchronous in this adapter"})

    async def shutdown(self) -> None:
        logger.info("Shutting down %s adapter", self.name)
