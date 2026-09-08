# CERBERUS Redesign — Current-State Gap Analysis (v2)

**Date:** 2026-09-07 (supersedes `REDESIGN_AUDIT.md`, which predates implementation)
**Branch:** `phase-cd-adapters-sandbox` (uncommitted redesign work present)
**Test baseline:** 73 passed pre-fix → **98 passed post-fix** (25 new regression tests)
**Bugs found & fixed:** 9 (6 from code audit, 2 from live browser verification,
1 from CLI REPL smoke test)
**Method:** Every spec section was re-checked against the *current* code —
`cyberai/ui/server.py` (~1590 lines), `cyberai/ui/static/index.html` (~2560 lines),
`cyberai/orchestrator/cli/cli.py` (~1650 lines), `cyberai/orchestrator/events.py`,
`cyberai/orchestrator/master.py`, `cyberai/collaboration/pipeline.py`,
`cyberai/orchestrator/memory/memory_manager.py`, `cyberai/orchestrator/routing/model_router.py`.

Legend: ✅ implemented & working · 🟡 implemented but broken/partial · ❌ missing

---

## 1. What is already implemented (do NOT rebuild)

A previous session implemented the bulk of the redesign spec. The following are
**present and functional** (subject to the bug list below):

| Spec area | Where | Status |
|---|---|---|
| §3–§4 Three-pane AI Security IDE shell (nav / workspace / live rail / statusbar) | `index.html` `#app` grid | ✅ |
| §5 AI workspace: objective launcher, stage checklist, live transcript | `index.html` workspace view | ✅ |
| §6 Live agent activity via SSE (`/api/realtime`) | `server.py` `LiveEventBus` + `connectEvents()` | ✅ |
| §7 Model router UI with editable routing | `/api/models/routing` GET/POST + models view | ✅ |
| §8 Sessions browser + detail | `/api/sessions`, `/api/sessions/{id}` + sessions view | ✅ |
| §9 Session replay timeline | `_session_timeline()` + `openSession()` | ✅ |
| §10 Findings explorer with filters | `/api/findings` + findings view | ✅ |
| §11 Semantic memory search | `/api/memory/semantic` + memory view | ✅ |
| §12 Targets with authorization + reachability state | `/api/targets` (derived `state`) | ✅ |
| §13 Security center (policy mode, blocked actions, approvals) | `/api/security` + security view | 🟡 (approvals demo-seeded) |
| §14 CLI interactive REPL with `/` commands, `watch`, `replay` | `cli.py` `interactive` + 40 commands | ✅ (output modes + cp1252 fix) |
| §16 Ctrl+K command palette | `index.html` `COMMANDS` + palette | ✅ |
| §18 System health view | `/api/system-health` + health view | ✅ |
| §21 Accessibility (`prefers-reduced-motion`, `:focus-visible`) | `index.html` CSS | ✅ |
| §22 Responsive (<900px rail collapse) | `index.html` media query | ✅ |
| §24 API improvements block | `server.py` "NEW ENDPOINTS" section | ✅ |
| §25 Canonical event model | `cyberai/orchestrator/events.py` | ✅ |
| Legacy UI preserved | `index.legacy.html` | ✅ |

---

## 2. Confirmed bugs (frontend ↔ backend contract mismatches)

These were verified by cross-referencing every `fetch()` call in `index.html`
against the corresponding endpoint implementation in `server.py`.

### BUG-1: Operator console always returns 400 🔴 critical
- **Frontend** (`index.html:1322–1327`): POSTs `/api/command` with `{"command": cmd}`.
- **Backend** (`server.py:576–577`): reads `body.get("message")` → every console
  submission returns `400 "message is required"`.
- **Fix:** accept both keys server-side (`message` or `command`), keeping the
  documented `message` contract primary. Additive, backward-compatible.

