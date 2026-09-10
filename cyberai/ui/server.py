"""
CERBERUS — Command Center Web UI Server.

Serves the premium single-page "AI penetration-testing command center"
frontend.  All heavy lifting stays in the existing backend subsystems
(PolicyEngine, ToolRegistry, LLMGateway, MemoryStore, EvidenceManager,
KnowledgeBase, AdapterManager, PerformanceTracker).  The frontend only
presents — the backend authorizes and executes.

Endpoints
---------
/shell                      top-bar state (system, ai mode, model, engagement)
/bootstrap                  first-paint data (agents, targets, tools, models, memory, findings)
/realtime                   SSE stream of live orchestrator + audit events
/tasks                      launch a unified agent run
/command                    controlled operator console (routes via orchestrator)
/status                     platform status
/context                    deep AI context (evolution, capabilities, performance)
/engagements                lab targets as authorized engagements
/attack-surface             derived network graph from authorized scope
/evidence                   evidence vault (EvidenceManager)
/knowledge                  knowledge base search
/memory/search              experience memory search
/models                     model registry
/tools                      tool/adapter registry + health
/agents                     agent roster + performance
/system-health              subsystem health dashboard
/audit                      searchable audit trail
/threat                     threat score + live events feed
/decision-chain             CERBERUS signature decision chain
/approvals                  human-approval action queue
/notifications              critical-event notifications

Frontend never bypasses PolicyEngine/Orchestrator/ToolRegistry/LLMGateway.
"""

import asyncio
import json
import logging
import socket
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

from cyberai.config import WORKSPACE_ROOT

# Intentionally package-relative: the static frontend ships next to this
# module as package data — NOT a workspace resource (do not route through
# cyberai.config.resolve_path).
STATIC_DIR = Path(__file__).resolve().parent / "static"


# ---------------------------------------------------------------------------
# Live event bus — bridges orchestrator callbacks to SSE subscribers
# ---------------------------------------------------------------------------
class LiveEventBus:
    """Fan-out event bus for Server-Sent-Events to browser clients.

    Thin facade over the persistent EventStore (spec §24): every publish
    is normalized to the canonical event shape, persisted to SQLite, and
    fanned out to SSE subscribers. History therefore survives restarts
    and the CLI /watch sees the same stream as the Web UI.
    """

    def __init__(self, max_history: int = 500):
        from cyberai.orchestrator.event_store import get_event_store
        self._store = get_event_store()
        self._max_history = max_history
        self._subscribers: Dict[str, asyncio.Queue] = {}

    def subscribe(self) -> str:
        subscriber_id = f"sub-{time.time_ns()}"
        self._subscribers[subscriber_id] = asyncio.Queue(maxsize=300)
        for event in self._store.history(limit=60):
            try:
                self._subscribers[subscriber_id].put_nowait(event.sse_payload())
            except asyncio.QueueFull:
                break
        return subscriber_id

    def unsubscribe(self, subscriber_id: str) -> None:
        self._subscribers.pop(subscriber_id, None)

    def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish a (possibly legacy-shaped) event; canonicalized on ingest."""
        from cyberai.orchestrator.events import normalize
        ev = normalize({"type": event_type, "data": data, "ts": time.time()})
        self._store.append(ev)
        payload = ev.sse_payload()
        for subscriber_id in list(self._subscribers):
            q = self._subscribers.get(subscriber_id)
            if q is None:
                continue
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                try:
                    q.get_nowait()
                    q.put_nowait(payload)
                except Exception:
                    pass

    def history(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Legacy-shape history (SSE envelope) for older consumers."""
        return [e.sse_payload() for e in self._store.history(limit=limit)]


EVENT_BUS = LiveEventBus()
APPROVAL_QUEUE: List[Dict[str, Any]] = []  # in-memory approval requests
_SERVER_START = time.time()  # for /api/scorecard uptime KPI


def _seed_approvals() -> None:
    """Pre-populate the approval queue with clearly-marked demo requests."""
    if APPROVAL_QUEUE:
        return
    APPROVAL_QUEUE.extend([
        {
            "id": "appr-001",
            "action": "Isolate endpoint WORKSTATION-042",
            "reason": "Potential credential compromise (37 failed logins, same source)",
            "risk": "HIGH",
            "status": "PENDING",
            "timestamp": _now_iso(),
            "demo": True,
        },
        {
            "id": "appr-002",
            "action": "Update firewall rule for suspicious source 10.0.0.7",
            "reason": "Unexpected outbound connection to unknown external host",
            "risk": "MEDIUM",
            "status": "PENDING",
            "timestamp": _now_iso(),
            "demo": True,
        },
        {
            "id": "appr-003",
            "action": "Add threat-intel indicator to blocklist",
            "reason": "C2 domain observed in authorized lab telemetry",
            "risk": "LOW",
            "status": "PENDING",
            "timestamp": _now_iso(),
            "demo": True,
        },
    ])


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _now_hm() -> str:
    import datetime as dt
    return dt.datetime.now().strftime("%H:%M:%S")


# ---------------------------------------------------------------------------
# Safe subsystem accessors (backend only — frontend never reaches these)
# ---------------------------------------------------------------------------
def _policy():
    from cyberai.orchestrator import PolicyEngine
    return PolicyEngine()


def _tools():
    from cyberai.orchestrator import ToolRegistry
    return ToolRegistry()


def _memory_manager():
    from cyberai.orchestrator import MemoryManager
    return MemoryManager()


def _memory_store():
    from cyberai.memory.memory_store import MemoryStore
    return MemoryStore()


def _gateway():
    from cyberai.llm_gateway import LLMGateway
    return LLMGateway()


def _evidence():
    from cyberai.orchestrator.evidence.evidence import EvidenceManager
    return EvidenceManager()


def _knowledge():
    from cyberai.orchestrator.knowledge.knowledge_loader import KnowledgeBase
    return KnowledgeBase()


def _adapters():
    from cyberai.orchestrator.adapters.adapter_manager import AdapterManager
    return AdapterManager()


def _tracker():
    from cyberai.meta_learning.tracker import PerformanceTracker
    return PerformanceTracker()


def _capabilities():
    from cyberai.capabilities.registry import CapabilityRegistry
    return CapabilityRegistry()


