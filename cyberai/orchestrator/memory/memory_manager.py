"""
Memory Manager for the Cyber AI Orchestrator.

Persistent memory layer that stores structured experiences from
authorized lab tasks. Supports semantic retrieval for future planning.
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cyberai.config import config

logger = logging.getLogger(__name__)

# Finding states
UNVERIFIED = "UNVERIFIED"
LIKELY = "LIKELY"
VERIFIED = "VERIFIED"
REJECTED = "REJECTED"


class MemoryManager:
    """
    Manages persistent memory storage and retrieval.

    Uses SQLite for structured storage with JSON columns for flexibility.
    Supports semantic retrieval via embeddings when available.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.get_path("memory", "db_path", "memory/memory.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS experiences (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    target_id TEXT,
                    target_type TEXT,
                    environment TEXT,
                    observation TEXT,
                    hypothesis TEXT,
                    action TEXT,
                    tool TEXT,
                    result TEXT,
                    evidence TEXT,
                    confidence REAL,
                    lessons TEXT,
                    timestamp TEXT,
                    score REAL DEFAULT 0.0
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS findings (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    target_id TEXT,
                    observation TEXT,
                    evidence TEXT,
                    status TEXT,
                    confidence REAL,
                    source TEXT,
                    timestamp TEXT
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    target_id TEXT,
                    started_at TEXT,
                    ended_at TEXT,
                    status TEXT,
                    summary TEXT
                )
            """)

    def store_experience(self, experience: Dict[str, Any]) -> str:
        """
        Store a structured experience record.

        Args:
            experience: Dict with keys matching the experience schema

        Returns:
            The experience ID
        """
        exp_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        with self._conn:
            self._conn.execute(
                """
                INSERT INTO experiences (
                    id, session_id, target_id, target_type, environment,
                    observation, hypothesis, action, tool, result,
                    evidence, confidence, lessons, timestamp, score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    exp_id,
                    experience.get("session_id", ""),
                    experience.get("target_id", ""),
                    experience.get("target_type", ""),
                    experience.get("environment", "authorized_lab"),
                    experience.get("observation", ""),
                    experience.get("hypothesis", ""),
                    experience.get("action", ""),
                    experience.get("tool", ""),
                    experience.get("result", ""),
                    json.dumps(experience.get("evidence", "")),
                    experience.get("confidence", 0.0),
                    json.dumps(experience.get("lessons", [])),
                    experience.get("timestamp", now),
                    experience.get("score", 0.0),
                ),
            )
        logger.info(f"Stored experience {exp_id}")
        return exp_id

    def search_experiences(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search experiences by keyword (semantic search when embeddings available).

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of experience dicts
        """
        # Simple keyword search (semantic search can be added with embeddings)
        with self._conn:
            rows = self._conn.execute(
                """
                SELECT * FROM experiences
                WHERE observation LIKE ? OR hypothesis LIKE ? OR action LIKE ? OR lessons LIKE ?
                ORDER BY score DESC, timestamp DESC
                LIMIT ?
                """,
                (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_experiences_by_result(self, result: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get experiences filtered by result (success/failure)."""
        with self._conn:
            rows = self._conn.execute(
                """
                SELECT * FROM experiences
                WHERE result = ?
                ORDER BY score DESC, timestamp DESC
                LIMIT ?
                """,
                (result, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def score_experience(self, exp_id: str, score_delta: float) -> None:
        """
        Update the score of an experience.

        Positive scores for successful strategies, negative for failures.
        """
        with self._conn:
            self._conn.execute(
                "UPDATE experiences SET score = score + ? WHERE id = ?",
                (score_delta, exp_id),
            )
        logger.info(f"Updated score for {exp_id} by {score_delta}")

    def store_finding(self, finding: Dict[str, Any]) -> str:
        """
        Store a finding with verification status.

        Args:
            finding: Dict with observation, evidence, status, confidence, etc.

        Returns:
            The finding ID
        """
        finding_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        with self._conn:
            self._conn.execute(
                """
                INSERT INTO findings (
                    id, session_id, target_id, observation, evidence,
                    status, confidence, source, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    finding_id,
                    finding.get("session_id", ""),
                    finding.get("target_id", ""),
                    finding.get("observation", ""),
                    json.dumps(finding.get("evidence", "")),
                    finding.get("status", UNVERIFIED),
                    finding.get("confidence", 0.0),
                    finding.get("source", ""),
                    finding.get("timestamp", now),
                ),
            )
        logger.info(f"Stored finding {finding_id} with status {finding.get('status', UNVERIFIED)}")
        return finding_id

    def update_finding_status(self, finding_id: str, status: str) -> None:
        """Update the verification status of a finding."""
        with self._conn:
            self._conn.execute(
                "UPDATE findings SET status = ? WHERE id = ?",
                (status, finding_id),
            )
        logger.info(f"Updated finding {finding_id} status to {status}")

    def get_findings(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get findings, optionally filtered by status."""
        if status:
            with self._conn:
                rows = self._conn.execute(
                    "SELECT * FROM findings WHERE status = ? ORDER BY timestamp DESC",
                    (status,),
                ).fetchall()
        else:
            with self._conn:
                rows = self._conn.execute(
                    "SELECT * FROM findings ORDER BY timestamp DESC"
                ).fetchall()
        return [dict(row) for row in rows]

    def create_session(self, target_id: str) -> str:
        """Create a new session record."""
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._conn:
            self._conn.execute(
                "INSERT INTO sessions (id, target_id, started_at, status) VALUES (?, ?, ?, ?)",
                (session_id, target_id, now, "active"),
            )
        return session_id

    def end_session(self, session_id: str, summary: str = "") -> None:
        """End a session and record its summary."""
        now = datetime.now(timezone.utc).isoformat()
        with self._conn:
            self._conn.execute(
                "UPDATE sessions SET ended_at = ?, status = ?, summary = ? WHERE id = ?",
                (now, "completed", summary, session_id),
            )

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions."""
        with self._conn:
            rows = self._conn.execute(
                "SELECT * FROM sessions ORDER BY started_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID."""
        with self._conn:
            row = self._conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        return dict(row) if row else None

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()