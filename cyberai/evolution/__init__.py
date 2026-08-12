"""
Evolution Engine for the Cyber AI platform.

Implements a controlled evolutionary loop:
- Generate strategies
- Test in lab/simulation
- Score with fitness function
- Select successful variants
- Archive elite strategies
- Learn from failures
"""

from .strategy import Strategy, StrategyStatus
from .population import Population
from .mutation import MutationEngine
from .selection import SelectionEngine
from .evaluation import EvaluationEngine
from .fitness import FitnessFunction
from .archive import EliteArchive
from .engine import EvolutionEngine

__all__ = [
    "Strategy",
    "StrategyStatus",
    "Population",
    "MutationEngine",
    "SelectionEngine",
    "EvaluationEngine",
    "FitnessFunction",
    "EliteArchive",
    "EvolutionEngine",
]
