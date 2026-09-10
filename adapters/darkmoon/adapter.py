"""Compatibility shim.

The real adapter implementation (a SandboxedAdapter with a real
execution path) lives in this package's __init__.py. This module
re-exports it for any legacy imports of adapters.darkmoon.adapter.
"""

from . import Adapter  # noqa: F401 -- re-export

__all__ = ["Adapter"]