### BUG-2: STOP button returns 404 🔴 critical
- **Frontend** (`index.html:1302`): POSTs `/api/tasks/stop`.
- **Backend:** endpoint does not exist. Worse, the underlying mechanism is
  missing everywhere: `CyberAIOrchestrator` has **no `stop()` method**, yet the
  CLI REPL `/stop` calls `orch.stop()` (would `AttributeError`).
- **Fix (3 layers):**
  1. `CyberAIOrchestrator.stop()` — sets a cooperative cancel flag.
  2. `AgentPipeline.run()` — checks the flag between steps (cancellation point).
  3. `POST /api/tasks/stop` — calls `holder["orchestrator"].stop()` if a run
     is active, else returns `{"status": "no_active_task"}`.

### BUG-3: Workspace KPIs render 0/undefined 🔴
- **Frontend** `loadContext()` expects flat fields: `total_sessions`,
  `total_findings`, `total_memories`, `total_tools`, `total_models`,
  `total_capabilities`, `capability_routing`, `agent_performance`.
- **Backend** `/api/context` returns nested: `{evolution, capabilities,
  performance, sessions, llm_health}` — none of the flat fields exist.
- **Fix:** extend `/api/context` to *additionally* return the flat KPI fields
  (additive; nested fields stay for any other consumers).

### BUG-4: Scorecard cells render 0/undefined 🔴
- **Frontend** `loadScorecard()` expects flat: `total_sessions`,
  `total_findings`, `verified_findings`, `total_tool_calls`, `success_rate`, `uptime`.
- **Backend** `/api/scorecard` returns nested `{sessions:{total,...},
  findings:{total,by_status}, targets, tools, performance}`.
- **Fix:** add flat mirror fields to `/api/scorecard` (additive).

### BUG-5: Agent roster icons/roles mismatch 🟡 cosmetic-but-visible
- **Frontend** `AGENT_ICONS`/`AGENT_ROLES` keys: recon, analyst, exploit,
  reporter, planner, verifier, sentinel, archivist.
- **Backend** roster (`/api/bootstrap`): planner, researcher, recon, analyst,
  coder, verifier, reporter.
- **Effect:** researcher & coder render fallback 🤖 with no role text.
- **Fix:** align the frontend maps to the real 7-agent roster.

### BUG-6: Stray `</view>` closing tag 🟢 cosmetic
- `index.html:884` — invalid HTML where `</section>` is expected; browsers
  ignore it. Fix while in the file.

### BUG-7: SSE transcript rendered `?` for every field 🔴 (found in live verification)
- **Backend** (`server.py` `event_stream`): sends `data: {"type":…, "data":…, "ts":…}`
  — the full envelope.
- **Frontend** `safeParse(e.data)` returned that envelope, but every handler
  read fields directly (`d.agent`, `d.phase`, `d.objective`) — nested one level
  too deep, so the whole transcript showed `[AGENT] ? started`, `[PHASE] ?`.
- **Fix:** `safeParse()` now unwraps `{type, data, ts}` → returns `data` when
  the envelope shape is detected. Verified live: transcript now shows
  `[AGENT] researcher started`, `[PHASE] executing`, real objectives and counts.

### BUG-8: `[PLAN] plan ready — [object Object],…` 🟡 (found in live verification)
- `plan_ready` handler concatenated the `steps` array of objects into the feed
  line instead of counting them.
- **Fix:** count `Array.isArray(d.steps) ? d.steps : d.phases` → `plan ready — 5 phases`.
  Verified live.

### BUG-9: REPL crashes on legacy Windows code pages (cp1252) 🔴 (found in CLI smoke test)
- `input(prompt)` and `click.secho` both raise `UnicodeEncodeError` on cp1252
  consoles when printing the `❯` prompt glyph — the REPL died on the very first
  read, making it **unusable on any legacy Windows console**.
- Even after the prompt was fixed, the `▶ ■ ⚠ ⏳ ⛔ ✔` glyphs in
  `_repl_task`/`_repl_stop`/`_repl_result` crashed those commands — and the
  REPL's catch-all error handler masked the fact that `/task` never launched.
- `/stop` during the orchestrator-construction race window reported
  "no running task" even though a task was starting.
