"""
Adapter for mcpstrike (mcpstrike).

Integrates with the MCP tool gateway (Ollama-driven) via FastAPI + MCP.
Preserves all original code; this file is a thin wrapper.
"""

import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from cyberai.orchestrator.adapters.base import (
    AdapterCapability,
    AdapterResult,
    SecurityToolAdapter,
)

logger = logging.getLogger(__name__)


# Original project metadata preserved
ORIGINAL_NAME = "mcpstrike"
ORIGINAL_REPOSITORY = "https://github.com/ente0/mcpstrike"
LICENSE = "MIT"

_ADAPTER_DIR = Path(__file__).resolve().parent
API_URL_ENV = "MCPSTRIKE_API_URL"
API_TOKEN_ENV = "MCPSTRIKE_API_TOKEN"
DOCKER_AVAILABLE = False
MCP_AVAILABLE = True
LOCAL_LLM = True


class Adapter(SecurityToolAdapter):
    """Thin adapter that wraps mcpstrike for the Cyber AI Orchestrator."""

    name = "mcpstrike"
    version = "0.1.0"
    description = "MCP tool gateway (Ollama-driven)"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._api_url = os.environ.get("MCPSTRIKE_API_URL", "http://localhost:8000")
        self._api_token = os.environ.get("MCPSTRIKE_API_TOKEN", "")

    async def health_check(self) -> Dict[str, Any]:
        """Check if the mcpstrike service or CLI is available."""
        # Check Docker availability if Docker is used
        if DOCKER_AVAILABLE:
            docker_ok = shutil.which("docker") is not None
            if not docker_ok:
                return {
                    "status": "WARN",
                    "message": "Docker not installed - mcpstrike requires Docker",
                    "details": {"docker_available": False},
                }

        # Check if API port is listening (for services with APIs)
        if self._api_url:
            try:
                port = 8000
                if port > 0:
                    import socket
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(2)
                    try:
                        s.connect(("127.0.0.1", port))
                        s.close()
                        return {
                            "status": "OK",
                            "message": "Service is running",
                            "details": {"url": self._api_url},
                            }
                    except (ConnectionRefusedError, socket.timeout):
                        return {
                            "status": "WARN",
                            "message": "Service not running (port not listening)",
                            "details": {"url": self._api_url, "docker_available": DOCKER_AVAILABLE},
                        }
            except Exception as e:
                return {"status": "WARN", "message": str(e), "details": {}}

        # Check if CLI tool is available
        cli_name = "mcpstrike"
        # Try common CLI entry points
        for candidate in ["mcpstrike", "mcpstrike", "python"]:
            path = shutil.which(candidate)
            if path:
                return {
                    "status": "OK",
                    "message": f"CLI tool available at {path}",
                    "details": {"cli": candidate, "path": path},
                }

        # Check if source code is present
        if _ADAPTER_DIR.exists():
            return {
                "status": "WARN",
                "message": "Source code present but service/CLI not started",
                "details": {"source_dir": str(_ADAPTER_DIR), "integration": "FastAPI + MCP"},
            }

        return {
            "status": "ERROR",
            "message": "mcpstrike not found",
            "details": {},
        }

    async def capabilities(self) -> List[AdapterCapability]:
        """Return the list of capabilities this adapter provides."""
        caps = []
        # Capabilities derived from the tool registry
        registry_caps = ['tool_execution', 'mcp_servers']
        for cap in registry_caps:
            caps.append(AdapterCapability(
                name=cap,
                description=f"Capability: {cap} via mcpstrike",
            ))
        return caps

    async def execute(self, task: Dict[str, Any]) -> AdapterResult:
        """
        Execute a task using mcpstrike.

        Args:
            task: Task spec with action, target, parameters

        Returns:
            AdapterResult with success/failure and output
        """
        action = task.get("action", "unknown")
        target = task.get("target", {})
        parameters = task.get("parameters", {})

        # Check if the tool is actually available
        health = await self.health_check()
        if health["status"] == "ERROR":
            return AdapterResult(
                success=False,
                error=f"Tool not available: {health['message']}",
            )

        # Delegate to the appropriate method based on integration type
        if DOCKER_AVAILABLE and shutil.which("docker"):
            # Could start Docker container and execute
            output = await self._execute_via_docker(action, target, parameters, health)
        elif self._api_url and health["status"] == "OK":
            output = await self._execute_via_api(action, target, parameters, health)
        else:
            # Source code present but service not running
            output = await self._execute_stub(action, target, parameters, health)

        return AdapterResult(
            success=bool(output.get("success", False)),
            output=output.get("output", ""),
            error=output.get("error"),
            evidence=output.get("evidence", []),
            metadata={
                "tool": self.name,
                "original": ORIGINAL_NAME,
                "action": action,
            },
        )

    async def _execute_via_docker(self, action, target, parameters, health):
        """Execute via Docker container."""
        return {
            "success": False,
            "output": "",
            "error": "mcpstrike Docker execution requires Docker daemon (not available)",
        }

    async def _execute_via_api(self, action, target, parameters, health):
        """Execute via HTTP API."""
        return {
            "success": False,
            "output": "",
            "error": f"API call to {self._api_url} for action '{action}' - not implemented",
        }

    async def _execute_stub(self, action, target, parameters, health):
        """Return a stub result when the tool is not executable."""
        return {
            "success": False,
            "output": "",
            "error": f"mcpstrike source present but service not started. "
                     f"Status: {health['status']}. "
                     f"Integration: FastAPI + MCP. "
                     f"See INTEGRATION.md for instructions.",
        }

    async def collect_results(self) -> AdapterResult:
        """Collect results from a previously executed task."""
        return AdapterResult(
            success=True,
            output="No async results to collect (stub implementation)",
        )

    async def shutdown(self) -> None:
        """Clean up any resources used by the adapter."""
        logger.info(f"Shutting down {self.name} adapter")
