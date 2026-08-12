"""
MCP Gateway for the Cyber AI Orchestrator.

Connects to MCP servers provided by integrated tools (HexStrike, MCPStrike,
Dark-Moon, etc.) and exposes them through a unified MCP interface.

Uses the FastMCP library when available, otherwise provides a stub
implementation that can be extended.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MCPGateway:
    """
    Manages MCP server connections and tool discovery.

    Discovers MCP servers from:
    - Configured MCP server definitions
    - Integrated adapters (hexstrike, mcpstrike, darkmoon)
    - Custom MCP configurations
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(__file__).parent / "mcp_config.json"
        self._servers: Dict[str, Dict[str, Any]] = {}
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load MCP server configuration."""
        if self.config_path.exists():
            import json
            try:
                with open(self.config_path) as f:
                    data = json.load(f)
                self._servers = data.get("mcp_servers", {})
                logger.info(f"Loaded {len(self._servers)} MCP server configurations")
            except Exception as e:
                logger.warning(f"Failed to load MCP config: {e}")
        else:
            logger.info("No MCP config file found - using defaults")

    def discover_mcp_servers(self) -> List[Dict[str, Any]]:
        """
        Discover available MCP servers from adapters.

        Checks each adapter directory for MCP server configurations
        and returns a list of discovered servers.
        """
        discovered = []

        adapter_dirs = {
            "hexstrike": {
                "name": "hexstrike-mcp",
                "type": "stdio",
                "command": "python",
                "args": ["hexstrike_mcp.py"],
                "cwd": str(Path(__file__).parent.parent.parent.parent / "adapters" / "hexstrike"),
                "capabilities": ["tool_execution", "mcp_servers"],
            },
            "mcpstrike": {
                "name": "mcpstrike-mcp",
                "type": "stdio",
                "command": "python",
                "args": ["-m", "mcpstrike.server"],
                "cwd": str(Path(__file__).parent.parent.parent.parent / "adapters" / "mcpstrike"),
                "capabilities": ["tool_execution", "mcp_servers"],
            },
            "darkmoon": {
                "name": "darkmoon-mcp",
                "type": "stdio",
                "command": "python",
                "args": ["mcp/src/server.py"],
                "cwd": str(Path(__file__).parent.parent.parent.parent / "adapters" / "darkmoon"),
                "capabilities": ["research", "analysis"],
            },
        }

        for name, config in adapter_dirs.items():
            adapter_path = Path(config["cwd"])
            if adapter_path.exists():
                # Check if the entry point exists
                entry = adapter_path / config["args"][-1]
                if entry.exists() or (len(config["args"]) > 1 and (adapter_path / config["args"][1]).exists()):
                    discovered.append(config)
                    self._servers[config["name"]] = config

        return discovered

    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all configured MCP servers."""
        results = {}
        for name, config in self._servers.items():
            results[name] = {"status": "NOT_TESTED", "message": "MCP server discovery mode"}
        # Also include discovered servers
        discovered = self.discover_mcp_servers()
        for server in discovered:
            if server["name"] not in results:
                results[server["name"]] = {"status": "DISCOVERED", "message": f"Found at {server['cwd']}"}
        return results

    def list_tools(self) -> List[str]:
        """List all tools available through MCP servers."""
        return sorted(self._tools.keys())

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Get tool info by name."""
        return self._tools.get(name)

    def to_dict(self) -> Dict[str, Any]:
        """Return the MCP gateway state as a dict."""
        return {
            "servers": self._servers,
            "tools": list(self._tools.keys()),
            "config_path": str(self.config_path),
        }
