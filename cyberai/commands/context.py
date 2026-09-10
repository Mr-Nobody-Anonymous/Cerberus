"""CommandContext — safe backend accessors shared by every host.

The Web UI, CLI, and API never import orchestrator subsystems directly in
their command paths; they go through this context so that:

1. Accessor lifecycle is uniform (construct → use → close).
2. Authorization always flows through PolicyEngine (never bypassed).
3. Tests can construct a context against temp databases.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CommandContext:
    """Bundles backend accessors + per-invocation state for handlers."""

    def __init__(self, workspace_root=None, event_publisher=None,
                 mission_runner=None, orchestrator_holder: Optional[Dict] = None):
        from pathlib import Path
        self.workspace_root = workspace_root or _default_root()
        # Optional async event publisher (Web UI passes EVENT_BUS.publish).
        self.event_publisher = event_publisher
        # Optional mission launcher (Web UI passes its asyncio.create_task
        # runner factory so /run behaves identically on every surface).
        self.mission_runner = mission_runner
        # Shared holder dict for the live orchestrator instance (Web UI).
        self.orchestrator_holder = orchestrator_holder or {}

    # ---------------------------------------------------------- accessors
    # Each accessor constructs a fresh instance; the caller (dispatcher)
    # closes it via close_resource() in a finally block. Handlers use
    # ``with ctx.policy() as pe:`` style helpers below.

    def policy(self):
        from cyberai.orchestrator import PolicyEngine
        return PolicyEngine()

    def memory_manager(self):
        from cyberai.orchestrator import MemoryManager
        return MemoryManager()

    def memory_store(self):
        from cyberai.memory.memory_store import MemoryStore
        return MemoryStore()

    def tools(self):
        from cyberai.orchestrator import ToolRegistry
        return ToolRegistry()

    def gateway(self):
        from cyberai.llm_gateway import LLMGateway
        return LLMGateway()

    def evidence(self):
        from cyberai.orchestrator.evidence.evidence import EvidenceManager
        return EvidenceManager()

    def knowledge(self):
        from cyberai.orchestrator.knowledge.knowledge_loader import KnowledgeBase
        return KnowledgeBase()

    def adapters(self):
        from cyberai.orchestrator.adapters.adapter_manager import AdapterManager
        return AdapterManager()

    def tracker(self):
        from cyberai.meta_learning.tracker import PerformanceTracker
        return PerformanceTracker()

    def capabilities(self):
        from cyberai.capabilities.registry import CapabilityRegistry
        return CapabilityRegistry()

    def event_store(self):
        from cyberai.orchestrator.event_store import get_event_store
        return get_event_store()

    # ------------------------------------------------------------ helpers
    def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish an event when a publisher is attached (no-op otherwise)."""
        if self.event_publisher:
            try:
                self.event_publisher(event_type, data)
            except Exception:  # noqa: BLE001 — publishing must never break a command
                logger.exception("event publish failed for %s", event_type)

    def status_snapshot(self) -> Dict[str, Any]:
        """Lightweight platform status (no long-lived orchestrator)."""
        from cyberai import CyberAIOrchestrator
        orch = CyberAIOrchestrator(simulate=True, local_only=True)
        try:
            return orch.get_status()
        finally:
            orch.close()

    @staticmethod
    def close_resource(resource) -> None:
        """Close any backend accessor uniformly (None-safe)."""
        if resource is None:
            return
        close = getattr(resource, "close", None)
        if callable(close):
            try:
                close()
            except Exception:  # noqa: BLE001
                logger.exception("failed closing %r", resource)


def _default_root():
    from cyberai.config import WORKSPACE_ROOT
    return WORKSPACE_ROOT
