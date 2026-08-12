"""
Fitness function for the Evolution Engine.

Configurable scoring of strategy performance.
Weights are configurable and documented.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default fitness weights (configurable)
DEFAULT_WEIGHTS = {
    "success": 1.0,
    "verification": 0.8,
    "evidence_quality": 0.6,
    "repeatability": 0.5,
    "unnecessary_actions": -0.3,
    "failures": -0.5,
}


class FitnessFunction:
    """
    Computes fitness scores for strategies.

    Fitness = success + verification + evidence_quality + repeatability
              - unnecessary_actions - failures

    All weights are configurable and documented.
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or dict(DEFAULT_WEIGHTS)

    def compute(
        self,
        success: bool = False,
        verification: str = "UNVERIFIED",
        evidence_count: int = 0,
        repeatable: bool = False,
        unnecessary_actions: int = 0,
        failure_count: int = 0,
    ) -> float:
        """
        Compute a fitness score.

        Args:
            success: Whether the task succeeded
            verification: Verification state (UNVERIFIED, LIKELY, VERIFIED, REJECTED)
            evidence_count: Number of evidence items collected
            repeatable: Whether the result was repeatable
            unnecessary_actions: Number of unnecessary actions taken
            failure_count: Number of failures encountered

        Returns:
            Fitness score (higher is better)
        """
        score = 0.0

        # Success component
        score += self.weights.get("success", 1.0) * (1.0 if success else 0.0)

        # Verification component
        verification_scores = {
            "VERIFIED": 1.0,
            "LIKELY": 0.6,
            "UNVERIFIED": 0.2,
            "REJECTED": 0.0,
        }
        score += self.weights.get("verification", 0.8) * verification_scores.get(verification, 0.0)

        # Evidence quality component (normalized to 0-1)
        evidence_score = min(evidence_count / 5.0, 1.0)
        score += self.weights.get("evidence_quality", 0.6) * evidence_score

        # Repeatability component
        score += self.weights.get("repeatability", 0.5) * (1.0 if repeatable else 0.0)

        # Unnecessary actions penalty
        score += self.weights.get("unnecessary_actions", -0.3) * min(unnecessary_actions, 5)

        # Failure penalty
        score += self.weights.get("failures", -0.5) * min(failure_count, 5)

        return max(0.0, min(score, 3.0))

    def compute_from_strategy_result(
        self,
        result: Dict[str, Any],
    ) -> float:
        """
        Compute fitness from a strategy evaluation result.

        Args:
            result: Dict with keys:
                - success: bool
                - verification: str
                - evidence_count: int
                - repeatable: bool
                - unnecessary_actions: int
                - failure_count: int

        Returns:
            Fitness score
        """
        return self.compute(
            success=result.get("success", False),
            verification=result.get("verification", "UNVERIFIED"),
            evidence_count=result.get("evidence_count", 0),
            repeatable=result.get("repeatable", False),
            unnecessary_actions=result.get("unnecessary_actions", 0),
            failure_count=result.get("failure_count", 0),
        )

    def get_weights(self) -> Dict[str, float]:
        """Return the current weights."""
        return dict(self.weights)

    def set_weights(self, weights: Dict[str, float]) -> None:
        """Update the weights."""
        self.weights.update(weights)
        logger.info(f"Updated fitness weights: {self.weights}")