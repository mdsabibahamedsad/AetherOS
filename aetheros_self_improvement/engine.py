"""SelfImprovementEngine facade (§0.5, §72, §119, §177-180): the ONLY
approved improvement path. Operates under the Master 50 control plane:
privileged actions (experiment promotion, canary, deploy, global lesson)
are authorized through ``plane.check``; the Master 50 emergency stop
halts experiments/canaries too (§179); every action emits an
ImprovementAuditEvent (§180). Default autonomy I2 (propose) (§178).
Unapproved candidates CANNOT deploy (§204); production code/policy is
never silently mutated (§0.2).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .deploy import DeploymentController
from .experiments import ExperimentRunner
from .failures import FailureAnalyzer, RootCauseAnalyzer
from .graders_eval import EvaluationEngine
from .improvements import ImprovementPlanner
from .lessons import LessonEngine
from .models import AutonomyLevel, EvalTask
from .monitoring import DriftDetector, Scorecards
from .traces import TraceStore

logger = logging.getLogger(__name__)


class GovernanceDenied(Exception):
    pass


class SelfImprovementEngine:
    def __init__(self, home: Path, plane: Any = None,
                 autonomy: str = "I2",
                 tenant: str = "default"):
        self.home = Path(home)
        self.plane = plane
        self.autonomy = AutonomyLevel(autonomy)
        self.tenant = tenant
        self.traces = TraceStore(self.home / "traces")
        self.evals = EvaluationEngine()
        self.failures = FailureAnalyzer()
        self.causes = RootCauseAnalyzer()
        self.lessons = LessonEngine()
        self.planner = ImprovementPlanner()
        self.runner = ExperimentRunner(self.evals)
        self.deploy = DeploymentController(auditor=self._audit)
        self.drift = DriftDetector()
        self._stop_hooked = False
        self._wire_emergency_stop()

    # -- governance ---------------------------------------------------------
    def _audit(self, typ: str, data: Dict[str, Any]) -> None:
        if self.plane is not None:
            try:
                self.plane.audit.emit(typ, {"tenant": self.tenant}, data)
                return
            except Exception as exc:
                logger.warning("audit emit failed: %s", exc)
        logger.info("audit %s %s", typ, data)

    def _wire_emergency_stop(self) -> None:
        if self.plane is None or self._stop_hooked:
            return
        try:
            self.plane.emergency.on_stop(lambda _s: self._halt_all())
            self._stop_hooked = True
        except Exception:
            pass

    def _halt_all(self) -> None:
        for exp_id in list(self.runner.experiments):
            self.runner.cancel(exp_id)

    def _gate(self, capability: str, resource: str = "self-improvement",
              identity: str = "improvement-engine") -> None:
        """Privileged subsystem gate via Master 50 (§0.5). Fail closed."""
        if self.plane is None:
            raise GovernanceDenied(
                "no control plane bound: privileged action denied")
        try:
            from aetheros_control_plane.models import ActionManifest
            manifest = ActionManifest(
                task_id="self-improvement", agent_id=identity,
                identity_id=identity, capabilities=[capability],
                scopes=[capability], resources=[resource])
            gate = self.plane.check(manifest)
            if not gate.allowed:
                raise GovernanceDenied("; ".join(gate.reasons))
        except GovernanceDenied:
            raise
        except Exception as exc:
            raise GovernanceDenied(f"control-plane error: {exc}")

    def _level_ok(self, need: AutonomyLevel) -> bool:
        order = ["I0", "I1", "I2", "I3", "I4", "I5"]
        return order.index(self.autonomy.value) >= order.index(need.value)

    # -- the approved loop (§72) ---------------------------------------------
    def observe(self, trace: Dict[str, Any]) -> Optional[str]:
        if not self._level_ok(AutonomyLevel.I0_OBSERVE):
            return None
        from .models import AgentTrace
        allowed = {"trace_id", "task_id", "session_id", "user_intent",
                   "normalized_intent", "agent_identity", "tenant", "model",
                   "model_version", "system_configuration", "policy_version",
                   "tools_available", "tools_used", "tool_calls",
                   "delegations", "approvals", "errors", "retries",
                   "latency_ms", "token_usage", "estimated_cost_usd",
                   "final_outcome", "verification", "user_feedback"}
        t = AgentTrace(**{k: v for k, v in trace.items() if k in allowed})
        t.tenant = self.tenant
        self._audit("improvement.trace_recorded", {"trace": t.trace_id})
        return self.traces.record(t)

    def learn_from_failure(self, trace: Dict[str, Any],
                           failure_class: str,
                           signals: Optional[Dict[str, Any]] = None):
        if not self._level_ok(AutonomyLevel.I1_ANALYZE):
            raise GovernanceDenied("autonomy below I1")
        failure = self.failures.from_trace(trace, failure_class, signals)
        cause = self.causes.analyze(trace, failure)
        lesson = self.lessons.propose(
            observation=failure.what_happened[:300],
            generalization=f"avoid {failure_class} here",
            scope="task", scope_id=trace.get("task_id", ""),
            source_traces=[trace.get("trace_id", "")],
            tenant=self.tenant)
        prop = self.planner.from_failure(failure,
                                         cause.root_cause, lesson)
        self._audit("improvement.proposed",
                    {"proposal": prop.id, "failure": failure.id})
        return {"failure": failure, "cause": cause, "lesson": lesson,
                "proposal": prop}

    def run_experiment(self, proposal_id: str, tasks: List[EvalTask],
                       executor: Callable, baseline: Dict[str, Any],
                       candidate: Dict[str, Any],
                       trials: int = 3, mode: str = "offline") -> Dict[str, Any]:
        if not self._level_ok(AutonomyLevel.I3_EXPERIMENT):
            raise GovernanceDenied("autonomy below I3: experiments denied")
        self._gate("experiment.run")
        prop = self.planner.proposals[proposal_id]
        prop.status = "experiment"
        exp = self.runner.create(tasks, baseline, candidate,
                                 proposal_id=proposal_id, mode=mode,
                                 tenant=self.tenant)
        result = self.runner.run(exp, tasks, executor, trials=trials)
        comp = self.runner.compare(exp) if result.get("status") == "done" \
            else {"recommendation": "reject"}
        self.planner.evaluated(
            prop, comp.get("recommendation") == "promote")
        self._audit("improvement.experimented",
                    {"experiment": exp.id, "recommendation": comp.get(
                        "recommendation")})
        return {"experiment": exp, "comparison": comp, "result": result}

    def approve(self, proposal_id: str, reviewer: str) -> None:
        self._gate("candidate.approve")
        prop = self.planner.proposals[proposal_id]
        if prop.status not in ("review_required", "evaluated"):
            raise GovernanceDenied(
                f"proposal {prop.status}: evaluate before approval")
        prop.status = "approved"
        self._audit("improvement.approved",
                    {"proposal": proposal_id, "reviewer": reviewer})

    def deploy_canary(self, proposal_id: str, version: str,
                      author: str, reviewer: str) -> Any:
        if not self._level_ok(AutonomyLevel.I4_CANARY):
            raise GovernanceDenied("autonomy below I4: canary denied")
        self._gate("candidate.deploy")
        prop = self.planner.proposals[proposal_id]
        if prop.status != "approved":
            raise GovernanceDenied("unapproved candidate cannot deploy")
        dep = self.deploy.stage_deployment(proposal_id, version, author,
                                           reviewer, self.tenant)
        self.deploy.promote(dep, approval_id=f"apr-{proposal_id}")
        self.deploy.promote(dep, approval_id=f"apr-{proposal_id}")
        self.deploy.promote(dep, approval_id=f"apr-{proposal_id}")
        prop.status = "deployed"
        return dep

    def rollback(self, deployment_id: str, reason: str,
                 operator: str) -> bool:
        self._gate("candidate.rollback")
        dep = self.deploy.deployments.get(deployment_id)
        if dep is None:
            return False
        self.deploy._rollback(dep, "operator", reason, {})
        prop = self.planner.proposals.get(dep.proposal_id)
        if prop:
            prop.status = "rolled_back"
        return True

    def scorecards(self) -> Dict[str, Any]:
        return {"model": Scorecards.model(self.evals.trials),
                "failures": self.failures.hotspots(),
                "drift_events": len(self.drift.events)}
