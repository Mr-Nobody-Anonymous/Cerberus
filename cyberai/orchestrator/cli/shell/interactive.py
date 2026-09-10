"""Interactive console — Claude-Code-style REPL over the shared command bus.

Every slash command dispatches through cyberai.commands (the SAME handlers
the web UI and HTTP API use), so authorization and semantics are identical
on every surface (spec: "The web UI, CLI, and API should invoke the same
command handlers").

Non-slash input is treated as a task objective and launched in a background
thread (SIMULATE default keeps it safe offline).
"""

import asyncio
import shlex
import sys
import threading
from typing import Any, Dict, Optional

from .render import make_console, render_banner, render_result, render_hint
from .theme import state_style

# Live task handle (orchestrator + worker thread + last result)
_TASK: Dict[str, Any] = {"orchestrator": None, "thread": None,
                         "result": None, "error": None}

# BUG-9: glyphs like ❯ ▶ ✔ crash with UnicodeEncodeError on legacy Windows
# code pages (cp1252). Probe once; degrade to ASCII when needed.
_ASCII_MAP = {"❯": ">", "▶": ">", "✔": "+", "✗": "x", "⛔": "X", "⏳": "~",
              "■": "#", "⚠": "!", "…": "...", "·": "-", "→": "->",
              "—": "-", "§": "S"}


def _ascii_mode() -> bool:
    try:
        "❯▶✔⛔⏳■⚠·→—".encode(sys.stdout.encoding or "utf-8")
        return False
    except (UnicodeEncodeError, LookupError):
        return True


def _s(msg: str) -> str:
    """Degrade non-encodable glyphs to ASCII when the code page requires it."""
    if _ascii_mode():
        for k, v in _ASCII_MAP.items():
            msg = msg.replace(k, v)
    return msg


def _ascii_safe() -> bool:
    """True when the console code page can't render our glyphs (BUG-9)."""
    try:
        "❯▶✔⛔⏳".encode(sys.stdout.encoding or "utf-8")
        return False
    except (UnicodeEncodeError, LookupError):
        return True


def run_console(simulate: bool = True, verbose: bool = False) -> None:
    """Entry point — the interactive loop."""
    console = make_console()
    render_banner(console, "SIMULATE" if simulate else "LIVE")

    use_ptk = False
    session = None
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.formatted_text import HTML
        from .completion import build_completer, build_history
        completer = build_completer()
        history = build_history()
        if completer is not None:
            session = PromptSession(history=history, completer=completer,
                                   complete_while_typing=True)
            use_ptk = True
    except ImportError:
        pass

    while True:
        try:
            if use_ptk and session is not None:
                from prompt_toolkit.formatted_text import HTML
                line = session.prompt(
                    HTML('<style fg="#4ade80">cerberus</style>'
                         '<style fg="#4cc9f0"> ❯ </style>')).strip()
            else:
                console.print(_s("cerberus ❯ "), style="cb.prompt", end="")
                line = input("").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nbye.", style="cb.dim")
            return

        if not line:
            continue

        try:
            parts = shlex.split(line)
        except ValueError as e:
            console.print(f"  parse error: {e}", style="cb.err")
            continue

        cmd, args = parts[0], parts[1:]
        try:
            _dispatch(console, cmd, args, line, simulate, verbose)
        except SystemExit:
            return  # /quit — exit the REPL loop cleanly
        except Exception as e:  # noqa: BLE001 — REPL must never die
            console.print(f"  error: {e}", style="cb.err")


def _dispatch(console, cmd: str, args, line: str,
              simulate: bool, verbose: bool) -> None:
    """Route one parsed input line."""
    from cyberai.commands import get_dispatcher, load_builtin_commands

    # Non-slash input → task objective (chat/mission surface)
    if not cmd.startswith("/"):
        _launch_task(console, line, simulate)
        return

    name = cmd[1:].lower()

    # Local REPL controls (not command-bus commands)
    if name in ("quit", "exit"):
        console.print("bye.", style="cb.dim")
        raise SystemExit(0)
    if name == "clear":
        console.clear()
        return
    if name == "help":
        _show_help(console)
        return
    if name == "stop":
        _stop_task(console)
        return
    if name == "result":
        _show_result(console)
        return
    if name == "watch":
        _watch_events(console)
        return

    # Everything else → the shared command bus (same handlers as web/API)
    load_builtin_commands()
    dispatcher = get_dispatcher()
    result = dispatcher.execute(line)
    if result.data.get("chat") and not result.ok and result.error == "not a command":
        # Parser said "not a command" — shouldn't happen for slash input
        _launch_task(console, line, simulate)
        return
    render_result(console, result, verbose=verbose)


