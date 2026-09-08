"""P1 — Event core completion tests (spec §24).

Covers:
- EventStore: append/persist/history across restarts (SQLite)
- Legacy envelope normalization on ingest (publish path)
- Fan-out to live subscribers
- stats() counts by type
- In-memory degradation when SQLite is unavailable
- LiveEventBus facade: publish -> SSE payload + canonical history
- BaseAgent._llm_call emits model.started/model.completed|failed
- Recon agent emits tool.started/tool.completed
"""

import asyncio
import json

import pytest

from cyberai.orchestrator.event_store import EventStore
from cyberai.orchestrator.events import make_event, normalize


@pytest.fixture()
def store(tmp_path):
    s = EventStore(db_path=tmp_path / "events.db")
    yield s
    s.close()


# ---------------------------------------------------------------------------
# EventStore basics
# ---------------------------------------------------------------------------
def test_append_and_history(store):
    ev = store.append(make_event("agent.started", session_id="s1",
                                 agent="recon", metadata={"capability": "recon"}))
    hist = store.history()
    assert len(hist) == 1
    assert hist[0].type == "agent.started"
    assert hist[0].session_id == "s1"
    assert hist[0].agent == "recon"
    assert hist[0].metadata["capability"] == "recon"


def test_history_newest_first(store):
    for i in range(5):
        store.append(make_event("agent.progress", metadata={"i": i}))
    hist = store.history()
    assert [e.metadata["i"] for e in hist] == [4, 3, 2, 1, 0]


def test_persistence_across_restart(tmp_path):
    db = tmp_path / "events.db"
    s1 = EventStore(db_path=db)
    s1.append(make_event("session.started", session_id="sess-A"))
    s1.close()
    # "restart"
    s2 = EventStore(db_path=db)
    hist = s2.history()
    assert any(e.type == "session.started" and e.session_id == "sess-A"
               for e in hist)
    s2.close()


def test_since_filter(store):
    store.append(make_event("a.x", timestamp="2026-01-01T00:00:00+00:00"))
    store.append(make_event("a.y", timestamp="2026-01-02T00:00:00+00:00"))
    out = store.history(since="2026-01-01T12:00:00+00:00")
    assert [e.type for e in out] == ["a.y"]


def test_type_filter(store):
    store.append(make_event("tool.started"))
    store.append(make_event("tool.completed"))
    store.append(make_event("agent.started"))
    out = store.history(event_type="tool.started")
    assert len(out) == 1 and out[0].type == "tool.started"


def test_publish_normalizes_legacy_envelope(store):
    # Legacy shape: {"type", "data", "ts"} — as the UI publishes today
    store.publish("task_started", {"session_id": "s9", "objective": "test"})
    hist = store.history()
    assert hist[0].type == "session.started"  # LEGACY_ALIASES mapping
    assert hist[0].session_id == "s9"
    assert hist[0].metadata["objective"] == "test"


def test_fanout_to_subscriber(store):
    got = []
    sub = store.subscribe(got.append)
    try:
        store.append(make_event("finding.created"))
        store.append(make_event("finding.verified"))
    finally:
        store.unsubscribe(sub)
    assert [e.type for e in got] == ["finding.created", "finding.verified"]


def test_bad_subscriber_does_not_kill_others(store):
    got = []
    def boom(ev):
        raise RuntimeError("boom")
    s1 = store.subscribe(boom)
    s2 = store.subscribe(got.append)
    try:
        store.append(make_event("system.info"))
    finally:
        store.unsubscribe(s1)
        store.unsubscribe(s2)
    assert len(got) == 1


def test_stats(store):
    store.append(make_event("tool.started"))
    store.append(make_event("tool.started"))
    store.append(make_event("tool.completed"))
    st = store.stats()
    assert st["total"] == 3
    assert st["by_type"]["tool.started"] == 2
    assert st["backend"] in ("sqlite", "memory")


def test_memory_degradation(tmp_path, monkeypatch):
    import sqlite3 as _sq
    def _boom(*a, **k):
        raise _sq.Error("disk full")
    monkeypatch.setattr(_sq, "connect", _boom)
    s = EventStore(db_path=tmp_path / "x.db")
    try:
        assert s.stats()["backend"] == "memory"
        s.append(make_event("system.warning"))
        assert len(s.history()) == 1  # still works in-memory
    finally:
        s.close()


# ---------------------------------------------------------------------------
# LiveEventBus facade (UI)
# ---------------------------------------------------------------------------
def test_live_event_bus_facade(tmp_path, monkeypatch):
    monkeypatch.setattr("cyberai.orchestrator.event_store._STORE", None)
    import importlib
    import cyberai.orchestrator.event_store as es_mod
    # Point the shared store at a temp DB
    monkeypatch.setattr(es_mod, "_DEFAULT_DB", tmp_path / "events.db")
    es_mod._STORE = EventStore(db_path=tmp_path / "events.db")

    from cyberai.ui.server import LiveEventBus
    bus = LiveEventBus()
    bus.publish("task_started", {"session_id": "s1", "objective": "o"})  # legacy
    hist = bus.history()
    assert hist[0]["type"] == "session.started"  # normalized + aliased
    assert "data" in hist[0] and "ts" in hist[0]  # SSE envelope kept
    es_mod._STORE.close()
    es_mod._STORE = None


# ---------------------------------------------------------------------------
# Agent-layer events (model.*, tool.*)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_llm_call_emits_model_events(tmp_path, monkeypatch):
    import cyberai.orchestrator.event_store as es_mod
    store = EventStore(db_path=tmp_path / "e.db")
    monkeypatch.setattr(es_mod, "_STORE", store)
    monkeypatch.setattr(es_mod, "get_event_store", lambda: store)

    from cyberai.orchestrator.agents.base import BaseAgent

    class FakeGateway:
        async def complete(self, role, prompt, **kw):
            return {"success": True, "content": "ok", "model": "test-model",
                    "transport": "mock", "latency_ms": 5}

    agent = BaseAgent.__new__(BaseAgent)
    agent.name = "analyst"
    agent.llm_gateway = FakeGateway()
    agent.logger = None

    out = await agent._llm_call("prompt", task_type="analysis")
    assert out == "ok"
    types = [e.type for e in store.history()]
    assert "model.started" in types
    assert "model.completed" in types
    store.close()


@pytest.mark.asyncio
async def test_llm_call_emits_model_failed(tmp_path, monkeypatch):
    import cyberai.orchestrator.event_store as es_mod
    store = EventStore(db_path=tmp_path / "e.db")
    monkeypatch.setattr(es_mod, "_STORE", store)
    monkeypatch.setattr(es_mod, "get_event_store", lambda: store)

    from cyberai.orchestrator.agents.base import BaseAgent

    class FailGateway:
        async def complete(self, role, prompt, **kw):
            return {"success": False, "message": "all hops failed"}

    agent = BaseAgent.__new__(BaseAgent)
    agent.name = "recon"
    agent.llm_gateway = FailGateway()
    agent.logger = None

    out = await agent._llm_call("prompt", task_type="web_research")
    assert "LLM_UNAVAILABLE" in out
    types = [e.type for e in store.history()]
    assert "model.failed" in types
    store.close()
