"""CERBERUS security primitives.

This package centralises the safety-critical machinery that Phase C adapters
and the self-improvement pipeline depend on:

* ``sandbox`` — subprocess sandboxing: argument-list-only command construction
  (never ``shell=True``), wall-clock timeouts, memory ceilings, default-deny
  network policy, and explicit command-injection rejection.
* ``exceptions`` — the security exception hierarchy.
* ``policy_runner`` — the policy-engine gate that MUST run in front of every
  adapter ``execute()`` (no bypass path) and records every action to the
  evidence log, even on failure.

Nothing in ``cyberai`` may reach a subprocess, HTTP call, or MCP tool
invocation without passing through the policy engine first. The
``SandboxedAdapter`` base class (``orchestrator/adapters/base.py``) enforces
this for all security-tool adapters.
"""

from .exceptions import (
    CommandInjectionError,
    PolicyDeniedError,
    ResourceLimitError,
    SecurityError,
)

__all__ = [
    "SecurityError",
    "CommandInjectionError",
    "ResourceLimitError",
    "PolicyDeniedError",
]
