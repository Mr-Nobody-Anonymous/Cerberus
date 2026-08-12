"""
Elite Strategy Archive for the Evolution Engine.

Maintains the best verified strategies for future retrieval.
The archive becomes part of future planning and retrieval.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .strategy import Strategy, StrategyStatus

logger = logging.getLogger(__name__)


class EliteArchive:
    """Maintains the elite archive of best verified strategies."""

    def __init__(self, archive_dir: Optional[Path] = None, max_elite: int = 20):
        self.archive_dir = archive_dir or Path(__file__).parent.parent.parent / "memory" / "evolution" / "elite"
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.max_elite = max_elite
        self._elite: Dict[str, Strategy] = {}
        self._load()

    def _load(self) -> None:
        """Load elite strategies from disk."""
        for f in self.archive_dir.glob("*.json"):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                strategy = Strategy.from_dict(data)
                self._elite[strategy.strategy_id] = strategy
            except Exception as e:
                logger.warning(f"Failed to load elite strategy {f}: {e}")
        logger.info(f"Loaded {len(self._elite)} elite strategies")

    def _save(self, strategy: Strategy) -> None:
        """Save an elite strategy to disk."""
        path = self.archive_dir / f"{strategy.strategy_id}.json"
        with open(path, "w") as f:
            json.dump(strategy.to_dict(), f, indent=2)

    def add(self, strategy: Strategy) -> bool:
        """
        Add a strategy to the elite archive if it qualifies.

        A strategy qualifies if it is successful and has fitness above
        the current minimum elite fitness (or the archive is not full).

        Args:
            strategy: The strategy to add

        Returns:
            True if added, False otherwise
        """
        if strategy.status != StrategyStatus.SUCCESSFUL.value:
            return False

        # Check if already in archive
        if strategy.strategy_id in self._elite:
            return False

        # If archive is full, check if this strategy is better than the worst
        if len(self._elite) >= self.max_elite:
            worst = min(self._elite.values(), key=lambda s: s.fitness)
            if strategy.fitness <= worst.fitness:
                return False
            # Remove the worst
            self.remove(worst.strategy_id)

        self._elite[strategy.strategy_id] = strategy
        self._save(strategy)
        logger.info(f"Added strategy {strategy.strategy_id} to elite archive (fitness={strategy.fitness:.2f})")
        return True

    def remove(self, strategy_id: str) -> None:
        """Remove a strategy from the elite archive."""
        if strategy_id in self._elite:
            del self._elite[strategy_id]
            path = self.archive_dir / f"{strategy_id}.json"
            if path.exists():
                path.unlink()

    def get(self, strategy_id: str) -> Optional[Strategy]:
        """Get an elite strategy by ID."""
        return self._elite.get(strategy_id)

    def get_best(self, limit: int = 5) -> List[Strategy]:
        """Get the highest-fitness elite strategies."""
        sorted_strategies = sorted(
            self._elite.values(),
            key=lambda s: s.fitness,
            reverse=True,
        )
        return sorted_strategies[:limit]

    def get_by_task_type(self, task_type: str, limit: int = 5) -> List[Strategy]:
        """Get elite strategies for a specific task type."""
        matching = [
            s for s in self._elite.values()
            if s.task_type == task_type
        ]
        matching.sort(key=lambda s: s.fitness, reverse=True)
        return matching[:limit]

    def get_by_target_type(self, target_type: str, limit: int = 5) -> List[Strategy]:
        """Get elite strategies for a specific target type."""
        matching = [
            s for s in self._elite.values()
            if s.target_type == target_type or s.target_type == "general"
        ]
        matching.sort(key=lambda s: s.fitness, reverse=True)
        return matching[:limit]

    def get_all(self) -> List[Strategy]:
        """Get all elite strategies."""
        return list(self._elite.values())

    def size(self) -> int:
        """Get the number of elite strategies."""
        return len(self._elite)

    def clear(self) -> None:
        """Clear the elite archive."""
        self._elite.clear()
        for f in self.archive_dir.glob("*.json"):
            f.unlink()