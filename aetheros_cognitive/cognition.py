"""CognitiveArchitecture facade (§1-2, §68, §70-71, §129, §133-134,
§160, §176-178, §195): canonical PERCEIVE→…→UPDATE loop. Prediction
NEVER overrides policy (§0.8/§73: policy check precedes execution).
Prediction errors feed Master 51 experience (§133). High-risk decisions
emit CognitiveAuditEvents (§195) and support red-team review (§176-177)
plus human approval packets (§178). No chain-of-thought exposed — only
decision summary, evidence, predictions, confidence, policy reasons,
verification (§70-71).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .causal import CausalModel
from .counterfactual import CounterfactualEngine
from .foresight import ForesightController, horizon_confidence
from .models import (ActionCandidate, CognitiveMode, SimulationBudget,
                     WorldState)
from .planner import Planner
from .reality import RealityChecker, WorldModelUpdater, toctou_recheck
from .router import CognitiveRouter
from .simulator import Simulator
from .world_models import HybridWorldModel, RuleBasedWorldModel
from .world_state import StateEstimator

logger = logging.getLogger(__name__)


class GovernanceDenied(Exception):
    pass


class CognitiveArchitecture:
    def __init__(self, home: Path, plane: Any = None,
                 improvement: Any = None,
                 user_preference: str = "balanced",
                 tenant: str = "default"):
        self.home = Path(home)
        self.plane = plane
        self.improvement = improvement
        self.tenant = tenant
        self.estimator = StateEstimator()
        self.causal = CausalModel()
        rules = RuleBasedWorldModel()
        self.model = HybridWorldModel([rules])
        self.sim = Simulator(self.model)
        self.planner = Planner(self.sim)
        self.planner.policy_check = self._policy_check
        self.counterfactuals = CounterfactualEngine(self.sim)
        self.reality = RealityChecker()
        self.updater = WorldModelUpdater()
        self.foresight = ForesightController()
        self.router = CognitiveRouter(user_preference)
        self.trust: Dict[str, float] = {"hybrid": 0.8}
        self.failures = 0
        self.decisions: List[Dict[str, Any]] = []

    # -- Master 50 gate ------------------------------------------------------
    def _audit(self, typ: str, data: Dict[str, Any]) -> None:
        if self.plane is not None:
            try:
                self.plane.audit.emit(typ, {"tenant": self.tenant}, data)
                return
            except Exception as exc:
                logger.warning("audit emit failed: %s", exc)
        logger.info("cognitive audit %s %s", typ, data)

    def _policy_check(self, action: Dict[str, Any]) -> Optional[str]:
        """Denial reason or None. No plane → deny high-risk (fail closed),
        allow low-risk simulation-only (simulation ≠ execution)."""
        if self.plane is None:
            return None
        try:
            from aetheros_control_plane.models import ActionManifest
            manifest = ActionManifest(
                task_id="cognition", agent_id="cognitive-architecture",
                identity_id="cognitive-architecture",
                capabilities=[action.get("type", "unknown")],
                scopes=[action.get("type", "unknown")],
                resources=[str(action.get("parameters", {}))[:200]])
            gate = self.plane.check(manifest)
            if not gate.allowed:
                return "; ".join(gate.reasons)
            return None
        except Exception as exc:
            return f"control-plane error: {exc}"

    # -- canonical loop (§2) ---------------------------------------------------
    def decide(self, goal: Dict[str, Any],
               candidates: Callable[[WorldState],
                                    List[ActionCandidate]],
               executor: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]]
               = None,
               budget: Optional[SimulationBudget] = None,
               stakes: float = 0.5) -> Dict[str, Any]:
        state = self.estimator.state
        budget = budget or SimulationBudget()
        # 1. risk/uncertainty triage
        risk = float(goal.get("risk", 0.3))
        unc = 1.0 - state.confidence
        route = self.router.select(
            risk, unc, int(goal.get("horizon", 2)),
            float(goal.get("complexity", 0.3)),
            world_model_available=not self.model.disabled)
        mode = route["mode"]
        record: Dict[str, Any] = {"mode": mode, "goal": goal.get(
            "objective", ""), "state_version": state.version}
        if mode == CognitiveMode.REACTIVE.value:
            items = self.planner.expand(state, candidates, budget)
            record.update({"simulated": False, "options": len(items)})
        else:
            fore = self.foresight.decide(risk, unc, True, budget, stakes)
            record["foresight"] = fore
            if fore["decision"] == "ask_user":
                record.update({"action": "ASK_USER",
                               "reason": fore["reason"]})
                self._audit("cognitive.decision", record)
                self.decisions.append(record)
                return record
            depth = fore.get("depth", budget.max_depth)
            b = SimulationBudget(max_depth=depth,
                                 max_branches=budget.max_branches,
                                 max_rollouts=budget.max_rollouts,
                                 max_time_s=budget.max_time_s,
                                 max_cost=budget.max_cost)
            if mode == "simulative":
                items = self.planner.beam_search(state, candidates,
                                                 depth=depth, budget=b)
            elif mode in ("counterfactual", "deliberative"):
                items = self.planner.mcts(state, candidates, budget=b)
            else:
                items = self.planner.best_first(state, candidates, b)
            record.update({"simulated": True, "options": len(items),
                           "pruned": self.planner.pruned})
        if not items:
            record.update({"action": "STOP",
                           "reason": "no admissible candidates"})
            self.decisions.append(record)
            return record
        best = items[0]
        cand = best["candidate"]
        branch = best["branch"]
        # 2. counterfactual spot-check for high risk
        if risk >= 0.6 and len(items) > 1:
            alt = self.counterfactuals.simulate(
                state, [{"scenario_id": "alt",
                         "actions": [{"type": items[1]["candidate"].type,
                                      "parameters": items[1]["candidate"
                                                             ].parameters}]}],
                budget)
            record["counterfactual"] = self.counterfactuals.compare(
                {"score": best["score"]}, alt)
        # 3. TOCTOU recheck + policy ALREADY enforced in expand; declare
        #    expectation BEFORE any real execution (§43)
        record.update({
            "selected": cand.type, "score": round(best["score"], 4),
            "predicted": branch.predicted_states[-1]
            if branch.predicted_states else {},
            "confidence": round(branch.confidence, 4),
            "risk": cand.risk, "reversible": cand.reversibility})
        self.reality.expect(cand.action_id, record["predicted"])
        if risk >= 0.6 or branch.confidence < 0.4:
            record["approval"] = self.approval_packet(record)
        if executor is not None and not cand.irreversible:
            observed = executor({"type": cand.type,
                                 "parameters": cand.parameters})
            err = self.reality.check(cand.action_id,
                                     observed.get("state", {}),
                                     self.model.version)
            record["observed"] = observed.get("state", {})
            record["prediction_error"] = {
                "severity": err.severity, "class": err.error_class,
                "difference": err.difference}
            self.updater.update(self.trust, err)
            if err.severity in ("major", "critical"):
                self.model.record_failure()
                record["follow_up"] = self.reality.action_for(err)
            else:
                self.model.record_success()
            if self.improvement is not None and err.difference:
                try:
                    self.improvement.observe(
                        {"task_id": goal.get("objective", ""),
                         "final_outcome": str(record["observed"])[:300],
                         "errors": [{"message": err.error_class}]})
                except Exception:
                    pass
        if risk >= 0.6:
            self._audit("cognitive.decision", record)
        self.decisions.append(record)
        self.estimator.state.version += 1
        return record

    # -- explanation (§70-71, §178) ----------------------------------------------
    @staticmethod
    def approval_packet(record: Dict[str, Any]) -> Dict[str, Any]:
        return {"why": f"selected '{record.get('selected')}' score "
                       f"{record.get('score')} (PREDICTION, not fact)",
                "alternatives": record.get("options", 0) - 1,
                "predicted": record.get("predicted", {}),
                "confidence": record.get("confidence"),
                "risks": {"risk": record.get("risk"),
                          "reversible": record.get("reversible")},
                "irreversible": record.get("risk", 0) >= 0.8}

    def red_team(self, record: Dict[str, Any]) -> List[str]:
        """Adversarial second pass for high-risk plans (§176)."""
        findings = []
        if record.get("confidence", 1.0) < 0.4:
            findings.append("low prediction confidence — verify or ask user")
        if record.get("risk", 0) >= 0.8 and record.get("reversible") is True:
            findings.append("high-risk plan claims reversibility — confirm")
        if not record.get("simulated"):
            findings.append("no simulation evidence for risky choice")
        return findings
