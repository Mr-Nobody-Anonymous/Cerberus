"""Basic health check tests.

Run with ``python -m pytest tests/ -v`` from the repository root so the
``cyberai`` package resolves without any sys.path manipulation.
"""

def test_imports():
    """Test that core modules can be imported."""
    from cyberai.orchestrator import Orchestrator
    from cyberai.orchestrator import ToolRegistry
    from cyberai.orchestrator import PolicyEngine
    from cyberai.orchestrator import MemoryManager
    from cyberai.orchestrator import ModelRouter
    print("All core imports successful")


def test_orchestrator_init():
    """Test orchestrator initialization."""
    from cyberai.orchestrator import Orchestrator
    orch = Orchestrator()
    status = orch.get_status()
    assert status["platform"] == "Cyber AI Orchestrator"
    print(f"Orchestrator status: {status}")


def test_memory_manager():
    """Test memory manager initialization."""
    from cyberai.orchestrator import MemoryManager
    mm = MemoryManager()
    sessions = mm.list_sessions()
    assert isinstance(sessions, list)
    print(f"Memory manager initialized, {len(sessions)} sessions")


def test_policy_engine():
    """Test policy engine initialization."""
    from cyberai.orchestrator import PolicyEngine
    pe = PolicyEngine()
    targets = pe.list_targets()
    authorized = pe.list_authorized_targets()
    print(f"Policy engine: {len(targets)} targets, {len(authorized)} authorized")


def test_tool_registry():
    """Test tool registry initialization."""
    from cyberai.orchestrator import ToolRegistry
    tr = ToolRegistry()
    tools = tr.list_tools()
    assert len(tools) > 0
    print(f"Tool registry loaded {len(tools)} tools")


if __name__ == "__main__":
    test_imports()
    test_orchestrator_init()
    test_memory_manager()
    test_policy_engine()
    test_tool_registry()
    print("\nAll tests passed!")