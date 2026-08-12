"""
Observability subsystem for the Cyber AI platform.

Provides structured JSONL logging for:
- Tasks
- Models
- Agents
- Evolution
"""

from .logger import StructuredLogger

__all__ = ["StructuredLogger"]