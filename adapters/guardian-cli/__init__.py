import asyncio
import logging
import os
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

ORIGINAL_NAME = "Guardian"
_ADAPTER_DIR = Path(__file__).resolve().parent
# We'll use the local python interpreter and the cli/main.py entry point
GUARDIAN_CLI_CMD = ["python", "-m", "cli.main"]

class Adapter(SandboxedAdapter):
    name = "guardian-cli"
    version = "0.1.0"
    description = "CLI-based pentesting agent"

    def __init__(self, config=None):
        super().__init__(config)
        self._api_url = "http://localhost:0"
        self._api_token = None

    async def health_check(self) -> Dict[str, Any]:
        # Check if cli/main.py exists
        if not (_ADAPTER_DIR / "cli" / "main.py").exists():
            return {"status": "ERROR", "message": "cli/main.py not found", "details": {}}
        return {"status": "AVAILABLE", "message": "CLI module present", "details": {}}

    async def capabilities(self) -> List[AdapterCapability]:
        return [
            AdapterCapability("recon", "Network recon via Guardian scan"),
            AdapterCapability("scan", "Port scan via Guardian scan"),
            AdapterCapability("analysis", "Analyze via Guardian analyze"),
            AdapterCapability("report", "Report via Guardian report"),
        ]

    async def _do_execute(self, task: Dict[str, Any]) -> AdapterResult:
        action = task.get("action", "scan")
        target = task.get("target", {})
        target_host = target.get("host") or target.get("id", "")
        params = task.get("parameters", {})

        if not target_host:
            return AdapterResult(False, error="No target host specified")

        # Construct command: guardian <action> --target <host> [extra params]
        # Based on scan.py: target is a mandatory option --target or -t
        cmd = [sys.executable, "-m", "cli.main", action, "--target", target_host]
        
        # Add ports if provided in parameters
        if "ports" in params:
            cmd.extend(["--ports", str(params["ports"])])
        
        # Add model override if provided
        if "model" in params:
            cmd.extend(["--model", str(params["model"])])

        logger.info(f"Executing Guardian {action} on {target_host}: {' '.join(cmd)}")

        # Note: We run from the ADAPTER_DIR so that the 'cli' module is importable
        exec_result = await asyncio.to_thread(
            run_subprocess, cmd,
            timeout=params.get("timeout", 300),
            network_allowed=self._net_allowed(target),
            cwd=str(_ADAPTER_DIR)
        )

        # In a real implementation, we would parse the output.
        # For now, we'll return the stdout/stderr as findings/evidence.
        findings = []
        if exec_result.success:
            findings.append({
                "description": f"Guardian {action} completed on {target_host}",
                "confidence": 0.7,
                "source": self.name
            })

        return AdapterResult(
            success=exec_result.success,
            output=exec_result.stdout,
            error=exec_result.error,
            evidence=[{"type": "cli_output", "output": exec_result.stdout, "stderr": exec_result.stderr}],
            metadata={
                "tool": self.name,
                "action": action,
                "target_host": target_host,
                "command": cmd,
                "returncode": exec_result.returncode
            }
        )

    async def collect_results(self) -> AdapterResult:
        return AdapterResult(True, output="No async results to collect")

    async def shutdown(self) -> None:
        logger.info(f"Shutting down {self.name} adapter")

    def _net_allowed(self, target) -> bool:
        # Allow networking if exploitation or recon is intended
        allowed_actions = target.get("allowed_actions", [])
        return any(a in allowed_actions for a in ["recon", "scan", "exploitation"])

