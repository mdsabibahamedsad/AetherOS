"""Benchmark runner CLI and orchestration."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .measure import BenchmarkHarness, EnvironmentInfo, run_benchmark
from .storage import BaselineStore, RegressionDetector, ResultStore


class BenchmarkRegistry:
    """Registry for benchmark harnesses."""

    def __init__(self):
        self._harnesses: Dict[str, Callable[[], BenchmarkHarness]] = {}
        self._categories: Dict[str, List[str]] = {}

    def register(self, category: str, benchmark_id: str, factory: Callable[[], BenchmarkHarness]):
        key = f"{category}/{benchmark_id}"
        self._harnesses[key] = factory
        self._categories.setdefault(category, []).append(benchmark_id)

    def get(self, category: str, benchmark_id: str) -> Optional[BenchmarkHarness]:
        key = f"{category}/{benchmark_id}"
        factory = self._harnesses.get(key)
        return factory() if factory else None

    def list_category(self, category: str) -> List[str]:
        return self._categories.get(category, [])

    def list_all(self) -> Dict[str, List[str]]:
        return dict(self._categories)

    def run_category(self, category: str, environment: Optional[EnvironmentInfo] = None) -> List[Any]:
        results = []
        for bench_id in self.list_category(category):
            harness = self.get(category, bench_id)
            if harness:
                harness.environment = environment or EnvironmentInfo()
                results.append(run_benchmark(harness))
        return results

    def run_all(self, environment: Optional[EnvironmentInfo] = None) -> List[Any]:
        results = []
        for category in self._categories:
            results.extend(self.run_category(category, environment))
        return results


REGISTRY = BenchmarkRegistry()


def register_benchmark(category: str, benchmark_id: str):
    """Decorator to register a benchmark harness factory."""
    def decorator(factory: Callable[[], BenchmarkHarness]):
        REGISTRY.register(category, benchmark_id, factory)
        return factory
    return decorator


def build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AetherOS Performance Benchmarks (Master 71)")
    sub = parser.add_subparsers(dest="command", required=True)

    # list command
    list_p = sub.add_parser("list", help="List available benchmarks")
    list_p.add_argument("--category", help="Filter by category")

    # run command
    run_p = sub.add_parser("run", help="Run benchmarks")
    run_p.add_argument("--category", help="Run all benchmarks in category")
    run_p.add_argument("--benchmark", help="Run specific benchmark (category/id)")
    run_p.add_argument("--all", action="store_true", help="Run all benchmarks")
    run_p.add_argument("--iterations", type=int, default=10, help="Measurement iterations")
    run_p.add_argument("--warmup", type=int, default=3, help="Warmup iterations")
    run_p.add_argument("--results-dir", default="benchmark_results", help="Results directory")
    run_p.add_argument("--baseline-dir", default="benchmarks/baselines", help="Baselines directory")
    run_p.add_argument("--save-baseline", action="store_true", help="Save as baseline")
    run_p.add_argument("--baseline-name", default="default", help="Baseline name")

    # compare command
    cmp_p = sub.add_parser("compare", help="Compare results with baselines")
    cmp_p.add_argument("--results-dir", default="benchmark_results", help="Results directory")
    cmp_p.add_argument("--baseline-dir", default="benchmarks/baselines", help="Baselines directory")
    cmp_p.add_argument("--run-id", help="Specific run ID to compare")
    cmp_p.add_argument("--thresholds", help="JSON file with per-benchmark thresholds")

    # report command
    rep_p = sub.add_parser("report", help="Generate performance report")
    rep_p.add_argument("--results-dir", default="benchmark_results", help="Results directory")
    rep_p.add_argument("--output", help="Output file (default: stdout)")

    # baseline command
    base_p = sub.add_parser("baseline", help="Manage baselines")
    base_p.add_argument("--list", action="store_true", help="List baselines")
    base_p.add_argument("--set", help="Set current run as baseline (run_id)")
    base_p.add_argument("--results-dir", default="benchmark_results")
    base_p.add_argument("--baseline-dir", default="benchmarks/baselines")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_cli()
    args = parser.parse_args(argv)

    env = EnvironmentInfo()
    print(f"Environment: {env.os}, CPU: {env.cpu}, RAM: {env.ram_gb}GB")
    print(f"Environment fingerprint: {env.fingerprint()}")

    if args.command == "list":
        if args.category:
            benchmarks = REGISTRY.list_category(args.category)
            print(f"Category '{args.category}': {benchmarks}")
        else:
            for cat, benches in REGISTRY.list_all().items():
                print(f"\n{cat}:")
                for b in benches:
                    print(f"  {b}")
        return 0

    elif args.command == "run":
        results_dir = Path(args.results_dir)
        results_dir.mkdir(parents=True, exist_ok=True)
        result_store = ResultStore(results_dir)

        if args.benchmark:
            category, bench_id = args.benchmark.split("/", 1)
            harness = REGISTRY.get(category, bench_id)
            if not harness:
                print(f"Benchmark not found: {args.benchmark}")
                return 1
            harness.environment = env
            harness.measurement_iterations = args.iterations
            harness.warmup_iterations = args.warmup
            result = run_benchmark(harness)
            print(result.to_json())
            run_dir = result_store.save_run([result])
            print(f"Saved to: {run_dir}")
            if args.save_baseline:
                baseline_store = BaselineStore(args.baseline_dir)
                baseline_store.save_baseline(result, args.baseline_name)
                print(f"Saved as baseline: {args.baseline_name}")

        elif args.category:
            harnesses = []
            for bench_id in REGISTRY.list_category(args.category):
                h = REGISTRY.get(args.category, bench_id)
                if h:
                    h.environment = env
                    h.measurement_iterations = args.iterations
                    h.warmup_iterations = args.warmup
                    harnesses.append(h)
            results = [run_benchmark(h) for h in harnesses]
            for r in results:
                print(r.to_json())
            run_dir = result_store.save_run(results)
            print(f"Saved to: {run_dir}")
            if args.save_baseline:
                baseline_store = BaselineStore(args.baseline_dir)
                for r in results:
                    baseline_store.save_baseline(r, args.baseline_name)

        elif args.all:
            harnesses = []
            for category in REGISTRY.list_all():
                for bench_id in REGISTRY.list_category(category):
                    h = REGISTRY.get(category, bench_id)
                    if h:
                        h.environment = env
                        h.measurement_iterations = args.iterations
                        h.warmup_iterations = args.warmup
                        harnesses.append(h)
            results = [run_benchmark(h) for h in harnesses]
            for r in results:
                print(r.to_json())
            run_dir = result_store.save_run(results)
            print(f"Saved to: {run_dir}")
            if args.save_baseline:
                baseline_store = BaselineStore(args.baseline_dir)
                for r in results:
                    baseline_store.save_baseline(r, args.baseline_name)
        else:
            print("Specify --benchmark, --category, or --all")
            return 1

        return 0

    elif args.command == "compare":
        results_dir = Path(args.results_dir)
        baseline_dir = Path(args.baseline_dir)
        result_store = ResultStore(results_dir)
        baseline_store = BaselineStore(baseline_dir)

        thresholds = {}
        if args.thresholds:
            thresholds = json.loads(Path(args.thresholds).read_text())

        if args.run_id:
            results = result_store.load_run(args.run_id)
        else:
            results = result_store.load_all_results()

        if not results:
            print("No results to compare")
            return 1

        detector = RegressionDetector(baseline_store, result_store)
        check = detector.check_regressions(results, thresholds)
        print(json.dumps(check, indent=2, default=str))

        # Print human-readable report
        print("\n" + detector.generate_regression_report(results))
        return 0

    elif args.command == "report":
        results_dir = Path(args.results_dir)
        result_store = ResultStore(results_dir)
        results = result_store.load_all_results()

        if not results:
            print("No results to report")
            return 1

        # Group by category
        by_category: Dict[str, List[Any]] = {}
        for r in results:
            by_category.setdefault(r.category, []).append(r)

        lines = [
            "# AetherOS Performance Benchmark Report",
            f"Generated: {time.ctime()}",
            f"Total benchmarks: {len(results)}",
            "",
        ]

        for cat in sorted(by_category.keys()):
            lines.append(f"## {cat}")
            for r in sorted(by_category[cat], key=lambda x: x.benchmark_id):
                lines.append(f"\n### {r.name} ({r.benchmark_id})")
                lines.append(f"Status: {r.status}")
                lines.append(f"Iterations: {r.iterations} (warmup: {r.warmup_iterations})")
                for metric, value in sorted(r.metrics.items()):
                    unit = r.units.get(metric, "")
                    lines.append(f"- {metric}: {value:.3f} {unit}")
            lines.append("")

        report = "\n".join(lines)
        if args.output:
            Path(args.output).write_text(report)
            print(f"Report written to {args.output}")
        else:
            print(report)
        return 0

    elif args.command == "baseline":
        baseline_store = BaselineStore(args.baseline_dir)
        result_store = ResultStore(args.results_dir)

        if args.list:
            for bid, name in baseline_store.list_baselines():
                print(f"{bid}: {name}")
            return 0

        if args.set:
            results = result_store.load_run(args.set)
            if not results:
                print(f"No results for run: {args.set}")
                return 1
            for r in results:
                baseline_store.save_baseline(r, "default")
                print(f"Set baseline for {r.benchmark_id}")
            return 0

        print("Use --list or --set <run_id>")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())