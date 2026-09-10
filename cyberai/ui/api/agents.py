"""Agent endpoints.

    GET /api/v1/agents     list agents with performance stats
    GET /api/v1/agents/{name}  one agent detail
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

_BASE_AGENTS = [
    {"name": "planner", "role": "Mission planning", "capability": "planning"},
    {"name": "researcher", "role": "Threat intelligence", "capability": "research"},
    {"name": "recon", "role": "Network discovery", "capability": "reconnaissance"},
    {"name": "analyst", "role": "Pattern analysis", "capability": "analysis"},
    {"name": "coder", "role": "Exploit / PoC code", "capability": "code_generation"},
    {"name": "verifier", "role": "Evidence validation", "capability": "verification"},
    {"name": "reporter", "role": "Report generation", "capability": "reporting"},
]


@router.get("")
async def list_agents():
    from cyberai.meta_learning.tracker import PerformanceTracker
    tracker = PerformanceTracker()
    try:
        stats = tracker.get_all_stats("agent")
    except Exception:  # noqa: BLE001
        stats = {}
    finally:
        tracker.close()
    out = []
    for a in _BASE_AGENTS:
        ag = stats.get(a["name"], {})
        calls = sum(v.get("calls", 0) for v in ag.values())
        rates = [v.get("success_rate", 0) for v in ag.values()]
        out.append({
            **a,
            "calls": calls,
            "success_rate": round(sum(rates) / len(rates), 3) if rates else None,
        })
    return {"agents": out}


@router.get("/{name}")
async def get_agent(name: str):
    base = next((a for a in _BASE_AGENTS if a["name"] == name), None)
    if not base:
        raise HTTPException(status_code=404, detail=f"unknown agent: {name}")
    from cyberai.meta_learning.tracker import PerformanceTracker
    tracker = PerformanceTracker()
    try:
        stats = tracker.get_all_stats("agent").get(name, {})
    except Exception:  # noqa: BLE001
        stats = {}
    finally:
        tracker.close()
    return {**base, "performances": stats}
