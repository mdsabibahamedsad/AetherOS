"""Tests for the task monitoring module."""

from __future__ import annotations

from aetheros_automation.monitoring import TaskMonitor
from aetheros_automation.models.models import TaskStatus


class TestTaskMonitor:
    def test_tracks_created_and_completed(self):
        monitor = TaskMonitor()
        monitor.on_task_created({"task_id": "t1", "name": "job"})
        monitor.on_task_started({"task_id": "t1"})
        monitor.on_task_completed({"task_id": "t1"})
        task = monitor.get_task("t1")
        assert task["status"] == TaskStatus.COMPLETED.value
        assert task["progress"] == 100.0

    def test_summary_counts_by_status(self):
        monitor = TaskMonitor()
        monitor.on_task_created({"task_id": "t1"})
        monitor.on_task_started({"task_id": "t1"})
        monitor.on_task_completed({"task_id": "t1"})
        monitor.on_task_created({"task_id": "t2"})
        monitor.on_task_started({"task_id": "t2"})
        summary = monitor.get_summary()
        assert summary["total_tasks"] == 2
        assert summary["completed_tasks"] == 1
        assert summary["running_tasks"] == 1
        assert summary["by_status"][TaskStatus.RUNNING.value] == 1

    def test_failed_task_tracked(self):
        monitor = TaskMonitor()
        monitor.on_task_created({"task_id": "t1"})
        monitor.on_task_failed({"task_id": "t1", "error": "boom"})
        task = monitor.get_task("t1")
        assert task["status"] == TaskStatus.FAILED.value
        assert monitor.get_summary()["failed_tasks"] == 1

    def test_track_direct_with_progress(self):
        monitor = TaskMonitor()
        monitor.track("t1", name="job", status="running", progress=50)
        monitor.update_progress("t1", 75)
        assert monitor.get_task("t1")["progress"] == 75

    def test_activity_history(self):
        monitor = TaskMonitor()
        monitor.on_task_created({"task_id": "t1"})
        monitor.on_task_completed({"task_id": "t1"})
        activity = monitor.get_activity()
        assert len(activity) == 2
        assert activity[0]["event"] == "completed"

    def test_filters_by_status(self):
        monitor = TaskMonitor()
        monitor.on_task_created({"task_id": "t1"})
        monitor.on_task_started({"task_id": "t1"})
        monitor.on_task_created({"task_id": "t2"})
        running = monitor.get_tasks(status=TaskStatus.RUNNING.value)
        assert [t["task_id"] for t in running] == ["t1"]

    def test_update_listener(self):
        monitor = TaskMonitor()
        events = []
        monitor.on_update(lambda event, data: events.append((event, data["task_id"])))
        monitor.on_task_started({"task_id": "t1"})
        assert ("started", "t1") in events

    def test_agent_started_tracking(self):
        monitor = TaskMonitor()
        monitor.on_agent_started({"agent_id": "ag-1", "task_id": "t1", "role": "developer"})
        task = monitor.get_task("t1")
        assert task["agent_id"] == "ag-1"
