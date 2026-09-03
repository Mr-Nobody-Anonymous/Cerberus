import asyncio
from unittest.mock import MagicMock
import pytest
from cyberai.orchestrator.adapters.base import SandboxedAdapter, AdapterResult
from cyberai.security.policy_runner import PolicyDeniedError

@pytest.fixture
def drakben_adapter():
    import importlib
    mod = importlib.import_module('adapters.drakben')
    adapter = mod.Adapter()
    assert isinstance(adapter, SandboxedAdapter)
    return adapter

@pytest.fixture
def authorized_policy():
    from unittest.mock import MagicMock
    pol = MagicMock()
    pol.is_authorized.return_value = True
    pol.check_action_allowed.return_value = True
    return pol

@pytest.fixture
def denied_policy():
    from unittest.mock import MagicMock
    pol = MagicMock()
    pol.is_authorized.return_value = False
    pol.check_action_allowed.return_value = False
    return pol

def test_drakben_is_sandboxed_adapter(drakben_adapter):
    assert isinstance(drakben_adapter, SandboxedAdapter)
    assert drakben_adapter.name == 'drakben'

@pytest.mark.asyncio
async def test_drakben_health_check_real_probe(drakben_adapter):
    health = await drakben_adapter.health_check()
    assert health['status'] in ('AVAILABLE', 'WARN', 'ERROR')
    assert 'details' in health

@pytest.mark.asyncio
async def test_drakben_denied_for_unauthorized_target(drakben_adapter, denied_policy):
    drakben_adapter.policy_engine = denied_policy
    evidence = MagicMock()
    evidence.store_evidence.return_value = 'ev-denied'
    drakben_adapter.evidence_manager = evidence
    drakben_adapter.session_id = 'sess-test'

    result = await drakben_adapter.execute({
        'action': 'scan',
        'target': {'id': 'evil.example.com'},
    })

    assert result.success is False
    assert 'Policy denied' in result.error
    evidence.store_evidence.assert_called_once()
    call_kwargs = evidence.store_evidence.call_args.kwargs
    assert call_kwargs['content']['success'] is False

@pytest.mark.asyncio
async def test_drakben_executes_for_authorized_target(drakben_adapter, authorized_policy):
    drakben_adapter.policy_engine = authorized_policy
    evidence = MagicMock()
    evidence.store_evidence.return_value = 'ev-ok'
    drakben_adapter.evidence_manager = evidence
    drakben_adapter.session_id = 'sess-test'

    result = await drakben_adapter.execute({
        'action': 'recon',
        'target': {
            'id': 'juice-shop',
            'host': '127.0.0.1',
            'environment': 'authorized_lab',
            'allowed': True,
            'allowed_actions': ['recon', 'scan', 'verification'],
        },
        'parameters': {'timeout': 30},
    })

    evidence.store_evidence.assert_called_once()
    rec = evidence.store_evidence.call_args.kwargs
    assert rec['source'] == 'drakben'
    assert rec['session_id'] == 'sess-test'
    assert rec['content']['success'] is True

    assert result.metadata['tool'] == 'drakben'
    assert result.metadata['target_host'] == '127.0.0.1'
    assert 'command' in result.metadata
    assert isinstance(result.metadata['command'], list)
    assert all(isinstance(c, str) for c in result.metadata['command'])

@pytest.mark.asyncio
async def test_drakben_requires_target_host(drakben_adapter, authorized_policy):
    drakben_adapter.policy_engine = authorized_policy
    drakben_adapter.evidence_manager = MagicMock()
    drakben_adapter.session_id = 'sess-test'

    result = await drakben_adapter.execute({
        'action': 'scan',
        'target': {'environment': 'authorized_lab'},  # no id/host
    })
    # Policy gate denies based on missing target ID first
    assert result.success is False
    assert 'Policy denied' in result.error
