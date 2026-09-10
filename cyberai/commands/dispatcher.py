"""Dispatcher — resolves parsed commands against the registry."""

import logging
from typing import Any, Dict, Optional

from cyberai.commands.context import CommandContext
from cyberai.commands.models import CommandResult, ParsedCommand
from cyberai.commands.registry import CommandRegistry, get_registry

logger = logging.getLogger(__name__)


class Dispatcher:
    """Executes parsed commands against a registry + context.

    Usage (any host):
        dispatcher = Dispatcher(get_registry())
        result = dispatcher.execute("/findings status=VERIFIED", ctx)
    """

    def __init__(self, registry: Optional[CommandRegistry] = None):
        self.registry = registry or get_registry()

    def execute(self, raw: str, ctx: Optional[CommandContext] = None) -> CommandResult:
        """Parse + invoke. Non-command text returns ok=False, chat=True."""
        from cyberai.commands.parser import parse_command

        parsed = parse_command(raw)
        if not parsed.is_command:
            return CommandResult(
                ok=False, command="", error="not a command",
                data={"chat": True, "text": parsed.raw},
            )
        if not parsed.name:
            return CommandResult.failure("/", "empty command")
        ctx = ctx or CommandContext()
        return self.registry.invoke(parsed.name, ctx, parsed)

    def execute_parsed(self, parsed: ParsedCommand,
                       ctx: Optional[CommandContext] = None) -> CommandResult:
        """Invoke an already-parsed command (used by API layer)."""
        if not parsed.is_command:
            return CommandResult(
                ok=False, command="", error="not a command",
                data={"chat": True, "text": parsed.raw},
            )
        ctx = ctx or CommandContext()
        return self.registry.invoke(parsed.name, ctx, parsed)

    def suggestions(self, fragment: str) -> list:
        """Autocomplete suggestions for a partial command name."""
        from cyberai.commands.parser import suggestions
        return suggestions(fragment, self.registry.names())

    def help(self, name: str = "") -> Dict[str, Any]:
        """Structured help for one command or the whole catalog."""
        if name:
            spec = self.registry.command(name)
            if spec is None:
                return {"ok": False, "error": f"unknown command: /{name}"}
            return {
                "ok": True,
                "name": spec.name,
                "category": spec.category,
                "description": spec.description,
                "usage": spec.usage,
                "examples": spec.examples,
                "aliases": spec.aliases,
                "destructive": spec.destructive,
            }
        return {
            "ok": True,
            "categories": {
                cat: [
                    {"name": s.name, "description": s.description,
                     "usage": s.usage, "aliases": s.aliases}
                    for s in self.registry.specs(category=cat)
                ]
                for cat in self.registry.categories()
            },
        }
