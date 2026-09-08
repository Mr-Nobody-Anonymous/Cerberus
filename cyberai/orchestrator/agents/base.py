"""
Base agent class for the Cyber AI Orchestrator.

All agent types inherit from BaseAgent, which provides:
- LLM gateway access (via model routing)
- Tool registry access (via tool gateway)
- Memory manager access (for experience retrieval)
- Session logger integration
- Task execution context
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _event_store():
    """Lazily fetch the shared EventStore (spec §24) — never fatal."""
    try:
        from cyberai.orchestrator.event_store import get_event_store
        return get_event_store()
    except Exception:  # noqa: BLE001 — events are advisory
        return None


class BaseAgent:
    """
    Base class for all orchestrator agents.

    Each agent receives references to the shared platform services
    (model router, tool registry, memory, policy) and implements
    an async run() method that processes a task.
    """

    def __init__(
        self,
        name: str,
        model_router=None,
        tool_registry=None,
        memory_manager=None,
        policy_engine=None,
        session_logger=None,
        llm_gateway=None,
    ):
        self.name = name
        self.model_router = model_router
        self.tool_registry = tool_registry
        self.memory = memory_manager
        self.policy = policy_engine
        self.logger = session_logger
        self.llm_gateway = llm_gateway

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task. Must be implemented by subclasses.

        Args:
            task: Task specification dict

        Returns:
            Result dict
        """
        raise NotImplementedError(f"Agent {self.name} must implement run()")

    async def _get_gateway(self):
        """Return the shared LLM gateway (lazily created if not injected)."""
        if self.llm_gateway is None:
            from cyberai.llm_gateway import LLMGateway

            self.llm_gateway = LLMGateway()
        return self.llm_gateway

    async def _llm_call(self, prompt: str, task_type: str = "default", **kwargs) -> str:
        """
        Make an LLM call through the gateway's transport fallback chain
        (LiteLLM proxy -> direct Ollama -> direct provider API).

        Args:
            prompt: The prompt text
            task_type: Task type for routing (e.g. "planning", "reasoning")
            **kwargs: Additional parameters forwarded to complete()

        Returns:
            LLM response text ("" on failure — never fabricated)
        """
        if self.logger:
            self.logger.log_event(
                "",
                "model_calls",
                {
                    "agent": self.name,
                    "task_type": task_type,
                    "prompt": prompt[:500],
                    "kwargs": {k: str(v)[:200] for k, v in kwargs.items()},
                },
            )

        try:
            gateway = await self._get_gateway()
            store = _event_store()
            if store is not None:
                store.publish("model.started", {
                    "agent": self.name, "task_type": task_type,
                }, agent=self.name)
            response = await gateway.complete(role=task_type, prompt=prompt, **kwargs)
            if store is not None:
                ok = bool(response.get("success"))
                store.publish(
                    "model.completed" if ok else "model.failed", {
                        "agent": self.name,
                        "task_type": task_type,
                        "model": response.get("model", ""),
                        "transport": response.get("transport", ""),
                        "latency_ms": response.get("latency_ms"),
                        "error": response.get("message", "") if not ok else "",
                    }, agent=self.name)
            if not response.get("success"):
                logger.error(
                    "LLM call failed in %s (task_type=%s): errors=%s blocked=%s",
                    self.name, task_type,
                    response.get("errors", []), response.get("blocked", []),
                )
                return f"[LLM_UNAVAILABLE: {response.get('message', 'all hops failed')}]"
            return response.get("content", "")
        except Exception as e:  # noqa: BLE001 — structured, logged failure
            logger.error("LLM call raised in %s: %s", self.name, e)
            return f"[LLM_ERROR: {e}]"

    def _record_experience(
        self,
        session_id: str,
        target_id: str,
        observation: str,
        hypothesis: str,
        action: str,
        tool: str,
        result: str,
        evidence: Optional[List] = None,
        confidence: float = 0.0,
        lessons: Optional[List] = None,
        score: float = 0.0,
    ) -> Optional[str]:
        """Record an experience in the memory system."""
        if not self.memory:
            return None

        return self.memory.store_experience({
            "session_id": session_id,
            "target_id": target_id,
            "target_type": "authorized_lab",
            "environment": "authorized_lab",
            "observation": observation,
            "hypothesis": hypothesis,
            "action": action,
            "tool": tool,
            "result": result,
            "evidence": evidence or [],
            "confidence": confidence,
            "lessons": lessons or [],
            "score": score,
        })
