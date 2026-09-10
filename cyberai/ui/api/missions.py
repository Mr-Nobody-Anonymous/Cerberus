"""Mission endpoints — launch, monitor, stop missions.

    GET   /api/v1/missions             mission-kind sessions
    POST  /api/v1/missions             launch a mission (async runner)
    GET   /api/v1/missions/{id}        mission detail
    POST  /api/v1/missions/{id}/stop   cooperative stop
    POST  /api/v1/missions/{id}/pause  (reserved — maps to stop semantics)
    POST  /api/v1/missions/{id}/resume (reserved — relaunch objective)

Mission launching mirrors the legacy POST /api/tasks exactly: same
CyberAIOrchestrator flags, same event publishing, same PermissionError
handling. Modes: SIMULATE (default, safest), PLAN (dry-run), LAB, AUTHORIZED.
"""

import asyncio
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request

from cyberai.ui.api._helpers import (get_session_or_404, now_iso,
                                     parse_session_meta, require_fields,
                                     session_title, write_session_meta)
from cyberai.ui.server import EVENT_BUS

router = APIRouter(prefix="/api/v1/missions", tags=["missions"])

_MODES = {
    "SIMULATE": {"simulate": True, "dry_run": False},
    "PLAN": {"simulate": True, "dry_run": True},
    "LAB": {"simulate": False, "dry_run": False},
    "AUTHORIZED": {"simulate": False, "dry_run": False},
}

# Shared live-mission holder (same pattern as server.py's holder).
MISSION_HOLDER: Dict[str, Any] = {"orchestrator": None, "mission": None}


def _launch_runner(objective: str, target_id: Optional[str], mode: str,
                   flags: Dict[str, Any], session_id: Optional[str] = None):
    """Create the async runner — identical semantics to /api/tasks."""

    async def runner():
        from cyberai import CyberAIOrchestrator
        orch = CyberAIOrchestrator(local_only=True, **flags)
        MISSION_HOLDER["orchestrator"] = orch
        MISSION_HOLDER["mission"] = {"objective": objective, "mode": mode,
                                     "started_at": now_iso()}
        try:
            result = await orch.run(
                objective,
                target_id=target_id,
                event_callback=lambda etype, edata: EVENT_BUS.publish(etype, edata),
                scope="authorized_lab",
            )
            EVENT_BUS.publish("task_result", {
                "task_id": result.get("id"),
                "status": result.get("status"),
                "findings_count": len(result.get("findings", [])),
            })
            EVENT_BUS.publish("audit", {
                "actor": "CERBERUS", "agent": "orchestrator", "tool": "master",
                "target": target_id or "-", "action": f"mission run ({mode})",
                "result": "SUCCESS", "session": result.get("id", ""),
            })
        except PermissionError as e:
            EVENT_BUS.publish("task_error", {"error": str(e)})
            EVENT_BUS.publish("policy.blocked", {
                "reason": str(e), "policy": "LAB_ONLY",
                "action": "mission run", "target": target_id or "-",
                "human_readable": (
                    f"Target '{target_id or 'unspecified'}' is not authorized "
                    "for active testing. Register it in lab/targets/targets.yaml "
                    "with allowed: true, or run in SIMULATE mode."),
            })
        except Exception as e:  # noqa: BLE001
            EVENT_BUS.publish("task_error", {"error": str(e)})
        finally:
            orch.close()
            MISSION_HOLDER["orchestrator"] = None
            MISSION_HOLDER["mission"] = None

    return asyncio.create_task(runner())


@router.get("")
async def list_missions(q: str = "", status: str = "", limit: int = 100):
    from cyberai.orchestrator import MemoryManager
    mm = MemoryManager()
    try:
        rows = mm.list_sessions()
    finally:
        mm.close()
    out = []
    for s in rows:
        meta = parse_session_meta(s)
        if meta.get("kind", "mission") != "mission":
            continue
        if status and (s.get("status") or "") != status:
            continue
        title = session_title(s, meta)
        if q and q.lower() not in title.lower():
            continue
        out.append({
            "id": s.get("id"),
            "title": title,
            "objective": s.get("objective"),
            "target_id": s.get("target_id"),
            "status": s.get("status"),
            "mode": meta.get("mode", "LAB"),
            "started_at": s.get("started_at"),
            "completed_at": s.get("completed_at"),
            "findings_count": s.get("findings_count"),
        })
    return {"missions": out[:limit], "total": len(out)}


@router.post("", status_code=202)
async def launch_mission(body: Dict[str, Any]):
    """Launch a mission. Body: {objective, target_id?, mode?}"""
    require_fields(body, "objective")
    objective = str(body["objective"]).strip()
    target_id = str(body.get("target_id") or "").strip() or None
    mode = str(body.get("mode") or "SIMULATE").upper()
    if mode not in _MODES:
        raise HTTPException(status_code=400,
                            detail=f"invalid mode {mode!r}; valid: {', '.join(_MODES)}")
    flags = _MODES[mode]

    # Record the mission session row up-front so the UI can track it.
    from cyberai.orchestrator import MemoryManager
    mm = MemoryManager()
    try:
        session_id = mm.create_session(target_id=target_id or "", objective=objective)
        meta = {"kind": "mission", "mode": mode, "title": objective[:80],
                "created_at": now_iso()}
        write_session_meta(mm, session_id, meta)
    finally:
        mm.close()

    _launch_runner(objective, target_id, mode, flags, session_id)
    return {"status": "accepted", "objective": objective, "mode": mode,
            "session_id": session_id}


@router.get("/{mission_id}")
async def mission_detail(mission_id: str):
    from cyberai.orchestrator import MemoryManager
    mm = MemoryManager()
    try:
        session = get_session_or_404(mm, mission_id)
        findings = [f for f in mm.get_findings()
                    if f.get("session_id") == mission_id]
    finally:
        mm.close()
    live = MISSION_HOLDER.get("mission")
    return {
        "session": session,
        "findings": findings,
        "live": live,
        "mode": parse_session_meta(session).get("mode", "LAB"),
    }


@router.post("/{mission_id}/stop")
async def stop_mission(mission_id: str):
    """Cooperative stop — never errors, mirrors /api/tasks/stop."""
    orch = MISSION_HOLDER.get("orchestrator")
    if orch is None:
        return {"status": "no_active_mission"}
    try:
        orch.stop()
        EVENT_BUS.publish("audit", {
            "actor": "OPERATOR", "agent": "-", "tool": "console",
            "target": "-", "action": "stop mission", "result": "ISSUED",
            "session": mission_id,
        })
        return {"status": "stop_requested"}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "detail": str(e)}


@router.post("/{mission_id}/pause")
async def pause_mission(mission_id: str):
    """Pause maps to cooperative stop (pipeline checkpoints at step bounds)."""
    result = await stop_mission(mission_id)
    return result


@router.post("/{mission_id}/resume")
async def resume_mission(mission_id: str, body: Dict[str, Any] = None):
    """Resume relaunches the stored objective in the same mode."""
    from cyberai.orchestrator import MemoryManager
    mm = MemoryManager()
    try:
        session = get_session_or_404(mm, mission_id)
        meta = parse_session_meta(session)
        objective = session.get("objective") or ""
        if not objective:
            raise HTTPException(status_code=400, detail="session has no objective")
        mode = meta.get("mode", "SIMULATE")
        if mode not in _MODES:
            mode = "SIMULATE"
    finally:
        mm.close()
    flags = _MODES[mode]
    _launch_runner(objective, session.get("target_id") or None, mode, flags)
    return {"status": "resumed", "objective": objective, "mode": mode}
