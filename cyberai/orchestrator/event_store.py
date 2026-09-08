"""
CERBERUS — Persistent Event Store (spec §24).

The canonical event model lives in `cyberai.orchestrator.events`. This
module adds the missing persistence + fan-out layer:

    EventStore
      ├── append(event)          persist + fan out to subscribers
      ├── history(limit, since)  newest-first canonical events
      └── subscribe()/unsubscribe()  live tails (CLI /watch, SSE)

Design rules (consistent with the platform's "SQLite-first" philosophy):
- SQLite is the default and only required backend (spec §12).
- The store is crash-safe: a corrupted DB degrades to in-memory mode
  with a warning — it never takes the platform down.
- Events are stored in the canonical shape; legacy envelopes are
  normalized on ingest via `events.normalize()`.
- The UI's LiveEventBus and the CLI's /watch both delegate here, so
  the Web UI and CLI are two windows onto the SAME event stream.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from cyberai.config import WORKSPACE_ROOT
from cyberai.orchestrator.events import (  # noqa: F401 (Event re-exported)
    Event, LEGACY_ALIASES, make_event, normalize,
)

logger = logging.getLogger(__name__)

_DEFAULT_DB = WORKSPACE_ROOT / "logs" / "events.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    type TEXT NOT NULL,
    session_id TEXT NOT NULL DEFAULT '-',
    agent TEXT NOT NULL DEFAULT '-',
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events (ts DESC);
CREATE INDEX IF NOT EXISTS idx_events_type ON events (type);
CREATE INDEX IF NOT EXISTS idx_events_session ON events (session_id);
"""


class EventStore:
    """Persistent, fan-out event store backing both the UI and the CLI."""

    def __init__(self, db_path: Optional[Path] = None, max_history: int = 2000):
        self._db_path = Path(db_path) if db_path else _DEFAULT_DB
        self._max_history = max_history
        self._subscribers: Dict[str, Callable[[Event], None]] = {}
        self._lock = threading.RLock()
        self._memory_history: List[Event] = []
        self._sqlite_ok = False
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    # ------------------------------------------------------------------ db
    def _init_db(self) -> None:
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.executescript(_SCHEMA)
            self._conn.commit()
            self._sqlite_ok = True
        except Exception as e:  # noqa: BLE001 — degrade, never crash
            logger.warning("EventStore: SQLite unavailable (%s) — in-memory mode", e)
            self._sqlite_ok = False
            self._conn = None

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

    # ------------------------------------------------------------- ingest
    def append(self, event: Event) -> Event:
        """Persist an event and fan it out to live subscribers."""
        with self._lock:
            if self._sqlite_ok and self._conn is not None:
                try:
                    self._conn.execute(
                        "INSERT INTO events (ts, type, session_id, agent, metadata) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (event.timestamp, event.type, event.session_id,
                         event.agent, json.dumps(event.metadata, default=str)),
                    )
                    self._conn.commit()
                except Exception as e:  # noqa: BLE001
                    logger.debug("EventStore insert failed: %s", e)
            self._memory_history.append(event)
            if len(self._memory_history) > self._max_history:
                self._memory_history = self._memory_history[-self._max_history:]
            subscribers = list(self._subscribers.values())
        for cb in subscribers:
            try:
                cb(event)
            except Exception:  # noqa: BLE001 — one bad subscriber never kills others
                pass
        return event

    def append_raw(self, raw: Dict[str, Any]) -> Event:
        """Normalize a legacy/raw envelope then append (UI bridge path)."""
        return self.append(normalize(raw))

    def publish(self, event_type: str, data: Dict[str, Any],
                session_id: str = "-", agent: str = "-") -> Event:
        """Convenience: build a canonical event from parts and append.

        Mirrors the legacy LiveEventBus.publish(event_type, data) call
        shape so existing publishers can migrate with a one-line change.
        """
        sid = session_id
        ag = agent
        if sid == "-" and isinstance(data, dict):
            sid = str(data.get("session_id") or data.get("session") or "-")
            ag = str(data.get("agent") or ag)
        # Legacy type names (task_started etc.) map to canonical ones
        etype = LEGACY_ALIASES.get(event_type, event_type)
        return self.append(make_event(etype, session_id=sid, agent=ag,
                                      metadata=data))

    # ------------------------------------------------------------- read
    def history(self, limit: int = 200, since: str = "",
                event_type: str = "") -> List[Event]:
        """Newest-first event history (survives restarts via SQLite)."""
        with self._lock:
            if self._sqlite_ok and self._conn is not None:
                try:
                    q = ("SELECT ts, type, session_id, agent, metadata "
                         "FROM events")
                    conds, params = [], []
                    if since:
                        conds.append("ts > ?")
                        params.append(since)
                    if event_type:
                        conds.append("type = ?")
                        params.append(event_type)
                    if conds:
                        q += " WHERE " + " AND ".join(conds)
                    q += " ORDER BY id DESC LIMIT ?"
                    params.append(int(limit))
                    rows = self._conn.execute(q, params).fetchall()
                    return [Event(
                        type=r["type"], session_id=r["session_id"],
                        agent=r["agent"], timestamp=r["ts"],
                        metadata=json.loads(r["metadata"] or "{}"),
                    ) for r in rows]
                except Exception as e:  # noqa: BLE001
                    logger.debug("EventStore query failed: %s", e)
            # In-memory fallback (newest first)
            out = list(reversed(self._memory_history))
            if since:
                out = [e for e in out if e.timestamp > since]
            if event_type:
                out = [e for e in out if e.type == event_type]
            return out[:limit]

    # -------------------------------------------------------- subscribers
    def subscribe(self, callback: Callable[[Event], None]) -> str:
        sub_id = f"sub-{time.time_ns()}"
        with self._lock:
            self._subscribers[sub_id] = callback
        return sub_id

    def unsubscribe(self, sub_id: str) -> None:
        with self._lock:
            self._subscribers.pop(sub_id, None)

    # ------------------------------------------------------------- stats
    def stats(self) -> Dict[str, Any]:
        """Counts by type — powers the UI activity feed badges."""
        with self._lock:
            if self._sqlite_ok and self._conn is not None:
                try:
                    rows = self._conn.execute(
                        "SELECT type, COUNT(*) AS n FROM events "
                        "GROUP BY type ORDER BY n DESC").fetchall()
                    total = self._conn.execute(
                        "SELECT COUNT(*) AS n FROM events").fetchone()["n"]
                    return {"total": total,
                            "by_type": {r["type"]: r["n"] for r in rows},
                            "backend": "sqlite"}
                except Exception:  # noqa: BLE001
                    pass
        counts: Dict[str, int] = {}
        for e in self._memory_history:
            counts[e.type] = counts.get(e.type, 0) + 1
        return {"total": len(self._memory_history), "by_type": counts,
                "backend": "memory"}


# ---------------------------------------------------------------------------
# Module-level shared store (one per process)
# ---------------------------------------------------------------------------
_STORE: Optional[EventStore] = None
_STORE_LOCK = threading.Lock()


def get_event_store() -> EventStore:
    """Return the process-wide shared EventStore (lazily created)."""
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            _STORE = EventStore()
        return _STORE
