"""
Evaluation engine for the Evolution Engine.

Evaluates strategies in the lab/simulation environment and
records results for fitness computation.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .strategy import Strategy, StrategyStatus

logger = logging.getLogger(__name__)


class EvaluationEngine:
    """
    Evaluates strategies in a controlled environment.

    In simulation mode, returns deterministic mock results.
    In real mode, would execute strategies against authorized lab targets.
    """

    def __init__(self, simulate: bool = True):
        self.simulate = simulate
        self._evaluation_results: Dict[str, Dict[str, Any]] = {}

    async def evaluate(self, strategy: Strategy, task_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Evaluate a strategy.

        Args:
            strategy: The strategy to evaluate
            task_context: Task context for evaluation

        Returns:
            Evaluation result dict
        """
        if self.simulate:
            result = self._simulate_evaluation(strategy, task_context or {})
        else:
            result = await self._real_evaluation(strategy, task_context or {})

        # Update strategy with results
        strategy.actual_result = result.get("output", "")
        strategy.fitness = result.get("fitness", 0.0)
        strategy.verification = result.get("verification", "UNVERIFIED")
        strategy.evaluated_at = datetime.now(timezone.utc).isoformat()
        strategy.status = (
            StrategyStatus.SUCCESSFUL.value if result.get("success", False)
            else StrategyStatus.FAILED.value
        )

        self._evaluation_results[strategy.strategy_id] = result
        return result

    def _simulate_evaluation(self, strategy: Strategy, task_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate strategy evaluation with deterministic mock results.

        Uses a hash of the strategy ID to produce deterministic results
        so the same strategy always gets the same simulated score.
        """
        import hashlib

        # Deterministic pseudo-random based on strategy ID
        seed = int(hashlib.sha256(strategy.strategy_id.encode()).hexdigest()[:8], 16)
        rng = __import__("random").Random(seed)

        # Simulate success probability based on strategy quality indicators
        success_prob = 0.5
        if strategy.tools:
            success_prob += 0.1
        if strategy.agent:
            success_prob += 0.1
        if strategy.model:
            success_prob += 0.05
        if strategy.preconditions:
            success_prob += 0.05

        success = rng.random() < success_prob
        evidence_count = rng.randint(0, 5) if success else rng.randint(0, 2)
        unnecessary_actions = rng.randint(0, 3)
        failure_count = 0 if success else rng.randint(1, 3)
        repeatable = success and rng.random() < 0.7

        verification = "VERIFIED" if success and repeatable else (
            "LIKELY" if success else "UNVERIFIED"
        )

        from .fitness import FitnessFunction
        fitness_fn = FitnessFunction()
        fitness = fitness_fn.compute(
            success=success,
            verification=verification,
            evidence_count=evidence_count,
            repeatable=repeatable,
            unnecessary_actions=unnecessary_actions,
            failure_count=failure_count,
        )

        return {
            "success": success,
            "verification": verification,
            "evidence_count": evidence_count,
            "repeatable": repeatable,
            "unnecessary_actions": unnecessary_actions,
            "failure_count": failure_count,
            "fitness": fitness,
            "output": f"Simulated result for strategy: {strategy.description}",
            "simulated": True,
        }

    async def _real_evaluation(self, strategy: Strategy, task_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Real evaluation against authorized lab targets.

        This would execute the strategy's actions through the tool
        registry and adapters. For now, falls back to simulation.
        """
        logger.warning("Real evaluation not yet implemented - falling back to simulation")
        return self._simulate_evaluation(strategy, task_context)

    def get_result(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get the evaluation result for a strategy."""
        return self._evaluation_results.get(strategy_id)

    def get_all_results(self) -> Dict[str, Dict[str, Any]]:
        """Get all evaluation results."""
        return dict(self._evaluation_results)