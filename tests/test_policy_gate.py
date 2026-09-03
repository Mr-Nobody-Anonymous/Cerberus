"""Phase C/D — policy gate + SandboxedAdapter tests.

Proves the hard safety contract:
- Every adapter execute() passes through the policy engine first.
- Unauthorized targets are denied BEFORE any real work, with a log entry.
- The action is recorded to the evidence log even on denial/failure.
- There is no path around the gate.
"""

import asyncio
from unittest.mock import MagicMock

import pytest

from cyberai.orchestrator.adapters.base import (
    AdapterResult,
    SandboxedAdapter,
)
from cyberai.security.policy_runner import PolicyDeniedError, authorize
from cyberai.security.sandbox import CommandInjectionError, validate_args


class _DummyPolicy:
    """A policy engine stub with one authorized target."""

    def __init__(self, authorized_ids, allowed_actions=None):
        self._ids = set(authorized_ids)
        self._actions = set(allowed_actions or ["scan", "recon", "analysis",
                                                 "exploitation", "verification"])

    def is_authorized(self, target_id):
        return target_id in self._ids

    def check_action_allowed(self, target_id, action):
        return action in self._actions


class _RealAdapter(SandboxedAdapter):
    """A real (non-stub) adapter that records what it was asked to do."""

    name = "test-real-adapter"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.did_execute = False
        self.last_task = None

    async def health_check(self):
        return {"status": "AVAILABLE"}

    async def capabilities(self):
        return []

    async def _do_execute(self, task):
        self.did_execute = True
        self.last_task = task
        return AdapterResult(success=True, output="done",
                             metadata={"tool": self.name})

    async def collect_results(self):
        return AdapterResult(success=True)

    async def shutdown(self):
        pass


def test_authorize_permits_authorized_target():
    pol = _DummyPolicy(["lab-web-01"])
    authorize(pol, {"id": "lab-web-01"}, "scan")  # should not raise


def test_authorize_denies_unknown_target():
    pol = _DummyPolicy(["lab-web-01"])
    with pytest.raises(PolicyDeniedError, match="not authorized"):
        authorize(pol, {"id": "evil.com"}, "scan")


def test_authorize_denies_disallowed_action():
    pol = _DummyPolicy(["lab-web-01"], allowed_actions=["recon"])
    with pytest.raises(PolicyDeniedError, match="not in allowed_actions"):
        authorize(pol, {"id": "lab-web-01"}, "exploitation")


def test_authorize_denies_missing_target_id():
    pol = _DummyPolicy(["lab-web-01"])
    with pytest.raises(PolicyDeniedError, match="no target id"):
        authorize(pol, {}, "scan")


def test_sandboxed_adapter_blocks_unauthorized_before_execute():
    """The gate MUST run before _do_execute. An unauthorized target must
    never reach the real work, and the denial must be recorded."""
    pol = _DummyPolicy(["lab-web-01"])
    evidence = MagicMock()
    evidence.store_evidence.return_value = "ev-123"

    adapter = _RealAdapter()
    adapter.policy_engine = pol
    adapter.evidence_manager = evidence
    adapter.session_id = "sess-1"

    result = asyncio.run(adapter.execute({
        "action": "scan",
        "target": {"id": "evil.com"},
    }))

    assert result.success is False
    assert "Policy denied" in result.error
    assert result.metadata.get("denied") is True
    # CRITICAL: the real work must NOT have run.
    assert adapter.did_execute is False
    # The denied action must still be recorded.
    evidence.store_evidence.assert_called_once()


def test_sandboxed_adapter_runs_for_authorized_target():
    pol = _DummyPolicy(["lab-web-01"])
    evidence = MagicMock()
    evidence.store_evidence.return_value = "ev-456"

    adapter = _RealAdapter()
    adapter.policy_engine = pol
    adapter.evidence_manager = evidence
    adapter.session_id = "sess-1"

    result = asyncio.run(adapter.execute({
        "action": "scan",
        "target": {"id": "lab-web-01"},
        "parameters": {"fast": True},
    }))

    assert result.success is True
    assert adapter.did_execute is True
    assert adapter.last_task["parameters"]["fast"] is True
    evidence.store_evidence.assert_called_once()


def test_validate_args_rejects_injection():
    """Command injection is rejected at the validation layer."""
    with pytest.raises(CommandInjectionError):
        validate_args(["python", "-c", "print(1); os.system('rm -rf /')"])


def test_validate_args_accepts_safe_command():
    validate_args(["python", "script.py", "--target", "127.0.0.1"])
