"""
CERBERUS — Unified Event Model.

Canonical event schema + vocabulary shared by the Web UI (SSE) and the
CLI (pollable feed).  Both clients consume the same event architecture;
only the transport differs.

Schema
------
Every event is a JSON-serializable dict with the canonical shape::

    {
        "type": "agent.started",          # from EVENT_TYPES
        "session_id": "uuid-or-'-'",      # optional, "-" when not in a session
        "agent": "recon",                 # optional, "-" when no agent involved
        "timestamp": "2026-09-07T12:00:00+00:00",  # ISO-8601 UTC
        "metadata": {...}                 # free-form, type-specific payload
    }

The legacy UI bus shape ({"type", "data", "ts"}) is still accepted by
`normalize()` so existing publishers keep working during migration.

Usage
-----
    from cyberai.orchestrator.events import Event, make_event

    ev = make_event("agent.started", session_id=sid, agent="recon",
                    metadata={"capability": "reconnaissance"})
    bus.publish_event(ev)          # UI SSE
    print(ev.cli_line())           # CLI one-line rendering
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Event vocabulary (spec §25)
# ---------------------------------------------------------------------------
SESSION_EVENTS = [
    "session.started",
    "session.completed",
    "session.failed",
]

AGENT_EVENTS = [
    "agent.started",
    "agent.progress",
    "agent.completed",
    "agent.failed",
]

TOOL_EVENTS = [
    "tool.started",
    "tool.completed",
    "tool.failed",
]

FINDING_EVENTS = [
    "finding.created",
    "finding.verified",
    "finding.rejected",
]

APPROVAL_EVENTS = [
    "approval.required",
    "approval.granted",
    "approval.denied",
]

MODEL_EVENTS = [
    "model.started",
    "model.completed",
    "model.failed",
]

POLICY_EVENTS = [
    "policy.blocked",
    "policy.allowed",
]

SYSTEM_EVENTS = [
    "system.warning",
    "system.error",
    "system.info",
]

EVENT_TYPES: List[str] = (
    SESSION_EVENTS + AGENT_EVENTS + TOOL_EVENTS + FINDING_EVENTS
    + APPROVAL_EVENTS + MODEL_EVENTS + POLICY_EVENTS + SYSTEM_EVENTS
)

# Legacy aliases emitted by the current UI server — normalized on ingest.
LEGACY_ALIASES = {
    "task_started": "session.started",
    "task_completed": "session.completed",
    "task_error": "session.failed",
    "task_result": "session.completed",
    "plan_ready": "agent.progress",
    "phase": "agent.progress",
    "audit": "system.info",
    "notification": "system.info",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Event:
    """A single canonical platform event."""

    type: str
    session_id: str = "-"
    agent: str = "-"
    timestamp: str = field(default_factory=_now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "session_id": self.session_id,
            "agent": self.agent,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    # ------------------------------------------------------------------ CLI
    def cli_line(self) -> str:
        """One-line CLI rendering: [HH:MM:SS] [TYPE] agent detail."""
        ts = self.timestamp
        try:
            hhmmss = datetime.fromisoformat(ts).strftime("%H:%M:%S")
        except Exception:
            hhmmss = ts[:8] if len(ts) >= 8 else ts
        agent = self.agent if self.agent != "-" else ""
        detail = self._detail()
        prefix = f"[{hhmmss}] [{self.type}]"
        if agent:
            prefix += f" {agent}"
        return f"{prefix} {detail}".rstrip()

    def _detail(self) -> str:
        m = self.metadata or {}
        for key in ("objective", "message", "summary", "action", "tool",
                    "error", "detail", "title", "observation", "phase"):
            if m.get(key):
                return str(m[key])[:120]
        return ""

    # ------------------------------------------------------------------ Web
    def sse_payload(self) -> Dict[str, Any]:
        """Payload for the SSE stream (keeps the legacy envelope)."""
        return {"type": self.type, "data": self.to_dict(), "ts": time.time()}


def make_event(
    event_type: str,
    session_id: str = "-",
    agent: str = "-",
    metadata: Optional[Dict[str, Any]] = None,
    timestamp: Optional[str] = None,
) -> Event:
    """Create a canonical event, validating the type against the vocabulary.

    Unknown types are kept as-is (forward compatibility) but flagged via
    `metadata["_unknown_type"]` so tests can catch vocabulary drift.
    """
    meta = dict(metadata or {})
    if event_type not in EVENT_TYPES:
        meta.setdefault("_unknown_type", True)
    return Event(
        type=event_type,
        session_id=session_id or "-",
        agent=agent or "-",
        timestamp=timestamp or _now_iso(),
        metadata=meta,
    )


def normalize(raw: Dict[str, Any]) -> Event:
    """Normalize a legacy bus event ({"type", "data", "ts"}) into an Event.

    Accepts both the legacy envelope and the canonical shape.
    """
    etype = str(raw.get("type", "system.info"))
    etype = LEGACY_ALIASES.get(etype, etype)

    if "metadata" in raw:
        # Canonical shape
        return Event(
            type=etype,
            session_id=str(raw.get("session_id", "-")),
            agent=str(raw.get("agent", "-")),
            timestamp=str(raw.get("timestamp", _now_iso())),
            metadata=dict(raw.get("metadata") or {}),
        )

    # Legacy envelope: {"type", "data": {...}, "ts": epoch}
    data = raw.get("data") or {}
    ts = raw.get("ts")
    if isinstance(ts, (int, float)):
        stamp = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    else:
        stamp = _now_iso()
    session_id = str(data.get("session_id", data.get("session", "-")))
    agent = str(data.get("agent", "-"))
    # Promote well-known detail keys into metadata
    meta = {k: v for k, v in data.items() if k not in ("session_id", "session", "agent")}
    return Event(type=etype, session_id=session_id, agent=agent,
                 timestamp=stamp, metadata=meta)


def validate(event: Event) -> List[str]:
    """Return a list of schema problems (empty list = valid)."""
    problems: List[str] = []
    if not event.type or not isinstance(event.type, str):
        problems.append("type must be a non-empty string")
    elif "." not in event.type:
        problems.append(f"type '{event.type}' is not namespaced (expected 'x.y')")
    if not isinstance(event.timestamp, str) or not event.timestamp:
        problems.append("timestamp must be a non-empty ISO-8601 string")
    else:
        try:
            datetime.fromisoformat(event.timestamp)
        except Exception:
            problems.append(f"timestamp '{event.timestamp}' is not ISO-8601")
    if not isinstance(event.metadata, dict):
        problems.append("metadata must be a dict")
    return problems
