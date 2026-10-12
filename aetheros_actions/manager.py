"""ComputerUseManager — the unified orchestration layer (Steps 2, 16).

Coordinates every component of the AetherOS Computer-Use architecture behind
a single object:

    OBSERVE → PLAN → AUTHORIZE → EXECUTE → VERIFY → RECOVER → REPORT

Responsibilities:

* session lifecycle (create / stop / emergency-stop),
* the explicit state machine (Step 18),
* per-action authorization against risk + autonomy + trust (Step 14),
* execution through the installed adapters (browser/desktop), (Steps 6, 12)
* verification of expected state (Step 17),
* bounded, non-destructive recovery (Step 19),
* loop detection with safe shutdown (Step 20),
* full audit trail (Step 38),
* visibility hooks for human-in-the-loop / UI (Step 42).

Explicit "never continue after fatal verification failure" is enforced: a
failed verification or an unsafe recovery transitions the run to FAILED and
no further actions execute.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from aetheros_actions.audit import AuditLogger
from aetheros_actions.executor import ActionResult, ActionExecutor
from aetheros_actions.loops import LoopDetector, LoopInfo
from aetheros_actions.model import Action, ActionType, Observation, RiskLevel, TrustSource
from aetheros_actions.observer import ObservationBackends, ScreenObserver
from aetheros_actions.permissions import AutonomyLevel, Decision, PermissionDecision, PermissionManager
from aetheros_actions.planner import ActionPlanner, PlanVerdict
from aetheros_actions.recovery import RecoveryManager
from aetheros_actions.session import ComputerUseSession, SessionManager, StopSignal
from aetheros_actions.state import ComputerUseState, StateMachine
from aetheros_actions.trust import classify_text
from aetheros_actions.verifier import ActionVerifier, VerificationResult, VerificationVerdict

_NEW_TRACE = uuid.uuid4().hex

_NOT_REQUIRED = VerificationVerdict.NOT_REQUIRED
_FAILED = VerificationVerdict.FAIL


def _attach_receipts(report) -> None:
    """Best-effort: fill ``report.receipts`` from its steps (Step 63)."""
    try:
        from aetheros_actions.receipts import run_receipts
        report.receipts = [r.to_dict() for r in run_receipts(report)]
    except Exception:  # noqa: BLE001 - receipts are best-effort
        pass


@dataclass
class StepOutcome:
    """Result of running one plan step."""

    action: Action
    decision: Decision
    result: ActionResult
    verification: VerificationResult
    loop: Optional[LoopInfo] = None

    @property
    def ok(self) -> bool:
        return (self.decision.decision != PermissionDecision.DENY
                and self.result.ok
                and self.verification.passed)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.to_dict(),
            "decision": self.decision.to_dict(),
            "result": self.result.to_dict(),
            "verification": self.verification.to_dict(),
            "loop": self.loop.to_dict() if self.loop else None,
            "ok": self.ok,
        }


@dataclass
class RunReport:
    """Full audit report of a plan execution."""

    ok: bool
    session_id: str
    final_state: ComputerUseState
    steps: List[StepOutcome] = field(default_factory=list)
    loop_detected: Optional[LoopInfo] = None
    stopped_by_user: bool = False
    stopped_by_loop: bool = False
    trace_id: str = ""
    warnings: List[str] = field(default_factory=list)
    receipts: List[Dict[str, Any]] = field(default_factory=list)
    preview: Optional[Dict[str, Any]] = None      # dry-run preview (Step 60)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "session_id": self.session_id,
            "final_state": self.final_state.value,
            "loop_detected": self.loop_detected.to_dict() if self.loop_detected else None,
            "stopped_by_user": self.stopped_by_user,
            "stopped_by_loop": self.stopped_by_loop,
            "trace_id": self.trace_id,
            "warnings": self.warnings,
            "steps": [s.to_dict() for s in self.steps],
            "receipts": self.receipts,
            "preview": self.preview,
        }


class ComputerUseManager:
    """High-level orchestrator for the computer-use action pipeline."""

    def __init__(
        self,
        *,
        executor: Optional[ActionExecutor] = None,
        permission_manager: Optional[PermissionManager] = None,
        verifier: Optional[ActionVerifier] = None,
        recovery: Optional[RecoveryManager] = None,
        planner: Optional[ActionPlanner] = None,
        loop_detector: Optional[LoopDetector] = None,
        observer: Optional[ScreenObserver] = None,
        audit: Optional[AuditLogger] = None,
        sessions: Optional[SessionManager] = None,
        confirm_callback: Optional[Callable[[Decision], bool]] = None,
        # Steps 61 / 71-72 / 73 / 75 / 95 — additive hardening. All default to
        # safe inert instances; existing callers are unchanged.
        idempotency=None,
        anomaly_detector=None,
        quarantine=None,
        lock_manager=None,
        intent_verifier=None,
        block_on_intent_drift: bool = False,
    ) -> None:
        self.sessions = sessions or SessionManager()
        self.planner = planner or ActionPlanner()
        self.permission_manager = permission_manager or PermissionManager(
            confirm_callback=confirm_callback,
        )
        self.executor = executor or ActionExecutor()
        self.verifier = verifier or ActionVerifier()
        self.recovery = recovery or RecoveryManager()
        self.observer = observer or ScreenObserver()
        self.loop_detector = loop_detector or LoopDetector()
        self.audit = audit or AuditLogger()
        from aetheros_actions.anomaly import AgentQuarantine, AnomalyDetector
        from aetheros_actions.idempotency import IdempotencyRegistry
        from aetheros_actions.intent import IntentVerifier
        from aetheros_actions.lock import ResourceLockManager
        self.idempotency = idempotency or IdempotencyRegistry()
        self.anomaly_detector = anomaly_detector or AnomalyDetector()
        self.quarantine = quarantine or AgentQuarantine()
        self.lock_manager = lock_manager or ResourceLockManager()
        self.intent_verifier = intent_verifier or IntentVerifier()
        self.block_on_intent_drift = block_on_intent_drift

    # ── sessions ─────────────────────────────────────────────────────

    def create_session(
        self,
        agent_id: str = "",
        autonomy_level: Any = AutonomyLevel.SAFE_AUTONOMOUS,
    ) -> ComputerUseSession:
        return self.sessions.create(agent_id=agent_id, autonomy_level=autonomy_level)

    def get_session(self, session_id: str) -> Optional[ComputerUseSession]:
        return self.sessions.get(session_id)

    def stop_session(self, session_id: str) -> None:
        s = self.sessions.get(session_id)
        if s:
            s.stop()
            self.recovery.state.retries_used = 0

    def emergency_stop_all(self) -> int:
        return self.sessions.stop_all(StopSignal.EMERGENCY_STOP)

    # ── public entry points ──────────────────────────────────────────

    def observe(self, session: ComputerUseSession, mode: str = "desktop") -> Observation:
        """Observe the environment (State: IDLE→OBSERVING)."""
        try:
            session.state.transition(ComputerUseState.OBSERVING)
        except Exception:  # noqa: BLE001
            pass
        obs = self.observer.observe(mode=mode)
        try:
            session.state.transition(ComputerUseState.IDLE)
        except Exception:  # noqa: BLE001
            pass
        return obs

    def plan(
        self,
        session: ComputerUseSession,
        goal: str,
        steps: List[Dict[str, Any]],
        *,
        source: TrustSource = TrustSource.AGENT_PLAN,
    ) -> PlanVerdict:
        """Plan + authorize-aware step assembly (State: IDLE→PLANNING)."""
        try:
            session.state.transition(ComputerUseState.PLANNING)
        except Exception:  # noqa: BLE001
            pass
        for step in steps:
            step.setdefault("agent_id", session.agent_id)
            step.setdefault("session_id", session.session_id)
            step.setdefault("source", source)
        verdict = self.planner.plan(goal, steps, agent_id=session.agent_id,
                                    session_id=session.session_id, source=source)
        if verdict.ok:
            # Steps 59/63: annotate reversibility so receipts/previews carry it.
            from aetheros_actions.reversibility import annotate_plan_actions
            annotate_plan_actions(verdict.actions)
            # Step 95: original-intent drift check (warning by default).
            from aetheros_actions.intent import IntentVerifier
            try:
                drift = self.intent_verifier.check(goal, verdict.actions)
                if drift.drifted:
                    verdict.warnings.append(
                        "intent drift detected: " + "; ".join(drift.reasons)
                    )
            except Exception:  # noqa: BLE001 - intent check is advisory
                pass
        if not verdict.ok:
            try:
                session.state.transition(ComputerUseState.FAILED)
            except Exception:  # noqa: BLE001
                pass
        else:
            try:
                session.state.transition(ComputerUseState.IDLE)
            except Exception:  # noqa: BLE001
                pass
        return verdict

    def run_plan(
        self,
        session: ComputerUseSession,
        goal: str,
        steps: List[Dict[str, Any]],
        *,
        source: TrustSource = TrustSource.AGENT_PLAN,
        dry_run: bool = False,
        trace_id: str = "",
    ) -> RunReport:
        """Execute a full plan with the Plan→Authorize→Act→Verify→Recover loop.

        ``dry_run=True`` (Step 58/60) returns a preview report without
        executing anything. ``trace_id`` correlates every step/receipt in the
        report. Returns a :class:`RunReport`; never raises on action-level
        failures.
        """
        plan = self.plan(session, goal, steps, source=source)
        if not plan.ok:
            # The plan itself was refused (e.g. untrusted source). Surface
            # each proposed step as a DENY so the report reflects the refusal.
            denied_steps = [
                self._denied_outcome(session, step, plan.warnings)
                for step in steps
            ]
            report = RunReport(ok=False, session_id=session.session_id,
                               final_state=ComputerUseState.FAILED,
                               steps=denied_steps,
                               stopped_by_loop=False, stopped_by_user=False,
                               trace_id=trace_id,
                               warnings=list(plan.warnings))
            _attach_receipts(report)
            return report

        run_trace = trace_id or _NEW_TRACE
        for action in plan.actions:
            action.trace_id = run_trace

        # Step 95: block destructive intent drift when opted in.
        if self.block_on_intent_drift:
            from aetheros_actions.intent import IntentVerifier
            try:
                drift = self.intent_verifier.check(goal, plan.actions)
            except Exception:  # noqa: BLE001
                drift = None
            if drift is not None and drift.drifted:
                denied_steps = [
                    self._denied_outcome(session, step, ["intent drift blocked"])
                    for step in steps
                ]
                report = RunReport(ok=False, session_id=session.session_id,
                                   final_state=ComputerUseState.FAILED,
                                   steps=denied_steps,
                                   stopped_by_loop=False, stopped_by_user=False,
                                   trace_id=run_trace,
                                   warnings=["intent drift blocked: "
                                             + "; ".join(drift.reasons)])
                _attach_receipts(report)
                return report

        # Step 58/60: dry-run preview — no execution, nothing touched.
        if dry_run:
            from aetheros_actions.dryrun import plan_dry_run
            preview = plan_dry_run(goal, plan.actions)
            return RunReport(
                ok=True,
                session_id=session.session_id,
                final_state=ComputerUseState.COMPLETED,
                steps=[],
                trace_id=run_trace,
                preview=preview.to_dict(),
            )

        outcomes: List[StepOutcome] = []
        # Reset recovery + loop accounting for the run.
        self.recovery = RecoveryManager(
            max_retries=self.recovery.max_retries,
            max_destructive_retries=self.recovery.max_destructive_retries,
            max_run_attempts=self.recovery.max_run_attempts,
            retry_interval=self.recovery.retry_interval,
            reobserve=self.recovery.reobserve,
        )
        self.loop_detector = LoopDetector(
            window_size=self.loop_detector.window_size,
            repeat_threshold=self.loop_detector.repeat_threshold,
            failure_threshold=self.loop_detector.failure_threshold,
        )
        self.anomaly_detector.reset()

        for action in plan.actions:
            if session.should_stop():
                try:
                    session.state.transition(ComputerUseState.CANCELLED)
                except Exception:  # noqa: BLE001
                    pass
                return RunReport(ok=False, session_id=session.session_id,
                                 final_state=session.state.state,
                                 steps=outcomes, stopped_by_user=True,
                                 trace_id=run_trace,
                                 warnings=list(plan.warnings))
            # Pause support.
            if session.is_paused():
                session.resume()
            outcome = self.run_step(session, action)
            outcomes.append(outcome)
            if not outcome.ok:
                break

        final = session.state.state
        loop = self.loop_detector.detect()
        stopped_by_loop = bool(loop) and final in (ComputerUseState.FAILED,
                                                   ComputerUseState.CANCELLED)
        report = RunReport(
            ok=all(o.ok for o in outcomes),
            session_id=session.session_id,
            final_state=final,
            steps=outcomes,
            loop_detected=loop,
            stopped_by_loop=stopped_by_loop and not session.should_stop(),
            trace_id=run_trace,
            warnings=list(plan.warnings),
        )
        # Step 63: durable per-action receipts correlated by trace_id.
        _attach_receipts(report)
        # Release any resource locks this agent/session took during the run.
        self.lock_manager.release_all(session.session_id)
        return report

    def run_step(self, session: ComputerUseSession, action: Action) -> StepOutcome:
        """Run a single action through the full pipeline (Steps 14-19)."""
        self.audit.record(action, decision="PENDING")

        # Step 72: quarantined agents cannot drive the computer.
        if action.agent_id and self.quarantine.is_quarantined(action.agent_id):
            decision = Decision(PermissionDecision.DENY, action,
                                reason="agent is quarantined (anomaly detected)")
            self.audit.record(action, decision="DENY",
                              error="quarantined agent blocked")
            return StepOutcome(
                action=action, decision=decision,
                result=ActionResult(ok=False, action=action, error=decision.reason),
                verification=VerificationResult(verdict=_NOT_REQUIRED, action=action),
            )

        # Step 61: idempotency — skip actions already executed by key.
        if action.idempotency_key:
            from aetheros_actions.idempotency import get_idempotency_registry
            registry = self.idempotency
            if not registry.check_and_record(action.idempotency_key,
                                             action.action_id,
                                             session_id=session.session_id):
                decision = Decision(PermissionDecision.ALLOW, action,
                                    reason="idempotency: already executed")
                self.audit.record(action, decision="ALLOW",
                                  meta={"summary": "idempotency skip (already executed)"})
                return StepOutcome(
                    action=action, decision=decision,
                    result=ActionResult(ok=True, action=action,
                                        message="already executed (idempotency skip)"),
                    verification=VerificationResult(
                        verdict=_NOT_REQUIRED, action=action),
                )

        # Step 75: resource locks — never share keyboard/mouse/clipboard/etc.
        from aetheros_actions.lock import ACTION_RESOURCES
        resource = ACTION_RESOURCES.get(action.action_type.value)
        lock_holder = session.session_id
        if resource and not self.lock_manager.acquire(resource, lock_holder):
            held = self.lock_manager.held_by(resource)
            decision = Decision(PermissionDecision.DENY, action,
                                reason=f"resource {resource!r} held by {held!r}")
            self.audit.record(action, decision="DENY",
                              error=f"resource lock held by {held!r}")
            return StepOutcome(
                action=action, decision=decision,
                result=ActionResult(ok=False, action=action, error=decision.reason),
                verification=VerificationResult(verdict=_NOT_REQUIRED, action=action),
            )

        # 1. Authorize.
        try:
            session.state.transition(ComputerUseState.WAITING_FOR_PERMISSION)
        except Exception:  # noqa: BLE001
            pass
        decision = self.permission_manager.authorize(action, session.autonomy_level)
        if decision.decision == PermissionDecision.REQUIRE_CONFIRMATION:
            decision = self.permission_manager.confirm(action)
        self.audit.record(action, decision=decision.decision.value)
        if decision.decision == PermissionDecision.DENY:
            if resource:
                self.lock_manager.release(resource, lock_holder)
            try:
                session.state.transition(ComputerUseState.COMPLETED)
            except Exception:  # noqa: BLE001
                pass
            denied = StepOutcome(
                action=action,
                decision=decision,
                result=ActionResult(ok=False, action=action,
                                    error=decision.reason),
                verification=VerificationResult(
                    verdict=_NOT_REQUIRED, action=action),
            )
            return denied

        # 2. Execute (State: EXECUTING → VERIFYING) with bounded recovery.
        try:
            session.state.transition(ComputerUseState.EXECUTING)
        except Exception:  # noqa: BLE001
            pass

        attempts = 0
        result = ActionResult(ok=False, action=action, error="not executed")
        while True:
            if session.should_stop():
                try:
                    session.state.transition(ComputerUseState.CANCELLED)
                except Exception:  # noqa: BLE001
                    pass
                result = ActionResult(ok=False, action=action,
                                      error="stopped by user")
                break
            attempts += 1
            result = self.executor.execute(action)
            self.audit.record(action, decision=decision.decision.value,
                              ok=result.ok, error=result.error,
                              elapsed_ms=result.elapsed_ms)
            self.loop_detector.record(action, failed=not result.ok)
            loop = self.loop_detector.detect()
            if loop:
                return self._loop_shutdown(session, action, decision, result, loop)

            # Step 71/72: anomaly detection → quarantine the responsible agent.
            self.anomaly_detector.record(action)
            anomaly = self.anomaly_detector.detect(agent_id=action.agent_id)
            if anomaly:
                return self._anomaly_shutdown(session, action, decision,
                                              result, anomaly)

            if result.ok:
                break
            # Bounded recovery.
            rec = self.recovery.should_retry(action, attempts, result)
            if not rec.should_retry:
                try:
                    session.state.transition(ComputerUseState.FAILED)
                except Exception:  # noqa: BLE001
                    pass
                self.recovery.record_success()
                failed = StepOutcome(
                    action=action,
                    decision=decision,
                    result=result,
                    verification=VerificationResult(
                        verdict=_FAILED, action=action,
                        detail=rec.reason),
                )
                return failed

        # 3. Verify (Step 17).
        try:
            session.state.transition(ComputerUseState.VERIFYING)
        except Exception:  # noqa: BLE001
            pass
        verification = self.verifier.verify(action)
        self.audit.record(action, decision=decision.decision.value,
                          ok=result.ok and verification.passed)
        try:
            session.state.transition(ComputerUseState.COMPLETED)
        except Exception:  # noqa: BLE001
            pass
        self.recovery.record_success()
        if resource:
            self.lock_manager.release(resource, lock_holder)
        return StepOutcome(action=action, decision=decision, result=result,
                            verification=verification)

    # ── internals ────────────────────────────────────────────────────

    def _denied_outcome(self, session, step, reasons) -> StepOutcome:
        """Build a DENY StepOutcome for a refused plan step."""
        action = Action(
            action_type=ActionType(str(step.get("action", "")).upper())
            if str(step.get("action", "")).upper() in ActionType.__members__
            else ActionType.SCREENSHOT,
            target=str(step.get("target", "")),
            parameters=dict(step.get("parameters") or {}),
            reason=str(step.get("reason", "")),
            agent_id=session.agent_id,
            session_id=session.session_id,
        )
        reason = ("; ".join(reasons) if reasons else "plan refused")
        decision = Decision(PermissionDecision.DENY, action, reason=reason)
        return StepOutcome(
            action=action,
            decision=decision,
            result=ActionResult(ok=False, action=action, error=reason),
            verification=VerificationResult(
                verdict=_NOT_REQUIRED, action=action),
        )

    def _loop_shutdown(
        self, session, action, decision, result, loop: LoopInfo,
    ) -> StepOutcome:
        try:
            session.state.transition(ComputerUseState.CANCELLED)
        except Exception:  # noqa: BLE001
            pass
        self.audit.record(action, decision=decision.decision.value,
                          ok=False, error=f"loop detected: {loop.kind}")
        self.lock_manager.release_all(session.session_id)
        return StepOutcome(
            action=action,
            decision=decision,
            result=result,
            verification=VerificationResult(
                verdict=_FAILED, action=action,
                detail=f"loop detected: {loop.kind} — stopped safely"),
            loop=loop,
        )

    def _anomaly_shutdown(
        self, session, action, decision, result, anomaly,
    ) -> StepOutcome:
        """Quarantine the responsible agent + stop the run (Steps 71-72)."""
        try:
            session.state.transition(ComputerUseState.CANCELLED)
        except Exception:  # noqa: BLE001
            pass
        detail = (f"anomaly detected: {anomaly.kind} "
                  f"({anomaly.detail}) — agent quarantined")
        if action.agent_id:
            try:
                self.quarantine.quarantine_agent(
                    action.agent_id,
                    reason=detail,
                    evidence=[anomaly.to_dict()],
                )
            except Exception:  # noqa: BLE001 - quarantine best-effort
                pass
        self.audit.record(action, decision=decision.decision.value,
                          ok=False, error=f"anomaly: {anomaly.kind}")
        self.lock_manager.release_all(session.session_id)
        return StepOutcome(
            action=action,
            decision=decision,
            result=result,
            verification=VerificationResult(
                verdict=_FAILED, action=action,
                detail=detail),
        )

    # ── embedding hooks (Step 42: visible mode) ──────────────────────

    def attach_observer_backends(self, backends: ObservationBackends) -> None:
        self.observer = ScreenObserver(backends)


def get_computer_use_manager() -> ComputerUseManager:
    """Return the process-wide ComputerUseManager singleton."""
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = ComputerUseManager()
    return _MANAGER


_MANAGER: Optional[ComputerUseManager] = None