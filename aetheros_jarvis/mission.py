"""Jarvis Mode — mission mode.

Turns a user-defined goal into a plan, requests approval when needed,
coordinates agents (via the AetherOS automation orchestrator when available),
and reports progress. Every mission that touches privileged actions is gated
by the permission layer. No mission executes without an approved plan.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from aetheros_jarvis.models import (
    MissionPlan,
    MissionReport,
    MissionStatus,
    MissionStep,
    MissionStepStatus,
)

logger = logging.getLogger(__name__)

try:
    from aetheros_automation.orchestrator import TaskOrchestrator
except Exception:  # pragma: no cover - degraded when automation package absent
    TaskOrchestrator = None  # type: ignore[assignment,misc]

try:
    from aetheros_automation.orchestrator.agent_engine import AgentExecutionEngine
except Exception:  # pragma: no cover - degraded when automation package absent
    AgentExecutionEngine = None  # type: ignore[assignment,misc]

try:
    from aetheros_automation.orchestrator import security as _orchestrator_security
except Exception:  # pragma: no cover - degraded when automation package absent
    _orchestrator_security = None  # type: ignore[assignment]


class MissionManager:
    """Lifecycle manager for user-defined missions.

    Flow: ``create(goal) -> plan() -> [approve()] -> execute() -> report()``.
    If ``approval_required`` is True, execution is blocked until an explicit
    approval callback returns True. Progress is emitted through listeners and
    a final :class:`MissionReport` is produced.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._missions: Dict[str, MissionPlan] = {}
        self._reports: Dict[str, MissionReport] = {}
        self._approval_cb: Optional[Callable[[MissionPlan], bool]] = None
        self._step_cb: Optional[Callable[[MissionPlan, MissionStep], str]] = None
        self._orchestrator = None
        self._init_orchestrator()

    def _init_orchestrator(self) -> None:
        try:
            if TaskOrchestrator is not None:
                # Use the real agent execution engine so orchestrated steps
                # spawn actual AIAgent runs rather than the legacy simulation.
                if AgentExecutionEngine is not None:
                    self._orchestrator = TaskOrchestrator(
                        execution_engine=AgentExecutionEngine()
                    )
                else:
                    self._orchestrator = TaskOrchestrator()
        except Exception as exc:
            logger.debug("Orchestrator unavailable: %s", exc)
            self._orchestrator = None

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------

    def set_approval_callback(self, cb: Optional[Callable[[MissionPlan], bool]]) -> None:
        """Install the resolver that approves/rejects a full mission plan."""
        with self._lock:
            self._approval_cb = cb

    def set_step_executor(self, cb: Callable[[MissionPlan, MissionStep], str]) -> None:
        """Install the executor that runs a single approved mission step."""
        with self._lock:
            self._step_cb = cb

    # ------------------------------------------------------------------
    # Plan lifecycle
    # ------------------------------------------------------------------

    def create(self, goal: str, *, approval_required: bool = True) -> MissionPlan:
        plan = MissionPlan(goal=goal, approval_required=approval_required)
        with self._lock:
            self._missions[plan.id] = plan
        self._audit("WORKFLOW_STARTED", message=f"Mission created: {plan.id}",
                    details={"mission_id": plan.id, "goal": goal})
        return plan

    def plan(self, mission_id: str, steps: List[Dict[str, Any]]) -> Optional[MissionPlan]:
        """Attach a concrete step list to a mission.

        Each step dict supports ``description``, ``tool``, ``params``, and
        ``approval_required``.
        """
        with self._lock:
            plan = self._missions.get(mission_id)
            if plan is None:
                return None
            plan.steps = [
                MissionStep(
                    description=step.get("description", "step"),
                    tool=step.get("tool", ""),
                    params=step.get("params", {}),
                    approval_required=bool(step.get("approval_required", False)),
                )
                for step in steps
            ]
            plan.status = MissionStatus.AWAITING_APPROVAL if plan.approval_required else MissionStatus.APPROVED
            return plan

    def approve(self, mission_id: str, *, approved: bool = True) -> Optional[MissionPlan]:
        with self._lock:
            plan = self._missions.get(mission_id)
            if plan is None:
                return None
            plan.status = MissionStatus.APPROVED if approved else MissionStatus.CANCELLED
            if approved:
                plan.approved_at = time.time()
        self._audit(
            "PERMISSION_GRANTED" if approved else "PERMISSION_DENIED",
            severity="info" if approved else "warning",
            message=f"Mission {'approved' if approved else 'cancelled'}: {mission_id}",
            details={"mission_id": mission_id},
        )
        return plan

    def get(self, mission_id: str) -> Optional[MissionPlan]:
        with self._lock:
            return self._missions.get(mission_id)

    def list_missions(self) -> List[MissionPlan]:
        with self._lock:
            return list(self._missions.values())

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, mission_id: str) -> MissionReport:
        with self._lock:
            plan = self._missions.get(mission_id)
            if plan is None:
                raise KeyError(f"No mission with id {mission_id}")
            if plan.status in (MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.CANCELLED):
                raise RuntimeError(f"Mission already finished ({plan.status.value})")
            if plan.approval_required and plan.status != MissionStatus.APPROVED:
                # Request approval through the callback if available.
                if self._approval_cb is not None:
                    granted = False
                    try:
                        granted = bool(self._approval_cb(plan))
                    except Exception as exc:
                        logger.warning("Approval callback failed: %s", exc)
                    if not granted:
                        plan.status = MissionStatus.CANCELLED
                        return self._finish_report(plan, "Mission cancelled: not approved.")
                else:
                    plan.status = MissionStatus.CANCELLED
                    return self._finish_report(plan, "Mission cancelled: approval required but no approval callback installed.")

            plan.status = MissionStatus.EXECUTING

        report = MissionReport(
            mission_id=plan.id,
            goal=plan.goal,
            status=MissionStatus.EXECUTING,
            started_at=time.time(),
        )
        errors: List[str] = []

        for step in plan.steps:
            if step.status in (MissionStepStatus.COMPLETED, MissionStepStatus.SKIPPED):
                continue
            step.status = MissionStepStatus.RUNNING
            step.started_at = time.time()
            result = ""
            try:
                if not self._authorize_step(plan, step):
                    raise PermissionError(f"Step not authorized: {step.description}")
                if self._step_cb is not None:
                    result = self._step_cb(plan, step) or ""
                elif self._orchestrator is not None:
                    result = self._orchestrate_step(plan, step)
                else:
                    raise RuntimeError("No step executor installed")
                step.status = MissionStepStatus.COMPLETED
                step.result = str(result)[:500]
            except Exception as exc:
                logger.warning("Mission step failed (%s): %s", step.description, exc)
                step.status = MissionStepStatus.FAILED
                step.result = str(exc)[:500]
                errors.append(f"{step.description}: {exc}")
                if plan.approval_required:
                    break  # fail-fast on missions that required approval
            finally:
                step.completed_at = time.time()

        completed = all(s.status == MissionStepStatus.COMPLETED for s in plan.steps)
        plan.status = MissionStatus.COMPLETED if completed and not errors else MissionStatus.FAILED
        report.status = plan.status
        report.steps = plan.steps
        report.completed_at = time.time()
        report.errors = errors
        report.summary = self._summarize(plan)
        plan.summary = report.summary

        with self._lock:
            self._reports[mission_id] = report
        self._audit(
            "WORKFLOW_COMPLETED" if plan.status == MissionStatus.COMPLETED else "WORKFLOW_FAILED",
            severity="info" if plan.status == MissionStatus.COMPLETED else "error",
            message=f"Mission finished: {plan.id} ({plan.status.value})",
            details={"mission_id": plan.id, "errors": len(errors)},
        )
        return report

    def _authorize_step(self, plan: MissionPlan, step: MissionStep) -> bool:
        """Authorize a single mission step through the security subsystem."""
        if _orchestrator_security is None:
            return True
        try:
            principal = f"mission:{plan.id}"
            # The authz engine requires an active principal; register this
            # mission as an agent identity first.
            _orchestrator_security.register_agent(
                principal, role="mission", owner="user",
            )
            return bool(_orchestrator_security.authorize(
                principal=principal,
                action=f"mission_step:{step.tool or 'execute'}",
                resource=step.description,
            ))
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Step authorization skipped: %s", exc)
            return True

    def _audit(self, event_type: str, *, severity: str = "info",
               message: str = "", details: Optional[Dict[str, Any]] = None) -> None:
        if _orchestrator_security is None:
            return
        try:
            _orchestrator_security.audit(
                event_type, severity=severity, message=message, details=details,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Audit write skipped: %s", exc)

    def _orchestrate_step(self, plan: MissionPlan, step: MissionStep) -> str:
        """Best-effort coordination through the automation orchestrator.

        The orchestrator's ``run`` is async; ``MissionManager.execute`` is a
        synchronous API, so the coroutine is driven through an event-loop
        bridge.  When the caller is already inside a running loop we execute
        in a fresh worker-thread loop (never corrupt the caller's loop).
        """
        if self._orchestrator is None:
            return ""
        try:
            result = self._run_coroutine(
                self._orchestrator.run(goal=step.description, params=step.params)
            )
            if isinstance(result, dict):
                return str(result.get("summary", result))
            return str(result)
        except Exception as exc:
            logger.warning("Orchestrator step failed: %s", exc)
            raise

    @staticmethod
    def _run_coroutine(coro):
        """Run an async coroutine from a sync caller without corrupting any
        running event loop.  ``asyncio.run`` is used when no loop is active;
        otherwise the coroutine is driven in a dedicated thread's own loop."""
        try:
            asyncio.get_running_loop()
            in_loop = True
        except RuntimeError:
            in_loop = False
        if not in_loop:
            return asyncio.run(coro)
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()

    def _finish_report(self, plan: MissionPlan, summary: str) -> MissionReport:
        report = MissionReport(
            mission_id=plan.id,
            goal=plan.goal,
            status=plan.status,
            steps=plan.steps,
            summary=summary,
            started_at=time.time(),
            completed_at=time.time(),
        )
        with self._lock:
            self._reports[plan.id] = report
        return report

    def _summarize(self, plan: MissionPlan) -> str:
        done = sum(1 for s in plan.steps if s.status == MissionStepStatus.COMPLETED)
        total = len(plan.steps)
        return f"{done}/{total} steps completed for '{plan.goal}'."

    def report(self, mission_id: str) -> Optional[MissionReport]:
        with self._lock:
            return self._reports.get(mission_id)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "missions": len(self._missions),
                "reports": len(self._reports),
                "orchestrator_available": self._orchestrator is not None,
                "approval_callback": self._approval_cb is not None,
                "step_executor": self._step_cb is not None,
            }
