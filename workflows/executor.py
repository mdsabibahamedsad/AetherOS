"""Background executor — daemon process for persistent workflow execution."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from threading import Thread
from typing import Any, Optional

from workflows.store import WorkflowStore
from workflows.engine import WorkflowEngine
from workflows.models import WorkflowConfig, WorkflowStatus, ExecutionStatus

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """Manages background execution of workflows, including queued and scheduled runs."""

    def __init__(self, store: Optional[WorkflowStore] = None, max_concurrent: int = 5):
        self.store = store or WorkflowStore()
        self.engine = WorkflowEngine(store)
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running: dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._worker_task: Optional[asyncio.Task] = None
        self._running_flag = False

    async def enqueue(self, workflow_id: str, context: dict = None) -> None:
        await self._queue.put((workflow_id, context or {}))
        logger.info("Enqueued workflow %s", workflow_id)

    async def _process_queue(self) -> None:
        while self._running_flag:
            try:
                workflow_id, context = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0)
                async with self._semaphore:
                    task = asyncio.create_task(
                        self.engine.run_async(workflow_id, context))
                    self._running[workflow_id] = task
                    try:
                        await task
                    except asyncio.CancelledError:
                        logger.info("Workflow %s cancelled", workflow_id)
                    finally:
                        self._running.pop(workflow_id, None)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("Queue worker error: %s", e)

    async def start(self) -> None:
        if self._running_flag:
            return
        self._running_flag = True
        self._worker_task = asyncio.create_task(self._process_queue())
        logger.info("Workflow executor started")

    async def stop(self) -> None:
        self._running_flag = False
        for wf_id, task in list(self._running.items()):
            task.cancel()
        if self._worker_task:
            self._worker_task.cancel()
        logger.info("Workflow executor stopped")

    def is_running(self) -> bool:
        return self._running_flag


class ExecutorDaemon:
    """Long-running daemon for background workflow execution."""

    def __init__(self, poll_interval: float = 5.0):
        self.executor = WorkflowExecutor()
        self.poll_interval = poll_interval
        self._daemon_task: Optional[asyncio.Task] = None
        self._running_flag = False

    async def _daemon_loop(self) -> None:
        await self.executor.start()
        while self._running_flag:
            try:
                pending = self.executor.store.list_executions(
                    status=ExecutionStatus.PENDING)
                for rec in pending:
                    await self.executor.enqueue(rec.workflow_id)
                running = self.executor.store.list_executions(
                    status=ExecutionStatus.RUNNING)
                for rec in running:
                    if rec.id not in self.executor._running:
                        await self.executor.enqueue(rec.workflow_id)
            except Exception as e:
                logger.error("Daemon loop error: %s", e)
            await asyncio.sleep(self.poll_interval)

    async def start(self) -> None:
        if self._running_flag:
            return
        self._running_flag = True
        self._daemon_task = asyncio.create_task(self._daemon_loop())
        logger.info("Executor daemon started")

    async def stop(self) -> None:
        self._running_flag = False
        if self._daemon_task:
            self._daemon_task.cancel()
        await self.executor.stop()
        logger.info("Executor daemon stopped")
