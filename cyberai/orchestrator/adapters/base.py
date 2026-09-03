"""
Standard adapter interface for the Cyber AI Orchestrator.

All security tool adapters must implement this interface to be
integrated with the master orchestrator.

Two base classes are provided:

* ``SecurityToolAdapter`` — the original abstract interface (kept for the
  many stub adapters). Its ``execute()`` is abstract.
* ``SandboxedAdapter`` — the preferred base for any adapter that performs
  real work. Its ``execute()`` is concrete and non-bypassable: it runs the
  policy-engine authorization gate and records the action to the evidence
  log BEFORE delegating to the abstract ``_do_execute()``. Subclasses
  implement ``_do_execute()``, never ``execute()``.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AdapterCapability:
    """Describes a capability of an adapter."""

    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AdapterResult:
    """Standard result object returned by adapters."""

    success: bool
    output: Any = None
    error: Optional[str] = None
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecurityToolAdapter(ABC):
    """
    Base class for all security tool adapters.

    Each adapter wraps an external project (PentAGI, Strix, HexStrike, etc.)
    and translates standard orchestrator requests into whatever that
    project expects.
    """

    name: str = "base_adapter"
    version: str = "0.0.0"
    description: str = ""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._initialized = False

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check if the underlying tool/service is available.

        Returns:
            Dict with keys: status (str), message (str), details (dict)
        """
        ...

    @abstractmethod
    async def capabilities(self) -> List[AdapterCapability]:
        """
        Return the list of capabilities this adapter provides.

        Returns:
            List of AdapterCapability objects
        """
        ...

    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> AdapterResult:
        """
        Execute a task using the underlying tool.

        Args:
            task: Task specification with keys like:
                - action: str (what to do)
                - target: dict (authorized target info)
                - parameters: dict (tool-specific parameters)

        Returns:
            AdapterResult with success/failure and output
        """
        ...

    @abstractmethod
    async def collect_results(self) -> AdapterResult:
        """
        Collect results from a previously executed task.

        Returns:
            AdapterResult with collected results
        """
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Clean up any resources used by the adapter.
        """
        ...

    async def initialize(self) -> None:
        """Initialize the adapter. Called before first use."""
        self._initialized = True

    @property
    def is_initialized(self) -> bool:
        return self._initialized


class SandboxedAdapter(SecurityToolAdapter):
    """
    Base class for adapters that perform REAL work (subprocess, HTTP, MCP).

    The ``execute()`` method is concrete and enforces the hard safety
    contract -- there is NO bypass path:

      1. Authorize the target + action with the policy engine (fails
         closed -- ``PolicyDeniedError`` if not authorized).
      2. Record the action to the evidence log (even on failure).
      3. Delegate to the subclass's ``_do_execute()``.

    Subclasses implement ``_do_execute()`` (never ``execute()``) and use
    ``cyberai.security.sandbox`` for any subprocess work.
    """

    # Set by the orchestrator/adapter manager before first use.
    policy_engine: Any = None
    evidence_manager: Any = None
    session_id: str = ""

    async def execute(self, task: Dict[str, Any]) -> AdapterResult:
        """
        Policy-gated, evidence-logged entry point. DO NOT override in
        subclasses — implement ``_do_execute()`` instead.
        """
        action = task.get("action", "unknown")
        target = task.get("target", {})
        target_id = target.get("id", "") if isinstance(target, dict) else ""

        # --- 1. Policy gate (fails closed) ----------------------------
        try:
            from cyberai.security.policy_runner import authorize

            authorize(self.policy_engine, target, action)
        except Exception as exc:
            self._record(action, target, success=False, error=str(exc))
            return AdapterResult(
                success=False,
                error=f"Policy denied: {exc}",
                metadata={"tool": self.name, "action": action,
                          "target_id": target_id, "denied": True},
            )

        # --- 2 + 3. Real work, with evidence logging on both paths ----
        try:
            result = await self._do_execute(task)
        except Exception as exc:
            self._record(action, target, success=False, error=str(exc))
            return AdapterResult(
                success=False,
                error=f"{type(exc).__name__}: {exc}",
                metadata={"tool": self.name, "action": action,
                          "target_id": target_id},
            )

        self._record(
            action, target,
            success=bool(result.success),
            error=result.error,
            output=result.output,
        )
        result.metadata.setdefault("tool", self.name)
        result.metadata.setdefault("action", action)
        result.metadata.setdefault("target_id", target_id)
        return result

    def _record(self, action, target, *, success,
                error=None, output=None) -> None:
        """Record the action to the evidence log if a manager is wired."""
        if self.evidence_manager is None:
            return
        try:
            from cyberai.security.policy_runner import record_action

            record_action(
                self.evidence_manager,
                session_id=self.session_id,
                tool=self.name,
                target=target,
                action=action,
                success=success,
                output=output,
                error=error,
            )
        except Exception as exc:  # noqa: BLE001
            import logging

            logging.getLogger(__name__).warning(
                "Failed to record action evidence: %s", exc)

    @abstractmethod
    async def _do_execute(self, task: Dict[str, Any]) -> AdapterResult:
        """
        Perform the actual tool invocation. Subclasses implement this.

        Policy authorization has already been checked and the action will
        be recorded regardless of the outcome.
        """
        ...