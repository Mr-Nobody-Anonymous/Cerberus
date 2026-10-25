"""Tests for the TaskScheduler subsystem (cyberai.orchestrator.scheduler).

Covers:
  - submit() queues tasks and returns unique IDs
  - get_result() retrieves stored results and times out to None
  - store_result() / cancel() / list_pending() / list_active()
"""

import asyncio
import contextlib
import time

import pytest

from cyberai.orchestrator.scheduler import TaskScheduler


@pytest.fixture
def scheduler():
    return TaskScheduler()


class TestSubmit:
    async def test_submit_returns_task_id(self, scheduler):
        task_id = await scheduler.submit("recon", {"action": "scan"})
        assert isinstance(task_id, str) and task_id

    async def test_submit_unique_ids(self, scheduler):
        ids = {await scheduler.submit("recon", {}) for _ in range(5)}
        assert len(ids) == 5

    async def test_submit_increases_pending(self, scheduler):
        assert scheduler.list_pending() == 0
        await scheduler.submit("recon", {})
        await scheduler.submit("analyst", {})
        assert scheduler.list_pending() == 2

    async def test_submit_priority_recorded_in_queue(self, scheduler):
        # The queue holds (priority, task_id, agent_name, task) tuples.
        await scheduler.submit("recon", {}, priority=1)
        priority, _task_id, agent, task = await scheduler._queue.get()
        assert priority == 1
        assert agent == "recon"
        assert task == {}


class TestResults:
    async def test_store_and_get_result(self, scheduler):
        task_id = await scheduler.submit("recon", {})
        scheduler.store_result(task_id, {"success": True, "output": "ok"})
        result = await scheduler.get_result(task_id, timeout=2)
        assert result == {"success": True, "output": "ok"}

    async def test_get_result_pops_result(self, scheduler):
        task_id = await scheduler.submit("recon", {})
        scheduler.store_result(task_id, {"done": True})
        first = await scheduler.get_result(task_id, timeout=2)
        assert first is not None
        # After popping, a second wait must time out (result consumed).
        second = await scheduler.get_result(task_id, timeout=0.6)
        assert second is None

    async def test_get_result_timeout_returns_none(self, scheduler):
        start = time.monotonic()
        result = await scheduler.get_result("nonexistent-id", timeout=0.6)
        elapsed = time.monotonic() - start
        assert result is None
        # The poll loop sleeps in 0.5s steps; a 0.6s budget should
        # return quickly rather than spinning forever.
        assert elapsed < 5

    async def test_get_result_immediate_when_already_stored(self, scheduler):
        scheduler.store_result("pre-stored", {"value": 42})
        result = await scheduler.get_result("pre-stored", timeout=2)
        assert result == {"value": 42}


class TestCancelAndCounts:
    async def test_cancel_unknown_task_returns_false(self, scheduler):
        assert await scheduler.cancel("no-such-task") is False

    async def test_cancel_running_task(self, scheduler):
        async def sleeper():
            await asyncio.sleep(60)

        loop_task = asyncio.ensure_future(sleeper())
        scheduler._tasks["t1"] = loop_task
        assert await scheduler.cancel("t1") is True
        # Give the loop a tick to process the cancellation.
        await asyncio.sleep(0)
        assert loop_task.cancelled() or loop_task.done()

    async def test_cancel_completed_task_returns_false(self, scheduler):
        loop_task = asyncio.ensure_future(asyncio.sleep(0))
        await loop_task
        scheduler._tasks["t2"] = loop_task
        assert await scheduler.cancel("t2") is False

    async def test_list_active_counts_only_running(self, scheduler):
        done_task = asyncio.ensure_future(asyncio.sleep(0))
        await done_task
        running_task = asyncio.ensure_future(asyncio.sleep(60))
        try:
            scheduler._tasks["done"] = done_task
            scheduler._tasks["running"] = running_task
            assert scheduler.list_active() == 1
        finally:
            running_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await running_task

    async def test_end_to_end_submit_execute_store(self, scheduler):
        """Worker drains the queue, executes, stores the result."""
        task_id = await scheduler.submit("recon", {"action": "scan"})

        async def worker():
            _priority, tid, agent, task = await scheduler._queue.get()
            await asyncio.sleep(0.05)  # simulate work
            scheduler.store_result(tid, {"agent": agent, **task})

        worker_task = asyncio.ensure_future(worker())
        result = await scheduler.get_result(task_id, timeout=5)
        await worker_task
        assert result == {"agent": "recon", "action": "scan"}
        assert scheduler.list_pending() == 0
