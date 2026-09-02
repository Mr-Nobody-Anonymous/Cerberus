"""
Evolution Engine coordinator.

Ties together:
- Strategy generation
- Population management
- Mutation/recombination
- Evaluation
- Selection
- Elite archive
- Failure learning
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .strategy import Strategy, StrategyStatus
from .population import Population
from .mutation import MutationEngine
from .selection import SelectionEngine
from .evaluation import EvaluationEngine
from .fitness import FitnessFunction
from .archive import EliteArchive
from cyberai.config import config

logger = logging.getLogger(__name__)


class EvolutionEngine:
    """
    Coordinates the evolutionary improvement loop.

    The engine generates candidate strategies, evaluates them in the
    lab/simulation, selects successful variants, archives elites,
    and learns from failures.
    """

    def __init__(
        self,
        evolution_dir: Optional[Path] = None,
        simulate: bool = True,
        population_size: int = 10,
        elite_size: int = 3,
        mutation_rate: float = 0.3,
        crossover_rate: float = 0.5,
    ):
        self.evolution_dir = evolution_dir or config.get_path(
            "memory", "evolution_dir", "memory/evolution"
        )
        self.evolution_dir.mkdir(parents=True, exist_ok=True)

        self.population = Population(self.evolution_dir / "population", max_size=population_size)
        self.mutation = MutationEngine(mutation_rate=mutation_rate, crossover_rate=crossover_rate)
        self.selection = SelectionEngine(elite_size=elite_size)
        self.evaluation = EvaluationEngine(simulate=simulate)
        self.fitness = FitnessFunction()
        self.elite_archive = EliteArchive(self.evolution_dir / "elite")

        self._failure_memory: List[Dict[str, Any]] = []
        self._load_failures()

    def _load_failures(self) -> None:
        """Load failure records from disk."""
        failures_dir = self.evolution_dir / "failures"
        failures_dir.mkdir(parents=True, exist_ok=True)
        for f in failures_dir.glob("*.json"):
            try:
                with open(f) as fh:
                    self._failure_memory.append(json.load(fh))
            except Exception as e:
                logger.warning(f"Failed to load failure record {f}: {e}")

    def _save_failure(self, failure: Dict[str, Any]) -> None:
        """Save a failure record to disk."""
        failures_dir = self.evolution_dir / "failures"
        failures_dir.mkdir(parents=True, exist_ok=True)
        path = failures_dir / f"{failure['strategy_id']}.json"
        with open(path, "w") as f:
            json.dump(failure, f, indent=2)

    def record_failure(
        self,
        strategy: Strategy,
        reason: str,
        failure_category: str,
        possible_improvement: str = "",
    ) -> None:
        """
        Record a failure for learning.

        Args:
            strategy: The failed strategy
            reason: Why it failed
            failure_category: Category of failure (e.g., "tool_unavailable", "no_evidence")
            possible_improvement: Possible improvement
        """
        failure = {
            "strategy_id": strategy.strategy_id,
            "description": strategy.description,
            "generation": strategy.generation,
            "reason": reason,
            "failure_category": failure_category,
            "environment": strategy.environment,
            "tools": strategy.tools,
            "agent": strategy.agent,
            "model": strategy.model,
            "observations": strategy.actual_result,
            "possible_improvement": possible_improvement,
            "timestamp": strategy.evaluated_at,
        }
        self._failure_memory.append(failure)
        self._save_failure(failure)
        logger.info(f"Recorded failure for strategy {strategy.strategy_id}: {failure_category}")

    def get_recent_failures(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent failure records."""
        return self._failure_memory[-limit:]

    def get_failures_by_tool(self, tool: str) -> List[Dict[str, Any]]:
        """Get failures associated with a specific tool."""
        return [
            f for f in self._failure_memory
            if tool in f.get("tools", [])
        ]

    def get_failures_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get failures by category."""
        return [
            f for f in self._failure_memory
            if f.get("failure_category") == category
        ]

    def should_avoid_similar(self, strategy: Strategy, confidence_threshold: float = 0.6) -> bool:
        """
        Check if a strategy is similar to historically failed approaches.

        Returns True if the strategy should be avoided.
        """
        for failure in self._failure_memory:
            if set(failure.get("tools", [])).intersection(set(strategy.tools)):
                if failure.get("failure_category") in ("tool_unavailable", "no_evidence"):
                    return True
                if failure["strategy_id"] == strategy.parent_id:
                    return True
        return False

    async def evolve_generation(
        self,
        task_type: str,
        task_context: Optional[Dict[str, Any]] = None,
        num_strategies: int = 3,
    ) -> Dict[str, Any]:
        """
        Run one complete evolutionary generation.

        Steps:
        1. Generate new strategies (mutations + recombinations)
        2. Filter unsafe/invalid strategies
        3. Evaluate each in the lab/simulation
        4. Score with fitness function
        5. Select successful variants
        6. Add to elite archive
        7. Record failures

        Args:
            task_type: Type of task to evolve strategies for
            task_context: Task context for evaluation
            num_strategies: Number of new strategies to generate

        Returns:
            Generation result dict
        """
        context = task_context or {}

        # Get existing successful strategies as parents
        successful = self.population.get_successful()
        if not successful:
            # Use elite archive
            successful = self.elite_archive.get_by_task_type(task_type)
        parents = successful[:2] if successful else []

        # Generate new strategies
        new_strategies: List[Strategy] = []

        # Mutations of successful strategies
        for parent in parents:
            variants = self.mutation.mutate(parent, num_variants=num_strategies)
            new_strategies.extend(variants)

        # Recombinations
        if len(parents) >= 2:
            hybrid = self.mutation.recombine(parents[0], parents[1])
            hybrid.task_type = task_type
            new_strategies.append(hybrid)

        # If no parents, generate basic strategies from scratch
        if not new_strategies:
            for i in range(num_strategies):
                s = Strategy(
                    description=f"Basic strategy {i+1} for {task_type}",
                    actions=[
                        {"action": "recon", "capability": "reconnaissance"},
                        {"action": "analysis", "capability": "analysis"},
                        {"action": "verification", "capability": "verification"},
                    ],
                    tools=["strix", "pentagi"] if i == 0 else ["cai", "analyst"],
                    task_type=task_type,
                    environment=context.get("environment", "authorized_lab"),
                )
                new_strategies.append(s)

        # Filter unsafe/invalid strategies
        valid_strategies = []
        for s in new_strategies:
            if self.should_avoid_similar(s):
                logger.info(f"Skipping strategy {s.strategy_id} - similar to failed approach")
                continue
            if not s.actions:
                logger.info(f"Skipping strategy {s.strategy_id} - no actions")
                continue
            valid_strategies.append(s)

        # Evaluate all valid strategies
        results = []
        for strategy in valid_strategies:
            strategy.task_type = task_type
            result = await self.evaluation.evaluate(strategy, context)
            results.append({
                "strategy_id": strategy.strategy_id,
                "description": strategy.description,
                "fitness": strategy.fitness,
                "success": result.get("success", False),
                "verification": strategy.verification,
            })

            if strategy.status == StrategyStatus.SUCCESSFUL.value:
                self.population.add(strategy)
                self.elite_archive.add(strategy)
            else:
                self.record_failure(
                    strategy,
                    reason=result.get("output", "Evaluation failed"),
                    failure_category="evaluation_failed",
                    possible_improvement="Adjust strategy actions or tools",
                )

        # Select next generation parents
        all_strategies = self.population.get_all()
        selected = self.selection.select_by_fitness(all_strategies, count=min(3, len(all_strategies)))

        generation_result = {
            "task_type": task_type,
            "new_strategies_generated": len(valid_strategies),
            "successful": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"]),
            "results": results,
            "selected_parents": [s.strategy_id for s in selected],
            "elite_size": self.elite_archive.size(),
            "population_size": self.population.size(),
            "failure_count": len(self._failure_memory),
        }
        logger.info(f"Evolution generation complete: {generation_result}")
        return generation_result

    def get_status(self) -> Dict[str, Any]:
        """Get evolution engine status."""
        return {
            "population_size": self.population.size(),
            "elite_size": self.elite_archive.size(),
            "failure_count": len(self._failure_memory),
            "elite_strategies": [
                {
                    "id": s.strategy_id,
                    "description": s.description[:80],
                    "fitness": s.fitness,
                    "generation": s.generation,
                }
                for s in self.elite_archive.get_best(limit=5)
            ],
            "recent_failures": self.get_recent_failures(limit=3),
        }