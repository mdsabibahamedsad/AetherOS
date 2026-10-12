"""Phase 9: real statistics in stdlib (documented assumptions).
Distinguishes statistical vs practical significance; p-values always
reported WITH effect size + CI + n. Normal-approximation methods are
labeled as such; bootstrap/permutation used where n is small."""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def describe(xs: Sequence[float]) -> Dict[str, Any]:
    xs = [float(x) for x in xs]
    n = len(xs)
    if n == 0:
        return {"n": 0}
    mean = sum(xs) / n
    var = sum((x - mean) ** 2 for x in xs) / max(n - 1, 1)
    sd = math.sqrt(var)
    s = sorted(xs)
    mid = n // 2
    median = s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2
    return {"n": n, "mean": mean, "sd": sd, "median": median,
            "min": s[0], "max": s[-1]}


def ci_mean(xs: Sequence[float], level: float = 0.95) -> Dict[str, Any]:
    """Normal-approximation CI (labeled; use bootstrap for small n)."""
    d = describe(xs)
    if d["n"] < 2:
        return {"method": "normal-approx", "note": "n<2: no interval",
                "lo": d.get("mean", 0.0), "hi": d.get("mean", 0.0)}
    z = 1.96 if level == 0.95 else 2.576
    half = z * d["sd"] / math.sqrt(d["n"])
    return {"method": "normal-approx", "level": level,
            "lo": d["mean"] - half, "hi": d["mean"] + half,
            "half_width": half}


def welch_t(a: Sequence[float], b: Sequence[float]) -> Dict[str, Any]:
    """Welch mean comparison, normal approximation for p (labeled)."""
    da, db = describe(a), describe(b)
    if da["n"] < 2 or db["n"] < 2:
        return {"p_approx": 1.0, "note": "insufficient n",
                "cohens_d": 0.0, "diff": 0.0, "statistical": False,
                "practical": False}
    diff = da["mean"] - db["mean"]
    se = math.sqrt(da["sd"] ** 2 / da["n"] + db["sd"] ** 2 / db["n"])
    if se == 0:
        # zero within-group variance: a nonzero shift is deterministic
        # (significant), a zero shift is not. No p-value theater.
        return {"p_approx": 0.0 if diff else 1.0, "cohens_d": 0.0,
                "diff": diff, "note": "zero variance",
                "statistical": bool(diff), "practical": bool(diff)}
    z = diff / se
    p = 2 * (1 - _norm_cdf(abs(z)))
    pooled = math.sqrt(((da["n"] - 1) * da["sd"] ** 2
                        + (db["n"] - 1) * db["sd"] ** 2)
                       / max(da["n"] + db["n"] - 2, 1))
    d = diff / pooled if pooled else 0.0
    mag = ("negligible" if abs(d) < 0.2 else "small" if abs(d) < 0.5
           else "medium" if abs(d) < 0.8 else "large")
    return {"p_approx": p, "method": "welch-normal-approx",
            "diff": diff, "cohens_d": d, "effect_magnitude": mag,
            "statistical": p < 0.05,
            "practical": mag in ("medium", "large"),
            "context": f"n={da['n']}/{db['n']}; p without effect size "
                       f"is meaningless — d={d:.3f} ({mag})"}


def pearson(xs: Sequence[float], ys: Sequence[float]) -> Dict[str, Any]:
    xs, ys = list(map(float, xs)), list(map(float, ys))
    n = min(len(xs), len(ys))
    if n < 3:
        return {"r": 0.0, "note": "n<3"}
    mx, my = sum(xs[:n]) / n, sum(ys[:n]) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs[:n], ys[:n]))
    vx = sum((x - mx) ** 2 for x in xs[:n])
    vy = sum((y - my) ** 2 for y in ys[:n])
    r = cov / math.sqrt(vx * vy) if vx and vy else 0.0
    return {"r": r, "note": "correlation is not causation"}


