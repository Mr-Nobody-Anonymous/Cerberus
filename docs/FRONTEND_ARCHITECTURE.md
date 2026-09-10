# CERBERUS Frontend Architecture

The web Command Deck is a React SPA served by the FastAPI backend —
a three-pane "AI Security IDE": activity bar + chat sidebar, main view,
live agent/security rail. This document maps the frontend structure,
data flow, and the contracts it shares with the CLI and API.

---

## 1. Stack

| Layer | Choice |
|---|---|
| Framework | React 18 + TypeScript (strict) |
| Build | Vite (`npm run build` → `dist/`, served by FastAPI at `/`) |
| Styling | CSS custom properties (`--cb-*` tokens) — no CSS framework |
| State | React context + reducer (`src/stores/app.tsx`) |
| Data | Thin `fetch` wrapper (`src/lib/api.ts`) + `useFetch` hook |
| Realtime | SSE (`GET /api/realtime`) via `useLiveEvents` |

---

## 2. Layout

```
App.tsx
├── TopBar                      status + connection + Ctrl+K hint
├── ActivityBar                 view switcher (icons)
├── Split (horizontal)
│   ├── ChatList (sidebar)      chat/mission sessions, collapsible
│   └── Split (vertical)
│       ├── MainView            page router (below)
│       └── RightPanel          LIVE AGENTS + SECURITY summary
├── CommandPalette              Ctrl+K — views, sessions, findings, commands
└── Toast                       notifications
```

`MainView` routes on `state.view`:

| View | Page | Data source |
|---|---|---|
| `chat` | `ChatView` | `chatsApi` (chat store + command bus) |
| `dashboard` | `DashboardPage` | findings/missions/targets/agents/models |
| `missions` | `MissionsPage` | `missionsApi` |
| `findings` | `FindingsPage` | `findingsApi` |
| `targets` | `TargetsPage` | `targetsApi` (authorize/revoke) |
| `agents` | `AgentsPage` | `agentsApi` |
| `tools` | `ToolsPage` | `toolsApi` |
| `models` | `ModelsPage` | `modelsApi` (+ routing) |
| `security` | `SecurityPage` | `securityApi` (+ approvals) |
| `memory` | `MemoryPage` | `memoryApi` (stats + search) |
| `evidence` | `EvidencePage` | `evidenceApi` |
| `sessions` | `SessionsPage` | `sessionsApi` |
| `workspace` | `WorkspacePage` | `workspaceApi` (tree + file) |
| `events` | `EventsPage` | SSE event store |

---

## 3. Data flow

```
Component ──► useFetch(() => someApi.list()) ──► lib/api.ts fetch()
                                                        │
                                                        ▼
                                              /api/v1/* (FastAPI)
                                                        │
                              ┌─────────────────────────┴──────────┐
                              ▼                                      ▼
                    shared command bus (cyberai.commands)    direct read models
                              │                                (MemoryManager,
                              ▼                                 ChatStore, …)
                    PolicyEngine-gated handlers
```

- `lib/api.ts` is the single HTTP module: typed interfaces for every
  DTO, one `get/post/patch/del` wrapper with error normalization.
- `useFetch` (in `src/hooks`) handles loading/error/refresh; most pages
  call `refresh()` after mutations instead of holding local copies.
- Live updates: `useLiveEvents` subscribes to SSE and feeds the event
  store; `RightPanel`/`SecurityPage` re-query on new events.

---

## 4. The shared command bus contract

The chat box and the command palette dispatch slash commands through
`POST /api/v1/commands/execute` — the **same dispatcher** the CLI shell
calls directly and the chat endpoint routes through. Consequences:

- The command catalog (`GET /api/v1/commands`) drives palette entries
  and chat autocomplete — no duplicated command list in the frontend.
- A `blocked` result renders as a policy notice in chat; `ok` is never
  true for blocked actions, on any surface.
- `/run` and `/stop` are flagged destructive in the spec; the UI shows
  confirmation before dispatching.

See `docs/COMMANDS.md` for the catalog and envelope.

---

## 5. Authorization UX (Targets view)

`TargetsPage` renders one card per target with a state pill:

- `UNAUTHORIZED` (red) → **AUTHORIZE** button
- anything else (`OFFLINE` yellow / `ACTIVE` green) → **REVOKE** button

Every target always shows exactly one action button — an authorized but
unreachable (`OFFLINE`) target can still be revoked. Buttons call
`PATCH /api/v1/targets/{id}` `{"allowed": bool}`, which merges the flag
into the PolicyEngine-backed record and publishes an audit event. The
policy file is the single source of truth; the CLI `/targets` command
and `GET /api/v1/targets` read the same records.

---

## 6. Styling tokens

`src/styles/` defines the palette as CSS custom properties; the CLI
shell theme (`cyberai/orchestrator/cli/shell/theme.py`) mirrors the
same tokens so both surfaces feel like one product:

| Token | Web | CLI (Rich) |
|---|---|---|
| Background | `--cb-bg0` #0b0e14 | `bg` #0b0e14 |
| Panel | `--cb-bg1` #11151d | `bg2` #11151d |
| Text | `--cb-text` #d7dae0 | `fg` #d7dae0 |
| Accent | `--cb-accent` #4cc9f0 | `accent` #4cc9f0 |
| Success | `--cb-green` #4ade80 | `green` #4ade80 |
| Warning | `--cb-yellow` #fbbf24 | `yellow` #fbbf24 |
| Danger | `--cb-red` #f87171 | `red` #f87171 |

State colors are semantic: green ACTIVE/VERIFIED, yellow OFFLINE/LIKELY,
red UNAUTHORIZED/FAILED, dim PENDING/UNKNOWN — in both surfaces.

---

## 7. Build & test

```powershell
cd cyberai/ui/frontend
npm run build        # strict TS → dist/
npm run lint         # eslint
```

- The FastAPI server serves the compiled `dist/` at `/` — after a
  rebuild, reload the browser (no server restart needed for static
  assets; server restart only for Python changes).
- Backend contract tests: `tests/test_ui_api.py`,
  `tests/test_security_regressions.py` (authorization + workspace paths).

---

## 8. File map

```
src/
├── App.tsx                    shell + context provider
├── stores/app.tsx             reducer: view, events, commands, toasts
├── hooks/                     useFetch, useLiveEvents, useGlobalShortcuts, useToast
├── lib/api.ts                 typed API client (single fetch wrapper)
├── components/
│   ├── layout/                TopBar, ActivityBar, Split, MainView, RightPanel, Toast
│   ├── chat/                  ChatList, ChatView, ChatInput, MessageBubble
│   └── command/               CommandPalette (Ctrl+K)
├── pages/                     14 view pages (see §2 table)
└── styles/                    tokens + global styles
```
