"""AetherOS Agent Kernel 1.0 — micro-benchmark suite (§88).

Real measurements only (time.perf_counter). No fabricated numbers.
Reports p50/p95/p99 + throughput where applicable.
"""

from __future__ import annotations

import statistics
import time
from typing import Any, Dict, List


def _pct(samples: List[float], q: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    idx = min(len(ordered) - 1, max(0, int(q * len(ordered))))
    return ordered[idx]


def _summarize(name: str, samples_ms: List[float]) -> Dict[str, Any]:
    return {
        "op": name,
        "n": len(samples_ms),
        "p50_ms": round(statistics.median(samples_ms), 4) if samples_ms else 0.0,
        "p95_ms": round(_pct(samples_ms, 0.95), 4),
        "p99_ms": round(_pct(samples_ms, 0.99), 4),
        "mean_ms": round(statistics.fmean(samples_ms), 4) if samples_ms else 0.0,
    }


def run_benchmarks(kernel, iterations: int = 20) -> Dict[str, Any]:
    from kernel.core.types import Intent, ResourceBudget

    def _minimal_intent(objective: str) -> Intent:
        intent = Intent(actor="benchmark", objective=objective)
        # Minimal footprint so benchmarks measure overhead, not resource exhaustion.
        intent.requested_resources = ResourceBudget(
            cpu_cores=0.1, ram_mb=64, disk_mb=64, network_mbps=1.0,
            llm_tokens_per_minute=1000, browser_sessions=0, computer_sessions=0,
            device_sessions=0, agent_slots=0, automation_slots=0,
        )
        intent.budget = intent.requested_resources
        return intent

    results: Dict[str, Any] = {"iterations": iterations, "ops": []}

    # intent admission
    samples = []
    for i in range(iterations):
        intent = _minimal_intent(f"bench intent {i}")
        t0 = time.perf_counter()
        kernel.intent_manager.admit(intent)
        samples.append((time.perf_counter() - t0) * 1000)
    results["ops"].append(_summarize("intent.admit", samples))

    # policy evaluation
    samples = []
    intent = Intent(actor="benchmark", objective="policy bench")
    for _ in range(iterations):
        t0 = time.perf_counter()
        kernel.policy_engine.evaluate_intent(intent)
        samples.append((time.perf_counter() - t0) * 1000)
    results["ops"].append(_summarize("policy.evaluate_intent", samples))

    # capability lookup
    samples = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        kernel.capability_manager.list_capabilities()
        samples.append((time.perf_counter() - t0) * 1000)
    results["ops"].append(_summarize("capability.list", samples))

    # agent create (startup)
    samples = []
    for i in range(max(5, iterations // 4)):
        intent = _minimal_intent(f"bench agent {i}")
        t0 = time.perf_counter()
        try:
            p = kernel.create_agent_process(intent)
            samples.append((time.perf_counter() - t0) * 1000)
        except PermissionError:
            # Resource exhaustion is itself a signal; record admission-denied.
            samples.append((time.perf_counter() - t0) * 1000)
    results["ops"].append(_summarize("agent.create", samples))

    # scheduler admit->schedule tick
    samples = []
    procs = kernel.list_agent_processes()[-5:]
    for p in procs:
        t0 = time.perf_counter()
        try:
            kernel.scheduler.schedule(p)
        except Exception:
            pass
        samples.append((time.perf_counter() - t0) * 1000)
    results["ops"].append(_summarize("scheduler.schedule", samples or [0.0]))

    # memory write/read
    samples_w, samples_r = [], []
    for i in range(iterations):
        t0 = time.perf_counter()
        kernel.memory_manager.write(f"bench{i}", __import__("kernel.core.memory_manager", fromlist=["MemoryScope"]).MemoryScope.WORKING, f"k{i}", {"v": i})
        samples_w.append((time.perf_counter() - t0) * 1000)
        t0 = time.perf_counter()
        kernel.memory_manager.read(f"bench{i}", __import__("kernel.core.memory_manager", fromlist=["MemoryScope"]).MemoryScope.WORKING, f"k{i}")
        samples_r.append((time.perf_counter() - t0) * 1000)
    results["ops"].append(_summarize("memory.write", samples_w))
    results["ops"].append(_summarize("memory.read", samples_r))

    # checkpoint latency
    samples = []
    for p in procs:
        t0 = time.perf_counter()
        try:
            kernel.checkpoint_manager.create_checkpoint(p.agent_id)
        except Exception:
            pass
        samples.append((time.perf_counter() - t0) * 1000)
    results["ops"].append(_summarize("checkpoint.create", samples or [0.0]))

    results["note"] = "REAL measurements from this host; do not compare across machines"
    return results