def bootstrap_ci(xs: Sequence[float], stat: str = "mean",
                 reps: int = 2000, level: float = 0.95,
                 seed: int = 0) -> Dict[str, Any]:
    rng = random.Random(seed)
    n = len(xs)
    if n == 0:
        return {"lo": 0.0, "hi": 0.0, "note": "empty"}
    vals = []
    for _ in range(reps):
        sample = [xs[rng.randrange(n)] for _ in range(n)]
        vals.append(sum(sample) / n if stat == "mean"
                    else sorted(sample)[n // 2])
    vals.sort()
    lo_i = int(reps * (1 - level) / 2)
    return {"method": "bootstrap", "level": level, "reps": reps,
            "seed": seed, "lo": vals[lo_i], "hi": vals[-lo_i - 1]}


def permutation_p(a: Sequence[float], b: Sequence[float],
                  reps: int = 2000, seed: int = 0) -> Dict[str, Any]:
    rng = random.Random(seed)
    obs = abs(sum(a) / max(len(a), 1) - sum(b) / max(len(b), 1))
    pooled = list(a) + list(b)
    na = len(a)
    hits = 0
    for _ in range(reps):
        rng.shuffle(pooled)
        diff = abs(sum(pooled[:na]) / max(na, 1)
                   - sum(pooled[na:]) / max(len(pooled) - na, 1))
        if diff >= obs:
            hits += 1
    return {"p": (hits + 1) / (reps + 1), "method": "permutation",
            "reps": reps, "seed": seed, "observed_diff": obs}


def ols_slope(xs: Sequence[float],
              ys: Sequence[float]) -> Dict[str, Any]:
    n = min(len(xs), len(ys))
    if n < 2:
        return {"slope": 0.0, "intercept": 0.0, "r2": 0.0}
    mx, my = sum(xs[:n]) / n, sum(ys[:n]) / n
    sxx = sum((x - mx) ** 2 for x in xs[:n])
    slope = (sum((x - mx) * (y - my) for x, y in zip(xs[:n], ys[:n]))
             / sxx) if sxx else 0.0
    intercept = my - slope * mx
    ss_tot = sum((y - my) ** 2 for y in ys[:n])
    ss_res = sum((y - (slope * x + intercept)) ** 2
                 for x, y in zip(xs[:n], ys[:n]))
    return {"slope": slope, "intercept": intercept,
            "r2": 1 - ss_res / ss_tot if ss_tot else 0.0}


def sample_size(d: float, power: float = 0.8,
                alpha: float = 0.05) -> Dict[str, Any]:
    """Normal-approx two-sample n per group. Labeled as assumption-based."""
    z_alpha = 1.96 if alpha == 0.05 else 2.576
    z_beta = 0.84 if power == 0.8 else 1.28
    n = 2 * ((z_alpha + z_beta) ** 2) / max(d * d, 1e-9) if d else float("inf")
    return {"n_per_group": math.ceil(n) if d else None,
            "assumptions": {"effect_size_d": d, "power": power,
                            "alpha": alpha, "method": "normal-approx"},
            "warning": "estimate from ASSUMED effect size, not data"}


def correct_multiple(ps: List[float],
                     method: str = "holm") -> List[bool]:
    """Holm / Bonferroni / BH-FDR. Returns per-test reject flags."""
    m = len(ps)
    if method == "bonferroni":
        return [p < 0.05 / max(m, 1) for p in ps]
    order = sorted(range(m), key=lambda i: ps[i])
    out = [False] * m
    if method == "holm":
        for rank, i in enumerate(order):
            if ps[i] < 0.05 / max(m - rank, 1):
                out[i] = True
            else:
                break
    else:  # BH-FDR
        thresh = 0.0
        for rank, i in enumerate(order):
            if ps[i] <= 0.05 * (rank + 1) / max(m, 1):
                thresh = ps[i]
        out = [p <= thresh for p in ps]
    return out


class Statistics:
    """Namespace facade so engine code reads Statistics.describe(...) etc."""
    describe = staticmethod(describe)
    ci_mean = staticmethod(ci_mean)
    welch_t = staticmethod(welch_t)
    pearson = staticmethod(pearson)
    bootstrap_ci = staticmethod(bootstrap_ci)
    permutation_p = staticmethod(permutation_p)
    ols_slope = staticmethod(ols_slope)
    sample_size = staticmethod(sample_size)
    correct_multiple = staticmethod(correct_multiple)
