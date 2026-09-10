# CERBERUS Commands — The Shared Command Bus

Every operator surface — the **web UI chat**, the **CLI interactive shell**,
and the **HTTP API** — dispatches through one command bus
(`cyberai.commands`). One parser, one registry, one set of handlers.
Authorization is therefore enforced identically everywhere: a target
revoked in the UI is instantly blocked in the CLI and API, and vice versa.

```
Web UI chat ─┐
CLI shell  ──┼─► Dispatcher.execute(line) ─► Registry ─► Handler ─► CommandResult
HTTP API   ──┘                                              │
                                                    PermissionError
                                                            │
                                                    blocked_result (ok=False)
```

---

## 1. Syntax

```
/name arg1 arg2 key=value "quoted value"
```

- Commands start with `/`; anything else is natural language (routed to
  the chat/mission surface, not the command bus).
- `key=value` pairs become kwargs; bare tokens become positional args.
- Names are case-insensitive; aliases are supported.
- Unknown commands return `ok=False` with suggestions, never an exception.

---

## 2. Catalog (25 commands, 5 categories)

### system

| Command | Usage | Description |
|---|---|---|
| `/help` (`/?`, `/h`) | `help [command]` | List commands or show help for one |
| `/status` (`/st`) | `status` | Platform status snapshot |
| `/health` | `health` | Component health probe |
| `/doctor` | `doctor` | Environment doctor (deps, docker, config) |

### security

| Command | Usage | Description |
|---|---|---|
| `/security` (`/sec`) | `security` | Security center: policy, blocks, events |
| `/targets` (`/target`, `/tg`) | `targets [authorize <id>]` | List targets with auth + reachability state |
| `/approvals` | `approvals` | List pending approvals |
| `/approve` | `approve <id>` | Approve a pending action |
| `/deny` | `deny <id>` | Deny a pending action |

> `/targets authorize <id>` authorizes a target; `/targets revoke <id>`
> revokes it. Both are policy-gated and audit-logged.

### missions

| Command | Usage | Description |
|---|---|---|
| `/run` (`/mission-run`) | `run <objective> [target=<id>] [mode=SIMULATE\|PLAN\|LAB\|AUTHORIZED]` | Launch a mission (safest mode default) |
| `/stop` | `stop` | Stop the running mission |
| `/mission` | `mission` | Active mission status |

> `/run` and `/stop` are flagged **destructive** — the UI shows a
> confirmation before dispatching them.

### operations

| Command | Usage | Description |
|---|---|---|
| `/findings` (`/f`, `/finding`) | `findings [status=UNVERIFIED\|LIKELY\|VERIFIED\|REJECTED] [q=text] [limit=200]` | List/filter findings by status |
| `/verify` | `verify <finding_id>` | Mark a finding VERIFIED |
| `/likely` | `likely <finding_id>` | Mark a finding LIKELY |
| `/reject` | `reject <finding_id>` | Mark a finding REJECTED |
| `/agents` (`/ag`) | `agents` | List agents with performance stats |
| `/tools` (`/t`) | `tools` | List registered tools + adapter presence |
| `/models` (`/m`) | `models` | List the model registry |
| `/routing` | `routing` | Show task-type → model routing |

### history

| Command | Usage | Description |
|---|---|---|
| `/sessions` (`/s`, `/history`) | `sessions [q=text] [status=active] [limit=100]` | List sessions (chats + missions) |
| `/session` | `session <id>` | Show one session with findings |
| `/fork` | `fork <id>` | Fork a session into a new one |
| `/rename` | `rename <id> title=New title` | Rename a session |
| `/memory` (`/mem`) | `memory <query>` or `memory` | Search long-term memory (or stats) |

---

## 3. Result envelope

Every handler returns a `CommandResult`:

```json
{
  "ok": true,            // success flag — NEVER true when blocked
  "command": "targets",  // canonical name
  "data": {...},         // full payload
  "rows": [...],         // optional table rows (CLI renders a table)
  "columns": [...],      // column order for rows
  "message": "target juice-shop authorized",  // human summary
  "blocked": false,      // true when policy denied the action
  "error": ""            // error text when ok=false
}
```

Precedence for renderers: `blocked` → `!ok` → `rows` → `message` → `data`.

---

## 4. Authorization contract

- Handlers raise `PermissionError` when policy denies an action; the
  registry converts it to `CommandResult.blocked_result(...)` —
  `ok=False, blocked=True`.
- **No surface can flip a blocked result to ok.** The web chat, CLI
  shell, and `/api/v1/commands/execute` all return the same envelope.
- Target authorization state lives in the `PolicyEngine` (single source
  of truth); `/targets`, `GET /api/v1/targets`, and the UI Targets view
  all read from it.
- Regression tests: `tests/test_security_regressions.py` (21 tests) lock
  this contract, including revoke→blocked→authorize round-trips through
  both the API and the command bus.

---

## 5. HTTP surface

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/commands` | Catalog (flattened + grouped by category) |
| `GET /api/v1/commands/{name}` | One command's spec |
| `POST /api/v1/commands/execute` | `{"input": "/status"}` → envelope |

The web chat (`POST /api/v1/chats/{id}/messages`) routes slash-command
content through this same bus before falling back to the LLM gateway.

---

## 6. Extending

Register a new command from any module:

```python
from cyberai.commands.models import CommandSpec
from cyberai.commands.registry import reset_registry

def _my_command(ctx, parsed):
    return CommandResult.success("my-command", data={"echo": parsed.raw})

spec = CommandSpec(
    name="my-command", category="operations",
    description="Echo the input", usage="my-command <text>",
    handler=_my_command, aliases=["echo"],
)
```

Rules:
- One category per command; keep descriptions short (they render in
  `/help` and the command palette).
- Raise `PermissionError` for policy denials — never return `ok=True`
  for an unauthorized action.
- Handlers receive `(ctx: CommandContext, parsed: ParsedCommand)`; use
  `parsed.arg(0)` / `parsed.kwarg("status")` accessors.
