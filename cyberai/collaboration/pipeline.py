"""
Agent Pipeline for multi-agent collaboration.

Coordinates multiple agents working on the same task.
Each agent receives only relevant context, not every previous output.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PipelineStep:
    """A step in the agent pipeline."""

    agent_name: str
    capability: str
    description: str = ""
    input_filter: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    output_key: str = ""
    result: Optional[Dict[str, Any]] = None
    status: str = "pending"  # pending, running, completed, failed


class AgentPipeline:
    """
    Coordinates a sequence of agents working on the same task.

    Each agent receives only the relevant context from the task state,
    not every previous output. This prevents context bloat.
    """

    def __init__(self, task: Any = None):
        self.task = task
        self.steps: List[PipelineStep] = []
        self._context: Dict[str, Any] = {}
        # Optional cooperative-cancellation probe, checked between steps.
        self.should_cancel: Optional[Callable[[], bool]] = None

    def add_step(
        self,
        agent_name: str,
        capability: str,
        description: str = "",
        input_filter: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        output_key: str = "",
    ) -> PipelineStep:
        """Add a step to the pipeline."""
        step = PipelineStep(
            agent_name=agent_name,
            capability=capability,
            description=description,
            input_filter=input_filter,
            output_key=output_key or agent_name,
        )
        self.steps.append(step)
        return step

    def _build_context_for_step(self, step: PipelineStep) -> Dict[str, Any]:
        """
        Build the context for a specific step.

        Only includes relevant information:
        - Task objective and scope
        - Previous step results (filtered)
        - Relevant observations
        - Relevant evidence
        """
        context = {
            "objective": self.task.objective if self.task else "",
            "scope": self.task.scope if self.task else "authorized_lab",
            "environment": self.task.environment if self.task else "authorized_lab",
        }

        # Include previous step results
        for prev_step in self.steps:
            if prev_step.status == "completed" and prev_step.result:
                context[prev_step.output_key] = prev_step.result

        # Include relevant observations
        if self.task and self.task.observations:
            context["observations"] = self.task.observations[-5:]

        # Include relevant evidence
        if self.task and self.task.evidence:
            context["evidence"] = self.task.evidence[-5:]

        # Apply custom input filter if provided
        if step.input_filter:
            context = step.input_filter(context)

        return context

    async def run(self, agent_executor: Callable[[str, Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run the pipeline.

        Args:
            agent_executor: Async callable that takes (agent_name, context)
                            and returns a result dict

        Returns:
            Pipeline result dict
        """
        results = {}
        for step in self.steps:
            # Cooperative cancellation point — checked between steps so an
            # in-flight agent call is allowed to finish, but no new step starts.
            if self.should_cancel is not None:
                try:
                    if self.should_cancel():
                        for s in self.steps:
                            if s.status == "pending":
                                s.status = "cancelled"
                        logger.info("Pipeline cancelled by operator between steps")
                        return {
                            "steps": [
                                {
                                    "agent": s.agent_name,
                                    "capability": s.capability,
                                    "status": s.status,
                                }
                                for s in self.steps
                            ],
                            "results": results,
                            "cancelled": True,
                        }
                except Exception as e:  # noqa: BLE001 — probe must never kill the run
                    logger.debug(f"Cancellation probe failed: {e}")
            step.status = "running"
            context = self._build_context_for_step(step)
            try:
                result = await agent_executor(step.agent_name, context)
                step.result = result
                step.status = "completed"
                results[step.output_key] = result
                logger.info(f"Pipeline step {step.agent_name} completed")
            except Exception as e:
                step.status = "failed"
                step.result = {"error": str(e)}
                results[step.output_key] = {"error": str(e)}
                logger.error(f"Pipeline step {step.agent_name} failed: {e}")

        return {
            "steps": [
                {
                    "agent": s.agent_name,
                    "capability": s.capability,
                    "status": s.status,
                }
                for s in self.steps
            ],
            "results": results,
        }

    def get_step_result(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get the result of a specific step."""
        for step in self.steps:
            if step.agent_name == agent_name:
                return step.result
        return None

    def get_all_results(self) -> Dict[str, Any]:
        """Get all step results."""
        return {
            step.output_key: step.result
            for step in self.steps
            if step.result is not None
        }

    def clear(self) -> None:
        """Clear the pipeline."""
        self.steps.clear()
