"""Target endpoints.

    GET   /api/v1/targets          list targets with auth + reachability
    PATCH /api/v1/targets/{id}     authorize/revoke (policy-gated)
"""

import socket
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from cyberai.ui.api._helpers import require_fields
from cyberai.ui.server import EVENT_BUS

router = APIRouter(prefix="/api/v1/targets", tags=["targets"])


def _port_open(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@router.get("")
async def list_targets():
    from cyberai.orchestrator import PolicyEngine
    pe = PolicyEngine()
    try:
        rows = pe.list_targets()
    finally:
        pe.close()
    out = []
    for t in rows:
        host = t.get("host", "")
        port = int(t.get("port") or 0)
        reachable = _port_open(port, host) if (host and port) else False
        if not t.get("allowed"):
            state = "UNAUTHORIZED"
        elif not reachable:
            state = "OFFLINE"
        else:
            state = "ACTIVE"
        out.append({**t, "state": state, "reachable": reachable})
    return {"targets": out, "total": len(out)}


@router.patch("/{target_id}")
async def update_target(target_id: str, body: Dict[str, Any]):
    """Authorize (allowed=true) or revoke (allowed=false) a target."""
    require_fields(body, "allowed")
    allowed = body["allowed"]
    if not isinstance(allowed, bool):
        raise HTTPException(status_code=400, detail="allowed must be a boolean")
    from cyberai.orchestrator import PolicyEngine
    pe = PolicyEngine()
    try:
        existing = pe.get_target(target_id)
        if not existing:
            raise HTTPException(status_code=404, detail="target not found")
        # register_target takes a single target dict — merge the new flag in.
        pe.register_target({**existing, "allowed": bool(allowed)})
    finally:
        pe.close()
    EVENT_BUS.publish("audit", {
        "actor": "OPERATOR", "agent": "-", "tool": "policy",
        "target": target_id, "action": "authorize" if allowed else "revoke",
        "result": "SUCCESS", "session": "-",
    })
    return {"id": target_id, "allowed": allowed}
