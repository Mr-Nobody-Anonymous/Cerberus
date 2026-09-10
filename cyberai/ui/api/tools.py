"""Tool endpoints.

    GET /api/v1/tools          list tools + adapter presence
    GET /api/v1/tools/{name}   tool detail with health
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


@router.get("")
async def list_tools():
    from cyberai.orchestrator import ToolRegistry
    from cyberai.orchestrator.adapters.adapter_manager import AdapterManager
    tr = ToolRegistry()
    am = AdapterManager()
    try:
        registry = tr.to_dict().get("tools", {})
        discovered = am.discover()
        out = []
        for name in sorted(registry):
            info = registry[name]
            out.append({
                "name": name,
                "present": name in discovered,
                "category": info.get("category", ""),
                "description": info.get("description", ""),
            })
        return {"tools": out, "total": len(out)}
    finally:
        close = getattr(am, "close", None)
        if callable(close):
            close()


@router.get("/{name}")
async def get_tool(name: str):
    from cyberai.orchestrator import ToolRegistry
    from cyberai.orchestrator.adapters.adapter_manager import AdapterManager
    tr = ToolRegistry()
    am = AdapterManager()
    try:
        registry = tr.to_dict().get("tools", {})
        if name not in registry:
            raise HTTPException(status_code=404, detail=f"unknown tool: {name}")
        discovered = am.discover()
        health = {"status": "NOT_TESTED"}
        try:
            health = await am.health_check(name)
        except Exception:  # noqa: BLE001
            pass
        return {
            "name": name,
            "registry": registry[name],
            "present": name in discovered,
            "health": health.get("status", "NOT_TESTED"),
        }
    finally:
        close = getattr(am, "close", None)
        if callable(close):
            close()
