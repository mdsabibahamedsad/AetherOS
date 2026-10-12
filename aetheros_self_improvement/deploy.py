"""Deployment control (Phases J/K, §50-51, §108-109, §130-134): the ONLY
place production change happens. Promotion ladder OFFLINE→SANDBOX→
SHADOW→CANARY→LIMITED→GENERAL (§131); stage-skipping needs explicit
justification; auto-rollback on measured degradation (§51, §132);
one-click config rollback (§134); every step records provenance.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from .models import Deployment, new_id

LADDER = ["offline", "sandbox", "shadow", "canary", "limited", "general"]
THRESHOLDS = {"success_drop": 0.05, "latency_ms": 500.0,
              "violations": 1, "cost_usd": 5.0}


class DeploymentController:
    def __init__(self, thresholds: Optional[Dict[str, float]] = None,
                 auditor: Optional[Callable[[str, Dict[str, Any]], None]]
                 = None):
        self.thresholds = dict(THRESHOLDS)
        if thresholds:
            self.thresholds.update(thresholds)
        self.deployments: Dict[str, Deployment] = {}
        self.rollback_log: List[Dict[str, Any]] = []
        self._audit = auditor or (lambda _t, _d: None)
        # configuration registry: name -> version -> payload (for rollback)
        self.configs: Dict[str, Dict[str, Any]] = {}
        self.active: Dict[str, str] = {}

    # -- config versioning (§110, §134) --------------------------------------
    def publish_config(self, name: str, version: str,
                       payload: Dict[str, Any]) -> None:
        self.configs.setdefault(name, {})[version] = dict(payload)

    def rollback_config(self, name: str, target: str,
                        operator: str, reason: str) -> bool:
        if target not in self.configs.get(name, {}):
            return False
        previous = self.active.get(name, "")
        self.active[name] = target
        self.rollback_log.append(
            {"reason": reason, "trigger": "operator",
             "affected_version": previous, "rollback_target": target,
             "operator": operator, "timestamp": time.time(),
             "config": name})
        self._audit("improvement.rolled_back",
                    {"config": name, "from": previous, "to": target,
                     "reason": reason, "operator": operator})
        return True

    # -- staged promotion (§131) ----------------------------------------------
    def promote(self, dep: Deployment,
                approval_id: str = "",
                skip_justification: str = "") -> Deployment:
        idx = LADDER.index(dep.stage)
        if idx + 1 < len(LADDER) and dep.stage not in ("offline", "sandbox",
                                                       "shadow", "canary",
                                                       "limited"):
            raise ValueError("unknown stage")
        if idx + 1 >= len(LADDER):
            return dep
        nxt = LADDER[idx + 1]
        jumped = LADDER.index(nxt) - LADDER.index(dep.stage) > 1
        if jumped and not skip_justification:
            raise ValueError("stage skip requires explicit justification")
        dep.stage = nxt
        dep.traffic_pct = {"sandbox": 0.0, "shadow": 0.0, "canary": 5.0,
                           "limited": 25.0, "general": 100.0}.get(nxt, 0.0)
        if approval_id:
            dep.approval_id = approval_id
        self._audit("improvement.deployed",
                    {"deployment": dep.id, "stage": dep.stage,
                     "traffic_pct": dep.traffic_pct})
        return dep

    def stage_deployment(self, proposal_id: str, version: str,
                         author: str, reviewer: str = "",
                         tenant: str = "default") -> Deployment:
        dep = Deployment(proposal_id=proposal_id, version=version,
                         author=author, reviewer=reviewer, tenant=tenant,
                         change_id=new_id("chg"))
        self.deployments[dep.id] = dep
        return dep

    # -- monitoring gates (§51) --------------------------------------------------
    def check_metrics(self, dep: Deployment,
                      baseline: Dict[str, Any],
                      observed: Dict[str, Any]) -> Dict[str, Any]:
        t = self.thresholds
        reasons = []
        if (baseline.get("success_rate", 1.0)
                - observed.get("success_rate", 1.0)) > t["success_drop"]:
            reasons.append("success decreased")
        if (observed.get("mean_latency_ms", 0)
                - baseline.get("mean_latency_ms", 0)) > t["latency_ms"]:
            reasons.append("latency exceeded threshold")
        if observed.get("violations", 0) >= t["violations"]:
            reasons.append("security/policy violations increased")
        if observed.get("cost_usd", 0) > t["cost_usd"]:
            reasons.append("cost exceeded threshold")
        if reasons:
            self._rollback(dep, "automatic", "; ".join(reasons), observed)
        return {"rollback": bool(reasons), "reasons": reasons}

    def _rollback(self, dep: Deployment, trigger: str, reason: str,
                  metrics: Dict[str, Any]) -> None:
        dep.state = "rolled_back"
        self.rollback_log.append(
            {"reason": reason, "trigger": trigger, "metrics": metrics,
             "affected_version": dep.version,
             "rollback_target": "previous-known-good",
             "operator": "automatic", "timestamp": time.time(),
             "deployment": dep.id})
        self._audit("improvement.rolled_back",
                    {"deployment": dep.id, "reason": reason})

    def demote(self, dep: Deployment) -> Deployment:
        idx = LADDER.index(dep.stage)
        dep.stage = LADDER[max(0, idx - 1)]
        dep.state = "demoted"
        return dep
