"""Command endpoints — the shared command bus over HTTP.

    GET  /api/v1/commands           command catalog (name, usage, description)
    GET  /api/v1/commands/{name}    one command's spec
    POST /api/v1/commands/execute   parse + dispatch a command line

The web UI, CLI, and chat all dispatch through this same bus, so
authorization (PermissionError → blocked) is enforced identically
everywhere.
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from cyberai.commands import get_dispatcher, load_builtin_commands

router = APIRouter(prefix="/api/v1/commands", tags=["commands"])


def _dispatcher():
    load_builtin_commands()  # idempotent: handlers register on import
    return get_dispatcher()


@router.get("")
async def list_commands():
    d = _dispatcher()
    catalog = d.help()
    # Flatten categories into a list for the command palette.
    flat = []
    for cat, cmds in (catalog.get("categories") or {}).items():
        for c in cmds:
            flat.append({"category": cat, **c})
    return {"commands": flat, "categories": catalog.get("categories"),
            "total": len(flat)}


@router.get("/{name}")
async def get_command(name: str):
    d = _dispatcher()
    info = d.help(name)
    if not info.get("ok"):
        raise HTTPException(status_code=404, detail=info.get("error"))
    return {"command": info}


@router.post("/execute")
async def execute_command(body: Dict[str, Any]):
    """Execute a command line, e.g. {"input": "/status"} or {"input": "/findings status=LIKELY"}."""
    if not str(body.get("input") or "").strip():
        raise HTTPException(status_code=400, detail="input is required")
    d = _dispatcher()
    result = d.execute(str(body["input"]))
    return result.to_dict()
