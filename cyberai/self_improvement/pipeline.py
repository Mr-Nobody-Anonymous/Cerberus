"""
Self-Improvement Pipeline.

Implements the controlled pipeline for AI-proposed code changes:
1. AI proposes change
2. Patch generated
3. Static checks
4. Unit tests
5. Integration tests
6. Security checks
7. Sandbox evaluation
8. Benchmark comparison
9. Human approval
10. Git branch
11. Merge

The AI must NOT automatically overwrite its production code.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .proposal import ImprovementProposal, ProposalStatus

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).parent.parent.parent


class SelfImprovementPipeline:
    """
    Manages the self-improvement proposal pipeline.

    Every proposed change goes through validation before it can be
    applied. The AI cannot directly modify production code.
    """

    def __init__(self, proposals_dir: Optional[Path] = None):
        self.proposals_dir = proposals_dir or WORKSPACE_ROOT / "memory" / "self_improvement" / "proposals"
        self.proposals_dir.mkdir(parents=True, exist_ok=True)
        self._proposals: Dict[str, ImprovementProposal] = {}
        self._load()

    def _load(self) -> None:
        """Load proposals from disk."""
        for f in self.proposals_dir.glob("*.json"):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                proposal = ImprovementProposal.from_dict(data)
                self._proposals[proposal.proposal_id] = proposal
            except Exception as e:
                logger.warning(f"Failed to load proposal {f}: {e}")

    def _save(self, proposal: ImprovementProposal) -> None:
        """Save a proposal to disk."""
        path = self.proposals_dir / f"{proposal.proposal_id}.json"
        with open(path, "w") as f:
            json.dump(proposal.to_dict(), f, indent=2)

    def create_proposal(
        self,
        reason: str,
        files_changed: List[str],
        patch: str = "",
        tests: Optional[List[str]] = None,
        benchmark: str = "",
        before_score: float = 0.0,
        risk: str = "low",
    ) -> ImprovementProposal:
        """
        Create a new improvement proposal.

        Args:
            reason: Why this change is proposed
            files_changed: Files that would be modified
            patch: The proposed patch
            tests: Tests to run
            benchmark: Benchmark to compare
            before_score: Current system score
            risk: Risk level (low, medium, high)

        Returns:
            The created proposal
        """
        proposal = ImprovementProposal(
            reason=reason,
            files_changed=files_changed,
            patch=patch,
            tests=tests or [],
            benchmark=benchmark,
            before_score=before_score,
            risk=risk,
        )
        self._proposals[proposal.proposal_id] = proposal
        self._save(proposal)
        logger.info(f"Created improvement proposal {proposal.proposal_id}")
        return proposal

    def run_validation(self, proposal: ImprovementProposal) -> Dict[str, Any]:
        """
        Run validation checks on a proposal.

        Steps:
        1. Static checks (syntax)
        2. Unit tests
        3. Security checks

        Returns:
            Validation result dict
        """
        results = {
            "static_checks": self._run_static_checks(proposal),
            "unit_tests": self._run_unit_tests(proposal),
            "security_checks": self._run_security_checks(proposal),
        }
        all_passed = all(r.get("passed", False) for r in results.values())
        results["all_passed"] = all_passed
        return results

    def _run_static_checks(self, proposal: ImprovementProposal) -> Dict[str, Any]:
        """Run static checks (Python syntax validation)."""
        passed = True
        errors = []
        for file_path in proposal.files_changed:
            full_path = WORKSPACE_ROOT / file_path
            if not full_path.exists():
                errors.append(f"File not found: {file_path}")
                passed = False
                continue
            if full_path.suffix == ".py":
                try:
                    compile(full_path.read_text(encoding="utf-8"), str(full_path), "exec")
                except SyntaxError as e:
                    errors.append(f"Syntax error in {file_path}: {e}")
                    passed = False
        return {"passed": passed, "errors": errors}

    def _run_unit_tests(self, proposal: ImprovementProposal) -> Dict[str, Any]:
        """Run unit tests for the proposal."""
        if not proposal.tests:
            return {"passed": True, "message": "No tests specified", "skipped": True}
        passed = True
        errors = []
        for test in proposal.tests:
            try:
                result = subprocess.run(
                    ["python", "-m", "pytest", test, "-q"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(WORKSPACE_ROOT),
                )
                if result.returncode != 0:
                    passed = False
                    errors.append(f"Test failed: {test}\n{result.stdout[-500:]}\n{result.stderr[-500:]}")
            except Exception as e:
                passed = False
                errors.append(f"Test error: {test}: {e}")
        return {"passed": passed, "errors": errors}

    def _run_security_checks(self, proposal: ImprovementProposal) -> Dict[str, Any]:
        """Run basic security checks on the proposal."""
        passed = True
        errors = []
        # Check for dangerous patterns in the patch
        dangerous_patterns = [
            "os.system(",
            "subprocess.call(",
            "subprocess.Popen(",
            "eval(",
            "exec(",
            "pickle.loads(",
            "yaml.load(",
        ]
        for pattern in dangerous_patterns:
            if pattern in proposal.patch:
                errors.append(f"Dangerous pattern found: {pattern}")
                passed = False
        return {"passed": passed, "errors": errors}

    def compare_benchmark(self, proposal: ImprovementProposal, after_score: float) -> bool:
        """
        Compare benchmark scores.

        A candidate is accepted only if it beats or preserves the baseline.

        Args:
            proposal: The proposal
            after_score: The score after the change

        Returns:
            True if the candidate should be accepted
        """
        proposal.after_score = after_score
        self._save(proposal)
        return after_score >= proposal.before_score

    def approve(self, proposal: ImprovementProposal) -> None:
        """Approve a proposal for application."""
        proposal.status = ProposalStatus.APPROVED.value
        proposal.reviewed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        self._save(proposal)
        logger.info(f"Approved proposal {proposal.proposal_id}")

    def reject(self, proposal: ImprovementProposal, reason: str = "") -> None:
        """Reject a proposal."""
        proposal.status = ProposalStatus.REJECTED.value
        proposal.metadata["rejection_reason"] = reason
        proposal.reviewed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        self._save(proposal)
        logger.info(f"Rejected proposal {proposal.proposal_id}: {reason}")

    def apply(self, proposal: ImprovementProposal) -> bool:
        """
        Apply an approved proposal.

        Creates a git branch, applies the patch, and records the
        rollback commit. Does NOT merge automatically.

        Args:
            proposal: The approved proposal

        Returns:
            True if applied successfully
        """
        if proposal.status != ProposalStatus.APPROVED.value:
            logger.warning(f"Cannot apply proposal {proposal.proposal_id} - not approved")
            return False

        try:
            # Create a git branch
            branch_name = f"improvement-{proposal.proposal_id[:8]}"
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                capture_output=True,
                text=True,
                cwd=str(WORKSPACE_ROOT),
                check=True,
            )

            # Record the rollback commit (current HEAD)
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(WORKSPACE_ROOT),
                check=True,
            )
            proposal.rollback_commit = result.stdout.strip()

            # Apply the patch if provided
            if proposal.patch:
                patch_file = self.proposals_dir / f"{proposal.proposal_id}.patch"
                patch_file.write_text(proposal.patch)
                subprocess.run(
                    ["git", "apply", str(patch_file)],
                    capture_output=True,
                    text=True,
                    cwd=str(WORKSPACE_ROOT),
                    check=True,
                )

            proposal.status = ProposalStatus.APPLIED.value
            self._save(proposal)
            logger.info(f"Applied proposal {proposal.proposal_id} on branch {branch_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to apply proposal {proposal.proposal_id}: {e}")
            return False

    def rollback(self, proposal: ImprovementProposal) -> bool:
        """
        Roll back an applied proposal.

        Args:
            proposal: The applied proposal

        Returns:
            True if rolled back successfully
        """
        if proposal.status != ProposalStatus.APPLIED.value:
            logger.warning(f"Cannot rollback proposal {proposal.proposal_id} - not applied")
            return False

        try:
            if proposal.rollback_commit:
                subprocess.run(
                    ["git", "checkout", proposal.rollback_commit, "--", "."],
                    capture_output=True,
                    text=True,
                    cwd=str(WORKSPACE_ROOT),
                    check=True,
                )
            proposal.status = ProposalStatus.ROLLED_BACK.value
            self._save(proposal)
            logger.info(f"Rolled back proposal {proposal.proposal_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to rollback proposal {proposal.proposal_id}: {e}")
            return False

    def get_proposal(self, proposal_id: str) -> Optional[ImprovementProposal]:
        """Get a proposal by ID."""
        return self._proposals.get(proposal_id)

    def list_proposals(self, status: Optional[str] = None) -> List[ImprovementProposal]:
        """List proposals, optionally filtered by status."""
        proposals = list(self._proposals.values())
        if status:
            proposals = [p for p in proposals if p.status == status]
        return sorted(proposals, key=lambda p: p.created_at, reverse=True)

    def get_status(self) -> Dict[str, Any]:
        """Get pipeline status."""
        return {
            "total_proposals": len(self._proposals),
            "approved": sum(1 for p in self._proposals.values() if p.status == ProposalStatus.APPROVED.value),
            "applied": sum(1 for p in self._proposals.values() if p.status == ProposalStatus.APPLIED.value),
            "rejected": sum(1 for p in self._proposals.values() if p.status == ProposalStatus.REJECTED.value),
            "rolled_back": sum(1 for p in self._proposals.values() if p.status == ProposalStatus.ROLLED_BACK.value),
        }