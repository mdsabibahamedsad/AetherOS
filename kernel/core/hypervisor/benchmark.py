"""
AetherOS Agent Hypervisor 1.0 — capsule benchmark suite (§109-§110).

Real measurements only (time.perf_counter). Reports p50/p95/p99. Never
invented. Isolation "escape" probes assert the guard denies — a probe that
fails to deny is reported as FAIL, never hidden.
"""

from __future__ import annotations

import statistics
import time
from typing import Any, Dict, List

from kernel.core.hypervisor.guards import check_egress_url, validate_capsule_path
from kernel.core.hypervisor.types import ReplayMode
from kernel.core.types import Intent


def _summarize(name: str, samples: List[float], unit: str = "ms") -> Dict[str, Any]:
    ordered = sorted(samples)
    n = len(ordered)

    def pct(q: float) -> float:
        if not ordered:
            return 0.0
        idx = min(n - 1, int(q * n))
        return round(ordered[idx], 4)

    return {
        "op": name, "n": n, "unit": unit,
        "p50": round(statistics.median(ordered), 4) if ordered else 0.0,
        "p95": pct(0.95), "p99": pct(0.99),
        "mean": round(sum(ordered) / n, 4) if n else 0.0,
    }


def run_capsule_benchmarks(hypervisor: Any, iterations: int = 20) -> Dict[str, Any]:
    """Run the capsule benchmark suite against a live hypervisor."""
    results: Dict[str, Any] = {"iterations": iterations, "ops": [],
                               "isolation_probes": [], "notes": []}

    def timed(op: str, fn: Any, n: int = iterations) -> None:
        samples = []
        for _ in range(n):
            start = time.perf_counter()
            fn()
            samples.append((time.perf_counter() - start) * 1000.0)
        results["ops"].append(_summarize(op, samples))

    # Startup: capsule creation latency (minimal profile, no agent start).
    created: List[str] = []

    def _create() -> None:
        capsule = hypervisor.create_capsule(
            Intent(actor="benchmark", objective="bench capsule"),
            "minimal")
        created.append(capsule.capsule_id)

    timed("capsule.create", _create, n=5)

    capsule_id = created[0]
    hypervisor.start_capsule(capsule_id)

    # Capability mediation latency (manifest gate + budgets + receipt).
    def _mediate() -> None:
        hypervisor.simulate(capsule_id, "memory.read", {"key": "k"})

    timed("capsule.mediate", _mediate)

    # Policy evaluation latency.
    def _policy() -> None:
        hypervisor.kernel.policy_engine.evaluate_intent(
            Intent(actor="benchmark", objective="bench policy"))

    timed("capsule.policy_evaluate", _policy)

    # Checkpoint / restore latency.
    def _checkpoint() -> None:
        hypervisor.snapshot_capsule(capsule_id)

    timed("capsule.checkpoint", _checkpoint, n=5)
    snapshots = hypervisor._capsule_snapshots.get(capsule_id, [])
    if snapshots:
        last = snapshots[-1]

        def _restore() -> None:
            hypervisor.restore_snapshot(last)

        timed("capsule.restore", _restore, n=5)

    # Replay latency (observe-only over accumulated receipts).
    hypervisor.replay(capsule_id, ReplayMode.OBSERVE_ONLY)

    def _replay() -> None:
        hypervisor.replay(capsule_id, ReplayMode.OBSERVE_ONLY)

    timed("capsule.replay_observe", _replay, n=5)

    # Isolation probes (§109): each must DENY/BLOCK honestly.
    escape_paths = ["../host", "/etc/passwd", "C:\\Windows\\System32",
                    "\\\\server\\share", "..\\..\\secret",
                    "workspace/../../outside"]
    denied = 0
    for probe in escape_paths:
        try:
            validate_capsule_path("/capsule/root", probe)
        except ValueError:
            denied += 1
    results["isolation_probes"].append(
        {"suite": "filesystem_escape", "probes": len(escape_paths),
         "denied": denied,
         "status": "PASS" if denied == len(escape_paths) else "FAIL"})

    egress_urls = ["http://169.254.169.254/latest/meta-data/",
                   "http://localhost:8500/admin",
                   "http://2130706433/",
                   "ftp://example.com/x"]
    blocked = sum(1 for u in egress_urls if not check_egress_url(u)[0])
    results["isolation_probes"].append(
        {"suite": "network_escape", "probes": len(egress_urls),
         "blocked": blocked,
         "status": "PASS" if blocked == len(egress_urls) else "FAIL"})

    # Cleanup benchmark capsules (never leak).
    for cid in created:
        try:
            hypervisor.destroy_capsule(cid)
        except Exception:
            pass

    results["notes"].append("REAL measurements from this host; do not compare across machines.")
    results["notes"].append("GPU quota: NOT_SUPPORTED (accounting-only); "
                            "VM isolation: UNAVAILABLE in 1.0.")
    return results
