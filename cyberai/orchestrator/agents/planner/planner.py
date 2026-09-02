"""
Planner Agent for the Cyber AI Orchestrator.

Creates strategic attack plans and task decompositions based on objectives
and historical experience. Retrieves relevant past experiences from memory
to inform planning decisions.
"""

import logging
from typing import Any, Dict, List, Optional

from ..base import BaseAgent
from .prompts import build_planning_prompt

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """
    Planning agent that decomposes security objectives into actionable steps.

    Retrieves relevant past experiences from memory to inform planning.
    Routes planning requests to the strongest reasoning model.
    """

    def __init__(self, **kwargs):
        super().__init__(name="planner", **kwargs)

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a plan for a security objective.

        Args:
            task: Dict with keys:
                - objective: The security objective to plan for
                - target_id: Authorized target identifier
                - session_id: Current session ID
                - constraints: Optional list of constraints

        Returns:
            Plan dict with steps and relevant experiences
        """
        objective = task.get("objective", "")
        target_id = task.get("target_id", "")
        session_id = task.get("session_id", "")
        constraints = task.get("constraints", [])

        # Retrieve relevant past experiences
        experiences = []
        if self.memory:
            experiences = self.memory.search_experiences(objective, limit=5)

        # Generate plan using LLM
        relevant = ""
        if experiences:
            relevant = "\n\n".join(
                f"- {e.get('observation', '')} (result: {e.get('result', 'unknown')}, score: {e.get('score', 0)})"
                for e in experiences
            )

        prompt = build_planning_prompt(
            objective=objective,
            target_id=target_id,
            constraints=constraints,
            experiences_text=relevant,
        )

        llm_response = await self._llm_call(prompt, task_type="planning")

        plan = {
            "session_id": session_id,
            "objective": objective,
            "target_id": target_id,
            "model": self.model_router.route("planning") if self.model_router else "unknown",
            "steps": self._default_steps(objective, target_id),
            "relevant_experiences": [
                {
                    "id": e["id"],
                    "observation": e["observation"],
                    "result": e["result"],
                    "score": e["score"],
                }
                for e in experiences
            ],
            "constraints": constraints,
            "raw_llm_response": llm_response[:2000],  # Trim for storage
        }

        # Log
        if self.logger and session_id:
            self.logger.log_event(session_id, "planner", {
                "agent": self.name,
                "objective": objective,
                "steps_count": len(plan["steps"]),
                "experiences_used": len(experiences),
            })

        return plan

    def _default_steps(self, objective: str, target_id: str) -> List[Dict[str, Any]]:
        """Generate default plan steps as a fallback."""
        return [
            {
                "step": 1,
                "action": "research",
                "tool": "pentagi",
                "description": f"Research target {target_id} for the objective: {objective}",
                "model": "vulnerability_research",
            },
            {
                "step": 2,
                "action": "recon",
                "tool": "strix",
                "description": f"Perform reconnaissance on {target_id}",
                "model": "web_research",
            },
            {
                "step": 3,
                "action": "analysis",
                "tool": "cai",
                "description": f"Analyze findings from reconnaissance for {target_id}",
                "model": "reasoning",
            },
            {
                "step": 4,
                "action": "verification",
                "tool": "verifier",
                "description": "Verify all findings before reporting",
                "model": "verification",
            },
            {
                "step": 5,
                "action": "reporting",
                "tool": "reporter",
                "description": f"Generate final report for {objective} on {target_id}",
                "model": "report_generation",
            },
        ]
