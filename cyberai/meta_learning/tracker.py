"""
Performance Tracker for Meta-Learning.

Records and aggregates performance statistics for models, agents, tools,
and strategies so the router can adapt based on measured performance.
"""

import json
import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PerformanceRecord:
    """A single performance observation."""

    entity_type: str  # model, agent, tool, strategy
    entity_name: str
    task_type: str
    capability: str = ""
    success: bool = False
    verification: str = "UNVERIFIED"
    latency: float = 0.0
    token_usage: int = 0
    quality_score: float = 0.0
    environment: str = "authorized_lab"
    target_type: str = ""
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "entity_type": self.entity_type,
            "entity_name": self.entity_name,
            "task_type": self.task_type,
            "capability": self.capability,
            "success": self.success,
            "verification": self.verification,
            "latency": self.latency,
            "token_usage": self.token_usage,
            "quality_score": self.quality_score,
            "environment": self.environment,
            "target_type": self.target_type,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class PerformanceTracker:
    """
    Tracks and aggregates performance statistics.

    Uses SQLite for persistent storage. Provides adaptive routing
    statistics: which model/agent/tool performs best for which task.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(__file__).parent.parent.parent / "memory" / "performance.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS performance (
                    record_id TEXT PRIMARY KEY,
                    entity_type TEXT,
                    entity_name TEXT,
                    task_type TEXT,
                    capability TEXT,
                    success INTEGER,
                    verification TEXT,
                    latency REAL,
                    token_usage INTEGER,
                    quality_score REAL,
                    environment TEXT,
                    target_type TEXT,
                    timestamp TEXT,
                    metadata TEXT
                )
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_perf_entity
                ON performance (entity_type, entity_name, task_type)
            """)

    def record(self, record: PerformanceRecord) -> str:
        """Record a performance observation."""
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO performance (
                    record_id, entity_type, entity_name, task_type, capability,
                    success, verification, latency, token_usage, quality_score,
                    environment, target_type, timestamp, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.record_id,
                    record.entity_type,
                    record.entity_name,
                    record.task_type,
                    record.capability,
                    1 if record.success else 0,
                    record.verification,
                    record.latency,
                    record.token_usage,
                    record.quality_score,
                    record.environment,
                    record.target_type,
                    record.timestamp,
                    json.dumps(record.metadata),
                ),
            )
        logger.debug(f"Recorded performance: {record.entity_type}={record.entity_name} task={record.task_type}")
        return record.record_id

    def record_simple(
        self,
        entity_type: str,
        entity_name: str,
        task_type: str,
        success: bool,
        capability: str = "",
        latency: float = 0.0,
        verification: str = "UNVERIFIED",
        quality_score: float = 0.0,
        **metadata: Any,
    ) -> str:
        """Convenience method to record a performance observation."""
        return self.record(PerformanceRecord(
            entity_type=entity_type,
            entity_name=entity_name,
            task_type=task_type,
            capability=capability,
            success=success,
            latency=latency,
            verification=verification,
            quality_score=quality_score,
            metadata=metadata,
        ))

    def get_stats(
        self,
        entity_type: str,
        entity_name: str,
        task_type: str,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics for an entity on a task type.

        Returns:
            Dict with calls, success_rate, avg_latency, avg_quality, etc.
        """
        with self._conn:
            rows = self._conn.execute(
                """
                SELECT * FROM performance
                WHERE entity_type = ? AND entity_name = ? AND task_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (entity_type, entity_name, task_type, limit),
            ).fetchall()
        records = [dict(r) for r in rows]
        if not records:
            return {
                "entity_type": entity_type,
                "entity_name": entity_name,
                "task_type": task_type,
                "calls": 0,
                "success_rate": 0.0,
                "avg_latency": 0.0,
                "avg_quality": 0.0,
                "verified_count": 0,
            }
        successes = sum(1 for r in records if r["success"])
        verified = sum(1 for r in records if r["verification"] == "VERIFIED")
        return {
            "entity_type": entity_type,
            "entity_name": entity_name,
            "task_type": task_type,
            "calls": len(records),
            "success_rate": successes / len(records),
            "avg_latency": sum(r["latency"] for r in records) / len(records),
            "avg_quality": sum(r["quality_score"] for r in records) / len(records),
            "verified_count": verified,
        }

    def best_for_task(
        self,
        entity_type: str,
        task_type: str,
        min_calls: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best-performing entity for a task type.

        Args:
            entity_type: model, agent, tool, strategy
            task_type: The task type
            min_calls: Minimum number of observations required

        Returns:
            The best entity stats, or None if insufficient data
        """
        with self._conn:
            rows = self._conn.execute(
                """
                SELECT entity_name,
                       COUNT(*) as calls,
                       SUM(success) as successes,
                       AVG(latency) as avg_latency,
                       AVG(quality_score) as avg_quality
                FROM performance
                WHERE entity_type = ? AND task_type = ?
                GROUP BY entity_name
                HAVING calls >= ?
                ORDER BY (successes * 1.0 / calls) DESC, avg_quality DESC
                """,
                (entity_type, task_type, min_calls),
            ).fetchall()
        if not rows:
            return None
        best = dict(rows[0])
        best["success_rate"] = best["successes"] / best["calls"]
        return best

    def ranking_for_task(
        self,
        entity_type: str,
        task_type: str,
        min_calls: int = 1,
    ) -> List[Dict[str, Any]]:
        """Get a ranked list of entities for a task type."""
        with self._conn:
            rows = self._conn.execute(
                """
                SELECT entity_name,
                       COUNT(*) as calls,
                       SUM(success) as successes,
                       AVG(latency) as avg_latency,
                       AVG(quality_score) as avg_quality
                FROM performance
                WHERE entity_type = ? AND task_type = ?
                GROUP BY entity_name
                HAVING calls >= ?
                ORDER BY (successes * 1.0 / calls) DESC, avg_quality DESC
                """,
                (entity_type, task_type, min_calls),
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["success_rate"] = d["successes"] / d["calls"] if d["calls"] else 0.0
            result.append(d)
        return result

    def get_all_stats(self, entity_type: str) -> Dict[str, Any]:
        """Get aggregated stats grouped by entity and task type."""
        with self._conn:
            rows = self._conn.execute(
                """
                SELECT entity_name, task_type,
                       COUNT(*) as calls,
                       SUM(success) as successes,
                       AVG(latency) as avg_latency,
                       AVG(quality_score) as avg_quality
                FROM performance
                WHERE entity_type = ?
                GROUP BY entity_name, task_type
                ORDER BY entity_name, (successes * 1.0 / calls) DESC
                """,
                (entity_type,),
            ).fetchall()
        result: Dict[str, Any] = {}
        for r in rows:
            d = dict(r)
            d["success_rate"] = d["successes"] / d["calls"] if d["calls"] else 0.0
            result.setdefault(d["entity_name"], {})[d["task_type"]] = d
        return result

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()