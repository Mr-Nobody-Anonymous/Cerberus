"""
Adapter Manager for the Cyber AI Orchestrator.

Dynamically loads and manages security tool adapters. Each adapter wraps
an external repository (PentAGI, Strix, HexStrike, etc.) and translates
standard orchestrator requests into whatever that project expects.

Adapters can be in one of these states:
    AVAILABLE   — service is running and healthy
    WARN        — source present but service not started (can still report health)
    ERROR       — source code not found
    NOT_IMPLEMENTED — adapter code not yet written
    STOPPED     — Docker available but container not running
"""

import importlib
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import AdapterCapability, AdapterResult, SecurityToolAdapter

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ADAPTERS_DIR = WORKSPACE_ROOT / "adapters"

# Known adapter directories and their integration methods
KNOWN_ADAPTERS = {
    "pentagi": {"integration": "rest_graphql", "docker": True, "port": 8443},
    "strix": {"integration": "server_api", "docker": True, "port": 8080},
    "darkmoon": {"integration": "mcp", "docker": True, "port": None},
    "hexstrike": {"integration": "flask_rest", "docker": False, "port": 8000},
    "mcpstrike": {"integration": "fastapi", "docker": False, "port": 8080},
    "cai": {"integration": "library", "docker": True, "port": None},
    "pentestgpt": {"integration": "cli", "docker": True, "port": None},
    "pentestagent": {"integration": "cli", "docker": True, "port": None},
    "cyberstrikeai": {"integration": "gin_rest", "docker": False, "port": 8080},
    "autopentest": {"integration": "cli", "docker": True, "port": None},
    "penclaw": {"integration": "cli", "docker": False, "port": None},
    "luan1aoagent": {"integration": "cli_web", "docker": True, "port": None},
    "aracne": {"integration": "cli", "docker": True, "port": None},
    "guardian_cli": {"integration": "cli", "docker": True, "port": None},
    "drakben": {"integration": "cli", "docker": True, "port": None},
    "kali_pentest": {"integration": "documentation", "docker": False, "port": None},
    "h4cker": {"integration": "documentation", "docker": False, "port": None},
}


class AdapterManager:
    """
    Discovers, loads, and manages security tool adapters dynamically.

    Usage:
        manager = AdapterManager()
        await manager.discover()
        health = await manager.health_check_all()
        result = await manager.execute("strix", task_dict)
    """

    def __init__(self):
        self._adapters: Dict[str, SecurityToolAdapter] = {}
        self._adapter_info: Dict[str, Dict[str, Any]] = {}
        self._load_known()

    def _load_known(self) -> None:
        """Load metadata for all known adapters."""
        for name, info in KNOWN_ADAPTERS.items():
            adapter_dir = ADAPTERS_DIR / name
            self._adapter_info[name] = {
                **info,
                "source_dir": adapter_dir,
                "source_present": adapter_dir.exists(),
            }

    def discover(self) -> List[str]:
        """
        Discover available adapter modules on disk.

        Returns:
            List of adapter names that have source code present.
        """
        available = []
        for name, info in self._adapter_info.items():
            adapter_dir = info["source_dir"]
            init_file = adapter_dir / "__init__.py"
            if init_file.exists():
                available.append(name)
            else:
                logger.debug(f"Adapter {name}: no __init__.py in {adapter_dir}")
        return sorted(available)

    def get_adapter(self, name: str) -> Optional[SecurityToolAdapter]:
        """
        Load and instantiate an adapter by name.

        Args:
            name: The adapter/tool name (e.g. "strix", "hexstrike")

        Returns:
            Adapter instance or None if not available
        """
        if name in self._adapters:
            return self._adapters[name]

        info = self._adapter_info.get(name)
        if not info or not info["source_present"]:
            return None

        # Try to import the adapter module
        # The import path may be "adapters.strix" or "adapters.guardian-cli"
        try:
            # Normalize hyphens in directory names to underscores for Python import
            import_name = name.replace("-", "_")
            module = importlib.import_module(f"adapters.{import_name}")
            adapter_cls = getattr(module, "Adapter", None)
            if adapter_cls:
                instance = adapter_cls()
                self._adapters[name] = instance
                return instance
        except ImportError as e:
            logger.debug(f"Adapter {name} import failed: {e}")
        except Exception as e:
            logger.warning(f"Adapter {name} instantiation failed: {e}")

        return None

    async def health_check(self, name: str) -> Dict[str, Any]:
        """
        Run a health check on a specific adapter.

        Returns:
            Dict with status (OK/WARN/ERROR/NOT_IMPLEMENTED), message, details
        """
        adapter = self.get_adapter(name)
        if adapter is None:
            return {
                "status": "NOT_IMPLEMENTED",
                "message": f"Adapter '{name}' not available (source not found or import failed)",
                "details": {},
            }
        return await adapter.health_check()

    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Run health checks on all known adapters.

        Returns:
            Dict mapping adapter name → health result dict
        """
        results = {}
        for name in self._adapter_info:
            results[name] = await self.health_check(name)
        return results

    async def execute(self, name: str, task: Dict[str, Any]) -> AdapterResult:
        """
        Execute a task via a specific adapter.

        Args:
            name: Adapter name
            task: Task spec dict

        Returns:
            AdapterResult from the adapter
        """
        adapter = self.get_adapter(name)
        if adapter is None:
            return AdapterResult(
                success=False,
                error=f"Adapter '{name}' not available",
            )
        return await adapter.execute(task)

    async def get_capable_adapters(self, capability: str) -> List[str]:
        """
        Find all adapters that advertise a given capability.

        Args:
            capability: The capability name (e.g. "research", "reconnaissance")

        Returns:
            List of adapter names that have this capability
        """
        capable = []
        for name in self._adapter_info:
            adapter = self.get_adapter(name)
            if adapter is None:
                continue
            try:
                caps = await adapter.capabilities()
                cap_names = [c.name for c in caps]
                if capability in cap_names:
                    capable.append(name)
            except Exception:
                continue
        return capable

    def list_adapters(self) -> List[Dict[str, Any]]:
        """List all known adapters with their status."""
        result = []
        for name, info in self._adapter_info.items():
            result.append({
                "name": name,
                "integration": info["integration"],
                "docker": info["docker"],
                "port": info.get("port"),
                "source_present": info["source_present"],
                "status": "AVAILABLE" if info["source_present"] else "NOT_IMPLEMENTED",
            })
        return sorted(result, key=lambda x: x["name"])

    async def shutdown_all(self) -> None:
        """Shut down all loaded adapters."""
        for name, adapter in self._adapters.items():
            try:
                await adapter.shutdown()
            except Exception as e:
                logger.warning(f"Adapter {name} shutdown error: {e}")

    async def describe(self, name: str) -> Dict[str, Any]:
        """
        Get detailed adapter description including health.

        Returns:
            Dict with adapter metadata, capabilities, and health
        """
        info = self._adapter_info.get(name, {})
        adapter = self.get_adapter(name)
        health = await self.health_check(name) if adapter else {
            "status": "NOT_IMPLEMENTED",
            "message": "Adapter not loadable",
        }

        caps = []
        if adapter:
            try:
                caps = [c.__dict__ for c in await adapter.capabilities()]
            except Exception:
                pass

        return {
            "name": name,
            "integration": info.get("integration", "unknown"),
            "docker": info.get("docker", False),
            "port": info.get("port"),
            "source_present": info.get("source_present", False),
            "health": health,
            "capabilities": caps,
        }