- **Fix (`cyberai/orchestrator/cli/cli.py`):** `_repl_echo()` helper probes
  `sys.stdout.encoding` once and degrades all glyphs to ASCII (`▶`→`>`,
  `■`→`#`, `⚠`→`!`, …) when the code page can't represent them; all REPL
  status messages route through it. The prompt renders via
  `click.secho(..., nl=False)` with the same probe. `/stop` now distinguishes
  "task is starting" from "no running task".
- **Verified:** live REPL session — `/task` → background launch → `/result`
  (⏳ still running → ✔ full JSON result with 5 findings and a generated
  report) → second `/task` → `/stop` → `/result`. Full suite re-run after
  the fix: **98 passed**.

---

## 3. Gaps vs. spec (not yet implemented)

| Spec | Gap | Effort |
|---|---|---|
| §14 | CLI output modes: `--json`, `--quiet`, `--verbose` global flags | ✅ implemented this session (status/models/tools/agents/findings/memory/session/scorecard) |
| §15 | Approvals wired to real orchestrator gates (queue is in-memory, demo-seeded) | L — touches core; defer |
| §26 | Tests for UI API endpoints, CLI, events | ✅ `tests/test_ui_api.py` (25 tests) added this session |
| §27 | `docs/UI_GUIDE.md` usage guide | ✅ added this session |
| §20 | Virtualized lists (feed caps at 200 — acceptable) | defer |
| §17 | Toast notifications (feed + badge covers it) | defer |

**Deferred rationale:** §15 real approval gates change orchestrator control
flow (a blocking wait for human decision inside `run()`). That is a core-behavior
change requiring its own design pass; the demo queue is clearly marked and safe.
§20/§17 are polish; current implementations satisfy the spec's intent.

---

## 4. Implementation plan (this session)

Phase-by-phase per spec §28, additive only, backend untouched except:

1. **Doc:** this gap analysis (§1 mandate).
2. **Server fixes (additive):** BUG-1 (accept `command` key), BUG-2 (`/api/tasks/stop`
   + `CyberAIOrchestrator.stop()` + pipeline cancellation point), BUG-3/4 (flat
   KPI mirrors on `/api/context` + `/api/scorecard`).
3. **Frontend fixes:** BUG-5 (roster maps), BUG-6 (stray tag), BUG-7 (SSE envelope
   unwrap in `safeParse`), BUG-8 (plan phase count).
4. **CLI (§14):** `--json/--quiet/--verbose` global flags on read commands.
5. **Tests (§26):** `tests/test_ui_api.py` — 25 regression tests covering every
   fix (command dual-key, stop endpoint, flat KPI fields, cooperative cancellation).
6. **Verify:** full pytest run (98 passed), live browser verification of console,
   STOP, KPIs, roster, SSE transcript, and a full simulated hunt end-to-end;
   CLI REPL smoke test (`/task` → `/result` → `/stop`) which surfaced BUG-9
   (cp1252 crash) — fixed and re-verified live.
7. **Docs (§27):** `docs/UI_GUIDE.md`; update `INTEGRATION_STATUS.md`.

## 5. Known limitations (honest §31 disclosure)

- Stop is **cooperative**: it takes effect at the next pipeline step boundary,
  not mid-agent. An in-flight LLM call completes.
- Approvals remain demo-seeded (clearly marked `demo: true`).
- Infra (Docker/Ollama/LiteLLM) is down in this environment; all verification
  uses simulate mode, which is the designed no-dependency path.
- `--verbose` currently only adds detail on `models` and `tools`; other commands
  accept the flag but don't emit extra content yet.
- The SSE envelope fix (`safeParse` unwrap) is verified in-browser only — it is
  frontend JS and not covered by pytest.
- The REPL cp1252 fix (BUG-9) is verified live on this Windows console only;
  other terminal/encoding combinations (e.g. UTF-8 Windows Terminal, macOS,
  Linux) were not exercised — the probe degrades to ASCII only when needed.
