"""Tests for the 12 real (SandboxedAdapter) adapters.

Covers the contract every real adapter must satisfy:

1. Inherits SandboxedAdapter (execute() is the non-bypassable policy
   gate — subclasses implement _do_execute()).
2. health_check() returns a valid status dict.
3. Policy gate denies unauthorized targets (fails closed) and records
   evidence even on denial.
4. Authorized execution records evidence and returns structured
   metadata.
5. Missing target host is rejected.
"""

import importlib
from unittest.mock import MagicMock

import pytest

from cyberai.orchestrator.adapters.base import SandboxedAdapter

# (module, name, kind) — kind drives how the authorized-path test mocks
# the tool: 'http' adapters are probed via _port_listening, 'cli'
# adapters via run_subprocess, 'library' adapters import in-process.
REAL_ADAPTERS = [
    ("pentagi", "pentagi", "http"),
    ("strix", "strix", "cli"),
    ("darkmoon", "darkmoon", "http"),
    ("hexstrike", "hexstrike", "http"),
    ("mcpstrike", "mcpstrike", "http"),
    ("cai", "cai", "library"),
    ("pentestgpt", "pentestgpt", "cli"),
    ("pentestagent", "pentestagent", "cli"),
    ("cyberstrikeai", "cyberstrikeai", "http"),
    ("autopentest", "autopentest", "cli"),
    ("penclaw", "penclaw", "cli"),
    ("luan1aoagent", "luan1aoagent", "cli"),
    ("aracne", "aracne", "cli"),
]

AUTHORIZED_TARGET = {
    "id": "juice-shop",
    "host": "127.0.0.1",
    "environment": "authorized_lab",
    "allowed": True,
    "allowed_actions": ["recon", "scan", "verification"],
}


def _make_adapter(module_name):
    mod = importlib.import_module(f"adapters.{module_name}")
    adapter = mod.Adapter()
    assert isinstance(adapter, SandboxedAdapter), (
        f"adapters.{module_name}.Adapter must inherit SandboxedAdapter"
    )
    return adapter


def _wire(adapter, policy):
    adapter.policy_engine = policy
    evidence = MagicMock()
    evidence.store_evidence.return_value = "ev-id"
    adapter.evidence_manager = evidence
    adapter.session_id = "sess-test"
    return evidence


@pytest.fixture
def authorized_policy():
    pol = MagicMock()
    pol.is_authorized.return_value = True
    pol.check_action_allowed.return_value = True
    return pol


@pytest.fixture
def denied_policy():
    pol = MagicMock()
    pol.is_authorized.return_value = False
    pol.check_action_allowed.return_value = False
    return pol


# --------------------------------------------------------------- structure
@pytest.mark.parametrize("module_name,adapter_name,kind", REAL_ADAPTERS)
def test_adapter_is_sandboxed(module_name, adapter_name, kind):
    adapter = _make_adapter(module_name)
    assert adapter.name == adapter_name
    # The policy gate must live in the base class, not the subclass:
    # execute() must NOT be overridden by the real adapter.
    from cyberai.orchestrator.adapters.base import SandboxedAdapter as Base

    assert "execute" not in adapter.__class__.__dict__ or not hasattr(
        adapter.__class__.__dict__.get("execute"), "__code__"
    ) or adapter.__class__.__dict__["execute"].__qualname__.startswith(
        "SandboxedAdapter"
    )


@pytest.mark.parametrize("module_name,adapter_name,kind", REAL_ADAPTERS)
@pytest.mark.asyncio
async def test_adapter_health_check(module_name, adapter_name, kind):
    adapter = _make_adapter(module_name)
    health = await adapter.health_check()
    assert health["status"] in ("AVAILABLE", "WARN", "ERROR", "UNAVAILABLE")
    assert isinstance(health["message"], str) and health["message"]
    assert "details" in health


# ------------------------------------------------------------ policy gate
@pytest.mark.parametrize("module_name,adapter_name,kind", REAL_ADAPTERS)
@pytest.mark.asyncio
async def test_adapter_denies_unauthorized_target(
    module_name, adapter_name, kind, denied_policy
):
    adapter = _make_adapter(module_name)
    evidence = _wire(adapter, denied_policy)

    result = await adapter.execute(
        {"action": "scan", "target": {"id": "evil.example.com"}}
    )

    assert result.success is False
    assert "Policy denied" in result.error
    assert result.metadata["denied"] is True
    evidence.store_evidence.assert_called_once()
    call_kwargs = evidence.store_evidence.call_args.kwargs
    assert call_kwargs["content"]["success"] is False


