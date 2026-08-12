"""
Researcher Agent for the Cyber AI Orchestrator.

Gathers information about targets, technologies, and vulnerabilities.
Routes research tasks to appropriate models and leverages tool adapters.
"""

import logging
from typing import Any, Dict, List, Optional

from ..base import BaseAgent

logger = logging.getLogger(__name__)


class ResearcherAgent(BaseAgent):
    """
    Research agent that gathers intelligence about targets and objectives.

    Uses vulnerability research models for deep analysis and fast models
    for classification and summarization of gathered information.
    """

    def __init__(self, **kwargs):
        super().__init__(name="researcher", **kwargs)

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Research a target or topic.

        Args:
            task: Dict with keys:
                - target: Target identifier or URL
                - topic: What to research
                - session_id: Current session ID
                - target_id: Authorized target ID (if target-based)

        Returns:
            Research result dict
        """
        target = task.get("target", "")
        topic = task.get("topic", "")
        target_id = task.get("target_id", "")
        session_id = task.get("session_id", "")

        # Retrieve relevant past experiences
        experiences = []
        query = f"{target} {topic}".strip()
        if self.memory:
            experiences = self.memory.search_experiences(query, limit=5)

        # Generate research prompt
        relevant = ""
        if experiences:
            relevant = "\n".join(
                f"- {e.get('observation', '')} (result: {e.get('result', '')})"
                for e in experiences
            )

        prompt = (
            f"You are a cybersecurity research agent. Research the following topic.\n\n"
            f"Target: {target}\n"
            f"Topic: {topic}\n"
            f"Target ID: {target_id}\n"
            f"\nPast relevant experiences:\n{relevant if relevant else 'None found.'}\n"
            f"\nProvide a structured summary of:\n"
            f"1. What is known about this target/topic\n"
            f"2. Known vulnerabilities or weaknesses\n"
            f"3. Recommended next steps\n"
            f"4. Tools that would be useful for further investigation\n"
        )

        llm_response = await self._llm_call(prompt, task_type="vulnerability_research")

        result = {
            "session_id": session_id,
            "target": target,
            "topic": topic,
            "research": llm_response,
            "relevant_experiences": len(experiences),
            "findings": [],
        }

        # Log
        if self.logger and session_id:
            self.logger.log_event(session_id, "planner", {
                "agent": self.name,
                "target": target,
                "topic": topic,
                "response_length": len(llm_response),
            })

        # Record experience
        self._record_experience(
            session_id=session_id,
            target_id=target_id or target,
            observation=f"Researched {topic} for {target}",
            hypothesis="Research will reveal relevant vulnerabilities or attack paths",
            action="research",
            tool="researcher_agent",
            result="success",
            confidence=0.6,
            lessons=[],
        )

        return result
