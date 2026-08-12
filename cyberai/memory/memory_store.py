"""
Typed Memory Store for the Cyber AI platform.

Implements:
- Episodic memory: What happened during experiments
- Semantic memory: What vulnerability patterns/techniques mean
- Procedural memory: What strategies historically worked
- Tool memory: Which tools worked in which environments
- Failure memory: Which strategies repeatedly failed
- Experiment memory: Which strategy was tested and how it scored

Uses SQLite with JSON columns for flexibility. Supports ranked
retrieval based on similarity, success rate, verification status,
recency, environment, tool, target type, and confidence.
"""

import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MEMORY_TYPES = {
    "episodic", "semantic", "procedural", "tool", "failure", "experiment"
}


@dataclass
class MemoryEntry:
    """A single memory entry."""

    memory_type: str  # episodic, semantic, procedural, tool, failure, experiment
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    success_rate: float = 0.0
    verification: str = "UNVERIFIED"  # UNVERIFIED, LIKELY, VERIFIED, REJECTED
    memory_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_accessed: str = ""
    access_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "memory_type": self.memory_type,
            "content": self.content,
            "metadata": self.metadata,
            "confidence": self.confidence,
            "success_rate": self.success_rate,
            "verification": self.verification,
            "timestamp": self.timestamp,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
        }


