"""
Structured JSONL logger for the Cyber AI platform.

Provides structured logging to per-subject log directories:
- logs/tasks/
- logs/models/
- logs/agents/
- logs/evolution/

Log entries include: timestamp, task ID, agent, model, tool, action,
result, latency, and verification state. Never logs secrets.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class StructuredLogger:
    """Writes structured JSONL log entries to subject-specific directories."""

    def __init__(self, logs_root: Optional[Path] = None):
        self.logs_root = logs_root or Path(__file__).parent.parent.parent / "logs"
        for sub in ("tasks", "models", "agents", "evolution"):
            (self.logs_root / sub).mkdir(parents=True, exist_ok=True)

    def _write(self, directory: str, entry: Dict[str, Any]) -> None:
        """Write a JSON line to a log file."""
        try:
            path = self.logs_root / directory / f"{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
            entry["timestamp"] = entry.get("timestamp") or datetime.now(timezone.utc).isoformat()
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write structured log: {e}")

    # --- Task logs --------------------------------------------------------
    def log_task(
        self,
        task_id: str,
        action: str,
        status: str,
        agent: str = "",
        model: str = "",
        tool: str = "",
        result: Any = None,
        latency: float = 0.0,
        verification: str = "",
        **extra: Any,
    ) -> None:
        """Log a task-level event."""
        entry = {
            "event": "task",
            "task_id": task_id,
            "action": action,
            "status": status,
            "agent": agent,
            "model": model,
            "tool": tool,
            "result": result,
            "latency": latency,
            "verification": verification,
            **extra,
        }
        self._write("tasks", entry)

    # --- Model logs -------------------------------------------------------
    def log_model_call(
        self,
        model: str,
        role: str,
        success: bool,
        latency: float = 0.0,
        token_usage: int = 0,
        task_id: str = "",
        **extra: Any,
    ) -> None:
        """Log a model call."""
        entry = {
            "event": "model_call",
            "model": model,
            "role": role,
            "success": success,
            "latency": latency,
            "token_usage": token_usage,
            "task_id": task_id,
            **extra,
        }
        self._write("models", entry)

    # --- Agent logs -------------------------------------------------------
    def log_agent(
        self,
        agent: str,
        capability: str,
        status: str,
        task_id: str = "",
        model: str = "",
        tool: str = "",
        latency: float = 0.0,
        **extra: Any,
    ) -> None:
        """Log an agent execution."""
        entry = {
            "event": "agent",
            "agent": agent,
            "capability": capability,
            "status": status,
            "task_id": task_id,
            "model": model,
            "tool": tool,
            "latency": latency,
            **extra,
        }
        self._write("agents", entry)

    # --- Evolution logs ---------------------------------------------------
    def log_evolution(
        self,
        event: str,
        strategy_id: str = "",
        generation: int = 0,
        fitness: float = 0.0,
        status: str = "",
        task_type: str = "",
        **extra: Any,
    ) -> None:
        """Log an evolution event."""
        entry = {
            "event": event,
            "strategy_id": strategy_id,
            "generation": generation,
            "fitness": fitness,
            "status": status,
            "task_type": task_type,
            **extra,
        }
        self._write("evolution", entry)