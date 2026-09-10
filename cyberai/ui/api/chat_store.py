"""Chat persistence — extends the existing MemoryManager session system.

Per the redesign spec: "Do not create a second unrelated persistence
system if the existing MemoryManager/session system can be extended."

Chats ARE sessions (rows in the same ``sessions`` table) with
``metadata.kind = "chat"``. Messages live in a new ``chat_messages``
table in the SAME SQLite database (memory/memory.db), added by an
idempotent migration on first use.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cyberai.config import config

_ROLES = ("user", "assistant", "system", "event")


class ChatStore:
    """Message persistence for chat sessions, sharing memory/memory.db."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.get_path("memory", "db_path", "memory/memory.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    model TEXT,
                    mode TEXT,
                    created_at TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chat_messages_session "
                "ON chat_messages(session_id, created_at)")

    # ------------------------------------------------------------ messages
    def append_message(self, session_id: str, role: str, content: str,
                       model: Optional[str] = None, mode: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if role not in _ROLES:
            raise ValueError(f"invalid role {role!r}; valid: {', '.join(_ROLES)}")
        msg_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO chat_messages (
                    id, session_id, role, content, model, mode, created_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (msg_id, session_id, role, content, model, mode, now,
                 json.dumps(metadata) if metadata else None),
            )
        return self.get_message(msg_id)

    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            "SELECT * FROM chat_messages WHERE id = ?", (message_id,)).fetchone()
        return self._decode(row)

    def list_messages(self, session_id: str,
                      limit: int = 200) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM chat_messages WHERE session_id = ? "
            "ORDER BY created_at ASC LIMIT ?",
            (session_id, limit)).fetchall()
        return [self._decode(r) for r in rows]

    def delete_messages(self, session_id: str) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM chat_messages WHERE session_id = ?", (session_id,))

    # ------------------------------------------------------------- session
    def delete_chat(self, session_id: str) -> None:
        """Delete a chat session row + its messages."""
        with self._conn:
            self._conn.execute(
                "DELETE FROM sessions WHERE id = ?", (session_id,))
            self._conn.execute(
                "DELETE FROM chat_messages WHERE session_id = ?", (session_id,))

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _decode(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        if row is None:
            return None
        d = dict(row)
        raw = d.get("metadata")
        if raw:
            try:
                d["metadata"] = json.loads(raw)
            except (TypeError, ValueError):
                d["metadata"] = {}
        else:
            d["metadata"] = {}
        return d

    def close(self) -> None:
        self._conn.close()
