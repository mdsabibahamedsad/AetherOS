"""TrustFabric benchmarks (§132-133, §139-140): real measured
latencies — authorization, policy eval, identity lookup, token
issue/validate, revocation, audit overhead, throughput. Prints actuals;
no targets claimed as results."""
from __future__ import annotations

import time
from typing import Any, Callable, Dict

from .fabric import TrustFabric
from aetheros_control_plane.models import IdentityType


def _time(fn: Callable[[], Any], n: int = 500) -> Dict[str, float]:
    xs = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        xs.append((time.perf_counter() - t0) * 1e6)
    xs.sort()
    return {"n": n, "p50_us": round(xs[n // 2], 1),
            "p95_us": round(xs[int(n * 0.95) - 1], 1),
            "p99_us": round(xs[-1], 1)}


class TrustFabricBenchmark:
    def __init__(self, fabric: TrustFabric):
        self.fabric = fabric

    def run(self) -> Dict[str, Any]:
        f = self.fabric
        ident = f.plane.identities.create(
            IdentityType.AGENT, "bench-agent", scopes=["read:docs"])
        out: Dict[str, Any] = {}
        out["propose"] = _time(
            lambda: f.propose(ident.id, "read", "/docs/a.md",
                              kind="filesystem", task_id="bench"))
        out["policy_simulate"] = _time(
            lambda: f.simulator.simulate("read", "/docs/a.md"), n=1000)
        out["identity_lookup"] = _time(
            lambda: f.plane.identities.get(ident.id), n=2000)
        tok = f.capabilities.issue("bench", "read", "/docs/a.md", "bench",
                                   audience="tool-x", max_uses=10 ** 9)
        out["token_validate"] = _time(
            lambda: f.capabilities.validate(tok, "tool-x"), n=1000)
        out["token_issue"] = _time(
            lambda: f.capabilities.issue("bench", "read", "/docs/a.md",
                                         "bench", audience="tool-x"), n=200)
        t0 = time.perf_counter()
        for _ in range(200):
            f.plane.audit.emit("bench", {"i": 1}, {"x": "y"})
        out["audit_200"] = {"wall_ms": round(
            (time.perf_counter() - t0) * 1000, 2)}
        t0 = time.perf_counter()
        for i in range(100):
            f.revoke("capability", f"ctok_{i}", "bench")
        out["revoke_100"] = {"wall_ms": round(
            (time.perf_counter() - t0) * 1000, 2)}
        out["paths_cumulative"] = _time(
            lambda: f.paths.cumulative_risk("bench"), n=2000)
        return out
