"""
Capability System for the Cyber AI platform.

The orchestrator reasons about capabilities rather than repository names.
For example: "I need reconnaissance" instead of "Use Strix".
"""

from .registry import CapabilityRegistry, CapabilityProvider

__all__ = ["CapabilityRegistry", "CapabilityProvider"]