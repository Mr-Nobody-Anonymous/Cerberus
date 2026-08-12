"""
Standard adapter interface for the Cyber AI Orchestrator.

All security tool adapters must implement this interface to be
integrated with the master orchestrator.
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