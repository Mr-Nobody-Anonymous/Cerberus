"""Regression tests for the UI API contract fixes (BUG-1..4).

Covers:
  - POST /api/command accepts BOTH {"message": ...} and {"command": ...} (BUG-1)
  - POST /api/tasks/stop always returns 200 (BUG-2)
  - GET /api/context exposes the flat KPI fields the SPA reads (BUG-3)
  - GET /api/scorecard exposes the flat fields the SPA reads (BUG-4)

Run with ``python -m pytest tests/test_ui_api.py -v`` from the repository root.
"""

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
httpx = pytest.importorskip("httpx", reason="httpx not installed for TestClient")

from fastapi.testclient import TestClient  # noqa: E402

from cyberai.ui.server import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    # TestClient runs the ASGI app in-process; no server restart needed.
    return TestClient(app)


# ---------------------------------------------------------------------------
# BUG-1: operator console contract
# ---------------------------------------------------------------------------
class TestCommandEndpoint:
    def test_command_key_accepted(self, client):
        """The SPA sends {"command": ...} — must NOT 400 (was the live bug)."""
        r = client.post("/api/command", json={"command": "help"})
        assert r.status_code == 200, r.text
        body = r.json()
        # The console interpreter returns its reply under "reply".
        assert "reply" in body and body["reply"]

    def test_message_key_still_accepted(self, client):
        """Documented contract {"message": ...} stays primary (backward-compat)."""
        r = client.post("/api/command", json={"message": "help"})
        assert r.status_code == 200, r.text
        assert "reply" in r.json()

    def test_empty_body_rejected(self, client):
        """Empty payload still 400s — the dual-key fix must not weaken validation."""
        r = client.post("/api/command", json={})
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# BUG-2: STOP button endpoint
# ---------------------------------------------------------------------------
class TestStopEndpoint:
    def test_stop_no_active_task(self, client):
        """No orchestrator running → 200 {"status": "no_active_task"}, never an error."""
        r = client.post("/api/tasks/stop")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "no_active_task"

    def test_stop_is_idempotent(self, client):
        r1 = client.post("/api/tasks/stop")
        r2 = client.post("/api/tasks/stop")
        assert r1.status_code == 200 and r2.status_code == 200


# ---------------------------------------------------------------------------
# BUG-3: workspace KPI flat fields
# ---------------------------------------------------------------------------
class TestContextFlatFields:
    @pytest.mark.parametrize("field", [
        "total_sessions", "total_findings", "total_memories",
        "total_tools", "total_models", "total_capabilities",
        "capability_routing", "agent_performance",
    ])
    def test_flat_kpi_present(self, client, field):
        r = client.get("/api/context")
        assert r.status_code == 200, r.text
        body = r.json()
        assert field in body, f"/api/context missing flat field '{field}'"
        assert body[field] is not None, f"flat field '{field}' is None"

    def test_nested_fields_retained(self, client):
        """Additive change: the nested structure must remain for other consumers."""
        r = client.get("/api/context")
        body = r.json()
        for nested in ("sessions", "capabilities", "performance"):
            assert nested in body, f"nested field '{nested}' was dropped (must be additive)"


# ---------------------------------------------------------------------------
# BUG-4: scorecard flat fields
# ---------------------------------------------------------------------------
class TestScorecardFlatFields:
    @pytest.mark.parametrize("field", [
        "total_sessions", "total_findings", "verified_findings",
        "total_tool_calls", "success_rate", "uptime",
    ])
    def test_flat_field_present(self, client, field):
        r = client.get("/api/scorecard")
        assert r.status_code == 200, r.text
        body = r.json()
        assert field in body, f"/api/scorecard missing flat field '{field}'"
        assert body[field] is not None, f"flat field '{field}' is None"

    def test_uptime_positive(self, client):
        r = client.get("/api/scorecard")
        assert r.json()["uptime"] >= 0

    def test_nested_fields_retained(self, client):
        r = client.get("/api/scorecard")
        body = r.json()
        for nested in ("sessions", "findings", "targets", "tools"):
            assert nested in body, f"nested field '{nested}' was dropped (must be additive)"


# ---------------------------------------------------------------------------
# BUG-2 (underlying mechanism): cooperative cancellation
# ---------------------------------------------------------------------------
class TestCooperativeCancellation:
    def test_orchestrator_stop_flag(self):
        """CyberAIOrchestrator.stop() sets the flag; run() resets it."""
        from cyberai import CyberAIOrchestrator
        orch = CyberAIOrchestrator(simulate=True, local_only=True)
        try:
            assert orch.stop_requested is False
            orch.stop()
            assert orch.stop_requested is True
        finally:
            orch.close()

    def test_pipeline_cancels_between_steps(self):
        """AgentPipeline with should_cancel→True returns cancelled result
        without executing any step."""
        import asyncio
        from cyberai.collaboration.pipeline import AgentPipeline

        pipeline = AgentPipeline()
        pipeline.add_step(agent_name="researcher", capability="research",
                           output_key="research")
        pipeline.add_step(agent_name="recon", capability="recon",
                           output_key="recon")
        pipeline.should_cancel = lambda: True

        executed: list = []

        async def executor(agent_name, context):
            executed.append(agent_name)
            return {"agent": agent_name}

        result = asyncio.run(pipeline.run(executor))
        assert result.get("cancelled") is True
        assert executed == [], "no step should execute when cancelled up front"
        statuses = [s["status"] for s in result["steps"]]
        assert all(s == "cancelled" for s in statuses)

    def test_pipeline_runs_without_cancel_probe(self):
        """should_cancel stays Optional — pipelines without it run normally."""
        import asyncio
        from cyberai.collaboration.pipeline import AgentPipeline

        pipeline = AgentPipeline()  # no should_cancel set
        pipeline.add_step(agent_name="researcher", capability="research",
                           output_key="research")

        async def executor(agent_name, context):
            return {"agent": agent_name, "ok": True}

        result = asyncio.run(pipeline.run(executor))
        assert result.get("cancelled") is not True
        assert result["steps"][0]["status"] == "completed"
