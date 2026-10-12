"""Head-to-head comparison (P36, P44, P48-49, P61-63), leaderboard (P60),
and the evidence-gated claims generator.

Nothing here invents numbers: every delta is computed from AgentResult
records; comparisons without executed runs return INSUFFICIENT EVIDENCE.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from benchmark import stats
from benchmark.adapters import capability_profile
from benchmark.metrics import AgentProfile, build_profiles
from benchmark.schema import AgentResult, TaskStatus


class HeadToHead:
    """P48/P49 — direct A-vs-B comparison over matched task_ids."""

    def __init__(self, a: str, b: str,
                 results: List[AgentResult],
                 env_a: Optional[Dict] = None,
                 env_b: Optional[Dict] = None):
        self.a_name, self.b_name = a, b
        profiles = build_profiles(results)
        if a not in profiles or b not in profiles:
            raise ValueError(
                f"INSUFFICIENT_EVIDENCE: need results for both {a!r} and "
                f"{b!r}; have {sorted(profiles)}")
        prof_a, prof_b = profiles[a], profiles[b]
        # match on task_id so we compare like-for-like executions only
        ta = {r.task_id: r for r in prof_a.results
              if r.status is not TaskStatus.BLOCKED}
        tb = {r.task_id: r for r in prof_b.results
              if r.status is not TaskStatus.BLOCKED}
        common = sorted(set(ta) & set(tb))
        self.common_tasks = common
        self.a = AgentProfile(a, [ta[t] for t in common])
        self.b = AgentProfile(b, [tb[t] for t in common])
        self.fairness_flags: List[str] = []
        if env_a and env_b:
            from benchmark.environment import fairness_check
            self.fairness_flags = fairness_check(env_a, env_b)

    def table(self) -> Dict[str, Dict]:
        sa, sb = self.a.scores(), self.b.scores()
        la = stats.latency_profile(self.a.latencies_ms())
        lb = stats.latency_profile(self.b.latencies_ms())
        toks_a = [r.total_tokens for r in self.a.results]
        toks_b = [r.total_tokens for r in self.b.results]
        speedups = None
        p50a, p50b = la.get("p50"), lb.get("p50")
        if p50a and p50b:
            speedups = round(p50b / p50a, 3)   # >1 means A faster
        sig = stats.significant(self.a.latencies_ms(),
                                self.b.latencies_ms())
        return {
            "agents": (self.a_name, self.b_name),
            "matched_tasks": len(self.common_tasks),
            "fairness_flags": self.fairness_flags,
            "verified_success": {
                self.a_name: round(sa["raw"]["task_success"], 4),
                self.b_name: round(sb["raw"]["task_success"], 4),
                "delta_pp": _pct_delta(sa["raw"]["task_success"],
                                       sb["raw"]["task_success"]),
            },
            "median_latency_ms": {
                self.a_name: p50a, self.b_name: p50b,
                "speedup_x": speedups,
                "statistically_significant_005": sig,
            },
            "tokens": {
                self.a_name: stats.mean(toks_a),
                self.b_name: stats.mean(toks_b),
                "delta_pct": _pct_delta(stats.mean(toks_a) or 0,
                                        stats.mean(toks_b) or 0),
            },
            "tool_calls_per_task": {
                self.a_name: self.a.tool_stats().get(
                    "avg_per_successful_task"),
                self.b_name: self.b.tool_stats().get(
                    "avg_per_successful_task"),
            },
            "cost_per_task_usd": {
                self.a_name: self.a.cost_per_task(),
                self.b_name: self.b.cost_per_task(),
            },
            "false_done": {
                self.a_name: sa["raw"]["false_done"],
                self.b_name: sb["raw"]["false_done"],
            },
            "overall_weighted": {
                self.a_name: sa["overall"],
                self.b_name: sb["overall"],
                "security_capped": (sa["security_capped"],
                                    sb["security_capped"]),
            },
        }


def _pct_delta(a: float, b: float) -> Optional[float]:
    """(a-b)/b * 100 — percentage points where meaningful; None on zero."""
    if b in (0, None):
        return None
    return round((a - b) / b * 100.0, 2)


# ------------------------------------------------------------------ P60

def leaderboard(results: List[AgentResult]) -> List[Dict]:
    profiles = build_profiles(results)
    rows = []
    for name, prof in profiles.items():
        # P60/P88 honesty: an agent whose runs are ALL BLOCKED was never
        # tested — it is listed as unranked rather than scored 0
        if all(r.status is TaskStatus.BLOCKED for r in prof.results):
            rows.append({"agent": name, "unranked_reason":
                         "all runs BLOCKED (never executed)",
                         "rank": None, "overall": None,
                         "success_verified": None, "speed_p50_ms": None,
                         "tokens_per_success": None, "cost_per_task": None,
                         "reliability": None, "safety_events": None,
                         "security_capped": False})
            continue
        s = prof.scores()
        raw = s["raw"]
        rows.append({
            "agent": name,
            "overall": s["overall"],
            "success_verified": raw["task_success"],
            "speed_p50_ms": raw["speed_p50_ms"],
            "tokens_per_success": raw["tokens_per_success"],
            "cost_per_task": raw["cost_per_task"],
            "reliability": raw["reliability"],
            "safety_events": sum(raw["safety_events"].values()),
            "security_capped": s["security_capped"],
        })
    rows.sort(key=lambda r: r["overall"] if r["overall"] is not None
              else -1.0, reverse=True)
    ranked = [r for r in rows if r["overall"] is not None]
    unranked = [r for r in rows if r["overall"] is None]
    for i, row in enumerate(ranked, start=1):
        row["rank"] = i
    return ranked + unranked


# ------------------------------------------------------------------ P62/63

def generate_claims(aetheros: str, baseline: str,
                    results: List[AgentResult]) -> List[str]:
    """Evidence-gated claim strings. Any missing measurement becomes
    'INSUFFICIENT EVIDENCE' — never marketing language."""
    try:
        h2h = HeadToHead(aetheros, baseline, results)
    except ValueError as exc:
        return [f"INSUFFICIENT EVIDENCE ({exc})"]
    claims: List[str] = []
    t = h2h.table()

    if h2h.common_tasks == 0:
        return ["INSUFFICIENT EVIDENCE: no commonly-executed tasks"]

    vs = t["verified_success"]
    da, db = vs[aetheros], vs[baseline]
    if da is not None and db is not None:
        claims.append(
            f"In our controlled benchmark, {aetheros} verified-success was "
            f"{da:.1%} vs {db:.1%} for {baseline} "
            f"(delta {vs['delta_pp']}pp, n={t['matched_tasks']}).")
    else:
        claims.append(f"INSUFFICIENT EVIDENCE for success-rate claim.")

    med = t["median_latency_ms"]
    sx = med.get("speedup_x")
    if sx:
        who = aetheros if sx > 1 else baseline
        other = baseline if sx > 1 else aetheros
        claims.append(
            f"In our controlled benchmark, median latency favored {who} "
            f"({abs(sx):.2f}x); significance@0.05="
            f"{med['statistically_significant_005']}.")
    else:
        claims.append("INSUFFICIENT EVIDENCE for speedup claim.")

    tk = t["tokens"]
    if tk[aetheros] and tk[baseline]:
        d = _pct_delta(tk[aetheros], tk[baseline])
        claims.append(
            f"Tokens/task: {aetheros}={tk[aetheros]:.0f}, "
            f"{baseline}={tk[baseline]:.0f} (delta {d}%).")
    else:
        claims.append("INSUFFICIENT EVIDENCE for token claim.")

    cost = t["cost_per_task_usd"]
    if cost.get(aetheros) and cost.get(baseline):
        claims.append(
            f"Cost/task: {aetheros}=${cost[aetheros]:.4f} vs "
            f"{baseline}=${cost[baseline]:.4f}.")
    else:
        claims.append("INSUFFICIENT EVIDENCE for cost claim.")

    if t["fairness_flags"]:
        claims.append("COMPARISONS CARRY FAIRNESS_WARNINGS: " +
                      "; ".join(t["fairness_flags"][:3]))
    return claims


# ------------------------------------------------------------------ P86/87

def pareto_frontier(points: Dict[str, Dict[str, float]],
                    axes=("speed", "quality", "cost", "safety"),
                    minimize=("cost",)) -> List[str]:
    """Pareto-efficient agents over selected axes (higher better except in
    `minimize`). Returns names on the frontier."""
    def dominates(x: Dict[str, float], y: Dict[str, float]) -> bool:
        better_or_equal = True
        strictly_better = False
        for ax in axes:
            vx, vy = x.get(ax), y.get(ax)
            if vx is None or vy is None:
                return False
            better = vx < vy if ax in minimize else vx > vy
            worse = vx > vy if ax in minimize else vx < vy
            if worse:
                return False
            if better:
                strictly_better = True
        return better_or_equal and strictly_better

    names = list(points)
    frontier = []
    for n in names:
        if not any(dominates(points[m], points[n])
                   for m in names if m != n):
            frontier.append(n)
    return frontier


def tradeoff_notes(results: List[AgentResult]) -> List[str]:
    """P87 — surface explicit tradeoffs between agent pairs."""
    notes: List[str] = []
    profiles = build_profiles(results)
    names = sorted(profiles)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            pa, pb = profiles[a], profiles[b]
            la, lb = stats.percentile(pa.latencies_ms(), 50), \
                stats.percentile(pb.latencies_ms(), 50)
            va, vb = pa.verified_success_rate(), pb.verified_success_rate()
            if None in (la, lb, va, vb):
                continue
            if la < lb and va < vb:
                notes.append(f"{a} is faster but less accurate than {b} "
                             f"({la:.0f}ms vs {lb:.0f}ms; "
                             f"{va:.0%} vs {vb:.0%})")
            elif lb < la and vb < va:
                notes.append(f"{b} is faster but less accurate than {a} "
                             f"({lb:.0f}ms vs {la:.0f}ms; "
                             f"{vb:.0%} vs {va:.0%})")
    return notes or ["no executed pairs available for tradeoff analysis"]


__all__ = [
    "HeadToHead",
    "capability_profile",
    "generate_claims",
    "leaderboard",
    "pareto_frontier",
    "tradeoff_notes",
]
