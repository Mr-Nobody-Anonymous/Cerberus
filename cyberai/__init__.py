"""
Cyber AI — A local, integrated, self-improving AI security research orchestrator.

The platform presents itself as ONE intelligent Cyber AI to the user while
internally coordinating multiple specialized agents, tools, models, memory
systems, evaluators, and an evolution engine.

Usage:
    from cyberai import CyberAIOrchestrator
    ai = CyberAIOrchestrator()
    result = await ai.run("Analyze my authorized lab target")
"""

__version__ = "2.0.0"
__platform_name__ = "Cyber AI"

__all__ = [
    "CyberAIOrchestrator",
    "__version__",
    "__platform_name__",
]