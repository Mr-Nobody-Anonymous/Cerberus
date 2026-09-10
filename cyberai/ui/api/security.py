"""Security endpoints.

    GET   /api/v1/security          policy state, blocked actions, events
    GET   /api/v1/security/approvals   pending approvals
    POST  /api/v1/security/approvals/{id}/approve
    POST  /api/v1/security/approvals/{id}/deny
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from cyberai.ui.server import APPROVAL_QUEUE, EVENT_BUS

router = APIRouter(prefix="/api/v1/security", tags=["security"])


@router.get("")
async def security_center():
    blocked = []
    for ev in EVENT_BUS.history(300):
        if ev.get("type") == "policy.blocked":
            blocked.append(ev.get("data", {}))
    from cyberai.orchestrator import PolicyEngine
    pe = PolicyEngine()
    try:
        all_targets = pe.list_targets()
        authorized = [t for t in all_targets if t.get("allowed")]
    except Exception:  # noqa: BLE001
        all_targets, authorized = [], []
    finally:
        pe.close()
    pending = [a for a in APPROVAL_QUEUE if a.get("status") == "PENDING"]
    recent = [
        {"type": ev.get("type"), "data": ev.get("data", {}), "ts": ev.get("ts")}
        for ev in EVENT_BUS.history(50)
        if ev.get("type") in ("policy.blocked", "approval.required",
                              "approval.granted", "approval.denied")
    ]
    return {
        "policy": {
            "mode": "LAB_ONLY",
            "description": "Active testing restricted to explicitly authorized lab targets",
            "targets_registered": len(all_targets),
            "targets_authorized": len(authorized),
        },
        "blocked_actions": blocked,
        "approvals_pending": len(pending),
        "recent_events": recent,
    }


@router.get("/approvals")
async def list_approvals():
    pending = [a for a in APPROVAL_QUEUE if a.get("status") == "PENDING"]
    decided = [a for a in APPROVAL_QUEUE if a.get("status") != "PENDING"]
    return {"pending": pending, "decided": decided}


def _decide(approval_id: str, decision: str) -> Dict[str, Any]:
    match = next((a for a in APPROVAL_QUEUE if a.get("id") == approval_id), None)
    if not match:
        raise HTTPException(status_code=404, detail=f"unknown approval: {approval_id}")
    match["status"] = "APPROVED" if decision == "granted" else "DENIED"
    from cyberai.ui.api._helpers import now_iso
    match["decided_at"] = now_iso()
    EVENT_BUS.publish(f"approval.{decision}", {"id": approval_id})
    EVENT_BUS.publish("audit", {
        "actor": "OPERATOR", "agent": "-", "tool": "policy",
        "target": "-", "action": f"approval {decision} {approval_id}",
        "result": "SUCCESS", "session": "-",
    })
    return {"id": approval_id, "status": match["status"]}


@router.post("/approvals/{approval_id}/approve")
async def approve(approval_id: str):
    return _decide(approval_id, "granted")


@router.post("/approvals/{approval_id}/deny")
async def deny(approval_id: str):
    return _decide(approval_id, "denied")
