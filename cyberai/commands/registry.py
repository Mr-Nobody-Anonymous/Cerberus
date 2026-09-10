"""Command registry — the catalog every host (CLI/Web/API) shares."""

import logging
from typing import Dict, List, Optional

from cyberai.commands.models import CommandSpec, CommandResult

logger = logging.getLogger(__name__)


class CommandRegistry:
    """Registry of CommandSpec objects keyed by canonical name + aliases."""

    def __init__(self) -> None:
        self._commands: Dict[str, CommandSpec] = {}
        self._aliases: Dict[str, str] = {}

    # ------------------------------------------------------------- register
    def register(self, spec: CommandSpec) -> None:
        if not spec.name or not spec.name.islower():
            raise ValueError(f"command name must be non-empty lowercase: {spec.name!r}")
        if spec.name in self._commands:
            raise ValueError(f"command already registered: /{spec.name}")
        self._commands[spec.name] = spec
        for alias in spec.aliases:
            if alias in self._aliases or alias in self._commands:
                logger.warning("alias %r conflicts, skipping (%s)", alias, spec.name)
                continue
            self._aliases[alias] = spec.name

    def command(self, name: str) -> Optional[CommandSpec]:
        """Look up by canonical name or alias (case-insensitive)."""
        key = name.lower().lstrip("/")
        if key in self._commands:
            return self._commands[key]
        canonical = self._aliases.get(key)
        return self._commands.get(canonical) if canonical else None

    def has(self, name: str) -> bool:
        return self.command(name) is not None

    # -------------------------------------------------------------- listing
    def names(self, include_hidden: bool = False) -> List[str]:
        out = [c.name for c in self._commands.values()
               if include_hidden or not c.hidden]
        return sorted(out)

    def specs(self, category: Optional[str] = None,
              include_hidden: bool = False) -> List[CommandSpec]:
        out = [c for c in self._commands.values()
               if (include_hidden or not c.hidden)
               and (category is None or c.category == category)]
        return sorted(out, key=lambda c: c.name)

    def categories(self) -> List[str]:
        return sorted({c.category for c in self._commands.values()})

    def help_all(self) -> str:
        lines = ["CERBERUS commands — shared by CLI, Web UI, and API"]
        for cat in self.categories():
            lines.append("")
            lines.append(f"  {cat}")
            for spec in self.specs(category=cat):
                lines.append(f"    /{spec.name:<14} {spec.description}")
        return "\n".join(lines)

    # ------------------------------------------------------------- dispatch
    def invoke(self, name: str, ctx, parsed) -> CommandResult:
        """Invoke a handler with uniform error capture."""
        spec = self.command(name)
        if spec is None:
            return CommandResult.failure(name, f"unknown command: /{name}")
        try:
            result = spec.handler(ctx, parsed)
        except PermissionError as e:
            return CommandResult.blocked_result(name, str(e))
        except Exception as e:  # noqa: BLE001 — uniform envelope
            logger.exception("command /%s failed", name)
            return CommandResult.failure(name, f"{type(e).__name__}: {e}")
        if isinstance(result, CommandResult):
            return result
        if isinstance(result, dict):
            return CommandResult.success(name, data=result)
        return CommandResult.success(name, data={"result": result})


# Global registry instance — all hosts share this one.
_REGISTRY = CommandRegistry()


def get_registry() -> CommandRegistry:
    return _REGISTRY


def reset_registry() -> None:
    """Test hook: clear the global registry (tests re-register handlers)."""
    global _REGISTRY
    _REGISTRY = CommandRegistry()
