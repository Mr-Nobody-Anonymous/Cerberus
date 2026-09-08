"""
Ghost Wargaming for the Cyber AI Orchestrator.

Implements the README's "Ghost Wargaming & Failure Learning" section:

- **Failure Memory**: Every failed strategy is recorded with reason/category
- **Avoidance Logic**: Similar-to-failed strategies are skipped automatically
- **Failure Analytics**: Query failures by tool or category
- **Fast-forward simulation**: Test evolved strategies in simulate mode

This module wraps the EvolutionEngine's failure memory and the simulate-mode
evaluation into a single "wargame" surface: you can replay historical
failures, check whether a candidate strategy would be avoided, and
fast-forward a whole generation without touching real targets.
"""

import logging
from typing import Any, Dict, List, Optional

from cyberai.evolution.engine import EvolutionEngine
from cyberai.evolution.population import Strategy, StrategyStatus

logger = logging.getLogger(__name__)


class GhostWargame:
    """Failure-learning + fast-forward simulation facade over EvolutionEngine."""

    def __init__(self, engine: Optional[EvolutionEngine] = None):
        self.engine = engine or EvolutionEngine()

    # -- failure memory ----------------------------------------------------

    def record_failure(self, strategy: Strategy, reason: str,
                       category: str, tool: str = "",
                       improvement: str = "") -> None:
        """Record a failed strategy for future avoidance."""
        self.engine.record_failure(
            strategy, reason=reason, failure_category=category,
            possible_improvement=improvement or "Adjust actions/tools",
        )
        if tool:
            # annotate the most recent failure with the tool
            recent = self.engine.get_recent_failures(limit=1)
            if recent:
                recent[0]["tools"] = [tool] if "tools" not in recent[0] else recent[0]["tools"] + [tool]

    def recent_failures(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Recent failure records (newest first)."""
        return self.engine.get_recent_failures(limit=limit)

    def failures_by_tool(self, tool: str) -> List[Dict[str, Any]]:
        """All failures associated with a tool."""
        return self.engine.get_failures_by_tool(tool)

    def failures_by_category(self, category: str) -> List[Dict[str, Any]]:
        """All failures in a category (tool_unavailable, no_evidence, ...)."""
        return self.engine.get_failures_by_category(category)

    # -- avoidance -----------------------------------------------------------

    def would_be_avoided(self, strategy: Strategy) -> bool:
        """True if the engine's avoidance logic would skip this strategy."""
        return self.engine.should_avoid_similar(strategy)

    def filter_avoided(self, strategies: List[Strategy]) -> Dict[str, List[Any]]:
        """Split strategies into (kept, avoided) based on failure memory."""
        kept, avoided = [], []
        for s in strategies:
            if self.engine.should_avoid_similar(s):
                avoided.append(s)
            else:
                kept.append(s)
        return {"kept": kept, "avoided": avoided}

    # -- fast-forward simulation ----------------------------------------------

    async def fast_forward(
        self,
        task_type: str,
        task_context: Optional[Dict[str, Any]] = None,
        num_strategies: int = 3,
    ) -> Dict[str, Any]:
        """Run a full evolution generation in simulate mode.

        No real tools run: the deterministic mock evaluator scores each
        strategy, failures are recorded, and avoidance is applied — a safe
        wargame of the next generation.
        """
        context = dict(task_context or {})
        context["simulate"] = True
        result = await self.engine.evolve_generation(
            task_type, task_context=context, num_strategies=num_strategies)
        result["mode"] = "simulate"
        return result

    # -- analytics -------------------------------------------------------------

    def analytics(self) -> Dict[str, Any]:
        """Aggregate failure analytics for the wargame dashboard."""
        failures = self.engine.get_recent_failures(limit=1000)
        by_category: Dict[str, int] = {}
        by_tool: Dict[str, int] = {}
        for f in failures:
            cat = f.get("failure_category", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1
            for t in f.get("tools", []):
                by_tool[t] = by_tool.get(t, 0) + 1
        return {
            "total_failures": len(failures),
            "by_category": by_category,
            "by_tool": by_tool,
            "population_size": self.engine.population.size(),
            "elite_size": self.engine.elite_archive.size(),
        }
