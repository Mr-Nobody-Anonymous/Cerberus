# CERBERUS Command Deck — UI Guide

The Command Deck is the three-pane "AI Security IDE" for CERBERUS:
nav + workspace + live agent rail, with an operator console and live SSE
transcript. This guide covers launching it, every view, the console
commands, keyboard shortcuts, and the CLI companion workflow.

---

## 1. Launch

```powershell
# from the repository root (use the workspace venv)
.\_cerberus-clean-check\Scripts\python.exe -m cyberai.orchestrator.cli ui
```

- Default URL: **http://127.0.0.1:8710** (binds localhost only)
- Options: `--port 8710`, `--no-browser`
- Requires `fastapi` + `uvicorn` (already in the workspace venv)

> After editing `cyberai/ui/server.py`, **restart the server** — Python
> code is not hot-reloaded. Static `index.html` changes only need a
> browser reload.

---

## 2. Layout

| Pane | Contents |
|---|---|
| **Left nav** | Workspace (New Task, Sessions, Findings, Memory), Platform (Models, Tools, Targets, Security, Health), Operations (Kill Chain, Wargame, Timeline) |
| **Center — workspace** | Objective launcher (target select, SIMULATE toggle, RUN/STOP), stage checklist (Authorization → Context → Recon → Analysis → Verification), live transcript, operator console |
| **Right rail** | LIVE AGENTS roster (7 agents with live idle/running/done state), SECURITY summary (policy mode, blocked actions, pending approvals, active target) |
| **Status bar** | Connection state, AGENTS/MODELS/TOOLS/SESSIONS counts, Ctrl+K hint |

---

## 3. Running a task

1. Type an objective (or accept the default).
2. Pick an authorized target from the dropdown (e.g. `juice-shop`).
3. Leave **SIMULATE** checked for the no-live-traffic path (recommended —
   deterministic mock results, no infra dependencies).
4. Click **▶ RUN TASK**.
5. Watch the transcript: `task_started → plan_ready → phase: executing →
   agent_started/completed (researcher, recon, analyst, verifier, reporter)
   → phase: verifying/evolving/reporting → task_completed`.
6. The scorecard (right column) refreshes on completion; sessions/findings
   badges update.

**STOP (■):** cooperative — the in-flight agent call finishes, then the run
halts at the next step boundary and the task is marked `cancelled`.
With no active task the button reports `no_active_task` (never errors).

---

## 4. Operator console

Type into the console box at the bottom of the workspace view and press
Enter. Commands:

| Command | Effect |
|---|---|
| `help` | list all commands |
| `status` | platform status |
| `targets` | authorized lab targets |
| `tools` | tool registry |
| `models` | model registry |
| `agents` | agent roster |
| `findings` | findings from memory |
| `evidence` | evidence vault |
| `memory <query>` | search experience memory |
| `knowledge <query>` | search knowledge base |
| `engagements` | authorized engagements |
| `health` | subsystem health summary |
| `audit` | recent audit trail |
| `simulate <objective>` | dispatch a full simulated AI run |
| `engage <target-id>` | select engagement |
| `clear` | clear console output |

---

## 5. Views

- **Sessions** — browse past sessions; click one for the replay timeline.
- **Findings** — filter by status (VERIFIED / LIKELY / UNVERIFIED / REJECTED).
- **Memory** — semantic search over experience memory.
- **Models** — registry + editable capability routing (POST `/api/models/routing`).
- **Tools** — tool registry + MCP gateway status.
- **Targets** — authorization + reachability state.
- **Security** — policy mode, blocked actions, approvals queue
  (⚠ approvals are demo-seeded, marked `demo: true`).
- **Health** — subsystem health.
- **Kill Chain / Wargame / Timeline** — operations views.

---

## 6. Keyboard

- **Ctrl+K** — command palette: search sessions, findings, memory, and
  every view/command.

---

## 7. CLI companion (same data, terminal-first)

```powershell
$py = ".\_cerberus-clean-check\Scripts\python.exe"

# Global output modes (spec §14) — put the flag BEFORE the command:
& $py -m cyberai.orchestrator.cli --json agents
& $py -m cyberai.orchestrator.cli --json session list
& $py -m cyberai.orchestrator.cli --json scorecard
& $py -m cyberai.orchestrator.cli --quiet findings      # suppress output
& $py -m cyberai.orchestrator.cli --verbose models      # extra detail

# Interactive REPL with background tasks:
& $py -m cyberai.orchestrator.cli interactive --simulate
#   /task <objective>   launch in background thread
#   /stop               cooperative stop of the running task
#   /result             show last task result JSON
#   /status /help       …and 40+ more commands
```

---

## 8. API quick reference (used by the UI)

| Endpoint | Purpose |
|---|---|
| `GET /api/shell` | top-bar state |
| `GET /api/bootstrap` | nav + roster + targets |
| `GET /api/context` | workspace KPIs (flat fields: `total_sessions`, `total_findings`, `total_memories`, `total_tools`, `total_models`, `total_capabilities`, `capability_routing`, `agent_performance`) |
| `GET /api/scorecard` | flat fields: `total_sessions`, `total_findings`, `verified_findings`, `total_tool_calls`, `success_rate`, `uptime` |
| `POST /api/tasks` | launch a task `{objective, target_id, simulate, dry_run}` |
| `POST /api/tasks/stop` | cooperative stop; `{"status": "no_active_task"}` when idle |
| `POST /api/command` | console — accepts `{"command": …}` or `{"message": …}` |
| `GET /api/realtime` | SSE stream (envelope `{type, data, ts}` per event) |
| `GET /api/sessions`, `GET /api/sessions/{id}` | sessions + replay timeline |
| `GET /api/findings` | findings explorer |
| `GET /api/memory/semantic?q=` | semantic memory search |
| `GET /api/models/routing`, `POST /api/models/routing` | model routing |
| `GET /api/targets` | targets with derived state |
| `GET /api/security` | policy + approvals |
| `GET /api/system-health` | subsystem health |

Regression coverage: `tests/test_ui_api.py` (25 tests) locks the contract
of every fixed endpoint.

---

## 9. Troubleshooting

- **KPIs show 0 / `–`** — the server was restarted while the page was open:
  reload the page (SSE reconnects automatically after brief drops).
- **Console 400** — should not happen anymore (dual-key contract); if it
  does, check the server is the current `server.py` build.
- **pywin32 `ModuleNotFoundError` warnings on stderr** — harmless noise
  from the venv; ignore.
- **Nothing runs live** — Docker/Ollama/LiteLLM may be down; SIMULATE mode
  is the designed no-dependency path and exercises the full pipeline.
