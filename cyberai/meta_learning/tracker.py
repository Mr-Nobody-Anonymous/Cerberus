"""
Performance Tracker for Meta-Learning.

Records and aggregates performance statistics for models, agents, tools,
and strategies so the router can adapt based on measured performance.

Uses SQLite with physical views for latency, verification status, and
success rate tracking. Provides adaptive routing statistics:
which model/agent/tool performs best for which task.

Physical Database Schema (performance.db):
    Table:  performance  — raw performance records
    Views:  v_latency_stats      — aggregated latency per entity/task
            v_verification_stats — verified/likely/unverified/rejected counts
            v_success_stats      — success rate per entity/task
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

from cyberai.config import config

logger = logging.getLogger(__name__)

# Physical schema with views for calculation
PERFORMANCE_SCHEMA = """
-- Performance records: tracks every model/agent/tool/strategy call
CREATE TABLE IF NOT EXISTS performance (
    record_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,      -- model, agent, tool, strategy
    entity_name TEXT NOT NULL,
    task_type TEXT NOT NULL,
    capability TEXT,
    success INTEGER DEFAULT 0,
    verification TEXT DEFAULT 'UNVERIFIED',
    latency REAL DEFAULT 0.0,
    token_usage INTEGER DEFAULT 0,
    quality_score REAL DEFAULT 0.0,
    environment TEXT DEFAULT 'authorized_lab',
    target_type TEXT,
    timestamp TEXT NOT NULL,
    metadata TEXT                   -- JSON object
);
CREATE INDEX IF NOT EXISTS idx_perf_entity
    ON performance (entity_type, entity_name, task_type);
CREATE INDEX IF NOT EXISTS idx_perf_task ON performance (task_type);
CREATE INDEX IF NOT EXISTS idx_perf_success ON performance (success);
CREATE INDEX IF NOT EXISTS idx_perf_ts ON performance (timestamp);

-- Latency tracking view
CREATE VIEW IF NOT EXISTS v_latency_stats AS
SELECT
    entity_type,
    entity_name,
    task_type,
    COUNT(*) as calls,
    AVG(latency) as avg_latency,
    MIN(latency) as min_latency,
    MAX(latency) as max_latency,
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
    SUM(latency) as total_latency
FROM performance
GROUP BY entity_type, entity_name, task_type;

-- Verification status tracking view
CREATE VIEW IF NOT EXISTS v_verification_stats AS
SELECT
    entity_type,
    entity_name,
    task_type,
    COUNT(*) as total,
    SUM(CASE WHEN verification = 'VERIFIED' THEN 1 ELSE 0 END) as verified,
    SUM(CASE WHEN verification = 'LIKELY' THEN 1 ELSE 0 END) as likely,
    SUM(CASE WHEN verification = 'UNVERIFIED' THEN 1 ELSE 0 END) as unverified,
    SUM(CASE WHEN verification = 'REJECTED' THEN 1 ELSE 0 END) as rejected
FROM performance
GROUP BY entity_type, entity_name, task_type;

-- Success rate tracking view
CREATE VIEW IF NOT EXISTS v_success_stats AS
SELECT
    entity_type,
    entity_name,
    task_type,
    COUNT(*) as calls,
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
    ROUND(SUM(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) / COUNT(*), 4) as success_rate,
    AVG(quality_score) as avg_quality
