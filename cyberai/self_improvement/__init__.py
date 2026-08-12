"""
Self-Improvement subsystem for the Cyber AI platform.

Provides a controlled pipeline for AI-proposed code changes:
- AI proposes change
- Patch generated
- Static checks
- Unit tests
- Integration tests
- Security checks
- Sandbox evaluation
- Benchmark comparison
- Human approval
- Git branch
- Merge

The AI must NOT automatically overwrite its production code.
"""

from .proposal import ImprovementProposal, ProposalStatus
from .pipeline import SelfImprovementPipeline

__all__ = ["ImprovementProposal", "ProposalStatus", "SelfImprovementPipeline"]