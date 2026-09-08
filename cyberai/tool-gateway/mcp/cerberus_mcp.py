"""
Cerberus MCP Server — exposes the Cerberus orchestrator itself as an
MCP server over stdio.

Tools:
  - status:        Platform status (adapters, models, MCP health)
  - findings:      Recent findings from memory
  - memory_search: Semantic (TF-IDF) search over the typed memory store
  - killchain:     F2T2EA kill-chain status / start / advance
  - wargame:       Ghost-wargaming failure analytics
  - hunt:          Launch a (simulated by default) hunt against a target

Run:
  python -m cyberai.tool-gateway.mcp.cerberus_mcp
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure the workspace root is importable when launched as a script
_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))

try:
    from mcp.server.fastmcp import FastMCP  # mcp v1 SDK
except ModuleNotFoundError:  # mcp 2.x renamed FastMCP → MCPServer
    from fastmcp import FastMCP

mcp = FastMCP("cerberus-orchestrator")


@mcp.tool()
def status() -> str:
    """Get Cerberus platform status: adapters, models, and MCP servers."""
    out: Dict[str, Any] = {"platform": "Cerberus"}

    try:
        from cyberai.orchestrator.cli._mcp import get_mcp_gateway
        gw = get_mcp_gateway()
        # Lightweight: list configured servers without probing each one
        # (a full probe takes minutes; use `mcp health` CLI for that)
        out["mcp_servers"] = {
            name: cfg.get("description", "")[:60]
            for name, cfg in gw._servers.items()
        }
    except Exception as e:
        out["mcp_servers"] = f"error: {e}"

    try:
        from cyberai.llm_gateway import LLMGateway
        gm = LLMGateway()
        out["models"] = gm.list_registry()
    except Exception as e:
        out["models"] = f"error: {e}"

    try:
        adapters_dir = _WORKSPACE_ROOT / "adapters"
        out["adapters"] = sorted(
            d.name for d in adapters_dir.iterdir() if d.is_dir()
            and not d.name.startswith(("_", "."))
        )
    except Exception as e:
        out["adapters"] = f"error: {e}"

    return json.dumps(out, default=str)


@mcp.tool()
def findings(limit: int = 10) -> str:
    """List recent findings recorded in Cerberus memory."""
    from cyberai.orchestrator import MemoryManager

    mm = MemoryManager()
    try:
        rows = mm.get_findings()
        return json.dumps({"count": len(rows), "findings": rows[:limit]},
                          default=str)
    finally:
        mm.close()


@mcp.tool()
def memory_search(query: str, memory_type: str = "", limit: int = 5) -> str:
    """Semantic (TF-IDF) search over Cerberus's typed memory store.

    Args:
        query: Natural-language query, e.g. 'SQL injection auth bypass'
        memory_type: Optional filter (semantic, failure, procedural, ...)
        limit: Max results (default 5)
    """
    from cyberai.memory.memory_store import MemoryStore

    ms = MemoryStore()
    results = ms.semantic_search(
        query, memory_type=memory_type or None, limit=limit)
    return json.dumps({
        "query": query,
        "count": len(results),
        "results": [
            {
                "similarity": r.get("similarity"),
                "memory_type": r["memory_type"],
                "content": r["content"][:200],
                "verification": r.get("verification"),
            }
            for r in results
        ],
    }, default=str)


@mcp.tool()
def killchain(target: str = "", action: str = "status") -> str:
    """F2T2EA kill-chain tracking (Find→Fix→Track→Target→Engage→Assess).

    Args:
        target: Target identifier (required for start/advance)
        action: 'status' (default), 'start', or 'advance'
    """
    from cyberai.orchestrator.workflows.kill_chain import (
        KillChainEngine, KillChainError,
    )

    engine = KillChainEngine()
    try:
        if action == "start" and target:
            chain = engine.start_chain(target)
            return json.dumps({
                "action": "start", "target": target,
                "chain_id": chain.chain_id,
                "current_phase": chain.current_phase.value,
                "status": chain.status,
            })
        if action == "advance" and target:
            result = engine.advance(target, note="advanced via MCP")
            return json.dumps({"action": "advance", "target": target,
                               **result})
        if target:
            chain = engine.get_chain(target)
            if not chain:
                return json.dumps({"error": f"no chain for {target}"})
            return json.dumps(chain.to_dict())
        return json.dumps(engine.status())
    except KillChainError as e:
        return json.dumps({"error": str(e)})
    finally:
        pass


@mcp.tool()
def wargame() -> str:
    """Ghost-wargaming failure analytics: what failed, by category and tool."""
    from cyberai.evolution import GhostWargame

    gw = GhostWargame()
    return json.dumps(gw.analytics(), default=str)


@mcp.tool()
def hunt(target: str, objective: str = "recon", simulate: bool = True) -> str:
    """Launch a hunt against a target (simulated by default for safety).

    Args:
        target: Target identifier (e.g. 'lab-web-01')
        objective: What to achieve (default 'recon')
        simulate: Dry-run without executing tools (default True)
    """
    import asyncio

    from cyberai.orchestrator.master import CyberAIOrchestrator

    orch = CyberAIOrchestrator(simulate=simulate)
    result = asyncio.run(orch.run(objective=objective, target_id=target))
    return json.dumps(result, default=str)


def main() -> None:
    """Entry point: run the Cerberus MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