def _show_help(console) -> None:
    """Render the command catalog grouped by category."""
    from rich.columns import Columns
    from rich.table import Table

    from cyberai.commands import load_builtin_commands
    reg = load_builtin_commands()

    table = Table(show_header=True, header_style="cb.header", expand=False,
                 border_style="cb.dim", title="operator commands",
                 title_style="cb.header")
    table.add_column("command", style="cb.accent", no_wrap=True)
    table.add_column("description", style="cb.fg")
    for cat in reg.categories():
        specs = [s for s in reg.specs(category=cat) if not s.hidden]
        if not specs:
            continue
        for s in specs:
            table.add_row(f"/{s.name}", _s(s.description))
    console.print(table)
    render_hint(console, _s("REPL: /help /clear /quit /stop /result /watch · "
                          "anything else = task objective"))


def _launch_task(console, objective: str, simulate: bool) -> None:
    """Launch a task in a background thread (keeps /stop reachable)."""
    console.print(_s(f"  ▶ launching: {objective}"), style="cb.info")
    if simulate:
        console.print("    mode: SIMULATE", style="cb.dim")

    if _TASK["thread"] is not None and _TASK["thread"].is_alive():
        console.print(_s("  ⚠ a task is already running — /stop it first"),
                      style="cb.warn")
        return

    from cyberai import CyberAIOrchestrator

    def _worker() -> None:
        orch = CyberAIOrchestrator(simulate=simulate)
        _TASK["orchestrator"] = orch
        _TASK["result"] = None
        _TASK["error"] = None
        try:
            _TASK["result"] = asyncio.run(orch.run(objective))
        except Exception as e:  # noqa: BLE001 — worker must never crash the REPL
            _TASK["error"] = str(e)
        finally:
            try:
                orch.close()
            except Exception:  # noqa: BLE001
                pass
            _TASK["orchestrator"] = None

    t = threading.Thread(target=_worker, daemon=True, name="cerberus-task")
    _TASK["thread"] = t
    t.start()
    console.print("    running in background — /stop to cancel, /result to view",
                  style="cb.dim")


def _stop_task(console) -> None:
    orch = _TASK.get("orchestrator")
    if orch is None:
        if _TASK["thread"] is not None and _TASK["thread"].is_alive():
            console.print(_s("  ⏳ task is starting — /stop again in a moment"),
                          style="cb.warn")
            return
        console.print(_s("  ■ no running task"), style="cb.warn")
        return
    try:
        orch.stop()
        console.print(_s("  ■ stop signal sent — takes effect at next step boundary"),
                      style="cb.warn")
    except Exception as e:  # noqa: BLE001
        console.print(f"  stop failed: {e}", style="cb.err")


def _show_result(console) -> None:
    if _TASK["thread"] is not None and _TASK["thread"].is_alive():
        console.print(_s("  ⏳ task still running"), style="cb.warn")
        return
    if _TASK.get("error"):
        console.print(_s(f"  ⛔ task failed: {_TASK['error']}"), style="cb.err")
        return
    result = _TASK.get("result")
    if result is None:
        console.print("  no task has been run yet", style="cb.warn")
        return
    console.print(_s("  ✔ last task result:"), style="cb.ok")
    console.print_json(data=result) if isinstance(result, dict) else console.print(result)


def _watch_events(console) -> None:
    """Inline event tail — reuses the watch command's logic."""
    import time as _time

    from cyberai.orchestrator import MemoryManager

    mm = MemoryManager()
    seen = set()
    count = 0
    console.print(_s("  watching for events (Ctrl+C to stop)…"), style="cb.dim")
    try:
        while True:
            for s in mm.list_sessions():
                sid = s.get("id")
                if sid and sid not in seen:
                    seen.add(sid)
                    console.print(f"  [TASK ] {sid[:8]} target={s.get('target_id','?')} "
                                  f"status={s.get('status','?')}")
                    count += 1
            for f in mm.get_findings():
                fid = f.get("id")
                if fid and fid not in seen:
                    seen.add(fid)
                    console.print(f"  [FIND ] {fid[:8]} [{f.get('status','')}] "
                                  f"{str(f.get('observation',''))[:80]}")
                    count += 1
            _time.sleep(2.0)
    except KeyboardInterrupt:
        pass
    finally:
        mm.close()
        console.print(f"  stopped after {count} events.", style="cb.dim")
