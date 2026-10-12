"""Graders (§57-60, §199) + evaluation engine (Phase B, §12-17, §61-62).

Grader ensemble: hard gates (security/unauthorized/missing artifact/
tests/state) fail deterministically and NO soft score may override them
(§59). ModelGrader is an honest seam: without a live provider it reports
STATUS NOT AVAILABLE instead of fake scores (§0.1, §0.3).
"""

from __future__ import annotations

import ast
import hashlib
import json
import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .models import EvalTask, TrialResult


class GraderUnavailable(Exception):
    pass


@dataclass
class GraderVerdict:
    grader_id: str
    version: str
    passed: bool
    score: float = 0.0
    weight: float = 1.0
    confidence: float = 1.0
    evidence: str = ""
    hard_gate: bool = False


class Grader:
    grader_id = "base"
    version = "v1"

    def grade(self, task: EvalTask, outcome: Any,
              ctx: Dict[str, Any]) -> GraderVerdict:
        raise NotImplementedError


class DeterministicGrader(Grader):
    """Exact/contains/numeric comparison from success_criteria."""
    grader_id = "deterministic"

    def grade(self, task: EvalTask, outcome: Any,
              ctx: Dict[str, Any]) -> GraderVerdict:
        crit = task.success_criteria or {}
        expected = crit.get("equals", task.expected_outcome)
        mode = crit.get("mode", "equals")
        if mode == "equals":
            ok = outcome == expected
        elif mode == "contains":
            ok = str(expected) in str(outcome)
        elif mode == "numeric_close":
            try:
                ok = abs(float(outcome) - float(expected)) <= float(
                    crit.get("tolerance", 1e-6))
            except Exception:
                ok = False
        else:
            ok = outcome == expected
        return GraderVerdict(self.grader_id, self.version, ok,
                             1.0 if ok else 0.0,
                             evidence=f"mode={mode}")


class OutcomeGrader(Grader):
    """Verifies final environment state (files/keys) — outcome-based."""
    grader_id = "outcome"

    def grade(self, task: EvalTask, outcome: Any,
              ctx: Dict[str, Any]) -> GraderVerdict:
        crit = task.success_criteria or {}
        state = ctx.get("final_state", {}) or {}
        required = crit.get("final_state", {})
        missing = [k for k, v in required.items() if state.get(k) != v]
        ok = not missing
        hard = bool(task.failure_criteria and
                    "missing required artifact" in task.failure_criteria)
        return GraderVerdict(self.grader_id, self.version, ok,
                             1.0 if ok else 0.0,
                             evidence=f"missing={missing}", hard_gate=hard)


class StaticAnalysisGrader(Grader):
    """Parses candidate Python for syntax + banned patterns (real check)."""
    grader_id = "static_analysis"
    BANNED = ("os.system(", "subprocess.call(", "__import__('os').system",)

    def grade(self, task: EvalTask, outcome: Any,
              ctx: Dict[str, Any]) -> GraderVerdict:
        code = str(outcome if isinstance(outcome, str)
                   else ctx.get("code", ""))
        try:
            ast.parse(code)
        except SyntaxError as exc:
            return GraderVerdict(self.grader_id, self.version, False,
                                 0.0, evidence=f"syntax: {exc}",
                                 hard_gate=True)
        bad = [b for b in self.BANNED if b in code]
        if bad and "no_shell" in (task.security_requirements or []):
            return GraderVerdict(self.grader_id, self.version, False, 0.0,
                                 evidence=f"banned={bad}", hard_gate=True)
        return GraderVerdict(self.grader_id, self.version, True, 1.0,
                             evidence="parse ok")


class ModelGrader(Grader):
    """LLM qualitative feedback seam. No provider → NOT AVAILABLE (§0.3)."""
    grader_id = "model"

    def __init__(self, judge_fn: Optional[Callable] = None):
        self._judge = judge_fn

    def grade(self, task: EvalTask, outcome: Any,
              ctx: Dict[str, Any]) -> GraderVerdict:
        if self._judge is None:
            raise GraderUnavailable(
                "STATUS: NOT AVAILABLE — no judge provider configured; "
                "model grading skipped, deterministic gates decide.")
        return self._judge(task, outcome, ctx)


class HumanGrader(Grader):
    grader_id = "human"

    def grade(self, task: EvalTask, outcome: Any,
              ctx: Dict[str, Any]) -> GraderVerdict:
        pending = ctx.get("human_verdict")
        if pending is None:
            return GraderVerdict(self.grader_id, self.version, False, 0.0,
                                 confidence=0.0,
                                 evidence="awaiting human review")
        return GraderVerdict(
            self.grader_id, self.version, bool(pending.get("passed")),
            float(pending.get("score", 0.0)),
            evidence=str(pending.get("note", "")))


GRADERS = {"deterministic": DeterministicGrader, "outcome": OutcomeGrader,
           "static_analysis": StaticAnalysisGrader, "model": ModelGrader,
           "human": HumanGrader}


