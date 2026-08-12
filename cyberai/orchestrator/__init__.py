"""
Cyber AI Orchestrator
=====================

Local AI security-research orchestration platform.

The orchestrator is the brain of the platform. It coordinates:
- Planning agents
- Research agents
- Verification agents
- LLM routing (via LiteLLM gateway)
- Tool routing (via MCP/adapters)
- Memory and experience storage
- Policy enforcement
- Evidence collection
"""

__version__ = "0.1.0"
__platform_name__ = "Cyber AI Orchestrator"

from .orchestrator import Orchestrator
from .memory.memory_manager import MemoryManager
from .policies.policy_engine import PolicyEngine
from .routing.model_router import ModelRouter
from .tool_registry import ToolRegistry

__all__ = [
    "Orchestrator",
    "MemoryManager",
    "PolicyEngine",
    "ModelRouter",
    "ToolRegistry",
]