def _port_open(port: int, host: str = "127.0.0.1", timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _docker_available() -> bool:
    import shutil
    return shutil.which("docker") is not None


def _read_session_logs() -> List[Dict[str, Any]]:
    """Read audit entries from session logs (if any), returning [] otherwise."""
    entries = []
    logs_dir = WORKSPACE_ROOT / "logs" / "sessions"
    if logs_dir.exists():
        for file in sorted(logs_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:10]:
            try:
                for line in file.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
            except Exception:
                continue
    return entries


# ---------------------------------------------------------------------------
# Controlled operator console — routes through orchestrator policy, never shell
# ---------------------------------------------------------------------------
def _command_response(message: str, holder: Dict[str, Any]) -> Dict[str, Any]:
    """Interpret console commands. All actions stay within CERBERUS subsystems."""
    m = message.strip()
    ml = m.lower()
    if not m:
        return {"reply": "Usage: type a command. 'help' lists commands."}

    if ml in ("help", "?"):
        return {"reply": (
            "CERBERUS CONSOLE COMMANDS\n"
            "  help                                 this help\n"
            "  status                               platform status\n"
            "  targets                              authorized lab targets\n"
            "  tools                                tool registry\n"
            "  models                               model registry\n"
            "  agents                               agent roster\n"
            "  findings                             findings from memory\n"
            "  evidence                             evidence vault\n"
            "  memory <query>                       search experience memory\n"
            "  knowledge <query>                    search knowledge base\n"
            "  engagements                          authorized engagements\n"
            "  health                               subsystem health summary\n"
            "  audit                                recent audit trail\n"
            "  simulate <objective>                 dispatch full AI run (simulated)\n"
            "  engage <target-id>                   select engagement\n"
            "  clear                                clear console output"
        )}

    if ml in ("status", "health"):
        try:
            from cyberai import CyberAIOrchestrator
            orch = CyberAIOrchestrator(simulate=True, local_only=True)
            s = orch.get_status()
            orch.close()
            return {"reply": json.dumps(s, indent=2, default=str)[:4000]}
        except Exception as e:
            return {"reply": f"ERROR: {e}"}

    if ml == "targets":
        try:
            targets = _policy().list_authorized_targets()
            lines = [f"AUTHORIZED TARGETS ({len(targets)})"]
            for t in targets:
                lines.append(f"  {t.get('id')}  {t.get('host')}:{t.get('port')}  {t.get('description','')}")
            return {"reply": "\n".join(lines) or "NONE REGISTERED"}
        except Exception as e:
            return {"reply": f"ERROR: {e}"}

    if ml == "tools":
        try:
            tools = _tools().list_tools()
            return {"reply": "TOOL REGISTRY (" + str(len(tools)) + ")\n  " + "\n  ".join(tools)}
        except Exception as e:
            return {"reply": f"ERROR: {e}"}

    if ml == "models":
        try:
            models = _gateway().list_registry()
            lines = [f"{(x.get('alias') or '?')} — {(x.get('provider') or '?')} — {(x.get('status') or '?')}" for x in models]
            return {"reply": "MODEL REGISTRY\n  " + "\n  ".join(lines)}
        except Exception as e:
            return {"reply": f"ERROR: {e}"}

    if ml == "agents":
        return {"reply": "AGENT ROSTER\n  planner, researcher, recon, analyst, coder, verifier, reporter"}

    if ml == "findings":
        try:
            mm = _memory_manager()
            findings = mm.get_findings()
            mm.close()
            if not findings:
                return {"reply": "NO FINDINGS IN MEMORY"}
            lines = [f"[{f.get('status','')}] {str(f.get('observation',''))[:90]}" for f in findings[:30]]
            return {"reply": "FINDINGS (" + str(len(findings)) + ")\n  " + "\n  ".join(lines)}
        except Exception as e:
            return {"reply": f"ERROR: {e}"}

    if ml == "evidence":
        return {"reply": "EVIDENCE — see Evidence Vault view."}

    if ml == "engagements":
        try:
            targets = _policy().list_targets()
            lines = [f"  {t.get('id')}  {'AUTHORIZED' if t.get('allowed') else 'NOT AUTHORIZED'}" for t in targets]
            return {"reply": "ENGAGEMENTS (" + str(len(targets)) + ")\n" + "\n".join(lines)}
        except Exception as e:
            return {"reply": f"ERROR: {e}"}

    if ml == "audit":
        return {"reply": "AUDIT — see Audit Log view (searchable + filterable)."}

    if ml.startswith("memory "):
        q = m[7:].strip()
        try:
            mm = _memory_manager()
            results = mm.search_experiences(q, limit=10)
            mm.close()
            if not results:
                return {"reply": f"NO MEMORY RESULTS FOR: {q}"}
            lines = [f"  [{r.get('result','')}][{r.get('tool','')}] {str(r.get('observation',''))[:80]}" for r in results]
            return {"reply": f"MEMORY SEARCH: {q}\n" + "\n".join(lines)}
        except Exception as e:
            return {"reply": f"ERROR: {e}"}

    if ml.startswith("knowledge "):
        q = m[10:].strip()
        try:
            kb = _knowledge()
            results = kb.search(q, limit=10)
            if not results:
                return {"reply": f"NO KNOWLEDGE RESULTS FOR: {q}"}
            lines = [f"  [{r.get('category','')}] {r.get('title','')}" for r in results]
            return {"reply": f"KNOWLEDGE SEARCH: {q}\n" + "\n".join(lines)}
        except Exception as e:
            return {"reply": f"ERROR: {e}"}

    if ml.startswith("engage "):
        target_id = m[7:].strip()
        try:
            target = _policy().get_target(target_id)
            if not target:
                return {"reply": f"UNKNOWN TARGET: {target_id}"}
            if not target.get("allowed"):
                return {"reply": f"SCOPE BLOCKED — target {target_id} is not authorized."}
            holder["active_engagement"] = target
            return {"reply": f"ENGAGEMENT ACTIVE: {target_id} ({target.get('host')}:{target.get('port')})"}
        except Exception as e:
            return {"reply": f"ERROR: {e}"}

    if ml == "clear":
        return {"reply": "", "clear": True}

    if ml.startswith("simulate ") or ml.startswith("sim "):
        objective = m.split(" ", 1)[1].strip()
        holder["pending_sim"] = objective
        return {"reply": "DISPATCH — CERBERUS agents engaging. Watch the LIVE EVENTS feed.", "simulate": objective}

    return {"reply": "UNRECOGNIZED. Type 'help' for the command list."}


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
def create_app():
    """Create the CERBERUS Command Center application."""
    try:
        from fastapi import FastAPI, HTTPException, Request
        from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, Response
        from fastapi.staticfiles import StaticFiles
    except ImportError:
        logger.warning("fastapi/uvicorn not installed - install with: pip install -e '.[api]'")
        return None

    app = FastAPI(title="CERBERUS Command Center", version="2.0.0")
    holder: Dict[str, Any] = {"orchestrator": None, "active_engagement": None}
    _seed_approvals()

    @app.get("/", response_class=HTMLResponse)
    async def index():
        file = STATIC_DIR / "index.html"
        if file.exists():
            return HTMLResponse(file.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>CERBERUS</h1><p>UI not found</p>")

    @app.get("/favicon.ico")
    async def favicon():
        icon = STATIC_DIR / "favicon.ico"
        if icon.exists():
            return Response(content=icon.read_bytes(), media_type="image/svg+xml")
        return Response(status_code=404)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # ------------------------------------------------------------------ shell
    @app.get("/api/shell")
    async def shell():
        """Top-bar state: system status, AI mode, model, active engagement."""
        try:
            from cyberai import CyberAIOrchestrator
            orch = CyberAIOrchestrator(simulate=True, local_only=True)
            status = orch.get_status()
            orch.close()
            ollama = "ONLINE" if _port_open(11434) else "OFFLINE"
            system = "ONLINE"
        except Exception:
            status = {}
            ollama = "UNKNOWN"
            system = "DEGRADED"
        active = holder.get("active_engagement") or {}
        return {
            "system": system,
            "ai_mode": status.get("phase", "MONITORING") if isinstance(status, dict) else "MONITORING",
            "ai_status": "ONLINE" if system == "ONLINE" else "DEGRADED",
            "model": (status.get("models") or [{}])[0].get("alias", "local-reasoner") if isinstance(status, dict) else "local-reasoner",
            "session": status.get("orchestrator", {}).get("sessions", 0) if isinstance(status, dict) else 0,
            "engagement": {
                "id": active.get("id", "none"),
                "authorized": bool(active.get("allowed")),
                "host": active.get("host", ""),
                "port": active.get("port", ""),
            } if active else {"id": "none", "authorized": False},
            "ollama": ollama,
            "clock": _now_hm(),
        }

    # ------------------------------------------------------------- bootstrap
    @app.get("/api/bootstrap")
    async def bootstrap():
        data: Dict[str, Any] = {
            "platform": "CERBERUS",
            "version": "2.0.0",
            "agents": [
                {"name": "planner", "role": "Mission planning", "icon": "PL"},
                {"name": "researcher", "role": "Threat intelligence", "icon": "RS"},
                {"name": "recon", "role": "Network discovery", "icon": "RN"},
                {"name": "analyst", "role": "Pattern analysis", "icon": "AN"},
                {"name": "coder", "role": "Exploit / PoC code", "icon": "CD"},
                {"name": "verifier", "role": "Evidence validation", "icon": "VR"},
                {"name": "reporter", "role": "Report generation", "icon": "RP"},
            ],
        }
        try:
            data["targets"] = _policy().list_authorized_targets()
        except Exception:
            data["targets"] = []
        try:
            data["tools"] = _tools().list_tools()
        except Exception:
            data["tools"] = []
        try:
            data["models"] = _gateway().list_registry()
        except Exception:
            data["models"] = []
        try:
            store = _memory_store()
            data["memory"] = store.get_stats()
            store.close()
        except Exception:
            data["memory"] = {"total": 0, "by_type": {}}
        try:
            mm = _memory_manager()
            data["findings"] = mm.get_findings()[:50]
            mm.close()
        except Exception:
            data["findings"] = []
        return data

    # ------------------------------------------------------------- realtime
    @app.get("/api/realtime")
    async def realtime(request: Request):
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
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
        )

    # ---------------------------------------------------------------- tasks
    @app.post("/api/tasks")
    async def start_task(request: Request):
        body = await request.json()
        objective = body.get("objective", "").strip()
        target_id = body.get("target_id") or None
        simulate = bool(body.get("simulate", True))
        dry_run = bool(body.get("dry_run", False))
        if not objective:
            raise HTTPException(status_code=400, detail="objective is required")

        async def runner():
            from cyberai import CyberAIOrchestrator
            orch = CyberAIOrchestrator(simulate=simulate, dry_run=dry_run, local_only=True)
            holder["orchestrator"] = orch
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
                EVENT_BUS.publish("audit", {
                    "actor": "CERBERUS", "agent": "orchestrator", "tool": "master",
                    "target": target_id or "-", "action": "task run",
                    "result": "SUCCESS", "session": result.get("id", ""),
                })
            except PermissionError as e:
                EVENT_BUS.publish("task_error", {"error": str(e)})
                EVENT_BUS.publish("policy.blocked", {
                    "reason": str(e),
                    "policy": "LAB_ONLY",
                    "action": "task run",
                    "target": target_id or "-",
                    "human_readable": (
                        f"Target '{target_id or 'unspecified'}' is not authorized "
                        "for active testing. Register it in lab/targets/targets.yaml "
                        "with allowed: true, or run in simulate mode."
                    ),
                })
                EVENT_BUS.publish("audit", {"actor": "CERBERUS", "agent": "-", "tool": "policy",
                                            "target": target_id or "-", "action": "task run",
                                            "result": "BLOCKED", "session": "-"})
            except Exception as e:
                EVENT_BUS.publish("task_error", {"error": str(e)})
            finally:
                orch.close()
                holder["orchestrator"] = None

        asyncio.create_task(runner())
        return {"status": "accepted", "objective": objective, "simulate": simulate}

    # ---------------------------------------------------------- tasks/stop
    @app.post("/api/tasks/stop")
    async def stop_task():
        """Request cooperative cancellation of the running task.

        Takes effect at the next pipeline step boundary (an in-flight agent
        call finishes). Returns 200 even when nothing is running so the UI
        STOP button never errors.
        """
        orch = holder.get("orchestrator")
        if orch is None:
            return {"status": "no_active_task"}
        try:
            orch.stop()
            EVENT_BUS.publish("audit", {
                "actor": "OPERATOR", "agent": "-", "tool": "console",
                "target": "-", "action": "stop task", "result": "ISSUED",
                "session": "-",
            })
            return {"status": "stop_requested"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    # -------------------------------------------------------------- command
    @app.post("/api/command")
    async def command(request: Request):
        body = await request.json()
        # Accept both the documented "message" key and the "command" key the
        # SPA console sends (contract fix — see git history, BUG-1).
        message = str(body.get("message") or body.get("command") or "").strip()
        if not message:
            raise HTTPException(status_code=400, detail="message is required")
        EVENT_BUS.publish("audit", {"actor": "OPERATOR", "agent": "-", "tool": "console",
                                   "target": "-", "action": message[:120], "result": "ISSUED",
                                   "session": "-"})
        result = _command_response(message, holder)
        sim = result.pop("simulate", None)
        if sim:
            from cyberai import CyberAIOrchestrator

            async def sim_runner():
                orch = CyberAIOrchestrator(simulate=True, local_only=True)
                holder["orchestrator"] = orch
                try:
                    await orch.run(
                        sim,
                        target_id=(holder.get("active_engagement") or {}).get("id") or "lab-web-01",
                        event_callback=lambda etype, edata: EVENT_BUS.publish(etype, edata),
                    )
                except Exception as e:
                    EVENT_BUS.publish("task_error", {"error": str(e)})
                finally:
                    orch.close()
                    holder["orchestrator"] = None
            asyncio.create_task(sim_runner())
        return result

    # --------------------------------------------------------------- status
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

    # -------------------------------------------------------------- context
    @app.get("/api/context")
    async def ai_context():
        ctx: Dict[str, Any] = {"generated_at": time.time()}
        try:
            from cyberai.evolution.engine import EvolutionEngine
            ctx["evolution"] = EvolutionEngine(simulate=True).get_status()
        except Exception as e:
            ctx["evolution"] = {"error": str(e)}
        try:
            ctx["capabilities"] = _capabilities().to_dict()
        except Exception as e:
            ctx["capabilities"] = {"error": str(e)}
        try:
            tracker = _tracker()
            ctx["performance"] = {
                "models": tracker.get_all_stats("model"),
                "agents": tracker.get_all_stats("agent"),
                "tools": tracker.get_all_stats("tool"),
            }
            tracker.close()
        except Exception as e:
            ctx["performance"] = {"error": str(e)}
        try:
            mm = _memory_manager()
            ctx["sessions"] = mm.list_sessions()
            mm.close()
        except Exception:
            ctx["sessions"] = []
        try:
            ctx["llm_health"] = await _gateway().health_check()
        except Exception as e:
            ctx["llm_health"] = {"error": str(e)}

        # ---- Flat KPI mirrors (additive) --------------------------------
        # The SPA's loadContext() reads these flat fields (see
        # git history, BUG-3). Nested fields above stay for
        # any other consumers.
        try:
            sessions = ctx.get("sessions") or []
            ctx["total_sessions"] = len(sessions)
        except Exception:
            ctx["total_sessions"] = 0
        try:
            mm = _memory_manager()
            findings = mm.get_findings()
            mm.close()
            ctx["total_findings"] = len(findings)
        except Exception:
            ctx["total_findings"] = 0
        try:
            store = _memory_store()
            stats = store.get_stats()
            store.close()
            ctx["total_memories"] = stats.get("total", 0)
        except Exception:
            ctx["total_memories"] = 0
        try:
            ctx["total_tools"] = len(_tools().to_dict().get("tools", {}))
        except Exception:
            ctx["total_tools"] = 0
        try:
            ctx["total_models"] = len(_gateway().list_registry())
        except Exception:
            ctx["total_models"] = 0
        try:
            ctx["total_capabilities"] = len(ctx.get("capabilities", {}).get("tools", {}))
        except Exception:
            ctx["total_capabilities"] = 0
        try:
            ctx["capability_routing"] = ctx.get("performance", {}).get("tools", {})
        except Exception:
            ctx["capability_routing"] = {}
        try:
            ctx["agent_performance"] = ctx.get("performance", {}).get("agents", {})
        except Exception:
            ctx["agent_performance"] = {}
        return ctx

    # ---------------------------------------------------------- engagements
    @app.get("/api/engagements")
    async def engagements():
        try:
            targets = _policy().list_targets()
        except Exception:
            targets = []
        return {"engagements": targets}

    # ------------------------------------------------------- attack surface
    @app.get("/api/attack-surface")
    async def attack_surface():
        """Derive a network graph from the authorized scope. Deterministic."""
        try:
            targets = _policy().list_authorized_targets()
        except Exception:
            targets = []
        nodes = []
        edges = []
        for i, t in enumerate(targets):
            ttype = "cloud"
            port = t.get("port", 0)
            proto = t.get("protocol", "http")
            if proto == "http":
                ttype = "web"
            elif port in (3306, 5432, 1433, 27017):
                ttype = "database"
            elif port == 22:
                ttype = "workstation"
            elif port == 53:
                ttype = "network"
            node_id = f"n{i}"
            nodes.append({
                "id": node_id,
                "label": t.get("id", f"target-{i}"),
                "kind": ttype,
                "host": t.get("host", ""),
                "port": port,
                "protocol": proto,
                "status": "normal",
            })
            edges.append({"from": "scope", "to": node_id})
        nodes.insert(0, {"id": "scope", "label": "SCOPE", "kind": "core", "status": "core"})
        return {"nodes": nodes, "edges": edges}

    # ------------------------------------------------------------- evidence
    @app.get("/api/evidence")
    async def evidence():
        try:
            evm = _evidence()
            items = []
            for f in (evm.evidence_dir).glob("*.json"):
                try:
                    items.append(json.loads(f.read_text()))
                except Exception:
                    continue
            return {"evidence": sorted(items, key=lambda x: x.get("timestamp", ""), reverse=True)[:200]}
        except Exception as e:
            return {"evidence": [], "error": str(e)}

    # ------------------------------------------------------------ knowledge
    @app.get("/api/knowledge")
    async def knowledge(q: str = ""):
        try:
            kb = _knowledge()
            if q.strip():
                results = kb.search(q.strip(), limit=50)
            else:
                results = []
            summary = kb.get_summary()
            return {"results": results, "summary": summary}
        except Exception as e:
            return {"results": [], "summary": {}, "error": str(e)}

    # ----------------------------------------------------------- memory/search
    @app.get("/api/memory/search")
    async def memory_search(q: str = "", limit: int = 20):
        if not q.strip():
            store = _memory_store()
            stats = store.get_stats()
            store.close()
            return {"results": [], "stats": stats}
        try:
            # Semantic (TF-IDF) search first — falls back to keyword
            # search internally when nothing is similar enough.
            store = _memory_store()
            results = store.semantic_search(q.strip(), limit=limit)
            store.close()
            stats_store = _memory_store()
            stats = stats_store.get_stats()
            stats_store.close()
            return {"results": results, "stats": stats}
        except Exception as e:
            return {"results": [], "stats": {}, "error": str(e)}

    # --------------------------------------------------------------- models
    @app.get("/api/models")
    async def models():
        try:
            await _gateway()  # ensure importable
        except Exception:
            pass
        try:
            models_list = _gateway().list_registry()
            return {"models": models_list}
        except Exception as e:
            return {"models": [], "error": str(e)}

    # ------------------------------------------------------------ hardware
    @app.get("/api/hardware")
    async def hardware():
        """System Capability page (spec §10): CPU/RAM/GPU + execution profile."""
        try:
            from cyberai.llm_gateway.hardware import detect_hardware, format_report
            hw = detect_hardware()
            return {
                "hardware": hw.as_dict(),
                "report": format_report(hw),
                "profile": hw.profile,
            }
        except Exception as e:
            return {"hardware": None, "report": "", "profile": "unknown",
                    "error": str(e)}

    # ---------------------------------------------------------------- tools
    @app.get("/api/tools")
    async def tools():
        try:
            tr = _tools()
            registry = tr.to_dict().get("tools", {})
            am = _adapters()
            discovered = am.discover()
            out = []
            for name, info in registry.items():
                health = {"status": "NOT_TESTED"}
                try:
                    health = await am.health_check(name)
                except Exception:
                    pass
                out.append({
                    "name": name,
                    "registry": info,
                    "present": name in discovered,
                    "health": health.get("status", "NOT_TESTED"),
                })
            return {"tools": sorted(out, key=lambda x: x["name"])}
        except Exception as e:
            return {"tools": [], "error": str(e)}

    # --------------------------------------------------------------- agents
    @app.get("/api/agents")
    async def agents():
        base = [
            {"name": "planner", "role": "Mission planning", "capability": "planning"},
            {"name": "researcher", "role": "Threat intelligence", "capability": "research"},
            {"name": "recon", "role": "Network discovery", "capability": "reconnaissance"},
            {"name": "analyst", "role": "Pattern analysis", "capability": "analysis"},
            {"name": "coder", "role": "Exploit / PoC code", "capability": "code_generation"},
            {"name": "verifier", "role": "Evidence validation", "capability": "verification"},
            {"name": "reporter", "role": "Report generation", "capability": "reporting"},
        ]
        try:
            tracker = _tracker()
            stats = tracker.get_all_stats("agent")
            tracker.close()
        except Exception:
            stats = {}
        for a in base:
            ag = stats.get(a["name"], {})
            a["performances"] = ag
            a["calls"] = sum(v.get("calls", 0) for v in ag.values())
            rates = [v.get("success_rate", 0) for v in ag.values()]
            a["success_rate"] = round(sum(rates) / len(rates), 3) if rates else None
        return {"agents": base}

    # --------------------------------------------------------- system health
    @app.get("/api/system-health")
    async def system_health():
        health = []
        try:
            from cyberai import CyberAIOrchestrator
            orch = CyberAIOrchestrator(simulate=True, local_only=True)
            orch_status = "HEALTHY"
            orch.close()
        except Exception:
            orch_status = "OFFLINE"
        health.append({"name": "Orchestrator", "status": orch_status, "detail": "CyberAIOrchestrator"})
        health.append({"name": "Ollama", "status": "HEALTHY" if _port_open(11434) else "OFFLINE", "detail": "localhost:11434"})
        health.append({"name": "LLM Gateway", "status": "HEALTHY" if _port_open(4000) else "OFFLINE", "detail": "localhost:4000"})
        health.append({"name": "Web UI", "status": "HEALTHY" if _port_open(8710) else "OFFLINE", "detail": "localhost:8710"})
        try:
            mm = _memory_manager()
            tables = mm._conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
            mm.close()
            health.append({"name": "Memory DB", "status": "HEALTHY", "detail": f"{tables} tables"})
        except Exception:
            health.append({"name": "Memory DB", "status": "OFFLINE", "detail": "unavailable"})
        try:
            tracker = _tracker()
            records = tracker._conn.execute("SELECT count(*) FROM performance").fetchone()[0]
            tracker.close()
            health.append({"name": "Meta-Learning", "status": "HEALTHY", "detail": f"{records} records"})
        except Exception:
            health.append({"name": "Meta-Learning", "status": "OFFLINE", "detail": "unavailable"})
        try:
            am = _adapters()
            discovered = am.discover()
            health.append({"name": "Adapters", "status": "DEGRADED" if not discovered else "HEALTHY",
                           "detail": f"{len(discovered)} present"})
        except Exception:
            health.append({"name": "Adapters", "status": "OFFLINE", "detail": "unavailable"})
        health.append({"name": "Docker", "status": "HEALTHY" if _docker_available() else "OFFLINE",
                       "detail": "daemon required for 10 adapters"})
        return {"components": health}

    # ---------------------------------------------------------------- audit
    @app.get("/api/audit")
    async def audit(q: str = "", actor: str = ""):
        entries = []
        # Live bus history (real orchestrator events)
        for ev in EVENT_BUS.history(300):
            if ev["type"] == "audit":
                entries.append({"timestamp": _now_iso(), **ev["data"]})
        # Session log files
        entries.extend(_read_session_logs())
        # Seed with demo entries if nothing real exists
        if not entries:
            now = _now_hm()
            entries = [
                {"timestamp": f"{now}", "actor": "CERBERUS", "agent": "recon", "tool": "strix",
                 "target": "lab-web-01", "action": "service discovery", "result": "SUCCESS", "session": "-", "demo": True},
                {"timestamp": f"{now}", "actor": "CERBERUS", "agent": "analyst", "tool": "cai",
                 "target": "lab-web-01", "action": "correlate findings", "result": "SUCCESS", "session": "-", "demo": True},
                {"timestamp": f"{now}", "actor": "OPERATOR", "agent": "-", "tool": "console",
                 "target": "-", "action": "viewed audit log", "result": "SUCCESS", "session": "-", "demo": True},
            ]
        if q:
            ql = q.lower()
            entries = [e for e in entries if ql in json.dumps(e, default=str).lower()]
        if actor:
            entries = [e for e in entries if e.get("actor", "").lower() == actor.lower()]
        return {"entries": entries[:300]}

    # --------------------------------------------------------------- threat
    @app.get("/api/threat")
    async def threat():
        try:
            mm = _memory_manager()
            findings = mm.get_findings()
            mm.close()
        except Exception:
            findings = []
        score = min(12 + len(findings) * 9, 92)
        severity = "LOW"
        if score >= 70:
            severity = "CRITICAL"
        elif score >= 45:
            severity = "HIGH"
        elif score >= 20:
            severity = "MEDIUM"
        events = [
            {"time": _now_hm(), "severity": "LOW", "source": "Endpoint", "type": "Process",
             "description": "New process started on WORKSTATION-042", "status": "Monitored"},
            {"time": _now_hm(), "severity": "MEDIUM", "source": "Network", "type": "Connection",
             "description": "Unexpected outbound connection to 10.0.0.7", "status": "Investigating"},
            {"time": _now_hm(), "severity": "HIGH", "source": "Authentication", "type": "Auth",
             "description": "Multiple failed login attempts detected", "status": "Analyzing"},
            {"time": _now_hm(), "severity": "INFO", "source": "System", "type": "Health",
             "description": "Platform health check completed", "status": "Monitored"},
        ]
        history = [max(5, score - 20 + i * 4) for i in range(8)]
        return {
            "score": score,
            "severity": severity,
            "alerts": {"critical": findings and 1 or 0, "high": 1, "medium": 1, "low": 2},
            "history": history,
            "events": events,
        }

    # ------------------------------------------------------ decision chain
    @app.get("/api/decision-chain")
    async def decision_chain():
        """CERBERUS signature: DETECT → CORRELATE → ASSESS → POLICY → RECOMMEND → APPROVAL."""
        real = [e for e in EVENT_BUS.history(500) if e["type"] in ("task_completed", "task_started", "plan_ready")]
        if real:
            steps = [
                {"stage": "DETECT", "detail": "Authorized scope + objective received from operator",
                 "status": "COMPLETE"},
                {"stage": "CORRELATE", "detail": "Memory retrieval + capability routing", "status": "COMPLETE"},
                {"stage": "ASSESS", "detail": "7 agents engaged on: " + str(real[-1].get("data", {}).get("objective", ""))[:90],
                 "status": "COMPLETE"},
                {"stage": "POLICY CHECK", "detail": "Target authorization + allowed actions enforced by PolicyEngine",
                 "status": "COMPLETE"},
                {"stage": "RECOMMEND", "detail": "Findings verified; report generated", "status": "COMPLETE"},
                {"stage": "APPROVAL", "detail": "Operator reviews in Command Center", "status": "AWAITING"},
            ]
        else:
            steps = [
                {"stage": "DETECT", "detail": "37 failed authentication attempts from same source within 90s", "status": "COMPLETE"},
                {"stage": "CORRELATE", "detail": "Same source + 3 accounts + credential-stuffing signature", "status": "COMPLETE"},
                {"stage": "ASSESS", "detail": "Classification: credential attack · Confidence: 94%", "status": "COMPLETE"},
                {"stage": "POLICY CHECK", "detail": "Endpoint isolation requires human approval (HIGH risk)", "status": "COMPLETE"},
                {"stage": "RECOMMEND", "detail": "Temporarily isolate WORKSTATION-042", "status": "COMPLETE"},
                {"stage": "APPROVAL", "detail": "Awaiting operator decision in approval queue", "status": "AWAITING"},
            ]
        return {"chain": steps}

    # ------------------------------------------------------------ approvals
    @app.get("/api/approvals")
    async def approvals():
        return {"queue": APPROVAL_QUEUE}

    @app.post("/api/approvals/{approval_id}")
    async def decide_approval(approval_id: str, request: Request):
        body = await request.json()
        decision = str(body.get("decision", "")).upper()
        if decision not in ("APPROVE", "DENY"):
            raise HTTPException(status_code=400, detail="decision must be APPROVE or DENY")
        for item in APPROVAL_QUEUE:
            if item["id"] == approval_id:
                item["status"] = decision
                item["decided_at"] = _now_iso()
                EVENT_BUS.publish("audit", {
                    "actor": "OPERATOR", "agent": "-", "tool": "approval",
                    "target": item.get("action", approval_id), "action": decision.lower(),
                    "result": "SUCCESS", "session": "-",
                })
                EVENT_BUS.publish("notification", {"severity": "INFO", "title": f"Action {decision}",
                                                   "detail": item.get("action", "")})
                return {"ok": True, "item": item}
        raise HTTPException(status_code=404, detail="approval not found")

    # --------------------------------------------------------- notifications
    @app.get("/api/notifications")
    async def notifications():
        notes = []
        for ev in EVENT_BUS.history(100):
            if ev["type"] in ("task_error", "notification", "task_completed"):
                notes.append({"type": ev["type"], "data": ev["data"], "ts": ev["ts"]})
        # Always surface pending approvals as critical notifications
        pending = [a for a in APPROVAL_QUEUE if a.get("status") == "PENDING"]
        if pending:
            notes.insert(0, {"type": "approval", "data": {"count": len(pending),
                          "detail": "High-risk action awaiting operator approval"}, "ts": time.time()})
        return {"notifications": notes[:30]}

    # ------------------------------------------------------------- scorecard
    @app.get("/api/scorecard")
    async def scorecard():
        """Platform-wide scorecard: sessions, findings, targets, tools, perf."""
        out: Dict[str, Any] = {"generated_at": _now_iso()}
        try:
            mm = _memory_manager()
            sessions = mm.list_sessions()
            findings = mm.get_findings()
            mm.close()
            by_status: Dict[str, int] = {}
            for f in findings:
                st = f.get("status", "UNKNOWN")
                by_status[st] = by_status.get(st, 0) + 1
            out["sessions"] = {
                "total": len(sessions),
                "completed": sum(1 for s in sessions if s.get("status") == "completed"),
                "active": sum(1 for s in sessions if s.get("status") == "active"),
            }
            out["findings"] = {"total": len(findings), "by_status": by_status}
        except Exception as e:
            out["sessions"] = {"error": str(e)}
            out["findings"] = {"error": str(e)}
        try:
            pe = _policy()
            targets = pe.list_targets()
            pe.close()
            out["targets"] = {
                "total": len(targets),
                "authorized": sum(1 for t in targets if t.get("allowed")),
            }
        except Exception as e:
            out["targets"] = {"error": str(e)}
        try:
            out["tools"] = {"total": len(_tools().list_tools())}
        except Exception as e:
            out["tools"] = {"error": str(e)}
        try:
            tracker = _tracker()
            out["performance"] = {
                "models": len(tracker.get_all_stats("model")),
                "agents": len(tracker.get_all_stats("agent")),
                "tools": len(tracker.get_all_stats("tool")),
            }
            tracker.close()
        except Exception as e:
            out["performance"] = {"error": str(e)}

        # ---- Flat mirrors (additive) ------------------------------------
        # The SPA's loadScorecard() reads these flat fields (see
        # git history, BUG-4). Nested fields above stay.
        try:
            out["total_sessions"] = out["sessions"].get("total", 0)
            out["total_findings"] = out["findings"].get("total", 0)
            out["verified_findings"] = out["findings"].get("by_status", {}).get("VERIFIED", 0)
        except Exception:
            out["total_sessions"] = 0
            out["total_findings"] = 0
            out["verified_findings"] = 0
        try:
            tracker = _tracker()
            tool_stats = tracker.get_all_stats("tool")
            tracker.close()
            calls = sum(v.get("calls", 0) for v in tool_stats.values())
            successes = sum(v.get("successes", 0) for v in tool_stats.values())
            out["total_tool_calls"] = calls
            out["success_rate"] = round(successes / calls, 4) if calls else 0.0
        except Exception:
            out["total_tool_calls"] = 0
            out["success_rate"] = 0.0
        try:
            import time as _time
            out["uptime"] = round(_time.time() - _SERVER_START, 1)
        except Exception:
            out["uptime"] = 0.0
        return out

    # ----------------------------------------------------------------- mcp
    @app.get("/api/mcp")
    async def mcp_overview():
        """MCP gateway overview: servers discovered + configured."""
        try:
            import importlib
            mod = importlib.import_module("cyberai.tool-gateway.mcp.mcp_server")
            gw = mod.MCPGateway()
            discovered = gw.discover_mcp_servers()
            return {
                "servers": [
                    {
                        "name": s.get("name"),
                        "type": s.get("type"),
                        "capabilities": s.get("capabilities", []),
                        "cwd": s.get("cwd"),
                    }
                    for s in discovered
                ],
                "configured": list(gw._servers.keys()),
                "tools": gw.list_tools(),
            }
        except Exception as e:
            return {"servers": [], "configured": [], "tools": [], "error": str(e)}

    @app.post("/api/mcp/call")
    async def mcp_call(request: Request):
        """Invoke a tool on an MCP server (structured error envelope)."""
        body = await request.json()
        server = str(body.get("server", "")).strip()
        tool = str(body.get("tool", "")).strip()
        arguments = body.get("arguments") or {}
        if not server or not tool:
            raise HTTPException(status_code=400, detail="server and tool are required")
        try:
            import importlib
            mod = importlib.import_module("cyberai.tool-gateway.mcp.mcp_server")
            gw = mod.MCPGateway()
            result = await gw.call_tool(server, tool, arguments)
            EVENT_BUS.publish("audit", {
                "actor": "OPERATOR", "agent": "-", "tool": f"mcp:{server}/{tool}",
                "target": str(arguments.get("target", "-")), "action": f"mcp call {tool}",
                "result": result.get("status", "?"), "session": "-",
            })
            return result
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    # ------------------------------------------------------------- timeline
    @app.get("/api/timeline")
    async def timeline(limit: int = 100):
        """Unified timeline: sessions + findings + audit events, newest first."""
        events: List[Dict[str, Any]] = []
        try:
            mm = _memory_manager()
            for s in mm.list_sessions()[:limit]:
                events.append({
                    "kind": "session",
                    "ts": s.get("started_at", ""),
                    "title": f"Session on {s.get('target_id', '?')}",
                    "detail": s.get("summary") or f"status={s.get('status', '?')}",
                    "id": s.get("id", ""),
                })
            for f in mm.get_findings()[:limit]:
                events.append({
                    "kind": "finding",
                    "ts": f.get("timestamp", ""),
                    "title": str(f.get("observation", ""))[:120],
                    "detail": f"status={f.get('status', '?')} confidence={f.get('confidence', 0):.2f}",
                    "id": f.get("id", ""),
                })
            mm.close()
        except Exception:
            pass
        for ev in EVENT_BUS.history(limit):
            etype = ev["type"]
            d = ev.get("data", {})
            if etype == "audit":
                events.append({
                    "kind": "audit",
                    "ts": _now_iso(),
                    "title": f"{d.get('action', '')} → {d.get('result', '')}",
                    "detail": f"actor={d.get('actor', '')} tool={d.get('tool', '')}",
                    "id": "",
                })
            elif etype in ("task_result", "task_completed"):
                events.append({
                    "kind": "task",
                    "ts": _now_iso(),
                    "title": f"Hunt finished: {d.get('status', d.get('findings_count', '?'))}",
                    "detail": f"findings={d.get('findings_count', '?')} objective={str(d.get('summary', d.get('objective', '')))[:80]}",
                    "id": str(d.get("task_id", "")),
                })
            elif etype == "task_error":
                events.append({
                    "kind": "error",
                    "ts": _now_iso(),
                    "title": "Hunt failed",
                    "detail": str(d.get("error", ""))[:160],
                    "id": "",
                })
        events.sort(key=lambda e: e.get("ts", ""), reverse=True)
        return {"events": events[:limit]}

    # ---------------------------------------------------------- hunt launch
    @app.post("/api/hunt")
    async def hunt(request: Request):
        """Launch a guided hunt (policy-checked) against an authorized target."""
        body = await request.json()
        target_id = str(body.get("target_id", "")).strip()
        objective = str(body.get("objective", "")).strip() or "Full reconnaissance and enumeration"
        simulate = bool(body.get("simulate", True))
        if not target_id:
            raise HTTPException(status_code=400, detail="target_id is required")
        try:
            target = _policy().get_target(target_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        if not target:
            raise HTTPException(status_code=404, detail=f"unknown target: {target_id}")
        if not target.get("allowed"):
            raise HTTPException(status_code=403, detail=f"target not authorized: {target_id}")

        async def runner():
            from cyberai import CyberAIOrchestrator
            orch = CyberAIOrchestrator(simulate=simulate, local_only=True)
            holder["orchestrator"] = orch
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
            except Exception as e:
                EVENT_BUS.publish("task_error", {"error": str(e)})
            finally:
                orch.close()
                holder["orchestrator"] = None

        asyncio.create_task(runner())
        return {"status": "accepted", "target_id": target_id, "objective": objective, "simulate": simulate}

    # ------------------------------------------------------ kill-chain panel
    @app.get("/api/killchain")
    async def killchain(target: str = ""):
        """F2T2EA kill-chain status (all chains, or one target)."""
        try:
            from cyberai.orchestrator.workflows.kill_chain import KillChainEngine
            engine = KillChainEngine()
            if target.strip():
                chain = engine.get_chain(target.strip())
                if not chain:
                    return {"chain": None, "status": engine.status()}
                return {"chain": chain.to_dict(), "status": engine.status()}
            return {"chains": engine.list_chains(), "status": engine.status()}
        except Exception as e:
            return {"chains": [], "status": {}, "error": str(e)}

    @app.post("/api/killchain/start")
    async def killchain_start(request: Request):
        body = await request.json()
        target = str(body.get("target", "")).strip()
        if not target:
            raise HTTPException(status_code=400, detail="target is required")
        try:
            from cyberai.orchestrator.workflows.kill_chain import KillChainEngine
            engine = KillChainEngine()
            chain = engine.start_chain(target)
            return {"chain": chain.to_dict()}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/killchain/advance")
    async def killchain_advance(request: Request):
        body = await request.json()
        target = str(body.get("target", "")).strip()
        note = str(body.get("note", "")).strip()
        finding = body.get("finding") or None
        if not target:
            raise HTTPException(status_code=400, detail="target is required")
        try:
            from cyberai.orchestrator.workflows.kill_chain import KillChainEngine
            engine = KillChainEngine()
            result = engine.advance(target, note=note, finding=finding)
            return {"chain": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/killchain/fail")
    async def killchain_fail(request: Request):
        body = await request.json()
        target = str(body.get("target", "")).strip()
        reason = str(body.get("reason", "")).strip() or "manual fail"
        category = str(body.get("category", "execution")).strip() or "execution"
        if not target:
            raise HTTPException(status_code=400, detail="target is required")
        try:
            from cyberai.orchestrator.workflows.kill_chain import KillChainEngine
            engine = KillChainEngine()
            result = engine.fail(target, reason=reason, category=category)
            return {"chain": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ------------------------------------------------------ wargame panel
    @app.get("/api/wargame")
    async def wargame():
        """Ghost-wargaming failure analytics."""
        try:
            from cyberai.evolution import GhostWargame
            gw = GhostWargame()
            analytics = gw.analytics()
            recent = gw.recent_failures(limit=10)
            return {"analytics": analytics, "recent_failures": recent}
        except Exception as e:
            return {"analytics": {}, "recent_failures": [], "error": str(e)}

    @app.post("/api/wargame/fast-forward")
    async def wargame_fast_forward(request: Request):
        """Run a simulated evolution generation (no live execution)."""
        body = await request.json()
        task_type = str(body.get("task_type", "vulnerability_research")).strip()
        num_strategies = int(body.get("num_strategies", 3))
        try:
            from cyberai.evolution import GhostWargame
            gw = GhostWargame()
            result = await gw.fast_forward(task_type, num_strategies=num_strategies)
            return {"result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ------------------------------------------- semantic memory search
    @app.get("/api/memory/semantic")
    async def memory_semantic(q: str = "", limit: int = 10, type: str = ""):
        """TF-IDF semantic memory search."""
        if not q.strip():
            return {"results": []}
        try:
            store = _memory_store()
            results = store.semantic_search(
                q.strip(),
                memory_type=(type.strip() or None),
                limit=limit,
            )
            store.close()
            return {"results": results}
        except Exception as e:
            return {"results": [], "error": str(e)}

    # =====================================================================
    # NEW ENDPOINTS — product redesign (spec §24/§25)
    # Additive only: every endpoint above is unchanged.
    # =====================================================================

    # ------------------------------------------------ sessions (spec §8)
    @app.get("/api/sessions")
    async def sessions(q: str = "", status: str = "", limit: int = 100):
        """Session browser: search, filter by status, newest first."""
        try:
            mm = _memory_manager()
            rows = mm.list_sessions()
            mm.close()
        except Exception as e:
            return {"sessions": [], "error": str(e)}
        if q:
            ql = q.lower()
            rows = [s for s in rows
                    if ql in (s.get("objective") or "").lower()
                    or ql in (s.get("target_id") or "").lower()
                    or ql in (s.get("id") or "").lower()]
        if status:
            rows = [s for s in rows if s.get("status") == status]
        return {"sessions": rows[:limit], "total": len(rows)}

    @app.get("/api/sessions/{session_id}")
    async def session_detail(session_id: str):
        """Session detail: metadata + findings + replay timeline."""
        try:
            mm = _memory_manager()
            s = mm.get_session(session_id)
            if not s:
                mm.close()
                raise HTTPException(status_code=404, detail="session not found")
            findings = [f for f in mm.get_findings()
                        if f.get("session_id") == session_id]
            mm.close()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        timeline = _session_timeline(session_id, s, findings)
        return {"session": s, "findings": findings, "timeline": timeline}

    # ----------------------------------------------- findings (spec §10)
    @app.get("/api/findings")
    async def findings(status: str = "", q: str = "", limit: int = 200):
        """Findings explorer: filter by verification status, search text."""
        try:
            mm = _memory_manager()
            rows = mm.get_findings(status=(status.strip() or None))
            mm.close()
        except Exception as e:
            return {"findings": [], "error": str(e)}
        if q:
            ql = q.lower()
            rows = [f for f in rows
                    if ql in str(f.get("observation", "")).lower()
                    or ql in str(f.get("source", "")).lower()]
        return {"findings": rows[:limit], "total": len(rows)}

    # ------------------------------------------------ targets (spec §12)
    @app.get("/api/targets")
    async def targets():
        """Target registry with explicit authorization + reachability state."""
        try:
            pe = _policy()
            rows = pe.list_targets()
            pe.close()
        except Exception as e:
            return {"targets": [], "error": str(e)}
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
        return {"targets": out}

    # ------------------------------------------- security center (§13)
    @app.get("/api/security")
    async def security():
        """Security center: policy state, blocked actions, approvals."""
        blocked = []
        for ev in EVENT_BUS.history(300):
            if ev.get("type") == "policy.blocked":
                blocked.append(ev.get("data", {}))
        try:
            pe = _policy()
            all_targets = pe.list_targets()
            pe.close()
            authorized = [t for t in all_targets if t.get("allowed")]
        except Exception:
            all_targets, authorized = [], []
        pending = [a for a in APPROVAL_QUEUE if a.get("status") == "PENDING"]
        return {
            "policy": {
                "mode": "LAB_ONLY",
                "description": "Active testing restricted to explicitly authorized lab targets",
                "targets_registered": len(all_targets),
                "targets_authorized": len(authorized),
            },
            "blocked_actions": blocked,
            "approvals_pending": len(pending),
            "recent_events": [
                {"type": ev.get("type"), "data": ev.get("data", {}), "ts": ev.get("ts")}
                for ev in EVENT_BUS.history(50)
                if ev.get("type") in ("policy.blocked", "approval.required",
                                      "approval.granted", "approval.denied")
            ],
        }

    # --------------------------------------- model routing (spec §7/§24)
    @app.get("/api/models/routing")
    async def model_routing():
        """Read the task-type → model-alias routing table."""
        try:
            from cyberai.orchestrator.routing.model_router import ModelRouter
            mr = ModelRouter()
            routes = mr.get_all_routes()
            return {"routes": routes}
        except Exception as e:
            return {"routes": {}, "error": str(e)}

    @app.post("/api/models/routing")
    async def update_model_routing(request: Request):
        """Update routing without editing YAML: {task_type, model_alias}."""
        body = await request.json()
        task_type = str(body.get("task_type", "")).strip()
        model_alias = str(body.get("model_alias", "")).strip()
        if not task_type or not model_alias:
            raise HTTPException(status_code=400,
                                detail="task_type and model_alias are required")
        try:
            from cyberai.orchestrator.routing.model_router import ModelRouter
            mr = ModelRouter()
            mr.update_route(task_type, model_alias)
            import yaml as _yaml
            _yaml.dump({"routes": mr.get_all_routes()})
            with open(mr.config_path, "w", encoding="utf-8") as f:
                f.write(_yaml.dump({"routes": mr.get_all_routes()},
                                   default_flow_style=False))
            EVENT_BUS.publish("audit", {
                "actor": "OPERATOR", "agent": "-", "tool": "model_router",
                "target": "-", "action": f"route {task_type} -> {model_alias}",
                "result": "SUCCESS", "session": "-",
            })
            return {"ok": True, "routes": mr.get_all_routes()}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ------------------------------------------- events feed (spec §25)
    @app.get("/api/events")
    async def events(since: str = "", limit: int = 200):
        """Pollable canonical event feed (CLI parity with the SSE stream).

        Backed by the persistent EventStore — history survives restarts.
        """
        from cyberai.orchestrator.event_store import get_event_store
        store = get_event_store()
        out = [ev.to_dict() for ev in store.history(limit=limit, since=since)]
        return {"events": out, "stats": store.stats()}

    # ------------------------------------------------ /api/v1 (spec §2)
    # New versioned surface for the redesigned frontend. Every router wraps
    # the same backend subsystems as the legacy /api routes above.
    try:
        from cyberai.ui.api import ALL_ROUTERS
        for _router in ALL_ROUTERS:
            app.include_router(_router)
        logger.info("mounted %d /api/v1 routers", len(ALL_ROUTERS))
    except Exception as e:  # noqa: BLE001
        logger.warning("could not mount /api/v1 routers: %s", e)

    return app


def _session_timeline(session_id: str, session: Dict[str, Any],
                      findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build a replay timeline (spec §9) from session + findings + logs."""
    timeline: List[Dict[str, Any]] = []
    started = session.get("started_at")
    if started:
        timeline.append({"t": started, "kind": "session.started",
                         "label": "Session started", "detail": session.get("objective", "")})
    for f in findings:
        ts = f.get("timestamp") or f.get("created_at") or started
        timeline.append({"t": ts, "kind": "finding.created",
                         "label": f"Finding: {str(f.get('observation', ''))[:60]}",
                         "detail": f"status={f.get('status', '?')} confidence={f.get('confidence', '?')}"})
    for entry in _read_session_logs():
        if entry.get("session") == session_id or entry.get("session_id") == session_id:
            timeline.append({"t": entry.get("timestamp", ""),
                             "kind": "tool.completed",
                             "label": f"{entry.get('agent', '-')} / {entry.get('tool', '-')}",
                             "detail": entry.get("action", "")})
    completed = session.get("completed_at") or session.get("ended_at")
    if completed:
        timeline.append({"t": completed, "kind": "session.completed",
                         "label": "Session completed", "detail": session.get("summary", "")})
    timeline.sort(key=lambda x: x.get("t") or "")
    return timeline


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
