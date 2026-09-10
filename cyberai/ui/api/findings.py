"""Findings endpoints.

    GET   /api/v1/findings        list/filter findings
    PATCH /api/v1/findings/{id}   update verification status
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from cyberai.ui.api._helpers import require_fields

router = APIRouter(prefix="/api/v1/findings", tags=["findings"])

_VALID_STATES = ("UNVERIFIED", "LIKELY", "VERIFIED", "REJECTED")


@router.get("")
async def list_findings(status: str = "", q: str = "", session_id: str = "",
                        limit: int = 200):
    from cyberai.orchestrator import MemoryManager
    mm = MemoryManager()
    try:
        rows = mm.get_findings(status=(status.strip().upper() or None))
    finally:
        mm.close()
    if session_id:
        rows = [f for f in rows if f.get("session_id") == session_id]
    if q:
        ql = q.lower()
        rows = [f for f in rows
                if ql in str(f.get("observation", "")).lower()
                or ql in str(f.get("source", "")).lower()]
    return {"findings": rows[:limit], "total": len(rows)}


@router.patch("/{finding_id}")
async def update_finding(finding_id: str, body: Dict[str, Any]):
    require_fields(body, "status")
    status = str(body["status"]).strip().upper()
    if status not in _VALID_STATES:
        raise HTTPException(
            status_code=400,
            detail=f"invalid status {status!r}; valid: {', '.join(_VALID_STATES)}")
    from cyberai.orchestrator import MemoryManager
    mm = MemoryManager()
    try:
        match = [f for f in mm.get_findings() if f.get("id") == finding_id]
        if not match:
            raise HTTPException(status_code=404, detail="finding not found")
        mm.update_finding_status(finding_id, status)
    finally:
        mm.close()
    from cyberai.ui.server import EVENT_BUS
    EVENT_BUS.publish("audit", {
        "actor": "OPERATOR", "agent": "-", "tool": "memory",
        "target": "-", "action": f"finding {status.lower()}",
        "result": "SUCCESS", "session": match[0].get("session_id", "-"),
    })
    return {"id": finding_id, "status": status}