def ensemble(task: EvalTask, outcome: Any,
             ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Hard gates first; soft scores never override them (§58-60)."""
    verdicts: List[GraderVerdict] = []
    for gid in task.graders or ["deterministic"]:
        g = GRADERS[gid]() if gid != "model" else ModelGrader()
        try:
            verdicts.append(g.grade(task, outcome, ctx))
        except GraderUnavailable as exc:
            verdicts.append(GraderVerdict(gid, "v1", True, 0.0, weight=0.0,
                                          confidence=0.0,
                                          evidence=str(exc)))
    hard_failed = [v.grader_id for v in verdicts
                   if v.hard_gate and not v.passed]
    scored = [v for v in verdicts if v.weight > 0]
    soft = (sum(v.score * v.weight for v in scored) /
            sum(v.weight for v in scored)) if scored else 0.0
    passed = not hard_failed and all(v.passed for v in verdicts
                                     if v.confidence > 0 or v.hard_gate)
    # abstentions (weight 0) don't block; real failures do.
    real = [v for v in verdicts if v.weight > 0 and v.confidence > 0]
    if real:
        passed = not hard_failed and all(v.passed for v in real)
    return {"passed": passed, "soft_score": round(soft, 4),
            "hard_gate_failed": hard_failed,
            "verdicts": [v.__dict__ for v in verdicts]}


# ---------------------------------------------------------------------------
# Datasets + engine
# ---------------------------------------------------------------------------

class EvalDataset:
    def __init__(self, name: str, kind: str = "capability",
                 version: str = "v1"):
        self.name = name
        self.kind = kind
        self.version = version
        self.tasks: List[EvalTask] = []

    def add(self, task: EvalTask) -> None:
        task.dataset = f"{self.name}@{self.version}"
        self.tasks.append(task)

    def fingerprint(self) -> str:
        blob = json.dumps([t.__dict__ for t in self.tasks], sort_keys=True,
                          default=str)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    def health(self) -> Dict[str, Any]:
        return {"tasks": len(self.tasks), "golden": sum(
            1 for t in self.tasks if t.golden),
            "holdout": sum(1 for t in self.tasks if t.holdout)}


class EvaluationEngine:
    """Runs real local task executors across trials (§12, §148)."""

    def __init__(self):
        self.datasets: Dict[str, EvalDataset] = {}
        self.trials: List[TrialResult] = []

    def register_dataset(self, ds: EvalDataset) -> None:
        self.datasets[f"{ds.name}@{ds.version}"] = ds

    def run_task(self, task: EvalTask,
                 executor: Callable[[Dict[str, Any], Dict[str, Any]],
                                    Dict[str, Any]],
                 config: Optional[Dict[str, Any]] = None,
                 trials: int = 1, seed: int = 0) -> List[TrialResult]:
        out: List[TrialResult] = []
        for i in range(trials):
            t0 = time.perf_counter()
            ctx: Dict[str, Any] = {"seed": seed + i,
                                   "config": config or {}}
            try:
                res = executor(dict(task.inputs), dict(config or {}))
                outcome = res.get("outcome")
                ctx.update(res.get("context", {}))
                status = "done"
            except Exception as exc:
                outcome, status = None, f"error: {type(exc).__name__}"
                ctx["error"] = str(exc)[:500]
            ens = ensemble(task, outcome, ctx)
            r = TrialResult(
                trial_id=f"{task.id}-t{i}-s{seed + i}", task_id=task.id,
                configuration=json.dumps(config or {}, sort_keys=True),
                seed=seed + i, outcome=outcome,
                grader_results=ens, passed=ens["passed"],
                hard_gate_failed=",".join(ens["hard_gate_failed"]),
                latency_ms=(time.perf_counter() - t0) * 1000,
                tokens=int(ctx.get("tokens", 0)),
                tool_calls=int(ctx.get("tool_calls", 0)), status=status)
            self.trials.append(r)
            out.append(r)
        return out

    @staticmethod
    def aggregate(results: List[TrialResult]) -> Dict[str, Any]:
        n = len(results)
        passed = sum(1 for r in results if r.passed)
        lat = [r.latency_ms for r in results]
        return {"trials": n, "passed": passed,
                "success_rate": passed / n if n else 0.0,
                "mean_latency_ms": round(statistics.mean(lat), 2) if lat
                else 0.0,
                "p95_latency_ms": round(sorted(lat)[max(
                    0, int(len(lat) * 0.95) - 1)], 2) if lat else 0.0,
                "total_tokens": sum(r.tokens for r in results),
                "hard_gate_failures": sum(
                    1 for r in results if r.hard_gate_failed)}

    def contamination_check(self, task: EvalTask,
                            optimized_examples: List[str]) -> Dict[str, Any]:
        """Flag eval inputs reused as optimization examples (§84)."""
        blob = json.dumps(task.inputs, sort_keys=True)
        hits = [e for e in optimized_examples if e and e in blob]
        return {"contaminated": bool(hits), "hits": len(hits)}
