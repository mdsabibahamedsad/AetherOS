from __future__ import annotations

import logging
import time
from typing import Any

from aetheros_automation.models.models import Task, TaskStatus

logger = logging.getLogger(__name__)


class AutomationWebAPI:
    """HTTP-oriented wrapper over AutomationEngine.

    Every method returns a JSON-serialisable dict so callers (Flask,
    FastAPI, Starlette, …) can render it directly.
    """

    def __init__(self, engine: Any) -> None:
        self._engine = engine

    # ------------------------------------------------------------------
    # status / health
    # ------------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        status = self._engine.get_status()
        return {
            "running": status.get("running", False),
            "running_tasks": status.get("by_status", {}).get("running", 0),
            "completed": status.get("by_status", {}).get("completed", 0),
            "failed": status.get("by_status", {}).get("failed", 0),
            "uptime": time.time() - self._engine._started_at
            if getattr(self._engine, "_started_at", None)
            else 0.0,
            "total_tasks": status.get("total_tasks", 0),
            "config": status.get("config", {}),
        }

    # ------------------------------------------------------------------
    # tasks
    # ------------------------------------------------------------------

    def get_task(self, task_id: str) -> dict[str, Any]:
        task: Task | None = self._engine.get_task(task_id)
        if task is None:
            return {"error": f"Task {task_id} not found"}
        return self._task_to_dict(task)

    def list_tasks(self, status: str | None = None) -> list[dict[str, Any]]:
        status_filter = None
        if status:
            try:
                status_filter = TaskStatus(status)
            except ValueError:
                return [{"error": f"Unknown status: {status}"}]

        tasks = self._engine.list_tasks(status_filter)
        return [self._task_to_dict(t) for t in tasks]

    def create_task(
        self,
        name: str,
        description: str,
        agent: str,
        steps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        from aetheros_automation.models.models import AgentRole, TaskStep

        agent_role = AgentRole.COORDINATOR
        try:
            agent_role = AgentRole(agent)
        except ValueError:
            pass

        task_steps = [
            TaskStep(
                id=uuid4_hex(),
                name=s.get("name", ""),
                action=s.get("action", ""),
                params=s.get("params", {}),
            )
            for s in steps
        ]

        task = self._engine.create_task(
            name=name,
            description=description,
            agent_role=agent_role,
            steps=task_steps,
        )
        return self._task_to_dict(task)

    def cancel_task(self, task_id: str) -> dict[str, Any]:
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._engine.cancel_task(task_id), loop
                )
                future.result(timeout=10)
            else:
                loop.run_until_complete(self._engine.cancel_task(task_id))
        except RuntimeError:
            import asyncio as _asyncio

            _asyncio.run(self._engine.cancel_task(task_id))
        except Exception as exc:
            return {"error": str(exc)}

        return {"success": True, "task_id": task_id, "status": "cancelled"}

    def pause_task(self, task_id: str) -> dict[str, Any]:
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._engine.pause_task(task_id), loop
                )
                future.result(timeout=10)
            else:
                loop.run_until_complete(self._engine.pause_task(task_id))
        except RuntimeError:
            asyncio.run(self._engine.pause_task(task_id))
        except Exception as exc:
            return {"error": str(exc)}

        return {"success": True, "task_id": task_id, "status": "paused"}

    def resume_task(self, task_id: str) -> dict[str, Any]:
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._engine.resume_task(task_id), loop
                )
                future.result(timeout=10)
            else:
                loop.run_until_complete(self._engine.resume_task(task_id))
        except RuntimeError:
            asyncio.run(self._engine.resume_task(task_id))
        except Exception as exc:
            return {"error": str(exc)}

        return {"success": True, "task_id": task_id, "status": "resumed"}

    # ------------------------------------------------------------------
    # workflows
    # ------------------------------------------------------------------

    def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        wf = getattr(self._engine, "_workflow_store", {}).get(workflow_id)
        if wf is None:
            return {"error": f"Workflow {workflow_id} not found"}
        return {
            "id": wf.id,
            "name": wf.name,
            "description": wf.description,
            "status": wf.status.value if wf.status else "unknown",
            "created_at": wf.created_at,
            "started_at": wf.started_at,
            "completed_at": wf.completed_at,
            "tasks": [self._task_to_dict(t) for t in wf.tasks],
            "graph": wf.graph,
        }

    def list_workflows(self) -> list[dict[str, Any]]:
        store = getattr(self._engine, "_workflow_store", {})
        return [
            {
                "id": w.id,
                "name": w.name,
                "description": w.description,
                "status": w.status.value if w.status else "unknown",
                "created_at": w.created_at,
                "started_at": w.started_at,
                "completed_at": w.completed_at,
                "task_count": len(w.tasks),
            }
            for w in store.values()
        ]

    # ------------------------------------------------------------------
    # logs
    # ------------------------------------------------------------------

    def get_logs(self, task_id: str, limit: int = 100) -> list[dict[str, Any]]:
        task = self._engine.get_task(task_id)
        if task is None:
            return [{"error": f"Task {task_id} not found"}]
        logs = [
            {
                "timestamp": e.timestamp,
                "level": e.level,
                "message": e.message,
                "source": getattr(e, "source", ""),
            }
            for e in task.logs[-limit:]
        ]
        return logs

    # ------------------------------------------------------------------
    # approvals
    # ------------------------------------------------------------------

    def get_pending_approvals(self) -> list[dict[str, Any]]:
        mgr = getattr(self._engine, "approvals", None)
        if mgr is None:
            return []

        import asyncio

        try:
            pending = asyncio.run(mgr.get_pending())
        except RuntimeError:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(mgr.get_pending(), loop)
                pending = future.result(timeout=10)
            else:
                pending = loop.run_until_complete(mgr.get_pending())
        except Exception:
            return []

        return [
            {
                "id": a.id,
                "task_id": a.task_id,
                "action": a.action,
                "description": a.description,
                "details": a.details,
                "status": a.status,
                "created_at": a.created_at,
            }
            for a in pending
        ]

    def respond_approval(
        self, approval_id: str, approved: bool, reason: str = ""
    ) -> dict[str, Any]:
        mgr = getattr(self._engine, "approvals", None)
        if mgr is None:
            return {"error": "Approval manager not available"}

        import asyncio

        try:
            result = asyncio.run(mgr.respond(approval_id, approved, reason))
        except RuntimeError:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    mgr.respond(approval_id, approved, reason), loop
                )
                result = future.result(timeout=10)
            else:
                result = loop.run_until_complete(
                    mgr.respond(approval_id, approved, reason)
                )
        except Exception as exc:
            return {"error": str(exc)}

        return {
            "success": result,
            "approval_id": approval_id,
            "approved": approved,
        }

    # ------------------------------------------------------------------
    # undo
    # ------------------------------------------------------------------

    def get_undo_actions(self, task_id: str) -> list[dict[str, Any]]:
        mgr = getattr(self._engine, "undo", None)
        if mgr is None:
            return []

        import asyncio

        try:
            actions = asyncio.run(mgr.list_actions(task_id))
        except RuntimeError:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    mgr.list_actions(task_id), loop
                )
                actions = future.result(timeout=10)
            else:
                actions = loop.run_until_complete(mgr.list_actions(task_id))
        except Exception:
            return []

        return [
            {
                "id": a.id,
                "action_type": a.action_type,
                "description": a.description,
                "timestamp": a.timestamp,
                "restored": a.restored,
            }
            for a in actions
        ]

    def perform_undo(self, undo_id: str) -> dict[str, Any]:
        mgr = getattr(self._engine, "undo", None)
        if mgr is None:
            return {"error": "Undo manager not available"}

        import asyncio

        try:
            result = asyncio.run(mgr.undo(undo_id))
        except RuntimeError:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(mgr.undo(undo_id), loop)
                result = future.result(timeout=10)
            else:
                result = loop.run_until_complete(mgr.undo(undo_id))
        except Exception as exc:
            return {"error": str(exc)}

        return {"success": result, "undo_id": undo_id}

    # ------------------------------------------------------------------
    # permissions
    # ------------------------------------------------------------------

    def get_permissions(self) -> list[dict[str, Any]]:
        mgr = getattr(self._engine, "permissions", None)
        if mgr is None:
            return []

        import asyncio

        try:
            granted = asyncio.run(mgr.list_granted())
        except RuntimeError:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    mgr.list_granted(), loop
                )
                granted = future.result(timeout=10)
            else:
                granted = loop.run_until_complete(mgr.list_granted())
        except Exception:
            return []

        return granted

    # ------------------------------------------------------------------
    # activity log
    # ------------------------------------------------------------------

    def get_activity_log(self, limit: int = 100) -> list[dict[str, Any]]:
        all_tasks = self._engine.list_tasks()
        recent = sorted(all_tasks, key=lambda t: t.created_at, reverse=True)[:limit]
        return [
            {
                "task_id": t.id,
                "name": t.name,
                "status": t.status.value if t.status else "unknown",
                "created_at": t.created_at,
                "completed_at": t.completed_at,
                "agent": t.agent.value if t.agent else None,
            }
            for t in recent
        ]

    # ------------------------------------------------------------------
    # emergency
    # ------------------------------------------------------------------

    def emergency_stop(self) -> dict[str, Any]:
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._engine.stop(), loop
                )
                future.result(timeout=30)
            else:
                loop.run_until_complete(self._engine.stop())
        except RuntimeError:
            asyncio.run(self._engine.stop())
        except Exception as exc:
            return {"error": str(exc)}

        return {"success": True, "message": "Emergency stop executed"}

    # ------------------------------------------------------------------
    # statistics
    # ------------------------------------------------------------------

    def get_statistics(self) -> dict[str, Any]:
        all_tasks = self._engine.list_tasks()
        total = len(all_tasks)
        completed = [t for t in all_tasks if t.status == TaskStatus.COMPLETED]
        failed = [t for t in all_tasks if t.status == TaskStatus.FAILED]
        running = [t for t in all_tasks if t.status == TaskStatus.RUNNING]
        cancelled = [t for t in all_tasks if t.status == TaskStatus.CANCELLED]

        durations = [t.actual_duration for t in completed if t.actual_duration > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        return {
            "total": total,
            "completed": len(completed),
            "failed": len(failed),
            "running": len(running),
            "paused": sum(1 for t in all_tasks if t.status == TaskStatus.PAUSED),
            "cancelled": len(cancelled),
            "pending": sum(1 for t in all_tasks if t.status == TaskStatus.PENDING),
            "avg_duration": avg_duration,
            "total_progress": (
                sum(t.progress for t in all_tasks) / total if total else 0.0
            ),
        }

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _task_to_dict(task: Task) -> dict[str, Any]:
        return {
            "id": task.id,
            "name": task.name,
            "description": task.description,
            "status": task.status.value if task.status else "unknown",
            "agent": task.agent.value if task.agent else None,
            "steps": [
                {
                    "id": s.id,
                    "name": s.name,
                    "action": s.action,
                    "status": s.status.value if s.status else "unknown",
                    "result": s.result,
                    "error": s.error,
                    "started_at": s.started_at,
                    "completed_at": s.completed_at,
                }
                for s in task.steps
            ],
            "dependencies": list(task.dependencies),
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "assigned_to": task.assigned_to,
            "result": task.result,
            "error": task.error,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "requires_approval": task.requires_approval,
            "approval_granted": task.approval_granted,
            "progress": task.progress,
            "estimated_duration": task.estimated_duration,
            "actual_duration": task.actual_duration,
            "parent_task_id": task.parent_task_id,
            "subtasks": list(task.subtasks),
            "metadata": dict(task.metadata),
        }


def uuid4_hex() -> str:
    import uuid

    return uuid.uuid4().hex[:12]
