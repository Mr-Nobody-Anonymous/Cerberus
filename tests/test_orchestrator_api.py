"""Tests for the orchestrator REST API (cyberai.orchestrator.api.api_server).

Covers all endpoints of create_app():
  - /            root info
  - /status      aggregate counters
  - /targets      and /targets/authorized
  - /sessions    list + 404 for unknown session
  - /findings    with optional status filter
  - /memory/search
  - /tools
  - /models

The app is created against isolated tmp storage (memory DB, targets
file) so tests never touch the real workspace databases.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
httpx = pytest.importorskip("httpx", reason="httpx not installed for TestClient")

from fastapi.testclient import TestClient  # noqa: E402

from cyberai.orchestrator.api.api_server import create_app  # noqa: E402

TARGETS_YAML = """\
targets:
- id: juice-shop
  host: 127.0.0.1
  port: 8080
  protocol: http
  environment: authorized_lab
  allowed: true
  allowed_actions: [recon, scan]
  description: Juice Shop
- id: blocked
  host: 127.0.0.1
  port: 8081
  protocol: http
  environment: authorized_lab
  allowed: false
  allowed_actions: []
  description: Not allowed
"""


@pytest.fixture
def client(tmp_path):
    """App wired to tmp memory DB + tmp targets file."""
    targets = tmp_path / "targets.yaml"
    targets.write_text(TARGETS_YAML, encoding="utf-8")

    from cyberai.orchestrator.memory.memory_manager import MemoryManager
    from cyberai.orchestrator.policies.policy_engine import PolicyEngine

    # check_same_thread=False: TestClient serves the ASGI app from a
    # different thread than the one where the connection was created.
    memory = MemoryManager(db_path=tmp_path / "memory.db")
    memory._conn.close()
    import sqlite3
    memory._conn = sqlite3.connect(str(tmp_path / "memory.db"),
                                   check_same_thread=False)
    memory._conn.row_factory = sqlite3.Row
    memory._init_db()
    policy = PolicyEngine(targets_path=targets)

    with patch("cyberai.orchestrator.api.api_server.MemoryManager",
               return_value=memory), \
         patch("cyberai.orchestrator.api.api_server.PolicyEngine",
               return_value=policy):
        app = create_app()
    assert app is not None, "FastAPI must be installed for these tests"
    return TestClient(app)


class TestRootAndStatus:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        body = r.json()
        assert body["platform"] == "Cyber AI Orchestrator"
        assert body["status"] == "running"

    def test_status_counts(self, client):
        r = client.get("/status")
        assert r.status_code == 200
        body = r.json()
        assert body["targets_authorized"] == 1  # only juice-shop
        assert body["sessions"] == 0
        assert isinstance(body["tools_registered"], int)
        assert isinstance(body["models"], int)


class TestTargets:
    def test_list_targets(self, client):
        r = client.get("/targets")
        assert r.status_code == 200
        ids = {t["id"] for t in r.json()["targets"]}
        assert ids == {"juice-shop", "blocked"}

    def test_list_authorized_targets(self, client):
        r = client.get("/targets/authorized")
        assert r.status_code == 200
        ids = {t["id"] for t in r.json()["targets"]}
        assert ids == {"juice-shop"}  # 'blocked' excluded


class TestSessions:
    def test_list_sessions_empty(self, client):
        r = client.get("/sessions")
        assert r.status_code == 200
        assert r.json()["sessions"] == []

    def test_get_unknown_session_404(self, client):
        r = client.get("/sessions/no-such-session")
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()


class TestFindings:
    def test_findings_empty(self, client):
        r = client.get("/findings")
        assert r.status_code == 200
        assert r.json()["findings"] == []

    def test_findings_with_status_filter(self, client):
        r = client.get("/findings", params={"status": "VERIFIED"})
        assert r.status_code == 200
        assert r.json()["findings"] == []


class TestMemorySearch:
    def test_search_returns_results_list(self, client):
        r = client.get("/memory/search", params={"query": "anything"})
        assert r.status_code == 200
        assert "results" in r.json()
        assert isinstance(r.json()["results"], list)


class TestToolsAndModels:
    def test_tools_listed(self, client):
        r = client.get("/tools")
        assert r.status_code == 200
        tools = r.json()["tools"]
        # ToolRegistry.to_dict() returns a name -> definition mapping.
        assert isinstance(tools, dict)
        assert tools  # registry is populated from tools.yaml

    def test_models_routes(self, client):
        r = client.get("/models")
        assert r.status_code == 200
        assert isinstance(r.json()["routes"], dict)


class TestCreateApp:
    def test_returns_fastapi_app(self, tmp_path):
        app = create_app()
        assert app is not None
        assert app.title == "Cyber AI Orchestrator API"
