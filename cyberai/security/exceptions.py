"""Security exception hierarchy for CERBERUS.

Raised by the sandbox and policy gate. Every one of these is a hard stop —
callers must never silently swallow these; they are logged and surfaced.
"""


class SecurityError(Exception):
    """Base class for all CERBERUS security violations."""


class CommandInjectionError(SecurityError):
    """Raised when an argument contains shell metacharacters that could
    enable command injection. Rejected BEFORE any subprocess execution."""


class ResourceLimitError(SecurityError):
    """Raised when a sandboxed process exceeds its wall-clock or memory limit."""


class PolicyDeniedError(SecurityError):
    """Raised when the policy engine denies an action against a target.
    The action was NOT performed."""
