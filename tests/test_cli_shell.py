"""Tests for the redesigned CLI shell (cyberai.orchestrator.cli.shell).

Covers:
  - theme: state → style mapping (green/yellow/red/dim)
  - render: CommandResult envelope rendering precedence
            (blocked → error → rows → message → data)
  - render: ASCII degradation on legacy Windows code pages (BUG-9)
  - completion: command catalog from the shared registry
  - interactive: dispatch routes to the shared command bus

Run with ``python -m pytest tests/test_cli_shell.py -v``.
"""

import pytest

rich = pytest.importorskip("rich", reason="rich not installed")

from cyberai.commands import get_dispatcher, load_builtin_commands  # noqa: E402
from cyberai.commands.models import CommandResult  # noqa: E402
from cyberai.orchestrator.cli.shell.render import (  # noqa: E402
    _s,
    make_console,
    render_result,
)
from cyberai.orchestrator.cli.shell.theme import state_style  # noqa: E402


@pytest.fixture()
def console():
    return make_console()


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
class TestTheme:
    @pytest.mark.parametrize("state,expected", [
        ("ACTIVE", "green"), ("RUNNING", "green"), ("VERIFIED", "green"),
        ("HEALTHY", "green"), ("ONLINE", "green"), ("OK", "green"),
        ("OFFLINE", "yellow"), ("UNVERIFIED", "yellow"), ("WARN", "yellow"),
        ("STARTING", "yellow"), ("DEGRADED", "yellow"), ("LIKELY", "yellow"),
        ("UNAUTHORIZED", "red"), ("REJECTED", "red"), ("FAILED", "red"),
        ("ERROR", "red"), ("DENIED", "red"), ("BLOCKED", "red"),
        ("PENDING", "dim"), ("UNKNOWN", "dim"),
    ])
    def test_state_styles(self, state, expected):
        assert expected in state_style(state)

    def test_unknown_state_is_dim(self):
        assert "dim" in state_style("SOMETHING-NEW")

    def test_state_style_is_never_empty(self):
        assert state_style("")


# ---------------------------------------------------------------------------
# ASCII degradation (BUG-9: cp1252 consoles crash on glyphs)
# ---------------------------------------------------------------------------
class TestAsciiDegradation:
    def test_degrades_all_mapped_glyphs(self, monkeypatch):
        """On a cp1252 console every mapped glyph must degrade to ASCII."""
        import io as _io
        import sys as _sys
        fake = _io.TextIOWrapper(_io.BytesIO(), encoding="cp1252")
        monkeypatch.setattr(_sys, "stdout", fake)
        degraded = _s("❯ ▶ ✔ ✗ ⛔ ⏳ ■ ⚠ … · → —")
        for glyph in ("❯", "▶", "✔", "✗", "⛔", "⏳", "■", "⚠", "…", "·", "→", "—"):
            assert glyph not in degraded
        # degraded output must itself be cp1252-encodable (never crashes)
        degraded.encode("cp1252")

    def test_plain_ascii_untouched(self):
        assert _s("plain text 123") == "plain text 123"

    def test_utf8_console_keeps_glyphs(self):
        """On UTF-8 consoles the pretty glyphs are preserved."""
        out = _s("✔ done")
        assert "✔" in out


# ---------------------------------------------------------------------------
# Render precedence
# ---------------------------------------------------------------------------
class TestRenderPrecedence:
    def _render(self, console, result, capsys):
        render_result(console, result, verbose=False)
        return capsys.readouterr().out

    def test_blocked_renders_error(self, console, capsys):
        r = CommandResult.blocked_result("targets", "not authorized")
        out = self._render(console, r, capsys)
        assert "BLOCKED" in out
        assert "not authorized" in out

    def test_failure_renders_error(self, console, capsys):
        r = CommandResult.failure("x", "boom")
        out = self._render(console, r, capsys)
        assert "boom" in out

    def test_rows_render_table(self, console, capsys):
        r = CommandResult.success(
            "targets", rows=[{"id": "juice-shop", "state": "UNAUTHORIZED"}],
            columns=["id", "state"])
        out = self._render(console, r, capsys)
        assert "juice-shop" in out
        assert "UNAUTHORIZED" in out

    def test_message_renders(self, console, capsys):
        r = CommandResult.success("targets", message="target x authorized")
        out = self._render(console, r, capsys)
        assert "target x authorized" in out

    def test_data_renders_json_when_no_rows(self, console, capsys):
        r = CommandResult.success("status", data={"uptime": 42})
        out = self._render(console, r, capsys)
        assert "uptime" in out

    def test_empty_rows_render_placeholder(self, console, capsys):
        r = CommandResult.success("findings", rows=[], columns=["id"])
        out = self._render(console, r, capsys)
        assert "no results" in out


# ---------------------------------------------------------------------------
# Completion catalog
# ---------------------------------------------------------------------------
class TestCompletion:
    def test_command_names_from_registry(self):
        from cyberai.orchestrator.cli.shell.completion import command_names
        load_builtin_commands()
        names = command_names()
        assert len(names) >= 20
        assert "/targets" in names
        assert "/findings" in names
        assert "/status" in names
        # hidden commands are excluded
        assert all(not n.startswith("/targets-") for n in names)

    def test_names_sorted(self):
        from cyberai.orchestrator.cli.shell.completion import command_names
        names = command_names()
        assert names == sorted(names)


# ---------------------------------------------------------------------------
# Interactive dispatch — same bus as web UI/API
# ---------------------------------------------------------------------------
class TestInteractiveDispatch:
    @classmethod
    def setup_class(cls):
        load_builtin_commands()
        cls.dispatcher = get_dispatcher()

    def test_slash_command_routes_to_bus(self, console, capsys):
        from cyberai.orchestrator.cli.shell.interactive import _dispatch
        _dispatch(console, "/status", [], "/status", simulate=True,
                  verbose=False)
        out = capsys.readouterr().out
        assert out.strip()  # rendered something (status snapshot)

    def test_quit_raises_system_exit(self, console):
        from cyberai.orchestrator.cli.shell.interactive import _dispatch
        with pytest.raises(SystemExit):
            _dispatch(console, "/quit", [], "/quit", simulate=True,
                      verbose=False)

    def test_non_slash_launches_task(self, console, capsys):
        from cyberai.orchestrator.cli.shell.interactive import _dispatch
        _dispatch(console, "analyze", ["analyze"], "analyze",
                  simulate=True, verbose=False)
        out = capsys.readouterr().out
        assert "launching" in out

    def test_help_renders_catalog(self, console, capsys):
        from cyberai.orchestrator.cli.shell.interactive import _dispatch
        _dispatch(console, "/help", [], "/help", simulate=True,
                  verbose=False)
        out = capsys.readouterr().out
        assert "/targets" in out
        assert "/findings" in out
