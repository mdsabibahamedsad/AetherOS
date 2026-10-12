"""Benchmark result storage and comparison utilities."""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .measure import BenchmarkResult, EnvironmentInfo


class BaselineStore:
    """Manages baseline performance data for regression detection."""

    def __init__(self, baselines_dir: Union[str, Path]):
        self.baselines_dir = Path(baselines_dir)
        self.baselines_dir.mkdir(parents=True, exist_ok=True)

    def save_baseline(self, result: BenchmarkResult, name: str = "default") -> Path:
        """Save a benchmark result as a baseline."""
        baseline_file = self.baselines_dir / f"{result.benchmark_id}_{name}.json"
        data = result.to_dict()
        data["baseline_name"] = name
        data["saved_at"] = time.time()
        baseline_file.write_text(json.dumps(data, indent=2))
        return baseline_file

    def load_baseline(self, benchmark_id: str, name: str = "default") -> Optional[BenchmarkResult]:
        """Load a baseline by benchmark ID and name."""
        baseline_file = self.baselines_dir / f"{benchmark_id}_{name}.json"
        if not baseline_file.exists():
            return None
        data = json.loads(baseline_file.read_text())
        env_data = data.pop("environment", None)
        env = EnvironmentInfo.from_dict(env_data) if env_data else None
        return BenchmarkResult(environment=env, **{k: v for k, v in data.items() if k in BenchmarkResult.__annotations__})

    def list_baselines(self, benchmark_id: Optional[str] = None) -> List[Tuple[str, str]]:
        """List all baselines, optionally filtered by benchmark_id."""
        results = []
        for f in self.baselines_dir.glob("*.json"):
            if benchmark_id and not f.name.startswith(benchmark_id):
                continue
            parts = f.stem.split("_", 1)
            bid = parts[0]
            name = parts[1] if len(parts) > 1 else "default"
            results.append((bid, name))
        return sorted(results)

    def compare_with_baseline(
        self,
        current: BenchmarkResult,
        baseline_name: str = "default",
        thresholds: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Compare current result with baseline, return regression analysis."""
        baseline = self.load_baseline(current.benchmark_id, baseline_name)
        if not baseline:
            return {"status": "NO_BASELINE", "baseline_name": baseline_name}

        thresholds = thresholds or {}
        regressions = []
        improvements = []
        stable = []

        for metric_key in current.metrics:
            if metric_key not in baseline.metrics:
                continue
            cur_val = current.metrics[metric_key]
            base_val = baseline.metrics[metric_key]
            if base_val == 0:
                continue
            delta_pct = ((cur_val - base_val) / base_val) * 100
            threshold = thresholds.get(metric_key, 10.0)  # default 10% threshold

            if delta_pct > threshold:
                regressions.append({
                    "metric": metric_key,
                    "baseline": base_val,
                    "current": cur_val,
                    "delta_pct": round(delta_pct, 2),
                    "threshold_pct": threshold,
                })
            elif delta_pct < -threshold:
                improvements.append({
                    "metric": metric_key,
                    "baseline": base_val,
                    "current": cur_val,
                    "delta_pct": round(delta_pct, 2),
                    "threshold_pct": threshold,
                })
            else:
                stable.append({
                    "metric": metric_key,
                    "baseline": base_val,
                    "current": cur_val,
                    "delta_pct": round(delta_pct, 2),
                })

        return {
            "status": "REGRESSION" if regressions else "OK",
            "benchmark_id": current.benchmark_id,
            "baseline_name": baseline_name,
            "regressions": regressions,
            "improvements": improvements,
            "stable": stable,
            "environment_match": current.environment.fingerprint() == baseline.environment.fingerprint() if current.environment and baseline.environment else False,
        }


class ResultStore:
    """Stores and manages benchmark run results."""

    def __init__(self, results_dir: Union[str, Path]):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir = self.results_dir / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def save_run(self, results: List[BenchmarkResult], run_id: Optional[str] = None) -> Path:
        """Save a benchmark run (collection of results)."""
        run_id = run_id or f"run_{int(time.time())}_{os.urandom(4).hex()}"
        run_dir = self.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Save individual results
        for result in results:
            result_file = run_dir / f"{result.benchmark_id}.json"
            result_file.write_text(result.to_json())

        # Save manifest
        manifest = {
            "run_id": run_id,
            "timestamp": time.time(),
            "result_count": len(results),
            "benchmark_ids": [r.benchmark_id for r in results],
            "environment": results[0].environment.to_dict() if results and results[0].environment else None,
        }
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

        return run_dir

    def load_run(self, run_id: str) -> List[BenchmarkResult]:
        """Load all results from a run."""
        run_dir = self.runs_dir / run_id
        if not run_dir.exists():
            return []
        results = []
        for f in run_dir.glob("*.json"):
            if f.name == "manifest.json":
                continue
            data = json.loads(f.read_text())
            env_data = data.pop("environment", None)
            env = EnvironmentInfo.from_dict(env_data) if env_data else None
            results.append(BenchmarkResult(environment=env, **{k: v for k, v in data.items() if k in BenchmarkResult.__annotations__}))
        return results

    def list_runs(self) -> List[str]:
        return sorted([d.name for d in self.runs_dir.iterdir() if d.is_dir()])

    def load_all_results(self) -> List[BenchmarkResult]:
        """Load all results from all runs."""
        all_results = []
        for run_id in self.list_runs():
            all_results.extend(self.load_run(run_id))
        return all_results


class RegressionDetector:
    """Automated regression detection across benchmark runs."""

    def __init__(self, baseline_store: BaselineStore, result_store: ResultStore):
        self.baseline_store = baseline_store
        self.result_store = result_store

    def check_regressions(
        self,
        results: List[BenchmarkResult],
        thresholds: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> Dict[str, Any]:
        """Check a list of results against their baselines."""
        thresholds = thresholds or {}
        all_regressions = []
        all_improvements = []
        summary = {"total": len(results), "regressions": 0, "improvements": 0, "stable": 0, "no_baseline": 0}

        for result in results:
            bench_thresholds = thresholds.get(result.benchmark_id, {})
            comparison = self.baseline_store.compare_with_baseline(result, thresholds=bench_thresholds)

            if comparison["status"] == "NO_BASELINE":
                summary["no_baseline"] += 1
                continue

            if comparison["regressions"]:
                summary["regressions"] += 1
                all_regressions.append({
                    "benchmark_id": result.benchmark_id,
                    "benchmark_name": result.name,
                    "regressions": comparison["regressions"],
                })

            if comparison["improvements"]:
                summary["improvements"] += 1
                all_improvements.append({
                    "benchmark_id": result.benchmark_id,
                    "benchmark_name": result.name,
                    "improvements": comparison["improvements"],
                })

            if not comparison["regressions"] and not comparison["improvements"]:
                summary["stable"] += 1

        return {
            "summary": summary,
            "regressions": all_regressions,
            "improvements": all_improvements,
            "timestamp": time.time(),
        }

    def generate_regression_report(self, results: List[BenchmarkResult]) -> str:
        """Generate human-readable regression report."""
        check = self.check_regressions(results)
        lines = [
            "# Performance Regression Report",
            f"Generated: {time.ctime(check['timestamp'])}",
            f"Total benchmarks: {check['summary']['total']}",
            f"Regressions: {check['summary']['regressions']}",
            f"Improvements: {check['summary']['improvements']}",
            f"Stable: {check['summary']['stable']}",
            f"No baseline: {check['summary']['no_baseline']}",
            "",
        ]

        if check["regressions"]:
            lines.append("## ⚠️ REGRESSIONS DETECTED")
            for reg in check["regressions"]:
                lines.append(f"\n### {reg['benchmark_name']} ({reg['benchmark_id']})")
                for r in reg["regressions"]:
                    lines.append(f"- **{r['metric']}**: {r['baseline']:.2f} → {r['current']:.2f} ({r['delta_pct']:+.1f}%, threshold: {r['threshold_pct']}%)")

        if check["improvements"]:
            lines.append("\n## ✅ IMPROVEMENTS")
            for imp in check["improvements"]:
                lines.append(f"\n### {imp['benchmark_name']} ({imp['benchmark_id']})")
                for i in imp["improvements"]:
                    lines.append(f"- **{i['metric']}**: {i['baseline']:.2f} → {i['current']:.2f} ({i['delta_pct']:+.1f}%)")

        return "\n".join(lines)