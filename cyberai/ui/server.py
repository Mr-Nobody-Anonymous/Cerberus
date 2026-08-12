"""
Cyber AI — Unified Web UI Server.

Serves a single human-facing cockpit for the whole platform:
  - One command box that talks to the unified CyberAIOrchestrator
  - Live Server-Sent-Events stream of every agent, phase, and finding
  - Live dashboard: targets, tools, models, agents, memory, LLM health
  - Runs standalone, no Docker required

Run:
    python -m cyberai.ui.server            # or via start_cerberus.py
"""

import asyncio
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Live event bus — bridges orchestrator callbacks to SSE subscribers
# ---------------------------------------------------------------------------
class LiveEventBus:
    """Fan-out event bus for Server-Sent-Events to browser clients."""

    def __init__(self, max_history: int = 500):
        self._subscribers: Dict[str, asyncio.Queue] = {}
        self._history: List[Dict[str, Any]] = []
        self._max_history = max_history
        self._lock = threading.Lock()

    def subscribe(self) -> str:
        """Register a new subscriber, returns its id."""
        subscriber_id = f"sub-{time.time_ns()}"
        self._subscribers[subscriber_id] = asyncio.Queue(maxsize=200)
        # Replay last events so a page refresh doesn't blank the feed
        for event in self._history[-50:]:
            try:
                self._subscribers[subscriber_id].put_nowait(event)
            except asyncio.QueueFull:
                break
        return subscriber_id

    def unsubscribe(self, subscriber_id: str) -> None:
        self._subscribers.pop(subscriber_id, None)

    def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        event = {"type": event_type, "data": data, "ts": time.time()}
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
        for subscriber_id in list(self._subscribers):
            q = self._subscribers.get(subscriber_id)
            if q is None:
                continue
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # Drop oldest for slow consumers
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except Exception:
                    pass

    def history(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return self._history[-limit:]


EVENT_BUS = LiveEventBus()


# ---------------------------------------------------------------------------
# Unified chat / command agent
# ---------------------------------------------------------------------------
def _command_response(message: str) -> Dict[str, Any]:
    """Local deterministic answers for the operator command box."""
    m = message.strip().lower()
    if m in ("help", "?"):
        return {
            "reply": (
                "COMMANDS\n"
                "  simulate <objective>   run a full simulated assessment\n"
                "  status                 platform status\n"
                "  targets                authorized lab targets\n"
                "  tools                  tool registry\n"
                "  models                 model registry\n"
                "  findings               findings in memory\n"
                "  help                   this help"
            )
        }
    if m in ("status", "health"):
        return {"reply": "CERBERUS ONLINE — run 'status' in the deck for full JSON."}
    if m in ("targets",):
        pc = _policy()
        targets = pc.list_authorized_targets()
        ids = ", ".join(t.get("id", "?") for t in targets) or "none registered"
        return {"reply": f"AUTHORIZED TARGETS: {ids}"}
    if m in ("tools",):
        tr = _tools()
        names = ", ".join(tr.list_tools())
        return {"reply": f"TOOL REGISTRY: {names}"}
    if m in ("models",):
        gw = _gateway()
        return {"reply": "MODEL REGISTRY — see Models panel."}
    if m in ("findings",):
        return {"reply": "FINDINGS — see Findings panel."}
    if m.startswith("simulate "):
        return {"reply": "DISPATCH — watch the agent feed begin.", "simulate": m[9:]}
    return {
        "reply": (
            "CERBERUS ONLINE. Ask a task like 'simulate analyze the lab target' "
            "or use the TASK LAUNCHER below."
        )
    }


# Lazy import helpers so the UI never breaks when subsystems are unavailable
def _policy():
    from cyberai.orchestrator import PolicyEngine
    return PolicyEngine()


def _tools():
    from cyberai.orchestrator import ToolRegistry
    return ToolRegistry()


def _gateway():
    from cyberai.llm_gateway import LLMGateway
    return LLMGateway()


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
def create_app():
    """Create the unified web UI application."""
    try:
        from fastapi import FastAPI, HTTPException, Request
        from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
    except ImportError:
        logger.warning("fastapi/uvicorn not installed - install with: pip install -e '.[api]'")
        return None

    app = FastAPI(title="CERBERUS Command Deck", version="2.0.0")
    orchestrator_holder: Dict[str, Any] = {"orchestrator": None}

    # ---- Static UI ----
    @app.get("/", response_class=HTMLResponse)
    async def index():
        ui_file = Path(__file__).parent / "static" / "index.html"
        if ui_file.exists():
            return HTMLResponse(ui_file.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>CERBERUS</h1><p>UI not found</p>")

    @app.get("/favicon.ico")
    async def favicon():
        icon_file = Path(__file__).parent / "static" / "favicon.ico"
        if icon_file.exists():
            from fastapi.responses import Response
            return Response(content=icon_file.read_bytes(), media_type="image/svg+xml")
        return Response(status_code=404)

    @app.get("/api/bootstrap")
    async def bootstrap():
        """All data the UI needs on first paint."""
        data: Dict[str, Any] = {
            "platform": "CERBERUS",
            "version": "2.0.0",
            "mode": "simulation-default",
            "agents": [
                {"name": "planner", "role": "Mission planning", "icon": "🧠"},
                {"name": "researcher", "role": "Threat intelligence", "icon": "🔍"},
                {"name": "recon", "role": "Network discovery", "icon": "🛰️"},
                {"name": "analyst", "role": "Pattern analysis", "icon": "📊"},
                {"name": "coder", "role": "Exploit / PoC code", "icon": "💻"},
                {"name": "verifier", "role": "Evidence validation", "icon": "✅"},
                {"name": "reporter", "role": "Report generation", "icon": "📋"},
            ],
        }
        try:
            data["targets"] = _policy().list_authorized_targets()
        except Exception as e:
            data["targets"] = []
            data["targets_error"] = str(e)
        try:
            data["tools"] = _tools().list_tools()
        except Exception as e:
            data["tools"] = []
            data["tools_error"] = str(e)
        try:
            data["models"] = _gateway().list_registry()
        except Exception as e:
            data["models"] = []
            data["models_error"] = str(e)
        try:
            from cyberai.memory.memory_store import MemoryStore
            store = MemoryStore()
            data["memory"] = store.get_stats()
            store.close()
        except Exception as e:
            data["memory"] = {"total": 0, "by_type": {}}
            data["memory_error"] = str(e)
        try:
            from cyberai.orchestrator import MemoryManager
            memory = MemoryManager()
            data["findings"] = memory.get_findings()[:50]
            memory.close()
        except Exception as e:
            data["findings"] = []
            data["findings_error"] = str(e)
        return data

    @app.get("/api/realtime")
    async def realtime(request: Request):
        """Server-Sent-Events stream of live agent activity."""
        subscriber_id = EVENT_BUS.subscribe()

        async def event_stream():
            try:
                yield "event: ready\ndata: {}\n\n"
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        event = EVENT_BUS._subscribers[subscriber_id].get_nowait()
                        payload = json.dumps(event)
                        yield f"event: {event['type']}\ndata: {payload}\n\n"
                    except asyncio.QueueEmpty:
                        await asyncio.sleep(0.25)
            finally:
                EVENT_BUS.unsubscribe(subscriber_id)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    @app.post("/api/tasks")
    async def start_task(request: Request):
        """Launch a unified agent run. Returns immediately; results stream live."""
        body = await request.json()
        objective = body.get("objective", "").strip()
        target_id = body.get("target_id") or None
        simulate = bool(body.get("simulate", True))
        dry_run = bool(body.get("dry_run", False))
        if not objective:
            raise HTTPException(status_code=400, detail="objective is required")

        async def runner():
            from cyberai import CyberAIOrchestrator
            orch = CyberAIOrchestrator(
                simulate=simulate,
                dry_run=dry_run,
                local_only=True,
            )
            orchestrator_holder["orchestrator"] = orch
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
                    "summary": _summarize_task(result),
                })
            except PermissionError as e:
                EVENT_BUS.publish("task_error", {"error": str(e)})
            except Exception as e:
                EVENT_BUS.publish("task_error", {"error": str(e)})
            finally:
                orch.close()
                orchestrator_holder["orchestrator"] = None

        asyncio.create_task(runner())
        return {"status": "accepted", "objective": objective, "simulate": simulate}

    @app.post("/api/command")
    async def command(request: Request):
        body = await request.json()
        message = str(body.get("message", "")).strip()
        if not message:
            raise HTTPException(status_code=400, detail="message is required")
        result = _command_response(message)
        # Simulate dispatch from the command box
        sim = result.pop("simulate", None)
        if sim:
            from cyberai import CyberAIOrchestrator
            async def sim_runner():
                orch = CyberAIOrchestrator(simulate=True, local_only=True)
                orchestrator_holder["orchestrator"] = orch
                try:
                    await orch.run(
                        sim,
                        target_id="lab-web-01",
                        event_callback=lambda etype, edata: EVENT_BUS.publish(etype, edata),
                    )
                except Exception as e:
                    EVENT_BUS.publish("task_error", {"error": str(e)})
                finally:
                    orch.close()
                    orchestrator_holder["orchestrator"] = None
            asyncio.create_task(sim_runner())
        return result

    @app.get("/api/status")
    async def status():
        try:
            from cyberai import CyberAIOrchestrator
            orch = CyberAIOrchestrator(simulate=True, local_only=True)
            try:
                return orch.get_status()
            finally:
                orch.close()
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    return app


def _summarize_task(task: Dict[str, Any]) -> str:
    """Produce a short human-readable summary of a finished task."""
    lines = [
        f"OBJECTIVE: {task.get('objective', '')[:120]}",
        f"STATUS: {task.get('status', '?').upper()}",
        f"FINDINGS: {len(task.get('findings', []))}",
        f"AGENTS: {', '.join(task.get('agents_used', [])) or 'none'}",
    ]
    report = task.get("final_report") or {}
    content = report.get("content", "")
    if content:
        lines.append("REPORT:")
        lines.append(content[:800])
    return "\n".join(lines)


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("cyberai.ui.server:app", host="127.0.0.1", port=8710, reload=False)
