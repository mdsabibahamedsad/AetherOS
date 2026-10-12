"""Baseline store + benchmark engine (P3, P13, P45-47, P90-91).

Anti-fabrication (P17-19): the engine only reports metrics produced by
checks that actually executed; an EvaluationRun that did not complete cannot
be published, and fabricated result injection is refused at the API boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from agent.quality.models import (
    Baseline,
    Candidate,
    EvaluationRun,
    MetricResult,
    RunStatus,
)


# ---------------------------------------------------------------- P3/P45

class BaselineStore:
    """Persistent baselines under ``<AETHEROS_HOME>/quality/baselines.json``."""

    def __init__(self, persist_path: Optional[str] = None):
        if persist_path:
            self.path = Path(persist_path)
        else:
            from aetheros_constants import get_aetheros_home

            d = get_aetheros_home() / "quality"
            d.mkdir(parents=True, exist_ok=True)
            self.path = d / "baselines.json"
        self._baselines: Dict[str, Baseline] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            for bid, b in raw.items():
                self._baselines[bid] = Baseline(
                    baseline_id=b["baseline_id"], label=b["label"],
                    version=b["version"], metrics=b.get("metrics", {}),
                    created_at=b.get("created_at", 0.0),
                    metadata=b.get("metadata", {}),
                )
        except (json.JSONDecodeError, OSError, KeyError):
            self._baselines = {}

    def _save(self) -> None:
        payload = {b.baseline_id: {
            "baseline_id": b.baseline_id, "label": b.label,
            "version": b.version, "metrics": b.metrics,
            "created_at": b.created_at, "metadata": b.metadata,
        } for b in self._baselines.values()}
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, sort_keys=True)
            os.replace(tmp, self.path)
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def record(self, baseline: Baseline) -> Baseline:
        self._baselines[baseline.baseline_id] = baseline
        self._save()
        return baseline

    def latest(self, label: str = "") -> Optional[Baseline]:
        latest = None
        for b in self._baselines.values():
            if label and b.label != label:
                continue
            # ">=" so equal timestamps resolve to the LAST recorded baseline
            if latest is None or b.created_at >= latest.created_at:
                latest = b
        return latest

    def all(self) -> List[Baseline]:
        return sorted(self._baselines.values(), key=lambda b: b.created_at)


# ---------------------------------------------------------------- P46-47

@dataclass
class ComparisonPolicy:
    """P47 — explicit, configurable degradation thresholds (never universal
    hard-coded values). Metrics in ``block_on_regression`` BLOCK release when
    the candidate degrades beyond ``max_regression_pct``."""

    max_regression_pct: float = 10.0
    block_on_regression: frozenset = frozenset({
        "task_success_rate", "verified_success_rate", "availability",
        "p95_latency_ms",
    })
    higher_is_better: frozenset = frozenset({
        "task_success_rate", "verified_success_rate", "availability",
        "throughput", "recovery_score",
    })


def _matches_policy(name: str, policy_set: frozenset) -> bool:
    """Engine-registered checks namespace their metrics
    (``<check>.<metric>``); policy names match on the dotted suffix too."""
    return name in policy_set or name.rsplit(".", 1)[-1] in policy_set


def compare_to_baseline(
    baseline: Baseline,
    candidate_metrics: Dict[str, float],
    policy: Optional[ComparisonPolicy] = None,
) -> Tuple[List[MetricResult], bool]:
    """P46-47 — compute deltas and the release-blocking verdict."""
    policy = policy or ComparisonPolicy()
    results: List[MetricResult] = []
    blocked = False
    for name, value in candidate_metrics.items():
        base = baseline.metrics.get(name)
        if base is None or base == 0:
            results.append(MetricResult(name=name, value=value,
                                        baseline_value=base,
                                        direction="new"))
            continue
        delta = value - base
        if _matches_policy(name, policy.higher_is_better):
            pct = (delta / base) * 100.0
            regressed = pct < -policy.max_regression_pct
        else:  # lower is better (e.g. latency)
            pct = ((base - value) / base) * 100.0
            regressed = pct < -policy.max_regression_pct
        direction = ("improved" if pct > 0.5 else
                     "regressed" if pct < -0.5 else "unchanged")
        is_block = regressed and _matches_policy(
            name, policy.block_on_regression)
        if is_block:
            blocked = True
        results.append(MetricResult(
            name=name, value=value, baseline_value=base,
            delta=round(delta, 4), direction=direction,
            threshold=policy.max_regression_pct, blocked=is_block,
        ))
    return results, blocked


# ---------------------------------------------------------------- P13/P90-91

CheckFn = Callable[[], Dict[str, float]]


@dataclass
class BenchmarkCheck:
    name: str
    category: str                   # functional|performance|security|reliability|quality
    domains: frozenset              # research|memory|computer_use|multi_agent|mcp|tools|agents
    fn: CheckFn
    critical: bool = False


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def reproducibility_metadata() -> Dict[str, str]:
    """P90 — every benchmark run records its full environment identity."""
    return {
        "code_commit": _git_commit(),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "timestamp": str(time.time()),
    }


def artifact_hash(payload: Any) -> str:
    """P91 — content hash for stored evaluation artifacts."""
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


class BenchmarkEngine:
    """Registry + runner. ``run`` executes every selected check for real and
    produces a COMPLETED EvaluationRun; failures land in run.failures."""

    def __init__(self):
        self._checks: Dict[str, BenchmarkCheck] = {}

    def register(self, check: BenchmarkCheck) -> None:
        self._checks[check.name] = check

    def checks(self, category: str = "", domain: str = "") -> List[BenchmarkCheck]:
        return [c for c in self._checks.values()
                if (not category or c.category == category)
                and (not domain or domain in c.domains)]

    def run(
        self,
        *,
        target: str,
        version: str,
        environment: str = "local",
        dataset: str = "default",
        category: str = "",
        domain: str = "",
        baseline: Optional[Baseline] = None,
        candidate: Optional[Candidate] = None,
        policy: Optional[ComparisonPolicy] = None,
    ) -> EvaluationRun:
        selected = self.checks(category=category, domain=domain)
        run = EvaluationRun(
            target=target, version=version, environment=environment,
            dataset=dataset, status=RunStatus.RUNNING,
            baseline_id=baseline.baseline_id if baseline else "",
            candidate_id=candidate.candidate_id if candidate else "",
            **reproducibility_metadata(),
        )
        metrics: Dict[str, float] = {}
        for check in selected:
            try:
                produced = check.fn()
                if not isinstance(produced, dict):
                    raise TypeError("check returned non-dict metrics")
                for k, v in produced.items():
                    metrics[f"{check.name}.{k}" if not k.startswith(check.name)
                            else k] = float(v)
            except Exception as exc:
                run.failures.append(
                    f"{check.name}: {type(exc).__name__}: {exc}")
                if check.critical:
                    run.warnings.append(
                        f"critical check failed: {check.name}")

        run.metrics = [
            MetricResult(name=k, value=v) for k, v in sorted(metrics.items())
        ]
        run.results = {"raw": metrics,
                       "artifact_hash": artifact_hash(metrics)}
        if baseline is not None and metrics:
            compared, blocked = compare_to_baseline(baseline, metrics, policy)
            run.metrics = compared
            run.results["blocked"] = blocked
        run.status = RunStatus.COMPLETED
        return run

    @staticmethod
    def publish(run: EvaluationRun) -> Dict[str, Any]:
        """P17/P18 — refuse to publish runs that did not really execute."""
        if not run.executed():
            raise ValueError(
                "refusing to publish an EvaluationRun that did not complete "
                "(fabricated results are never reported)")
        return run.to_dict()
