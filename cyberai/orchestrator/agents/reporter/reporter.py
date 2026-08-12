"""
Reporter Agent for the Cyber AI Orchestrator.

Generates final assessment reports from collected findings, evidence,
and analysis results. Produces structured reports in multiple formats.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import BaseAgent

logger = logging.getLogger(__name__)


class ReporterAgent(BaseAgent):
    """
    Report generation agent that synthesizes findings into reports.

    Routes report generation to fast local models for summarization.
    """

    def __init__(self, **kwargs):
        super().__init__(name="reporter", **kwargs)

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a final report for an assessment.

        Args:
            task: Dict with keys:
                - target_id: Authorized target ID
                - session_id: Current session ID
                - findings: List of findings
                - evidence: Evidence data
                - analysis: Analysis results
                - objective: The original assessment objective

        Returns:
            Report dict with generated content
        """
        target_id = task.get("target_id", "")
        session_id = task.get("session_id", "")
        findings = task.get("findings", [])
        evidence = task.get("evidence", [])
        analysis = task.get("analysis", "")
        objective = task.get("objective", "")

        now = datetime.now(timezone.utc).isoformat()

        # Build findings summary
        findings_summary = ""
        if findings:
            for f in findings:
                findings_summary += (
                    f"\n- Status: {f.get('status', 'UNVERIFIED')}"
                    f"\n  Observation: {f.get('observation', '')}"
                    f"\n  Confidence: {f.get('confidence', 0.0)}"
                    f"\n  Source: {f.get('source', 'unknown')}\n"
                )
        else:
            findings_summary = "\nNone recorded."

        evidence_summary = ""
        if evidence:
            evidence_summary = f"\n\nEvidence items collected: {len(evidence)}"
        else:
            evidence_summary = "\n\nNo evidence items collected."

        prompt = (
            f"You are a security report writer. Generate a professional penetration "
            f"testing report based on the following assessment data.\n\n"
            f"Objective: {objective}\n"
            f"Target: {target_id}\n"
            f"Date: {now}\n"
            f"\n--- FINDINGS ---\n{findings_summary}"
            f"\n--- ANALYSIS ---\n{analysis if analysis else 'No analysis provided.'}"
            f"\n--- EVIDENCE ---\n{evidence_summary}"
            f"\n\nGenerate a structured report with:\n"
            f"1. Executive Summary\n"
            f"2. Methodology\n"
            f"3. Findings (with severity, evidence, and verification status)\n"
            f"4. Recommendations\n"
            f"5. Conclusion\n"
            f"\nUse markdown formatting."
        )

        llm_response = await self._llm_call(prompt, task_type="report_generation")

        report = {
            "session_id": session_id,
            "target_id": target_id,
            "objective": objective,
            "generated_at": now,
            "findings_count": len(findings),
            "evidence_count": len(evidence),
            "content": llm_response,
            "status": "generated",
        }

        # Save report to session logs if logger available
        if self.logger and session_id:
            self.logger.log_event(session_id, "planner", {
                "agent": self.name,
                "findings_count": len(findings),
                "report_length": len(llm_response),
            })
            # Save evidence file
            self.logger.save_evidence(session_id, "final_report", report)

        # Record experience
        self._record_experience(
            session_id=session_id,
            target_id=target_id,
            observation=f"Generated report for objective: {objective}",
            hypothesis="Report will summarize all findings effectively",
            action="reporting",
            tool="reporter_agent",
            result="success",
            evidence=evidence,
            confidence=0.9,
        )

        return report
