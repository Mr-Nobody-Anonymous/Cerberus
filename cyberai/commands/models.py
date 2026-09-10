"""Data models for the shared command bus."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class CommandSpec:
    """Declarative description of one operator command.

    ``handler`` receives ``(ctx: CommandContext, parsed: ParsedCommand)``
    and returns a ``CommandResult`` (or a plain dict, which the dispatcher
    wraps automatically).
    """

    name: str
    category: str
    description: str
    handler: Callable[..., Any]
    aliases: List[str] = field(default_factory=list)
    usage: str = ""
    examples: List[str] = field(default_factory=list)
    # Commands that mutate state or launch missions must declare it so hosts
    # can gate them behind confirmation UIs.
    destructive: bool = False
    # Hidden commands are executed but not listed in /help output.
    hidden: bool = False

    def help_text(self) -> str:
        lines = [f"/{self.name} — {self.description}"]
        if self.usage:
            lines.append(f"  usage: /{self.usage}")
        for ex in self.examples:
            lines.append(f"  e.g.   /{ex}")
        return "\n".join(lines)


@dataclass
class ParsedCommand:
    """Result of parsing a raw operator input line.

    Supports both slash-command syntax (``/findings status=VERIFIED``)
    and plain natural-language text (``analyze lab-web-01``), which hosts
    may route to a chat/mission surface instead of the command bus.
    """

    raw: str
    name: str = ""
    args: List[str] = field(default_factory=list)
    kwargs: Dict[str, str] = field(default_factory=dict)
    is_command: bool = False

    def arg(self, index: int, default: str = "") -> str:
        """Positional argument at ``index`` ("" when absent)."""
        return self.args[index] if index < len(self.args) else default

    def kwarg(self, key: str, default: str = "") -> str:
        """Keyword argument ``key`` ("" when absent)."""
        return self.kwargs.get(key, default)


@dataclass
class CommandResult:
    """Uniform result envelope for every command invocation.

    Hosts (CLI, Web, API) render this differently but the payload is
    identical, guaranteeing surface parity.
    """

    ok: bool
    command: str
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    # Authorization/policy rejections set blocked=True (never ok=True).
    blocked: bool = False
    error: str = ""
    # Optional structured rows for table rendering in the CLI.
    rows: Optional[List[Dict[str, Any]]] = None
    columns: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "ok": self.ok,
            "command": self.command,
            "data": self.data,
            "message": self.message,
            "blocked": self.blocked,
        }
        if self.error:
            out["error"] = self.error
        if self.rows is not None:
            out["rows"] = self.rows
        if self.columns is not None:
            out["columns"] = self.columns
        return out

    @classmethod
    def success(cls, command: str, data: Optional[Dict[str, Any]] = None,
                message: str = "", **table) -> "CommandResult":
        return cls(ok=True, command=command, data=data or {}, message=message,
                   **table)

    @classmethod
    def failure(cls, command: str, error: str,
                data: Optional[Dict[str, Any]] = None) -> "CommandResult":
        return cls(ok=False, command=command, data=data or {}, error=error)

    @classmethod
    def blocked_result(cls, command: str, reason: str,
                       data: Optional[Dict[str, Any]] = None) -> "CommandResult":
        """Policy/authorization rejection — the ONLY way handlers report blocks."""
        return cls(ok=False, command=command, data=data or {},
                   error=reason, blocked=True)
