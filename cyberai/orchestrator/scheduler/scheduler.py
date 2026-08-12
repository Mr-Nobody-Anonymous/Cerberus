"""
Task Scheduler for the Cyber AI Orchestrator.

Manages async task scheduling, prioritization, and lifecycle.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Schedules and manages asynchronous tasks for the orchestrator."""

    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._results: Dict[str, Dict[str, Any]] = {}

    async def submit(
        self,
        agent_name: str,
        task: Dict[str, Any],
        priority: int = 5,
    ) -> str:
        """Submit a task for execution.

        Args:
            agent_name: Name of the agent to handle this task
            task: Task specification
            priority: Priority level (1=highest, 10=lowest)

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        await self._queue.put((priority, task_id, agent_name, task))
        logger.info(f"Submitted task {task_id} to agent '{agent_name}' (priority {priority})")
        return task_id

    async def get_result(self, task_id: str, timeout: float = 300) -> Optional[Dict[str, Any]]:
        """Wait for and retrieve a task result.

        Args:
            task_id: The task ID
            timeout: Maximum seconds to wait

        Returns:
            Result dict or None if timeout
        """
        deadline = datetime.now(timezone.utc).timestamp() + timeout
        while datetime.now(timezone.utc).timestamp() < deadline:
            if task_id in self._results:
                return self._results.pop(task_id)
            await asyncio.sleep(0.5)
        return None

    def store_result(self, task_id: str, result: Dict[str, Any]) -> None:
        """Store a task result."""
        self._results[task_id] = result

    async def cancel(self, task_id: str) -> bool:
        """Cancel a running task.

        Returns:
            True if task was cancelled, False if not found
        """
        task = self._tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    def list_pending(self) -> int:
        """Return count of pending tasks."""
        return self._queue.qsize()

    def list_active(self) -> int:
        """Return count of active tasks."""
        return len([t for t in self._tasks.values() if not t.done()])
