"""GovernanceBench (§97-98): real latency measurements only.

Measures policy/identity/trust/authorization/delegation latency plus
control-plane OFF vs ON comparison. Prints p50/p95/p99. Never invents
numbers — everything is timed on this machine.
"""
from __future__ import annotations

import statistics
import time

from aetheros_control_plane import UniversalControlPlane
from aetheros_control_plane.models import ActionManifest, IdentityType
from aetheros_control_plane.policy_risk import policy_from_yaml

POLICY = """policy:
  name: bench
  version: v1
  allow:
    - {capability: '*', resource: '*'}
"""

N = 1000


def percentile(xs, p):
    xs = sorted(xs)
    k = (len(xs) - 1) * p / 100
    f, c = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def timed(fn, n=N):
    xs = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        xs.append((time.perf_counter() - t) * 1e6)  # us
    return {"n": n, "p50_us": round(percentile(xs, 50), 1),
            "p95_us": round(percentile(xs, 95), 1),
            "p99_us": round(percentile(xs, 99), 1)}


def main():
    cp = UniversalControlPlane()
    cp.policies.publish(policy_from_yaml(POLICY))
    ident = cp.identities.create(IdentityType.AGENT, "bench",
                                 scopes=["filesystem.read:/workspace/**"])
    for dim in ("identity", "transport", "organization", "capability",
                "behavior", "provenance", "data_handling", "execution",
                "history", "policy"):
        cp.trust.add_evidence(ident.id, dim, 0.9, "bench")
    m = ActionManifest(identity_id=ident.id,
                       capabilities=["filesystem.read"],
                       scopes=["filesystem.read:/workspace/a"],
                       resources=["/workspace/a"])
    results = {
        "authorization_check": timed(lambda: cp.check(m)),
        "policy_evaluate": timed(
            lambda: cp.evaluator.evaluate("filesystem.read", "/workspace/a")),
        "trust_assess": timed(lambda: cp.trust.assess(ident.id)),
        "identity_lookup": timed(lambda: cp.identities.usable(ident.id)),
    }
    parent_scopes = cp.identities.scopes_for(ident.id)
    child = cp.identities.create(IdentityType.AGENT, "bench-child")
    i = {"n": 0}

    def _dlg():
        i["n"] += 1
        cp.delegation.delegate(parent_scopes, ident.id,
                               f"{child.id}-{i['n'] % 10}",
                               ["filesystem.read:/workspace/a"])
    # delegation creates grants; keep n small to avoid unbounded growth
    results["delegation_grant"] = timed(_dlg, n=200)

    # OFF vs ON: bare dict lookup vs full pipeline
    results["control_plane_OFF_baseline"] = timed(
        lambda: {"allowed": True})
    results["control_plane_ON_full_check"] = timed(
        lambda: cp.check(m), n=200)
    import json
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
