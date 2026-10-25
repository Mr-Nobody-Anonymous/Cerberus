"""Renderers — turn CommandResult envelopes into Rich output.

Every renderer accepts the shared CommandResult from the command bus, so
the CLI renders exactly what the web UI and API return (surface parity).
"""

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .theme import state_style

# Shared console factory (theme applied once). --no-color support: the CLI
# entry point sets _NO_COLOR before the first render call.
_NO_COLOR = {"enabled": False}


def make_console() -> Console:
    """Build a themed console; honors --no-color.

    BUG-9 safety net: on legacy Windows code pages (cp1252) any un-mapped
    glyph would raise UnicodeEncodeError inside Rich's buffered writer and
    poison every subsequent print. Reconfigure stdout/stderr with
    errors="replace" so the console can never crash on a stray character.
    """
    import sys as _sys
    for stream in (_sys.stdout, _sys.stderr):
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(errors="replace")
        except Exception:
            pass
    from .theme import CERBERUS_THEME
    return Console(theme=CERBERUS_THEME, no_color=_NO_COLOR["enabled"],
                   highlight=False)


def set_no_color(enabled: bool) -> None:
    _NO_COLOR["enabled"] = bool(enabled)


def _s(msg: str) -> str:
    """Degrade non-encodable glyphs on legacy Windows code pages (BUG-9)."""
    import sys as _sys
    try:
        "❯▶✔✗⛔⏳■⚠…·→—".encode(_sys.stdout.encoding or "utf-8")
        return msg
    except (UnicodeEncodeError, LookupError):
        return (msg.replace("❯", ">").replace("▶", ">").replace("✔", "+")
                   .replace("✗", "x").replace("⛔", "X").replace("⏳", "~")
                   .replace("■", "#").replace("⚠", "!").replace("…", "...")
                   .replace("·", "-").replace("→", "->").replace("—", "-"))


def render_result(console: Console, result, verbose: bool = False) -> None:
    """Render one CommandResult envelope.

    Order of precedence:
      1. blocked  → red panel (authorization/policy rejection)
      2. not ok   → red error line
      3. rows     → Rich table
      4. message  → green line
      5. data     → JSON block (verbose shows full payload)
    """
    if result.blocked:
        console.print(Panel(
            Text(_s(f"⛔ BLOCKED — {result.error}"), style="cb.err"),
            title="policy", border_style="cb.err", expand=False))
        return
    if not result.ok:
        console.print(Text(_s(f"✗ {result.error}"), style="cb.err"))
        return
    if result.message:
        console.print(Text(_s(f"✔ {result.message}"), style="cb.ok"))
    if result.rows is not None:
        render_rows(console, result.rows, result.columns)
    if result.data and (verbose or result.rows is None):
        render_data(console, result.data, verbose)


def render_rows(console: Console, rows: list[dict[str, Any]],
                columns: list[str] | None = None) -> None:
    """Render structured rows as a Rich table."""
    if not rows:
        console.print(Text("  (no results)", style="cb.dim"))
        return
    cols = columns or list(rows[0].keys())
    table = Table(show_header=True, header_style="cb.header", expand=False,
                 border_style="cb.dim", pad_edge=False)
    for c in cols:
        table.add_column(c, style="cb.mono", overflow="fold",
                         max_width=48 if c in ("observation", "description",
                                                "content", "objective") else None)
    for row in rows:
        vals = []
        for c in cols:
            v = row.get(c, "")
            s = str(v)
            if c in ("state", "status", "verification_status", "mode"):
                vals.append(Text(s, style=state_style(s)))
            elif c in ("allowed", "reachable", "ok"):
                vals.append(Text("yes" if v else "no",
                                 style="cb.green" if v else "cb.dim"))
            else:
                vals.append(s)
        table.add_row(*vals)
    console.print(table)


def render_data(console: Console, data: dict[str, Any], verbose: bool = False) -> None:
    """Render a data payload as pretty JSON (trimmed unless verbose)."""
    payload = data
    if not verbose and isinstance(payload, dict):
        trimmed = {}
        for k, v in payload.items():
            if isinstance(v, list) and len(v) > 8:
                trimmed[k] = [*v[:8], f"... +{len(v) - 8} more"]
            else:
                trimmed[k] = v
        payload = trimmed
    console.print_json(json.dumps(payload, default=str))


def render_banner(console: Console, mode: str = "LIVE") -> None:
    """Startup banner for the interactive console."""
    from rich.panel import Panel
    from rich.table import Table

    from .theme import BANNER
    mode_style = "cb.green" if mode == "SIMULATE" else "cb.accent"
    body = Text(BANNER, style="cb.banner")
    body.append(f"  [{mode}]", style=mode_style)
    console.print(Panel(body, border_style="cb.accent", expand=False,
                        subtitle="operator console"))
    # Status strip: mode pill + quick facts
    strip = Table.grid(padding=(0, 2))
    strip.add_column(style="cb.dim", justify="left")
    strip.add_column(style="cb.accent", justify="left")
    strip.add_row(_s("mode"), Text(mode, style=mode_style))
    strip.add_row(_s("help"), _s("/help for commands · /quit to exit"))
    console.print(strip)


def render_hint(console: Console, text: str) -> None:
    console.print(Text(_s(f"  {text}"), style="cb.dim"))
