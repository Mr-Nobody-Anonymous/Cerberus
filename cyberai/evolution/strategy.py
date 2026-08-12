"""
Strategy definition for the Evolution Engine.

A strategy is a candidate approach for solving a class of tasks.
Strategies are generated, tested in the lab, scored, and evolved.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class StrategyStatus(Enum):
    GENERATED = "generated"
    VALIDATED = "validated"
    TESTING = "testing"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    REJECTED = "rejected"
    ARCHIVED = "archived"


@dataclass
class Strategy:
    """A candidate strategy for solving a task."""

    description: str
    preconditions: List[str] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    agent: str = ""
    model: str = ""
    expected_result: str = ""
    actual_result: str = ""
    fitness: float = 0.0
    confidence: float = 0.0
    verification: str = "UNVERIFIED"
    strategy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str = ""
    generation: int = 1
    status: str = StrategyStatus.GENERATED.value
    task_type: str = ""
    environment: str = "authorized_lab"
    target_type: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evaluated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "strategy_id": self.strategy_id,
            "parent_id": self.parent_id,
            "generation": self.generation,
            "description": self.description,
            "preconditions": self.preconditions,
            "actions": self.actions,
            "tools": self.tools,
            "agent": self.agent,
            "model": self.model,
            "expected_result": self.expected_result,
            "actual_result": self.actual_result,
            "fitness": self.fitness,
            "confidence": self.confidence,
            "verification": self.verification,
            "status": self.status,
            "task_type": self.task_type,
            "environment": self.environment,
            "target_type": self.target_type,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "evaluated_at": self.evaluated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Strategy":
        """Deserialize from dict."""
        return cls(
            strategy_id=data.get("strategy_id", str(uuid.uuid4())),
            parent_id=data.get("parent_id", ""),
            generation=data.get("generation", 1),
            description=data.get("description", ""),
            preconditions=data.get("preconditions", []),
            actions=data.get("actions", []),
            tools=data.get("tools", []),
            agent=data.get("agent", ""),
            model=data.get("model", ""),
            expected_result=data.get("expected_result", ""),
            actual_result=data.get("actual_result", ""),
            fitness=data.get("fitness", 0.0),
            confidence=data.get("confidence", 0.0),
            verification=data.get("verification", "UNVERIFIED"),
            status=data.get("status", StrategyStatus.GENERATED.value),
            task_type=data.get("task_type", ""),
            environment=data.get("environment", "authorized_lab"),
            target_type=data.get("target_type", ""),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            evaluated_at=data.get("evaluated_at", ""),
        )

    def clone_with_mutation(self, mutation_description: str) -> "Strategy":
        """Create a mutated child strategy."""
        child = Strategy(
            description=mutation_description,
            preconditions=list(self.preconditions),
            actions=[dict(a) for a in self.actions],
            tools=list(self.tools),
            agent=self.agent,
            model=self.model,
            expected_result=self.expected_result,
            parent_id=self.strategy_id,
            generation=self.generation + 1,
            task_type=self.task_type,
            environment=self.environment,
            target_type=self.target_type,
        )
        return child