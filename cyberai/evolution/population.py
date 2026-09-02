"""
Population management for the Evolution Engine.

Manages a population of strategies across generations.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .strategy import Strategy, StrategyStatus
from cyberai.config import config

logger = logging.getLogger(__name__)


class Population:
    """Manages a population of strategies."""

    def __init__(self, population_dir: Optional[Path] = None, max_size: int = 50):
        self.population_dir = population_dir or config.get_path(
            "memory", "evolution_dir", "memory/evolution"
        ) / "population"
        self.population_dir.mkdir(parents=True, exist_ok=True)
        self.max_size = max_size
        self._strategies: Dict[str, Strategy] = {}
        self._load()

    def _load(self) -> None:
        """Load strategies from disk."""
        for f in self.population_dir.glob("*.json"):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                strategy = Strategy.from_dict(data)
                self._strategies[strategy.strategy_id] = strategy
            except Exception as e:
                logger.warning(f"Failed to load strategy {f}: {e}")
        logger.info(f"Loaded {len(self._strategies)} strategies from population")

    def _save(self, strategy: Strategy) -> None:
        """Save a strategy to disk."""
        path = self.population_dir / f"{strategy.strategy_id}.json"
        with open(path, "w") as f:
            json.dump(strategy.to_dict(), f, indent=2)

    def add(self, strategy: Strategy) -> None:
        """Add a strategy to the population."""
        self._strategies[strategy.strategy_id] = strategy
        self._save(strategy)
        # Trim if over max size
        if len(self._strategies) > self.max_size:
            self._trim()

    def _trim(self) -> None:
        """Remove lowest-fitness strategies when over max size."""
        sorted_strategies = sorted(
            self._strategies.values(),
            key=lambda s: s.fitness,
            reverse=True,
        )
        to_remove = sorted_strategies[self.max_size:]
        for strategy in to_remove:
            self.remove(strategy.strategy_id)

    def remove(self, strategy_id: str) -> None:
        """Remove a strategy from the population."""
        if strategy_id in self._strategies:
            del self._strategies[strategy_id]
            path = self.population_dir / f"{strategy_id}.json"
            if path.exists():
                path.unlink()

    def get(self, strategy_id: str) -> Optional[Strategy]:
        """Get a strategy by ID."""
        return self._strategies.get(strategy_id)

    def get_by_generation(self, generation: int) -> List[Strategy]:
        """Get all strategies from a specific generation."""
        return [s for s in self._strategies.values() if s.generation == generation]

    def get_successful(self) -> List[Strategy]:
        """Get all successful strategies."""
        return [s for s in self._strategies.values() if s.status == StrategyStatus.SUCCESSFUL.value]

    def get_failed(self) -> List[Strategy]:
        """Get all failed strategies."""
        return [s for s in self._strategies.values() if s.status == StrategyStatus.FAILED.value]

    def get_best(self, limit: int = 5) -> List[Strategy]:
        """Get the highest-fitness strategies."""
        sorted_strategies = sorted(
            self._strategies.values(),
            key=lambda s: s.fitness,
            reverse=True,
        )
        return sorted_strategies[:limit]

    def get_all(self) -> List[Strategy]:
        """Get all strategies."""
        return list(self._strategies.values())

    def size(self) -> int:
        """Get population size."""
        return len(self._strategies)

    def clear(self) -> None:
        """Clear the population."""
        self._strategies.clear()
        for f in self.population_dir.glob("*.json"):
            f.unlink()