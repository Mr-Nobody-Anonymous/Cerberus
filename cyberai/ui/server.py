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

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"


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
        subscriber_id = f"sub-{time.time_ns()}"
        self._subscribers[subscriber_id] = asyncio.Queue(maxsize=300)
        for event in self._history[-60:]:
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
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except Exception:
                    pass

    def history(self, limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock:
            return self._history[-limit:]


EVENT_BUS = LiveEventBus()
APPROVAL_QUEUE: List[Dict[str, Any]] = []  # in-memory approval requests


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

    # -------------------------------------------------------------- command
    @app.post("/api/command")
    async def command(request: Request):
        body = await request.json()
        message = str(body.get("message", "")).strip()
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
            mm = _memory_manager()
            results = mm.search_experiences(q.strip(), limit=limit)
            mm.close()
            store = _memory_store()
            stats = store.get_stats()
            store.close()
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
