"""Evidence endpoints.

    GET /api/v1/evidence          list evidence records
    GET /api/v1/evidence/{id}     evidence detail
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/evidence", tags=["evidence"])


@router.get("")
async def list_evidence(session_id: str = "", limit: int = 100):
    from cyberai.orchestrator.evidence.evidence import EvidenceManager
    em = EvidenceManager()
    try:
        if session_id:
            rows = em.list_evidence(session_id)
        else:
            # No session filter: aggregate across all known sessions.
            rows = []
            from cyberai.orchestrator import MemoryManager
            mm = MemoryManager()
            try:
                for s in mm.list_sessions():
                    try:
                        rows.extend(em.list_evidence(s.get("id")))
                    except Exception:  # noqa: BLE001
                        continue
            finally:
                mm.close()
    finally:
        close = getattr(em, "close", None)
        if callable(close):
            close()
    return {"evidence": rows[:limit], "total": len(rows)}


@router.get("/{evidence_id}")
async def get_evidence(evidence_id: str):
    from cyberai.orchestrator.evidence.evidence import EvidenceManager
    em = EvidenceManager()
    try:
        match = None
        from cyberai.orchestrator import MemoryManager
        mm = MemoryManager()
        try:
            for s in mm.list_sessions():
                try:
                    for e in em.list_evidence(s.get("id")):
                        if e.get("id") == evidence_id:
                            match = e
                            break
                except Exception:  # noqa: BLE001
                    continue
                if match:
                    break
        finally:
            mm.close()
    finally:
        close = getattr(em, "close", None)
        if callable(close):
            close()
    if not match:
        raise HTTPException(status_code=404, detail="evidence not found")
    return match