FROM performance
GROUP BY entity_type, entity_name, task_type;
"""


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

    Uses SQLite for persistent storage with physical views for fast
    aggregation. Provides adaptive routing statistics: which model/agent/
    tool performs best for which task.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.get_path(
            "memory", "performance_db_path", "memory/performance.db"
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema with tables and views."""
        with self._conn:
            self._conn.executescript(PERFORMANCE_SCHEMA)
        logger.info(f"Performance DB ready at {self.db_path}")

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------
    def record(self, record: PerformanceRecord) -> str:
        """
        Record a performance observation.

        Args:
            record: The PerformanceRecord to persist

        Returns:
            The record ID
        """
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
        logger.debug(
            f"Recorded performance: {record.entity_type}={record.entity_name} "
            f"task={record.task_type} success={record.success}"
        )
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

    # ------------------------------------------------------------------
    # Aggregated statistics
    # ------------------------------------------------------------------
    def get_stats(
        self,
        entity_type: str,
        entity_name: str,
        task_type: str,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics for an entity on a task type.

        Merges the physical latency, verification, and success views
        into a comprehensive stats dict.

        Args:
            entity_type: model, agent, tool, strategy
            entity_name: The entity name
            task_type: The task type
            limit: Max number of raw records to inspect

        Returns:
            Dict with calls, success_rate, avg_latency, verification stats, etc.
        """
        with self._conn:
            # Raw records for detailed inspection
            rows = self._conn.execute(
                """
                SELECT * FROM performance
                WHERE entity_type = ? AND entity_name = ? AND task_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (entity_type, entity_name, task_type, limit),
            ).fetchall()

            # Success + latency from view
            success_row = self._conn.execute(
                """
                SELECT * FROM v_success_stats
                WHERE entity_type = ? AND entity_name = ? AND task_type = ?
                """,
                (entity_type, entity_name, task_type),
            ).fetchone()

            # Verification from view
            verif_row = self._conn.execute(
                """
                SELECT * FROM v_verification_stats
                WHERE entity_type = ? AND entity_name = ? AND task_type = ?
                """,
                (entity_type, entity_name, task_type),
            ).fetchone()

            # Latency from view
            latency_row = self._conn.execute(
                """
                SELECT * FROM v_latency_stats
                WHERE entity_type = ? AND entity_name = ? AND task_type = ?
                """,
                (entity_type, entity_name, task_type),
            ).fetchone()

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

        return {
            "entity_type": entity_type,
            "entity_name": entity_name,
            "task_type": task_type,
            "calls": len(records),
            "success_rate": float(dict(success_row)["success_rate"]) if success_row else 0.0,
            "successes": int(dict(success_row)["successes"]) if success_row else 0,
            "avg_latency": float(dict(latency_row)["avg_latency"]) if latency_row else 0.0,
            "min_latency": float(dict(latency_row)["min_latency"]) if latency_row else 0.0,
            "max_latency": float(dict(latency_row)["max_latency"]) if latency_row else 0.0,
            "avg_quality": float(dict(success_row)["avg_quality"]) if success_row else 0.0,
            "verified_count": int(dict(verif_row)["verified"]) if verif_row else 0,
            "likely_count": int(dict(verif_row)["likely"]) if verif_row else 0,
            "unverified_count": int(dict(verif_row)["unverified"]) if verif_row else 0,
            "rejected_count": int(dict(verif_row)["rejected"]) if verif_row else 0,
            "verification": dict(verif_row) if verif_row else {},
            "latency_stats": dict(latency_row) if latency_row else {},
        }

    # ------------------------------------------------------------------
    # Adaptive routing: best_for_task / ranking_for_task
    # ------------------------------------------------------------------
    def best_for_task(
        self,
        entity_type: str,
        task_type: str,
        min_calls: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best-performing entity for a task type.

        Physical calculation combines success rate and quality score:
            composite = success_rate * 0.7 + avg_quality * 0.3

        Only entities with >= min_calls observations are considered.

        Args:
            entity_type: model, agent, tool, strategy
            task_type: The task type
            min_calls: Minimum number of observations required

        Returns:
            The best entity stats, or None if insufficient data
        """
        with self._conn:
            rows = self._conn.execute(
                f"""
                SELECT * FROM (
                    SELECT
                        p.entity_name,
                        COUNT(*) as calls,
                        SUM(CASE WHEN p.success = 1 THEN 1 ELSE 0 END) as successes,
                        AVG(p.latency) as avg_latency,
                        AVG(p.quality_score) as avg_quality,
                        SUM(CASE WHEN p.verification = 'VERIFIED' THEN 1 ELSE 0 END) as verified_count,
                        ROUND(SUM(CASE WHEN p.success = 1 THEN 1.0 ELSE 0.0 END) / COUNT(*), 4) as success_rate,
                        ROUND(SUM(CASE WHEN p.success = 1 THEN 1.0 ELSE 0.0 END)
                              / COUNT(*) * 0.7 + AVG(p.quality_score) * 0.3, 4) as composite_score
                    FROM performance p
                    WHERE p.entity_type = ? AND p.task_type = ?
                    GROUP BY p.entity_name
                )
                WHERE calls >= ?
                ORDER BY composite_score DESC, success_rate DESC, avg_quality DESC
                LIMIT 1
                """,
                (entity_type, task_type, min_calls),
            ).fetchone()
        if not rows:
            return None
        best = dict(rows)
        best["success_rate"] = float(best["success_rate"])
        best["composite_score"] = float(best["composite_score"])
        best["avg_latency"] = float(best["avg_latency"])
        best["avg_quality"] = float(best["avg_quality"])
        return best

    def ranking_for_task(
        self,
        entity_type: str,
        task_type: str,
        min_calls: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Get a ranked list of entities for a task type.

        Physical calculation uses composite scoring from the SQL view:
            composite = success_rate * 0.7 + avg_quality * 0.3

        Args:
            entity_type: model, agent, tool, strategy
            task_type: The task type
            min_calls: Minimum number of observations required

        Returns:
            Ranked list of entity stats dicts
        """
        with self._conn:
            rows = self._conn.execute(
                f"""
                SELECT * FROM (
                    SELECT
                        p.entity_name,
                        COUNT(*) as calls,
                        SUM(CASE WHEN p.success = 1 THEN 1 ELSE 0 END) as successes,
                        AVG(p.latency) as avg_latency,
                        AVG(p.quality_score) as avg_quality,
                        SUM(CASE WHEN p.verification = 'VERIFIED' THEN 1 ELSE 0 END) as verified_count,
                        ROUND(SUM(CASE WHEN p.success = 1 THEN 1.0 ELSE 0.0 END) / COUNT(*), 4) as success_rate,
                        ROUND(SUM(CASE WHEN p.success = 1 THEN 1.0 ELSE 0.0 END)
                              / COUNT(*) * 0.7 + AVG(p.quality_score) * 0.3, 4) as composite_score
                    FROM performance p
                    WHERE p.entity_type = ? AND p.task_type = ?
                    GROUP BY p.entity_name
                )
                WHERE calls >= ?
                ORDER BY composite_score DESC, success_rate DESC, avg_quality DESC
                """,
                (entity_type, task_type, min_calls),
            ).fetchall()

        result = []
        for r in rows:
            d = dict(r)
            d["success_rate"] = float(d["success_rate"])
            d["composite_score"] = float(d["composite_score"])
            d["avg_latency"] = float(d["avg_latency"])
            d["avg_quality"] = float(d["avg_quality"])
            result.append(d)
        return result

    def get_all_stats(self, entity_type: str) -> Dict[str, Any]:
        """
        Get aggregated stats grouped by entity and task type.

        Args:
            entity_type: model, agent, tool, strategy

        Returns:
            Dict mapping entity_name → task_type → stats
        """
        with self._conn:
            rows = self._conn.execute(
                """
                SELECT entity_name, task_type,
                       COUNT(*) as calls,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                       AVG(latency) as avg_latency,
                       AVG(quality_score) as avg_quality,
                       SUM(CASE WHEN verification = 'VERIFIED' THEN 1 ELSE 0 END) as verified_count,
                       ROUND(SUM(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) / COUNT(*), 4) as success_rate
                FROM performance
                WHERE entity_type = ?
                GROUP BY entity_name, task_type
                ORDER BY entity_name, success_rate DESC
                """,
                (entity_type,),
            ).fetchall()
        result: Dict[str, Any] = {}
        for r in rows:
            d = dict(r)
            d["success_rate"] = float(d["success_rate"])
            result.setdefault(d["entity_name"], {})[d["task_type"]] = d
        return result

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()