"""
Improvement Proposal for the Self-Improvement subsystem.

Every proposed self-modification has:
- Proposal ID
- Reason
- Files changed
- Tests
- Benchmark
- Before score
- After score
- Risk
- Rollback commit
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ProposalStatus(Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"


@dataclass
class ImprovementProposal:
    """A proposed code change to the orchestrator."""

    reason: str
    files_changed: List[str] = field(default_factory=list)
    tests: List[str] = field(default_factory=list)
    benchmark: str = ""
    before_score: float = 0.0
    after_score: float = 0.0
    risk: str = "low"  # low, medium, high
    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = ProposalStatus.DRAFT.value
    patch: str = ""
    rollback_commit: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reviewed_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "proposal_id": self.proposal_id,
            "reason": self.reason,
            "files_changed": self.files_changed,
            "tests": self.tests,
            "benchmark": self.benchmark,
            "before_score": self.before_score,
            "after_score": self.after_score,
            "risk": self.risk,
            "status": self.status,
            "patch": self.patch,
            "rollback_commit": self.rollback_commit,
            "created_at": self.created_at,
            "reviewed_at": self.reviewed_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImprovementProposal":
        """Deserialize from dict."""
        return cls(
            proposal_id=data.get("proposal_id", str(uuid.uuid4())),
            reason=data.get("reason", ""),
            files_changed=data.get("files_changed", []),
            tests=data.get("tests", []),
            benchmark=data.get("benchmark", ""),
            before_score=data.get("before_score", 0.0),
            after_score=data.get("after_score", 0.0),
            risk=data.get("risk", "low"),
            status=data.get("status", ProposalStatus.DRAFT.value),
            patch=data.get("patch", ""),
            rollback_commit=data.get("rollback_commit", ""),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            reviewed_at=data.get("reviewed_at", ""),
            metadata=data.get("metadata", {}),
        )