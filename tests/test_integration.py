"""
End-to-end integration tests for the Cyber AI Orchestrator.

These tests verify the full autonomous pipeline in simulation mode,
requiring no Docker, no Ollama, and no cloud APIs.

Run with ``python -m pytest tests/ -v`` from the repository root so the
``cyberai`` package resolves without any sys.path manipulation.

Test flow:
  USER → ORCHESTRATOR → PLAN → MEMORY RETRIEVAL → MODEL ROUTING →
  MOCK AGENT → MOCK TOOL → RESULT → VERIFY → MEMORY → EVOLUTION → REPORT
"""

import asyncio
import json
import os
from pathlib import Path

from cyberai import CyberAIOrchestrator
from cyberai import __version__
from cyberai.task import Task, TaskStatus, VerificationState
from cyberai.memory.memory_store import MemoryStore
from cyberai.capabilities.registry import CapabilityRegistry
from cyberai.evolution.engine import EvolutionEngine
from cyberai.orchestrator.adapters.adapter_manager import AdapterManager


def test_imports():
    """Test that all core modules can be imported."""
    assert __version__ == "2.0.0"
    assert CyberAIOrchestrator is not None
    assert Task is not None
    assert MemoryStore is not None
    assert CapabilityRegistry is not None
    assert EvolutionEngine is not None
    assert AdapterManager is not None


def test_stdlib_platform():
    """Verify the old import conflict is fixed."""
    import platform
    assert hasattr(platform, "system")
    assert platform.system() is not None


def test_orchestrator_init():
    """Test that the CyberAIOrchestrator can be created in simulation mode."""
    orch = CyberAIOrchestrator(simulate=True, dry_run=True)
    status = orch.get_status()
    assert status["platform"] == "Cyber AI"
    assert status["simulate"] is True
    assert "agents" in status
    assert "capabilities" in status
    orch.close()


def test_dry_run():
    """Test dry-run mode produces a plan without executing."""
    async def _run():
        orch = CyberAIOrchestrator(simulate=True, dry_run=True)
        result = await orch.run("Analyze authorized lab target")
        orch.close()
        return result

    result = asyncio.run(_run())
    assert result["status"] == "dry_run"
    assert "capabilities_identified" in result
    assert "actions" in result
    assert "models_planned" in result


def test_simulation():
    """Test full simulation mode runs the complete pipeline."""
    async def _run():
        orch = CyberAIOrchestrator(simulate=True)
        result = await orch.run("Analyze authorized lab target")
        orch.close()
        return result

    result = asyncio.run(_run())
    assert "id" in result
    assert result.get("status") == "completed"
    findings = result.get("findings", [])
    assert isinstance(findings, list)


def test_adapter_discovery():
    """Test that adapter manager discovers adapters."""
    manager = AdapterManager()
    discovered = manager.discover()
    assert isinstance(discovered, list)
    assert len(discovered) > 0


def test_adapter_health():
    """Test that adapter health checks work (return dicts, not crash)."""
    async def _run():
        manager = AdapterManager()
        results = await manager.health_check_all()
        return results

    results = asyncio.run(_run())
    assert isinstance(results, dict)
    for name, health in results.items():
        assert "status" in health
        assert health["status"] in ("OK", "WARN", "ERROR", "NOT_IMPLEMENTED")


def test_capability_registry():
    """Test that the capability registry works."""
    registry = CapabilityRegistry()
    caps = registry.list_capabilities()
    assert "reconnaissance" in caps


def test_memory_store():
    """Test that the typed memory store works."""
    store = MemoryStore()
    mem_id = store.store_simple(
        "episodic",
        "Test observation: target identified",
        confidence=0.8,
        success_rate=1.0,
        verification="VERIFIED",
    )
    assert mem_id is not None
    memories = store.retrieve_for_planning("Test observation")
    assert len(memories) > 0
    store.close()


def test_evolution_engine():
    """Test that the evolution engine can run a generation."""
    async def _run():
        engine = EvolutionEngine(simulate=True)
        result = await engine.evolve_generation(
            task_type="test",
            task_context={},
            num_strategies=3,
        )
        return result

    result = asyncio.run(_run())
    assert "results" in result
    assert len(result["results"]) > 0


def test_cli_doctor():
    """Test that the doctor health check runs without errors."""
    from cyberai.orchestrator.cli.doctor import run_health_check
    checks = list(run_health_check())
    assert len(checks) > 0
    for component, status, msg in checks:
        assert status in ("ok", "warn", "error", "info")


def test_policy_engine():
    """Test that the policy engine loads without errors."""
    from cyberai.orchestrator import PolicyEngine
    pe = PolicyEngine()
    targets = pe.list_targets()
    assert isinstance(targets, list)  # Should not crash even with no targets
    pe.close()


def test_model_router():
    """Test that the model router routes correctly."""
    from cyberai.orchestrator import ModelRouter
    mr = ModelRouter()
    route = mr.route("planning")
    assert isinstance(route, str)
    assert len(route) > 0


def test_task_state():
    """Test that the Task state object works properly."""
    task = Task(objective="Test objective")
    assert task.id is not None
    assert task.objective == "Test objective"
    assert task.status == TaskStatus.CREATED.value
    task.add_finding("Test finding", confidence=0.7, source="test")
    assert len(task.findings) == 1
    task.set_status(TaskStatus.COMPLETED)
    assert task.status == TaskStatus.COMPLETED.value
    d = task.to_dict()
    assert "id" in d
    assert "objective" in d
    assert "findings" in d


if __name__ == "__main__":
    test_imports()
    print("PASS test_imports")
    test_stdlib_platform()
    print("PASS test_stdlib_platform")
    test_orchestrator_init()
    print("PASS test_orchestrator_init")
    test_dry_run()
    print("PASS test_dry_run")
    test_simulation()
    print("PASS test_simulation")
    test_adapter_discovery()
    print("PASS test_adapter_discovery")
    test_adapter_health()
    print("PASS test_adapter_health")
    test_capability_registry()
    print("PASS test_capability_registry")
    test_memory_store()
    print("PASS test_memory_store")
    test_evolution_engine()
    print("PASS test_evolution_engine")
    test_cli_doctor()
    print("PASS test_cli_doctor")
    test_policy_engine()
    print("PASS test_policy_engine")
    test_model_router()
    print("PASS test_model_router")
    test_task_state()
    print("PASS test_task_state")
    print("\nAll integration tests passed!")
