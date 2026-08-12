"""
Selection engine for the Evolution Engine.

Selects strategies to propagate to the next generation based on fitness.
"""

import logging
import random
from typing import List, Optional

from .strategy import Strategy, StrategyStatus

logger = logging.getLogger(__name__)


class SelectionEngine:
    """Selects strategies for the next generation."""

    def __init__(self, elite_size: int = 3, tournament_size: int = 3):
        self.elite_size = elite_size
        self.tournament_size = tournament_size

    def select_elite(self, strategies: List[Strategy]) -> List[Strategy]:
        """
        Select the highest-fitness strategies (elite preservation).

        Args:
            strategies: All candidate strategies

        Returns:
            The elite strategies
        """
        sorted_strategies = sorted(
            strategies,
            key=lambda s: s.fitness,
            reverse=True,
        )
        return sorted_strategies[:self.elite_size]

    def select_by_fitness(self, strategies: List[Strategy], count: int) -> List[Strategy]:
        """
        Select strategies using fitness-proportional selection.

        Args:
            strategies: Candidate strategies
            count: Number to select

        Returns:
            Selected strategies
        """
        if not strategies:
            return []

        # Filter to successful strategies only
        successful = [s for s in strategies if s.status == StrategyStatus.SUCCESSFUL.value and s.fitness > 0]
        if not successful:
            successful = strategies

        # Normalize fitness to probabilities
        total_fitness = sum(s.fitness for s in successful)
        if total_fitness <= 0:
            return random.sample(successful, min(count, len(successful)))

        selected = []
        pool = list(successful)
        for _ in range(min(count, len(successful))):
            if not pool:
                break
            weights = [s.fitness / total_fitness for s in pool]
            chosen = random.choices(pool, weights=weights, k=1)[0]
            selected.append(chosen)
        return selected

    def tournament_select(self, strategies: List[Strategy]) -> Optional[Strategy]:
        """
        Select a strategy via tournament selection.

        Args:
            strategies: Candidate strategies

        Returns:
            The winning strategy
        """
        if not strategies:
            return None
        tournament = random.sample(
            strategies,
            min(self.tournament_size, len(strategies)),
        )
        return max(tournament, key=lambda s: s.fitness)

    def select_parents_for_recombination(self, strategies: List[Strategy]) -> Optional[List[Strategy]]:
        """
        Select two parents for recombination.

        Args:
            strategies: Candidate strategies

        Returns:
            Two parent strategies, or None if insufficient
        """
        if len(strategies) < 2:
            return None
        a = self.tournament_select(strategies)
        remaining = [s for s in strategies if s.strategy_id != a.strategy_id]
        b = self.tournament_select(remaining)
        return [a, b]