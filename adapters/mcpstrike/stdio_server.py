#!/usr/bin/env python
"""mcpstrike stdio MCP server launcher.

The upstream ``mcpstrike.server.app:main`` defaults to HTTP transport.
This launcher starts the same FastMCP app over **stdio** so it can be
spawned by the Cerberus MCP gateway (and any stdio MCP client).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the mcpstrike src tree is importable when run as a script
_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from mcpstrike.server.wrapper import MCPServerWrapper  # noqa: E402
import mcpstrike.server.app as app_module  # noqa: E402


def main() -> None:
    app_module.wrapper.run(transport="stdio")


if __name__ == "__main__":
    main()
