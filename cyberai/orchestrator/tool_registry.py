"""
Tool Registry for the Cyber AI Orchestrator.

Maintains a machine-readable registry of all available security tools
and their adapters. The orchestrator uses this registry to route
tasks to the appropriate tool.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default registry data based on actual repository capabilities
DEFAULT_TOOLS = {
    "pentagi": {
        "type": "security_agent",
        "adapter": "adapters.pentagi",
        "capabilities": ["research", "analysis", "exploitation", "reporting"],
        "api": "rest_graphql",
        "mcp": True,
        "docker": True,
        "local_llm": True,
        "status": "NOT_TESTED",
    },
    "strix": {
        "type": "security_agent",
        "adapter": "adapters.strix",
        "capabilities": ["assessment", "vulnerability_scanning"],
        "api": "server",
        "mcp": False,
        "docker": True,
        "local_llm": True,
        "status": "NOT_TESTED",
    },
    "hexstrike": {
        "type": "tool_gateway",
        "adapter": "adapters.hexstrike",
        "capabilities": ["tool_execution", "mcp_servers", "web_scraping"],
        "api": "flask_rest",
        "mcp": True,
        "docker": False,
        "local_llm": True,
        "status": "NOT_TESTED",
    },
    "mcpstrike": {
        "type": "tool_gateway",
        "adapter": "adapters.mcpstrike",
        "capabilities": ["tool_execution", "mcp_servers"],
        "api": "fastapi",
        "mcp": True,
        "docker": False,
        "local_llm": True,
        "status": "NOT_TESTED",
    },
    "darkmoon": {
        "type": "security_agent",
        "adapter": "adapters.darkmoon",
        "capabilities": ["research", "analysis", "exploitation"],
        "api": "mcp",
        "mcp": True,
        "docker": True,
        "local_llm": True,
        "status": "NOT_TESTED",
    },
    "cai": {
        "type": "security_agent",
        "adapter": "adapters.cai",
        "capabilities": ["research", "analysis", "agent_framework"],
        "api": "library",
        "mcp": True,
        "docker": True,
        "local_llm": False,
        "status": "NOT_TESTED",
    },
    "pentestgpt": {
        "type": "security_agent",
        "adapter": "adapters.pentestgpt",
        "capabilities": ["research", "planning"],
        "api": "cli",
        "mcp": False,
        "docker": True,
        "local_llm": False,
        "status": "NOT_TESTED",
    },
    "pentestagent": {
        "type": "security_agent",
        "adapter": "adapters.pentestagent",
        "capabilities": ["research", "analysis", "exploitation"],
        "api": "cli",
        "mcp": True,
        "docker": True,
        "local_llm": True,
        "status": "NOT_TESTED",
    },
    "cyberstrikeai": {
        "type": "security_agent",
        "adapter": "adapters.cyberstrikeai",
        "capabilities": ["tool_execution", "mcp_servers", "analysis"],
        "api": "gin_rest",
        "mcp": True,
        "docker": False,
        "local_llm": True,
        "status": "NOT_TESTED",
    },
    "autopentest": {
        "type": "security_agent",
        "adapter": "adapters.autopentest",
        "capabilities": ["research", "planning"],
        "api": "cli",
        "mcp": False,
        "docker": True,
        "local_llm": False,
        "status": "NOT_TESTED",
    },
    "penclaw": {
        "type": "analysis_tool",
        "adapter": "adapters.penclaw",
        "capabilities": ["static_analysis", "dynamic_scanning", "secret_detection"],
        "api": "cli",
        "mcp": False,
        "docker": False,
        "local_llm": True,
        "status": "NOT_TESTED",
    },
    "luan1aoagent": {
        "type": "security_agent",
        "adapter": "adapters.luan1aoagent",
        "capabilities": ["research", "analysis", "planning"],
        "api": "cli_web",
        "mcp": False,
        "docker": True,
        "local_llm": True,
        "status": "NOT_TESTED",
    },
    "aracne": {
        "type": "security_agent",
        "adapter": "adapters.aracne",
        "capabilities": ["research", "exploitation", "ssh_driven"],
        "api": "cli",
        "mcp": False,
        "docker": True,
        "local_llm": True,
        "status": "NOT_TESTED",
    },
    "guardian_cli": {
        "type": "security_agent",
        "adapter": "adapters.guardian-cli",
        "capabilities": ["research", "analysis", "reporting"],
        "api": "cli",
        "mcp": False,
        "docker": True,
        "local_llm": False,
        "status": "NOT_TESTED",
    },
    "drakben": {
        "type": "security_agent",
        "adapter": "adapters.drakben",
        "capabilities": ["research", "analysis", "exploitation"],
        "api": "cli",
        "mcp": False,
        "docker": True,
        "local_llm": True,
        "status": "NOT_TESTED",
    },
    "kali_pentest": {
        "type": "skill_definitions",
        "adapter": "adapters.kali-pentest",
        "capabilities": ["tool_guidance", "methodology"],
        "api": "documentation",
        "mcp": False,
        "docker": False,
        "local_llm": False,
        "status": "NOT_TESTED",
    },
    "h4cker": {
        "type": "knowledge_base",
        "adapter": "adapters.h4cker",
        "capabilities": ["reference", "training", "labs"],
        "api": "documentation",
        "mcp": False,
        "docker": False,
        "local_llm": False,
        "status": "NOT_TESTED",
    },
}


class ToolRegistry:
    """Registry of all available security tools and their adapters."""

    def __init__(self, registry_path: Optional[Path] = None):
        # Intentionally package-relative: tools.yaml is registry data that
        # ships next to this module — NOT a workspace resource (do not route
        # through cyberai.config.resolve_path).
        self.registry_path = registry_path or Path(__file__).parent / "tools.yaml"
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load tools from the registry file or use defaults."""
        if self.registry_path.exists():
            try:
                import yaml

                with open(self.registry_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                self._tools = data.get("tools", {})
                logger.info(f"Loaded {len(self._tools)} tools from {self.registry_path}")
            except Exception as e:
                logger.warning(f"Failed to load registry from {self.registry_path}: {e}")
                self._tools = DEFAULT_TOOLS
        else:
            self._tools = DEFAULT_TOOLS

    def list_tools(self) -> List[str]:
        """Return list of all registered tool names."""
        return sorted(self._tools.keys())

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Get tool info by name."""
        return self._tools.get(name)

    def get_tools_by_type(self, tool_type: str) -> List[Dict[str, Any]]:
        """Get all tools of a given type."""
        return [
            {"name": name, **info}
            for name, info in self._tools.items()
            if info.get("type") == tool_type
        ]

    def get_tools_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """Get all tools that have a given capability."""
        return [
            {"name": name, **info}
            for name, info in self._tools.items()
            if capability in info.get("capabilities", [])
        ]

    def get_adapter_path(self, tool_name: str) -> Optional[str]:
        """Get the adapter module path for a tool."""
        tool = self._tools.get(tool_name)
        if tool:
            return tool.get("adapter")
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Return the full registry as a dict."""
        return {"tools": self._tools}

    def to_yaml(self) -> str:
        """Return the registry as YAML."""
        import yaml

        return yaml.dump(self.to_dict(), default_flow_style=False)