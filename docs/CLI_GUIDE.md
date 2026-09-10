# CERBERUS CLI Guide

The CLI (`cyber-ai`, module `cyberai.orchestrator.cli`) is the
terminal-first twin of the web Command Deck: same command bus, same
policy engine, same data. This guide covers the interactive shell, the
~35 one-shot subcommands, and the global output flags.

---

## 1. Launch

```powershell
# from the repository root (use the workspace venv)
$py = ".\_cerberus-clean-check\Scripts\python.exe"

& $py -m cyberai.orchestrator.cli --help          # all commands
& $py -m cyberai.orchestrator.cli interactive     # the operator shell
& $py -m cyberai.orchestrator.cli ui               # the web Command Deck
```

---

## 2. The interactive shell

```powershell
& $py -m cyberai.orchestrator.cli interactive [--simulate] [--verbose]
```

A themed REPL (Rich + prompt_toolkit) with:

- **Slash commands** — the full shared catalog (see `docs/COMMANDS.md`),
  rendered as Rich tables with state-aware colors
  (green ACTIVE / yellow OFFLINE / red UNAUTHORIZED).
- **Tab completion** — command names after `/`, `key=` kwargs from each
  command's usage string.
- **Persistent history** — `~/.cerberus/cli_history` (↑/↓ recall across
  sessions).
- **Natural language** — any non-slash input launches a background task
  (mission objective) in SIMULATE mode by default.
- **Local controls** — `/help` (catalog), `/clear`, `/stop` (cooperative
  task stop), `/result` (last task JSON), `/watch` (live event stream),
  `/quit`.

```
   ___ _____ ___ ___ _  _ ___ _  _ ___
  / __|_   _| __| _ ) \| | __| \| | __|
 | (__  | | | _|| _ ) .` | _|| .` | _|
  \___| |_| |___|___|_|\_|___|_|\_|___|
  AI Cyber-Security IDE — operator console

  mode: SIMULATE   ·   /help for commands   ·   /quit to exit
cerberus ❯ /targets
```

> **Windows note:** on legacy code pages (cp1252) the shell
> automatically degrades glyphs (❯ → >, ✔ → +) and reconfigures stdout
> with `errors="replace"` — it never crashes on encoding. `--no-color`
> or the `NO_COLOR` env var disables ANSI colors.

### REPL task lifecycle

```
cerberus ❯ analyze the juice-shop target
  ▶ launching: analyze the juice-shop target
    mode: SIMULATE
cerberus ❯ /stop        # cooperative stop at next step boundary
cerberus ❯ /result      # last task result as JSON
cerberus ❯ /watch       # poll sessions+findings every 2s (Ctrl+C ends)
```

---

## 3. Global output flags (spec §14)

Put these BEFORE the subcommand — they apply to every command:

| Flag | Effect |
|---|---|
| `--json` | Machine-readable JSON output |
| `--yaml` | Machine-readable YAML output |
| `--table` | Force tabular output for list-like results |
| `--quiet` | Suppress human output (only errors); implies JSON |
| `--verbose` | Extra detail (durations, paths, diagnostics) |
| `--debug` | Tracebacks + internal diagnostics |
| `--no-color` | Disable ANSI colors (also honored via `NO_COLOR` env) |

```powershell
& $py -m cyberai.orchestrator.cli --json agents
& $py -m cyberai.orchestrator.cli --quiet findings
& $py -m cyberai.orchestrator.cli --verbose models
```

---

## 4. One-shot subcommands

| Area | Commands |
|---|---|
| Tasks | `task`, `assess` (alias), `simulate`, `watch`, `replay` |
| Platform | `status`, `models`, `adapters`, `tools`, `agents`, `profile`, `doctor`, `config`, `benchmark` |
| Knowledge | `findings`, `memory`, `intel`, `scorecard`, `report`, `history` |
| Lab | `lab list`, `lab register`, `lab start`, `lab stop`, `lab status` |
| Sessions | `session list`, `session show` |
| Operations | `hunt`, `blueprint`, `killchain`, `wargame`, `workflow`, `mcp`, `evolve` |
| UI | `ui` (launch the web Command Deck) |
| Shell | `interactive` (the REPL above) |

Examples:

```powershell
& $py -m cyberai.orchestrator.cli status
& $py -m cyberai.orchestrator.cli findings --status VERIFIED
& $py -m cyberai.orchestrator.cli lab list
& $py -m cyberai.orchestrator.cli doctor
& $py -m cyberai.orchestrator.cli intel
```

---

## 5. Architecture

```
cyberai/orchestrator/cli/
├── cli.py            # Click entry point: global flags + ~35 subcommands
└── shell/            # the interactive console (v2 redesign)
    ├── theme.py      # Rich theme mirroring web UI tokens + state colors
    ├── render.py     # CommandResult → Rich tables/panels/JSON
    ├── completion.py # prompt_toolkit completer + persistent history
    └── interactive.py# the REPL loop + background task lifecycle
```

Key contract: the shell dispatches every slash command through
`Dispatcher.execute()` — the **same handlers** as the web UI chat and
`POST /api/v1/commands/execute`. There is no CLI-specific command
implementation, so authorization cannot drift between surfaces.

Tests: `tests/test_cli_shell.py` (37 tests) covers theme state mapping,
render precedence, ASCII degradation (BUG-9), the completion catalog,
and interactive dispatch.
