"""Session endpoints — mission sessions + unified timeline.

    GET    /api/v1/sessions            list sessions (all kinds)
    GET    /api/v1/sessions/{id}       detail + findings + timeline
    PATCH  /api/v1/sessions/{id}       rename
    POST   /api/v1/sessions/{id}/fork  fork
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from cyberai.ui.api._helpers import (get_session_or_404, parse_session_meta,
                                     require_fields, session_title,
                                     write_session_meta)
from cyberai.ui.server import _session_timeline

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get("")
async def list_sessions(q: str = "", status: str = "", kind: str = "",
                        limit: int = 100):
    from cyberai.orchestrator import MemoryManager
    mm = MemoryManager()
    try:
        rows = mm.list_sessions()
    finally:
        mm.close()
    out = []
    for s in rows:
        meta = parse_session_meta(s)
        s_kind = meta.get("kind", "mission")
        if kind and s_kind != kind:
            continue
        if status and (s.get("status") or "") != status:
            continue
        title = session_title(s, meta)
        if q and q.lower() not in title.lower() \
                and q.lower() not in (s.get("id") or "").lower():
            continue
        out.append({
            "id": s.get("id"),
            "title": title,
            "objective": s.get("objective"),
            "target_id": s.get("target_id"),
            "status": s.get("status"),
            "kind": s_kind,
            "started_at": s.get("started_at"),
            "completed_at": s.get("completed_at"),
            "findings_count": s.get("findings_count"),
            "forked_from": meta.get("forked_from"),
        })
    return {"sessions": out[:limit], "total": len(out)}


@router.get("/{session_id}")
async def get_session(session_id: str):
    from cyberai.orchestrator import MemoryManager
    mm = MemoryManager()
    try:
        session = get_session_or_404(mm, session_id)
        findings = [f for f in mm.get_findings()
                    if f.get("session_id") == session_id]
    finally:
        mm.close()
    timeline = _session_timeline(session_id, session, findings)
    return {"session": session, "findings": findings, "timeline": timeline}


@router.patch("/{session_id}")
async def rename_session(session_id: str, body: Dict[str, Any]):
    require_fields(body, "title")
    from cyberai.orchestrator import MemoryManager
    mm = MemoryManager()
    try:
        session = get_session_or_404(mm, session_id)
        meta = parse_session_meta(session)
        meta["title"] = str(body["title"]).strip()
        write_session_meta(mm, session_id, meta)
        session = mm.get_session(session_id)
    finally:
        mm.close()
    return {"session": session,
            "title": session_title(session, parse_session_meta(session))}


@router.post("/{session_id}/fork", status_code=201)
async def fork_session(session_id: str, body: Dict[str, Any] = None):
    body = body or {}
    from cyberai.orchestrator import MemoryManager
    mm = MemoryManager()
    try:
        session = get_session_or_404(mm, session_id)
        meta = parse_session_meta(session)
        new_id = mm.create_session(
            target_id=session.get("target_id") or "",
            objective=session.get("objective") or "",
        )
        new_meta = dict(meta)
        new_meta["forked_from"] = session_id
        new_meta["title"] = str(body.get("title")
                                or f"{session_title(session, meta)} (fork)")
        write_session_meta(mm, new_id, new_meta)
        new_session = mm.get_session(new_id)
    finally:
        mm.close()
    return {"session": new_session, "forked_from": session_id}
