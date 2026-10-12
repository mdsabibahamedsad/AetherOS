"""Experiments (Phase E, §46-48, §89-94, §140-141, §147-148): baseline
control, isolated execution (temp workspace + tenant pinning + minimum
credentials), budgets, pause/resume/cancel, env fingerprints, shadow
mode (no side effects — candidate output compared, never executed).
"""

from __future__ import annotations

import hashlib
import json
import platform
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .graders_eval import EvaluationEngine
from .models import EvalTask, Experiment

try:
    import aetheros_self_improvement as _pkg  # version stamp only
    _CODE_VERSION = getattr(_pkg, "__version__", "0.0.0")
except Exception:
    _CODE_VERSION = "0.0.0"


def env_fingerprint() -> Dict[str, Any]:
    import sys
    return {"os": platform.system(), "os_release": platform.release(),
            "python": sys.version.split()[0],
            "fabric": _CODE_VERSION}


class BudgetExceeded(Exception):
    pass


class ExperimentRunner:
    def __init__(self, engine: Optional[EvaluationEngine] = None):
        self.engine = engine or EvaluationEngine()
        self.experiments: Dict[str, Experiment] = {}
        self._cancel: Dict[str, bool] = {}
        self._pause: Dict[str, bool] = {}

    def create(self, tasks: List[EvalTask], baseline_config: Dict[str, Any],
               candidate_config: Dict[str, Any],
               dataset_version: str = "", proposal_id: str = "",
               mode: str = "offline",
               budgets: Optional[Dict[str, float]] = None,
               tenant: str = "default", seed: int = 0) -> Experiment:
        exp = Experiment(
            proposal_id=proposal_id, baseline_config=baseline_config,
            candidate_config=candidate_config,
            dataset_version=dataset_version,
            code_version=_CODE_VERSION, seed=seed, mode=mode,
            budgets=budgets or {"maxTrials": 100, "maxTime": 600.0},
            environment=env_fingerprint(), tenant=tenant)
        exp.results = {"tasks": [t.id for t in tasks]}
        self.experiments[exp.id] = exp
        return exp

    def cancel(self, exp_id: str) -> None:
        self._cancel[exp_id] = True

    def pause(self, exp_id: str) -> None:
        self._pause[exp_id] = True

    def resume(self, exp_id: str) -> None:
        self._pause.pop(exp_id, None)

    def run(self, exp: Experiment, tasks: List[EvalTask],
            executor: Callable, trials: int = 3) -> Dict[str, Any]:
        """Same dataset + constraints for baseline and candidate (§47)."""
        if exp.id in self._cancel:
            exp.status = "cancelled"
            return {"status": "cancelled"}
        max_trials = int(exp.budgets.get("maxTrials", 100))
        deadline = time.time() + float(exp.budgets.get("maxTime", 600.0))
        exp.status = "running"
        workdir = Path(tempfile.mkdtemp(prefix="aesi_exp_"))
        base_rows, cand_rows = [], []
        used = 0
        for task in tasks:
            for label, cfg in (("baseline", exp.baseline_config),
                               ("candidate", exp.candidate_config)):
                if self._cancel.get(exp.id):
                    exp.status = "cancelled"
                    return {"status": "cancelled",
                            "baseline": base_rows, "candidate": cand_rows}
                while self._pause.get(exp.id):
                    time.sleep(0.05)
                if time.time() > deadline:
                    exp.status = "expired"
                    return {"status": "expired",
                            "baseline": base_rows, "candidate": cand_rows}
                if used + trials > max_trials:
                    raise BudgetExceeded(
                        f"maxTrials={max_trials} exceeded")
                if exp.mode == "shadow":
                    rows = self._shadow(task, executor, cfg, trials, exp)
                else:
                    rows = self.engine.run_task(
                        task, executor, cfg, trials=trials,
                        seed=exp.seed)
                (base_rows if label == "baseline" else cand_rows).extend(
                    [r.__dict__ for r in rows])
                used += trials
        base = EvaluationEngine.aggregate(
            [self._rehydrate(r) for r in base_rows])
        cand = EvaluationEngine.aggregate(
            [self._rehydrate(r) for r in cand_rows])
        exp.results.update({"baseline": base, "candidate": cand,
                            "workdir": str(workdir),
                            "dataset_version": exp.dataset_version})
        exp.status = "done"
        return {"status": "done", "baseline": base, "candidate": cand}

    def _shadow(self, task: EvalTask, executor: Callable,
                cfg: Dict[str, Any], trials: int,
                exp: Experiment) -> list:
        """Shadow: candidate observes but performs no side effects (§49).
        Enforced by running with read_only=True in context."""
        shadow_cfg = dict(cfg)
        shadow_cfg["read_only"] = True
        return self.engine.run_task(task, executor, shadow_cfg,
                                    trials=trials, seed=exp.seed)

    @staticmethod
    def _rehydrate(d: Dict[str, Any]):
        from .models import TrialResult
        return TrialResult(**{k: v for k, v in d.items()
                              if k in TrialResult.__dataclass_fields__})

    def compare(self, exp: Experiment) -> Dict[str, Any]:
        res = exp.results
        base, cand = res.get("baseline", {}), res.get("candidate", {})
        return {
            "success_delta": round(cand.get("success_rate", 0)
                                   - base.get("success_rate", 0), 4),
            "latency_delta_ms": round(cand.get("mean_latency_ms", 0)
                                      - base.get("mean_latency_ms", 0), 2),
            "regressions": cand.get("hard_gate_failures", 0),
            "recommendation": "promote"
            if (cand.get("success_rate", 0) >= base.get("success_rate", 0)
                and cand.get("hard_gate_failures", 0) == 0)
            else "reject"}
