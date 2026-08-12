"""
Verifier Agent for the Cyber AI Orchestrator.

Challenges important conclusions and ensures findings have proper
evidence before being accepted. Uses the finding states:
UNVERIFIED, LIKELY, VERIFIED, REJECTED.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Finding states
UNVERIFIED = "UNVERIFIED"
LIKELY = "LIKELY"
VERIFIED = "VERIFIED"
REJECTED = "REJECTED"


class VerifierAgent:
    """
    Verifies findings by challenging conclusions and checking evidence.

    The verifier asks:
    - What evidence proves this?
    - Is the evidence sufficient?
    - Could there be alternative explanations?
    - Was the test performed correctly?
    """

    def __init__(self, **kwargs):
        self.memory = kwargs.get("memory_manager")
        self.model_router = kwargs.get("model_router")
        self.tool_registry = kwargs.get("tool_registry")
        self.policy = kwargs.get("policy_engine")
        self.logger = kwargs.get("session_logger")

    async def verify_finding(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify a finding by checking its evidence.

        Args:
            finding: Dict with observation, evidence, confidence, source, etc.

        Returns:
            Updated finding with verification status
        """
        observation = finding.get("observation", "")
        evidence = finding.get("evidence", [])
        confidence = finding.get("confidence", 0.0)

        # Check if evidence exists
        if not evidence:
            finding["status"] = UNVERIFIED
            finding["verification_notes"] = "No evidence provided"
            return finding

        # Check evidence quality
        evidence_quality = self._assess_evidence(evidence)

        if evidence_quality["sufficient"]:
            finding["status"] = VERIFIED
            finding["verification_notes"] = (
                f"Evidence sufficient: {evidence_quality['reason']}"
            )
        elif evidence_quality["partial"]:
            finding["status"] = LIKELY
            finding["verification_notes"] = (
                f"Evidence partial: {evidence_quality['reason']}"
            )
        else:
            finding["status"] = REJECTED
            finding["verification_notes"] = (
                f"Evidence insufficient: {evidence_quality['reason']}"
            )

        # Update confidence based on verification
        if finding["status"] == VERIFIED:
            finding["confidence"] = min(confidence + 0.2, 1.0)
        elif finding["status"] == REJECTED:
            finding["confidence"] = max(confidence - 0.3, 0.0)

        # Store in memory if available
        if self.memory:
            finding_id = self.memory.store_finding(finding)
            finding["id"] = finding_id

        logger.info(
            f"Verified finding: {observation[:50]}... -> {finding['status']}"
        )
        return finding

    def _assess_evidence(self, evidence: List[Any]) -> Dict[str, Any]:
        """
        Assess the quality of evidence.

        Args:
            evidence: List of evidence items

        Returns:
            Dict with sufficient, partial, reason keys
        """
        if not evidence:
            return {
                "sufficient": False,
                "partial": False,
                "reason": "No evidence items",
            }

        # Count evidence items with actual content
        meaningful = [
            e for e in evidence
            if isinstance(e, dict) and e.get("content")
        ]

        if len(meaningful) >= 2:
            return {
                "sufficient": True,
                "partial": True,
                "reason": f"{len(meaningful)} evidence items with content",
            }
        elif len(meaningful) == 1:
            return {
                "sufficient": False,
                "partial": True,
                "reason": "Only 1 evidence item with content",
            }
        else:
            return {
                "sufficient": False,
                "partial": False,
                "reason": "Evidence items lack content",
            }

    async def challenge_conclusion(
        self,
        conclusion: str,
        evidence: List[Dict[str, Any]],
        tool_output: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Challenge a conclusion by asking what evidence proves it.

        Args:
            conclusion: The conclusion to challenge
            evidence: List of evidence dicts
            tool_output: Optional raw tool output

        Returns:
            Dict with challenge result
        """
        challenges = []

        # Challenge 1: Is there direct evidence?
        if not evidence:
            challenges.append("No direct evidence provided for this conclusion")

        # Challenge 2: Is the evidence from a reliable source?
        for e in evidence:
            source = e.get("source", "unknown")
            if source == "unknown":
                challenges.append(f"Evidence source unknown: {e.get('content', '')[:50]}")

        # Challenge 3: Is there tool output to confirm?
        if not tool_output and not evidence:
            challenges.append("No tool output or evidence to confirm this conclusion")

        verified = len(challenges) == 0

        return {
            "conclusion": conclusion,
            "challenges": challenges,
            "verified": verified,
            "status": VERIFIED if verified else UNVERIFIED,
        }
</content>
<task_progress>
- [x] Audit current implementation (PHASE2_AUDIT.md update needed)
- [x] Create CyberAIOrchestrator facade class (ONE AI entry point)
- [x] Wire up orchestrator: Task object, MemoryStore, LLMGateway, capabilities, agents, evolution
- [x] Add dry-run mode and simulation mode
- [x] Fix CLI: remove sys.path hacks, add task command with dry-run/simulate flags
- [x] Fix config references: docker-compose.yml, .env.example, .gitignore, .vscode/settings.json
- [x] Make adapters real: proper health checks + simulated execution fallback
- [x] Create adapter registry for dynamic loading
- [ ] Create end-to-end simulated test (cyber-ai simulate)
- [ ] Create regression/benchmark test suite
- [ ] Update PHASE2_AUDIT.md to reflect actual current state
- [ ] Create PHASE2_FINAL_STATUS.md with objective status
</task_progress>
</write_to_file>
</｜DSML｜tool_calls