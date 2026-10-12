"""Tests for the task queue module."""

from __future__ import annotations

import asyncio

import pytest

from aetheros_automation.core.task_queue import TaskQueue
from aetheros_automation.models.models import Task, TaskStatus


class TestTaskQueue:
    def test_enqueue_sets_queued_status(self):
        q = TaskQueue()
        task = Task(id="q1", name="job")
        q.enqueue(task)
        assert task.status == TaskStatus.QUEUED
        assert q.size() == 1

    def test_enqueue_with_delay_is_scheduled(self):
        q = TaskQueue()
        task = Task(id="q1", name="job")
        q.enqueue(task, delay=10)
        assert task.id in q._scheduled
        assert q.size() == 0

    def test_priority_ordering(self):
        q = TaskQueue()
        low = Task(id="low", name="low")
        high = Task(id="high", name="high")
        q.enqueue(low, priority=1)
        q.enqueue(high, priority=10)
        nxt = q._next_ready()
        assert nxt.task.id == "high"

    @pytest.mark.asyncio
    async def test_run_once_executes_handler(self):
        q = TaskQueue()
        q.set_handler(lambda task: f"done:{task.name}")
        task = Task(id="q1", name="job")
        q.enqueue(task)
        processed = await q.run_once()
        assert processed is True
        assert task.status == TaskStatus.COMPLETED
        assert task.result == "done:job"

    @pytest.mark.asyncio
    async def test_failure_retries_then_fails(self):
        q = TaskQueue(max_retries=2, retry_base_delay=0.001)
        q.set_handler(lambda task: (_ for _ in ()).throw(RuntimeError("boom")))
        task = Task(id="q2", name="bad")
        q.enqueue(task)
        for _ in range(20):
            await q.run_once()
            await asyncio.sleep(0.005)
        assert task.status == TaskStatus.FAILED
        assert q.get_stats()["failed"] == 1
        entry = q.get_task("q2")
        assert entry.attempts == 3

    @pytest.mark.asyncio
    async def test_retry_schedules_after_delay(self):
        q = TaskQueue(max_retries=1, retry_base_delay=0.001)
        q.set_handler(lambda task: (_ for _ in ()).throw(RuntimeError("boom")))
        task = Task(id="q2", name="bad")
        q.enqueue(task)
        await q.run_once()
        assert task.status == TaskStatus.PENDING
        assert task.id in q._scheduled
        assert q.get_stats()["scheduled"] == 1

    @pytest.mark.asyncio
    async def test_run_once_without_handler_fails_task(self):
        q = TaskQueue()
        task = Task(id="q1", name="job")
        q.enqueue(task)
        processed = await q.run_once()
        assert processed is True
        assert task.status == TaskStatus.FAILED

    def test_retry_moves_failed_back_to_queue(self):
        q = TaskQueue()
        task = Task(id="q1", name="job")
        q.enqueue(task)
        q._failed[task.id] = q._entries.pop(task.id)
        assert q.retry("q1") is True
        assert task.status == TaskStatus.QUEUED

    def test_retry_unknown_returns_false(self):
        q = TaskQueue()
        assert q.retry("nope") is False

    def test_stats_and_listing(self):
        q = TaskQueue()
        a = Task(id="a", name="a")
        b = Task(id="b", name="b")
        q.enqueue(a)
        q.enqueue(b, priority=5)
        stats = q.get_stats()
        assert stats["queued"] == 2
        assert stats["total"] == 2
        assert len(q.list_failed()) == 0
