"""MCP gateway accessor for the CLI.

The MCP gateway lives in the kebab-case package
``cyberai/tool-gateway/mcp`` (a legacy directory name that cannot be
renamed without breaking the documented layout). Standard ``import``
statements cannot reference kebab-case module names, so this helper
loads it via :func:`importlib.import_module` and re-exports the
:class:`~cyberai.tool-gateway.mcp.mcp_server.MCPGateway` class.
"""

import importlib
from typing import Any

_MCP_MODULE = "cyberai.tool-gateway.mcp.mcp_server"


def get_mcp_gateway() -> Any:
    """Return a fresh MCPGateway instance (loaded via importlib)."""
    module = importlib.import_module(_MCP_MODULE)
    return module.MCPGateway()


def get_mcp_module() -> Any:
    """Return the raw MCP gateway module object."""
    return importlib.import_module(_MCP_MODULE)
