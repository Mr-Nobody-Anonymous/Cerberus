"""
Analyst Agent for the Cyber AI Orchestrator.

Analyzes findings, evidence, and reconnaissance data to identify
potential vulnerabilities and prioritize risks.
"""

import logging
from typing import Any, Dict, List, Optional

from ..base import BaseAgent
from .prompts import build_analysis_prompt

logger = logging.getLogger(__name__)


class AnalystAgent(BaseAgent):
    """
    Analysis agent that processes findings and identifies vulnerabilities.

    Routes analysis tasks to strong reasoning models for deep analysis,
    and uses the verifier agent to challenge conclusions.
    """

    def __init__(self, **kwargs):
        super().__init__(name="analyst", **kwargs)

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze findings and evidence.

        Args:
            task: Dict with keys:
                - target_id: Authorized target ID
                - session_id: Current session ID
                - findings: List of findings to analyze
                - evidence: Evidence data
                - hypothesis: Optional hypothesis to test

        Returns:
            Analysis result dict
        """
        target_id = task.get("target_id", "")
        session_id = task.get("session_id", "")
        findings = task.get("findings", [])
        evidence = task.get("evidence", [])
        hypothesis = task.get("hypothesis", "")

        # Retrieve relevant past experiences
        experiences = []
        if self.memory and findings:
            experiences = self.memory.search_experiences(
                findings[0].get("observation", "") if findings else "analysis",
                limit=3,
            )

        # Build analysis prompt
        relevant = ""
        if experiences:
            relevant = "\n".join(
                f"- {e.get('observation', '')} (result: {e.get('result', '')}, score: {e.get('score', 0)})"
                for e in experiences
            )

        findings_text = ""
        if findings:
            for f in findings:
                findings_text += f"\n- Observation: {f.get('observation', '')}\n  Evidence: {f.get('evidence', [])}"

        evidence_text = ""
        if evidence:
            for e in evidence:
                evidence_text += f"\n- {e.get('type', 'evidence')}: {str(e.get('content', ''))[:500]}"

        prompt = build_analysis_prompt(
            target_id=target_id,
            hypothesis=hypothesis,
            findings_text=findings_text,
            evidence_text=evidence_text,
            experiences_text=relevant,
        )

        llm_response = await self._llm_call(prompt, task_type="reasoning")

        result = {
            "session_id": session_id,
            "target_id": target_id,
            "analysis": llm_response,
            "findings_count": len(findings),
            "evidence_count": len(evidence),
            "experiences_used": len(experiences),
        }

        # Log
        if self.logger and session_id:
            self.logger.log_event(session_id, "planner", {
                "agent": self.name,
                "findings_count": len(findings),
                "evidence_count": len(evidence),
            })

        # Record experience
        self._record_experience(
            session_id=session_id,
            target_id=target_id,
            observation=f"Analyzed {len(findings)} findings with {len(evidence)} evidence items",
            hypothesis=hypothesis or "Analysis will reveal prioritized risks",
            action="analysis",
            tool="analyst_agent",
            result="success",
            evidence=evidence,
            confidence=0.7,
        )

        return result