# ------------------------------------------------------- authorized path
def _fake_exec_result(success=True):
    """Build an object shaped like SandboxResult for CLI mocking."""
    r = MagicMock()
    r.success = success
    r.stdout = "sample output"
    r.stderr = ""
    r.error = None if success else "exit 1"
    r.returncode = 0 if success else 1
    r.timed_out = False
    return r


@pytest.mark.parametrize("module_name,adapter_name,kind", REAL_ADAPTERS)
@pytest.mark.asyncio
async def test_adapter_authorized_execution_records_evidence(
    module_name, adapter_name, kind, authorized_policy, monkeypatch
):
    adapter = _make_adapter(module_name)
    evidence = _wire(adapter, authorized_policy)

    if kind == "http":
        # Simulate the service being up: port probe returns True and the
        # HTTP POST returns 200.
        monkeypatch.setattr(
            adapter.__class__, "_port_listening",
            classmethod(lambda cls, port: True),
        )

        def fake_post(self, url, payload):
            return 200, '{"ok": true}'

        monkeypatch.setattr(adapter.__class__, "_http_post_json", fake_post)
    elif kind == "cli":
        # Simulate a successful sandboxed subprocess run. For Node-based
        # tools whose dist bundle is not built (health=WARN), also fake
        # the health check so the execution path is exercised.
        fake = _fake_exec_result(True)

        async def fake_to_thread(func, *args, **kwargs):
            return fake

        import adapters

        mod = importlib.import_module(f"adapters.{module_name}")
        monkeypatch.setattr(mod, "run_subprocess", lambda *a, **k: fake)
        monkeypatch.setattr(
            mod.asyncio, "to_thread", fake_to_thread
        )

        async def fake_health(self):
            return {"status": "AVAILABLE", "message": "faked for test",
                    "details": {}}

        monkeypatch.setattr(mod.Adapter, "health_check", fake_health)
    else:  # library (cai)
        mod = importlib.import_module(f"adapters.{module_name}")

        class _FakeAgent:
            def run(self, prompt):
                return "cai sample output"

        class _FakeCai:
            agents = {"default": _FakeAgent()}

        # cai adapter stores the module on health_check; make it succeed
        monkeypatch.setattr(
            mod.Adapter, "_import_cai", lambda self: _FakeCai()
        )

    result = await adapter.execute(
        {
            "action": "scan",
            "target": dict(AUTHORIZED_TARGET),
            "parameters": {"timeout": 30},
        }
    )

    # Evidence is recorded on the success path too.
    evidence.store_evidence.assert_called_once()
    rec = evidence.store_evidence.call_args.kwargs
    assert rec["source"] == adapter_name
    assert rec["session_id"] == "sess-test"

    assert result.metadata["tool"] == adapter_name
    assert result.metadata["target_host"] == "127.0.0.1"

    if kind == "cli":
        assert isinstance(result.metadata["command"], list)
        assert all(isinstance(c, str) for c in result.metadata["command"])
        assert result.metadata["returncode"] == 0
    if kind == "http":
        assert result.metadata["http_status"] == 200


@pytest.mark.parametrize("module_name,adapter_name,kind", REAL_ADAPTERS)
@pytest.mark.asyncio
async def test_adapter_requires_target_host(
    module_name, adapter_name, kind, authorized_policy
):
    """A target dict without host/id is rejected before any tool runs."""
    adapter = _make_adapter(module_name)
    _wire(adapter, authorized_policy)

    result = await adapter.execute(
        {"action": "scan", "target": {"environment": "authorized_lab"}}
    )

    assert result.success is False
    # Either the policy gate denies the empty target id, or the adapter
    # itself rejects the missing host — both are safe outcomes.
    assert result.error is not None
    assert (
        "Policy denied" in result.error
        or "No target host" in result.error
        or "host" in result.error.lower()
    )
