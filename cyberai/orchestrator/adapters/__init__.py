"""
Adapter framework for the Cyber AI Orchestrator.

This package provides the standard adapter interface and registry
for integrating external security tools into the platform.
"""

from .base import AdapterCapability, AdapterResult, SecurityToolAdapter
from .adapter_manager import AdapterManager, KNOWN_ADAPTERS

__all__ = [
    "AdapterCapability",
    "AdapterResult",
    "SecurityToolAdapter",
    "AdapterManager",
    "KNOWN_ADAPTERS",
]