class MemoryStore:
    """Typed, ranked memory store for experiences."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(__file__).parent.parent.parent / "memory" / "experiences.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    memory_type TEXT,
                    content TEXT,
                    metadata TEXT,
                    confidence REAL,
                    success_rate REAL,
                    verification TEXT,
                    timestamp TEXT,
                    last_accessed TEXT,
                    access_count INTEGER DEFAULT 0
                )
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_type
                ON memories (memory_type)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_ts
                ON memories (timestamp)
            """)

    def store(self, entry: MemoryEntry) -> str:
        """Store a memory entry."""
        if entry.memory_type not in MEMORY_TYPES:
            raise ValueError(f"Unknown memory type: {entry.memory_type}. Valid: {MEMORY_TYPES}")
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO memories (
                    memory_id, memory_type, content, metadata,
                    confidence, success_rate, verification,
                    timestamp, last_accessed, access_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.memory_id,
                    entry.memory_type,
                    entry.content,
                    json.dumps(entry.metadata),
                    entry.confidence,
                    entry.success_rate,
                    entry.verification,
                    entry.timestamp,
                    entry.last_accessed,
                    entry.access_count,
                ),
            )
        logger.debug(f"Stored {entry.memory_type} memory {entry.memory_id}")
        return entry.memory_id

    def store_simple(
        self,
        memory_type: str,
        content: str,
        confidence: float = 0.0,
        success_rate: float = 0.0,
        verification: str = "UNVERIFIED",
        **metadata: Any,
    ) -> str:
        """Convenience method to store a memory entry."""
        return self.store(MemoryEntry(
            memory_type=memory_type,
            content=content,
            confidence=confidence,
            success_rate=success_rate,
            verification=verification,
            metadata=metadata,
        ))

    def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a memory entry by ID."""
        with self._conn:
            row = self._conn.execute(
                "SELECT * FROM memories WHERE memory_id = ?", (memory_id,)
            ).fetchone()
        if not row:
            return None
        entry = dict(row)
        entry["metadata"] = json.loads(entry.get("metadata", "{}"))
        # Update access count
        with self._conn:
            self._conn.execute(
                "UPDATE memories SET access_count = access_count + 1, last_accessed = ? WHERE memory_id = ?",
                (datetime.now(timezone.utc).isoformat(), memory_id),
            )
        return entry

    def get_by_type(self, memory_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get memories of a specific type."""
        with self._conn:
            rows = self._conn.execute(
                """
                SELECT * FROM memories
                WHERE memory_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (memory_type, limit),
            ).fetchall()
        return [self._parse_row(r) for r in rows]

    def get_by_metadata(self, memory_type: str, key: str, value: Any, limit: int = 50) -> List[Dict[str, Any]]:
        """Get memories filtered by a metadata key-value pair."""
        # Load all of the type and filter in Python (simple approach)
        all_memories = self.get_by_type(memory_type, limit=1000)
        result = []
        for m in all_memories:
            if m.get("metadata", {}).get(key) == value:
                result.append(m)
            if len(result) >= limit:
                break
        return result

    def _parse_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Parse a database row into a memory dict with parsed metadata."""
        entry = dict(row)
        entry["metadata"] = json.loads(entry.get("metadata", "{}"))
        return entry

    def search(
        self,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 10,
        min_confidence: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Search memories by keyword with ranking.

        Ranking considers:
        - Text similarity (keyword match)
        - Success rate
        - Verification status
        - Recency
        - Confidence

        Args:
            query: The search query
            memory_type: Optional memory type filter
            limit: Max results
            min_confidence: Minimum confidence threshold

        Returns:
            Ranked list of memory entries
        """
        params: List[Any] = []
        sql = "SELECT * FROM memories WHERE 1=1"
        if memory_type:
            sql += " AND memory_type = ?"
            params.append(memory_type)
        sql += """
            AND (content LIKE ? OR metadata LIKE ?)
            ORDER BY
                CASE verification
                    WHEN 'VERIFIED' THEN 3
                    WHEN 'LIKELY' THEN 2
                    WHEN 'UNVERIFIED' THEN 1
                    ELSE 0
                END DESC,
                success_rate DESC,
                confidence DESC,
                timestamp DESC
            LIMIT ?
        """
        like = f"%{query}%"
        params.extend([like, like, limit])

        with self._conn:
            rows = self._conn.execute(sql, params).fetchall()
        return [self._parse_row(r) for r in rows]

    def retrieve_for_planning(
        self,
        task_objective: str,
        environment: str = "authorized_lab",
        target_type: str = "",
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories for planning.

        Uses a combined score:
        score = text_similarity * 0.4
              + success_rate * 0.2
              + verification_score * 0.2
              + recency_score * 0.1
              + environment_match * 0.1

        Args:
            task_objective: The task objective text
            environment: The environment
            target_type: The target type
            limit: Max results

        Returns:
            Ranked list of memory entries
        """
        # Simple keyword-based search first
        keywords = [w.lower() for w in task_objective.split() if len(w) > 3]
        if not keywords:
            return self.search(task_objective, limit=limit)

        all_memories = []
        for memory_type in ("procedural", "episodic", "semantic", "experiment"):
            all_memories.extend(self.get_by_type(memory_type, limit=100))

        if not all_memories:
            return []

        now = datetime.now(timezone.utc)
        scored = []
        for m in all_memories:
            content_lower = m["content"].lower()
            metadata = m.get("metadata", {})

            # Text similarity score (simple keyword overlap)
            matches = sum(1 for k in keywords if k in content_lower)
            sim_score = min(matches / max(len(keywords), 1), 1.0)

            # Success rate component
            success = float(m.get("success_rate", 0.0))

            # Verification component
            verification_scores = {"VERIFIED": 1.0, "LIKELY": 0.6, "UNVERIFIED": 0.2, "REJECTED": 0.0}
            verif_score = verification_scores.get(m.get("verification", "UNVERIFIED"), 0.0)

            # Recency component (0-1, newer is better)
            try:
                ts = datetime.fromisoformat(m["timestamp"])
                age_days = max((now - ts).total_seconds() / 86400, 0)
                recency = max(0.0, 1.0 - age_days / 30.0)
            except (ValueError, TypeError):
                recency = 0.0

            # Environment match
            env_match = 1.0 if metadata.get("environment") == environment else 0.5

            # Target type match
            tt_match = 1.0 if (not target_type or metadata.get("target_type") == target_type) else 0.5

            total = (
                sim_score * 0.4
                + success * 0.2
                + verif_score * 0.2
                + recency * 0.1
                + env_match * 0.05
                + tt_match * 0.05
            )

            # Include if there's at least some relevance
            if total > 0.1:
                scored.append((total, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:limit]]

    def record_experiment(
        self,
        strategy_id: str,
        strategy_description: str,
        generation: int,
        fitness: float,
        success: bool,
        verified: bool = False,
        **metadata: Any,
    ) -> str:
        """Record an experiment result (strategy tested and scored)."""
        return self.store_simple(
            memory_type="experiment",
            content=f"Strategy {strategy_id}: {strategy_description} (gen {generation})",
            confidence=min(fitness / 3.0, 1.0),
            success_rate=1.0 if success else 0.0,
            verification="VERIFIED" if verified else ("LIKELY" if success else "UNVERIFIED"),
            strategy_id=strategy_id,
            generation=generation,
            fitness=fitness,
            success=success,
            **metadata,
        )

    def record_failure(
        self,
        strategy_id: str,
        reason: str,
        failure_category: str,
        tool: str = "",
        agent: str = "",
        model: str = "",
        environment: str = "authorized_lab",
        **metadata: Any,
    ) -> str:
        """Record a failure for future avoidance."""
        return self.store_simple(
            memory_type="failure",
            content=f"Strategy {strategy_id} failed: {reason}",
            success_rate=0.0,
            verification="REJECTED",
            strategy_id=strategy_id,
            reason=reason,
            failure_category=failure_category,
            tool=tool,
            agent=agent,
            model=model,
            environment=environment,
            **metadata,
        )

    def get_failures_similar(self, strategy_description: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get failure memories similar to a strategy description."""
        return self.search(strategy_description, memory_type="failure", limit=limit)

    def update_feedback(
        self,
        memory_id: str,
        success_rate: Optional[float] = None,
        verification: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> None:
        """Update feedback metrics on a memory entry."""
        updates = []
        params: List[Any] = []
        if success_rate is not None:
            updates.append("success_rate = ?")
            params.append(success_rate)
        if verification is not None:
            updates.append("verification = ?")
            params.append(verification)
        if confidence is not None:
            updates.append("confidence = ?")
            params.append(confidence)
        if not updates:
            return
        params.append(memory_id)
        with self._conn:
            self._conn.execute(
                f"UPDATE memories SET {', '.join(updates)} WHERE memory_id = ?",
                params,
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        with self._conn:
            total = self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            by_type = {}
            for t in MEMORY_TYPES:
                count = self._conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE memory_type = ?", (t,)
                ).fetchone()[0]
                by_type[t] = count
        return {
            "total": total,
            "by_type": by_type,
        }

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()