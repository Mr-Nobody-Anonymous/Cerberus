"""Tests for the shared command bus (cyberai.commands).

Covers:
  - parser: slash syntax, kwargs, quoting, natural-language routing
  - registry: registration, aliases, duplicate rejection
  - dispatcher: unknown commands, chat routing, help
  - handlers: validation paths that don't require live backends
  - security: blocked results never report ok=True

Run with ``python -m pytest tests/test_command_bus.py -v``.
"""

import pytest

from cyberai.commands.models import CommandResult, CommandSpec, ParsedCommand
from cyberai.commands.parser import parse_command, suggestions, tokenize
from cyberai.commands.registry import CommandRegistry, reset_registry


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
class TestParser:
    def test_slash_command(self):
        p = parse_command("/findings status=VERIFIED q=sql")
        assert p.is_command
        assert p.name == "findings"
        assert p.kwargs == {"status": "VERIFIED", "q": "sql"}
        assert p.args == []

    def test_positional_args(self):
        p = parse_command("/run analyze the lab target=lab-web-01")
        assert p.is_command
        assert p.name == "run"
        assert p.args == ["analyze", "the", "lab"]
        assert p.kwargs == {"target": "lab-web-01"}

    def test_quoted_values(self):
        p = parse_command('/rename abc title="My New Title"')
        assert p.kwargs["title"] == "My New Title"

    def test_unbalanced_quote_fallback(self):
        p = parse_command('/rename abc title="unclosed')
        assert p.is_command
        assert p.name == "rename"

    def test_natural_language_not_command(self):
        p = parse_command("analyze my lab target")
        assert not p.is_command
        assert p.raw == "analyze my lab target"

    def test_empty_and_bare_slash(self):
        assert parse_command("").is_command is False
        p = parse_command("/")
        assert p.is_command
        assert p.name == ""

    def test_case_insensitive_name(self):
        p = parse_command("/FINDINGS")
        assert p.name == "findings"

    def test_suggestions(self):
        out = suggestions("f", ["findings", "fork", "verify", "agents"])
        assert out == ["findings", "fork"]

    def test_tokenize_limit(self):
        tokens = tokenize(" ".join(["x"] * 100))
        assert len(tokens) == 64


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
class TestRegistry:
    def setup_method(self):
        self.registry = CommandRegistry()

    def _spec(self, name="test", **kw):
        return CommandSpec(
            name=name, category="test", description="test command",
            handler=lambda ctx, parsed: {"ok": True}, **kw)

    def test_register_and_lookup(self):
        self.registry.register(self._spec())
        assert self.registry.has("test")
        assert self.registry.command("test").name == "test"

    def test_alias_lookup(self):
        self.registry.register(self._spec(aliases=["t"]))
        assert self.registry.command("t").name == "test"

    def test_duplicate_rejected(self):
        self.registry.register(self._spec())
        with pytest.raises(ValueError):
            self.registry.register(self._spec())

    def test_invalid_name_rejected(self):
        with pytest.raises(ValueError):
            self.registry.register(self._spec(name="BadName"))

    def test_invoke_wraps_dict(self):
        self.registry.register(self._spec())
        result = self.registry.invoke("test", None, ParsedCommand(raw="/test"))
        assert result.ok
        assert result.data == {"ok": True}

    def test_invoke_captures_exceptions(self):
        def boom(ctx, parsed):
            raise RuntimeError("kaboom")
        self.registry.register(CommandSpec(
            name="boom", category="test", description="x", handler=boom))
        result = self.registry.invoke("boom", None, ParsedCommand(raw="/boom"))
        assert not result.ok
        assert "kaboom" in result.error

    def test_invoke_permission_error_is_blocked(self):
        def denied(ctx, parsed):
            raise PermissionError("not authorized")
        self.registry.register(CommandSpec(
            name="denied", category="test", description="x", handler=denied))
        result = self.registry.invoke("denied", None, ParsedCommand(raw="/denied"))
        assert not result.ok
        assert result.blocked  # THE security invariant


# ---------------------------------------------------------------------------
# Built-in command loading + dispatcher
# ---------------------------------------------------------------------------
class TestBuiltinCommands:
    @classmethod
    def setup_class(cls):
        from cyberai.commands import load_builtin_commands, get_dispatcher
        load_builtin_commands()
        cls.dispatcher = get_dispatcher()

    def test_all_builtin_commands_registered(self):
        names = self.dispatcher.registry.names()
        for expected in ("help", "status", "targets", "findings", "agents",
                         "tools", "models", "sessions", "memory", "security",
                         "run", "stop", "fork", "rename", "verify", "reject",
                         "approve", "deny", "doctor", "health"):
            assert expected in names, f"missing /{expected}"

    def test_unknown_command_fails_cleanly(self):
        result = self.dispatcher.execute("/definitely-not-a-command")
        assert not result.ok
        assert "unknown command" in result.error

    def test_natural_language_routes_to_chat(self):
        result = self.dispatcher.execute("hello there")
        assert not result.ok
        assert result.data.get("chat") is True
        assert result.data.get("text") == "hello there"

    def test_help_catalog(self):
        result = self.dispatcher.execute("/help")
        assert result.ok
        assert "categories" in result.data
        assert "names" in result.data

    def test_help_single_command(self):
        result = self.dispatcher.execute("/help findings")
        assert result.ok
        assert result.data["name"] == "findings"

    def test_help_unknown(self):
        result = self.dispatcher.execute("/help bogus")
        assert not result.ok

    def test_suggestions(self):
        assert "findings" in self.dispatcher.suggestions("find")

    def test_run_requires_objective(self):
        result = self.dispatcher.execute("/run")
        assert not result.ok
        assert "usage" in result.error

    def test_run_rejects_invalid_mode(self):
        result = self.dispatcher.execute("/run test mode=BOGUS")
        assert not result.ok
        assert "invalid mode" in result.error

    def test_findings_rejects_invalid_status(self):
        result = self.dispatcher.execute("/findings status=NOPE")
        assert not result.ok
        assert "invalid status" in result.error

    def test_verify_requires_id(self):
        result = self.dispatcher.execute("/verify")
        assert not result.ok

    def test_fork_requires_id(self):
        result = self.dispatcher.execute("/fork")
        assert not result.ok

    def test_rename_requires_title(self):
        result = self.dispatcher.execute("/rename abc")
        assert not result.ok


# ---------------------------------------------------------------------------
# CommandResult envelope
# ---------------------------------------------------------------------------
class TestCommandResult:
    def test_success_factory(self):
        r = CommandResult.success("x", data={"a": 1}, message="done")
        assert r.ok and r.data == {"a": 1} and r.message == "done"

    def test_failure_factory(self):
        r = CommandResult.failure("x", "boom")
        assert not r.ok and r.error == "boom"

    def test_blocked_factory(self):
        r = CommandResult.blocked_result("x", "not authorized")
        assert not r.ok and r.blocked and r.error == "not authorized"

    def test_to_dict_shape(self):
        r = CommandResult(ok=True, command="x", data={"a": 1},
                          rows=[{"b": 2}], columns=["b"])
        d = r.to_dict()
        assert d["ok"] is True
        assert d["rows"] == [{"b": 2}]
        assert "error" not in d  # omitted when empty
