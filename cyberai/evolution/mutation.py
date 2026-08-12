"""
Mutation engine for the Evolution Engine.

Implements controlled evolutionary operators:
- Mutation: Create variants of successful strategies
- Recombination: Create hybrids from two strategies
- Specialization: Focus a strategy on a specific target type
- Generalization: Broaden a strategy to more target types
"""

import logging
import random
from typing import Any, Dict, List, Optional

from .strategy import Strategy

logger = logging.getLogger(__name__)


class MutationEngine:
    """Generates mutated strategy variants."""

    def __init__(self, mutation_rate: float = 0.3, crossover_rate: float = 0.5):
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate

    def mutate(self, strategy: Strategy, num_variants: int = 3) -> List[Strategy]:
        """
        Create mutated variants of a strategy.

        Args:
            strategy: The parent strategy
            num_variants: Number of variants to generate

        Returns:
            List of mutated child strategies
        """
        variants = []
        for i in range(num_variants):
            mutation_type = random.choice(["action", "tool", "agent", "model", "precondition"])
            variant = strategy.clone_with_mutation(
                f"Mutation {i+1} of: {strategy.description}"
            )
            variant.metadata["mutation_type"] = mutation_type
            variant.metadata["mutation_index"] = i

            if mutation_type == "action":
                self._mutate_action(variant)
            elif mutation_type == "tool":
                self._mutate_tool(variant)
            elif mutation_type == "agent":
                self._mutate_agent(variant)
            elif mutation_type == "model":
                self._mutate_model(variant)
            elif mutation_type == "precondition":
                self._mutate_precondition(variant)

            variants.append(variant)
        return variants

    def _mutate_action(self, strategy: Strategy) -> None:
        """Mutate the action sequence."""
        if not strategy.actions:
            return
        # Swap two actions or change an action parameter
        if len(strategy.actions) >= 2 and random.random() < 0.5:
            i, j = random.sample(range(len(strategy.actions)), 2)
            strategy.actions[i], strategy.actions[j] = strategy.actions[j], strategy.actions[i]
        else:
            idx = random.randrange(len(strategy.actions))
            action = strategy.actions[idx]
            if "parameters" in action and action["parameters"]:
                param_key = random.choice(list(action["parameters"].keys()))
                action["parameters"][param_key] = f"mutated_{param_key}"

    def _mutate_tool(self, strategy: Strategy) -> None:
        """Change the tool used."""
        if not strategy.tools:
            return
        idx = random.randrange(len(strategy.tools))
        strategy.tools[idx] = f"{strategy.tools[idx]}_alt"

    def _mutate_agent(self, strategy: Strategy) -> None:
        """Change the agent used."""
        if strategy.agent:
            strategy.agent = f"{strategy.agent}_variant"

    def _mutate_model(self, strategy: Strategy) -> None:
        """Change the model used."""
        if strategy.model:
            strategy.model = f"{strategy.model}_variant"

    def _mutate_precondition(self, strategy: Strategy) -> None:
        """Add or remove a precondition."""
        if strategy.preconditions and random.random() < 0.5:
            strategy.preconditions.pop(random.randrange(len(strategy.preconditions)))
        else:
            strategy.preconditions.append(f"additional_precondition_{len(strategy.preconditions)}")

    def recombine(self, strategy_a: Strategy, strategy_b: Strategy) -> Strategy:
        """
        Create a hybrid strategy from two parents.

        Args:
            strategy_a: First parent strategy
            strategy_b: Second parent strategy

        Returns:
            Hybrid child strategy
        """
        child = Strategy(
            description=f"Hybrid: {strategy_a.description} + {strategy_b.description}",
            preconditions=list(set(strategy_a.preconditions + strategy_b.preconditions)),
            actions=list(strategy_a.actions) + list(strategy_b.actions),
            tools=list(set(strategy_a.tools + strategy_b.tools)),
            agent=strategy_a.agent or strategy_b.agent,
            model=strategy_a.model or strategy_b.model,
            expected_result=strategy_a.expected_result or strategy_b.expected_result,
            parent_id=f"{strategy_a.strategy_id}+{strategy_b.strategy_id}",
            generation=max(strategy_a.generation, strategy_b.generation) + 1,
            task_type=strategy_a.task_type or strategy_b.task_type,
            environment=strategy_a.environment or strategy_b.environment,
            target_type=strategy_a.target_type or strategy_b.target_type,
        )
        child.metadata["recombination"] = True
        child.metadata["parents"] = [strategy_a.strategy_id, strategy_b.strategy_id]
        return child

    def specialize(self, strategy: Strategy, target_type: str) -> Strategy:
        """
        Create a specialized variant for a specific target type.

        Args:
            strategy: The parent strategy
            target_type: The target type to specialize for

        Returns:
            Specialized child strategy
        """
        child = strategy.clone_with_mutation(
            f"Specialized for {target_type}: {strategy.description}"
        )
        child.target_type = target_type
        child.metadata["specialization"] = target_type
        return child

    def generalize(self, strategy: Strategy) -> Strategy:
        """
        Create a generalized variant that works across more target types.

        Args:
            strategy: The parent strategy

        Returns:
            Generalized child strategy
        """
        child = strategy.clone_with_mutation(
            f"Generalized: {strategy.description}"
        )
        child.target_type = "general"
        child.metadata["generalization"] = True
        return child