"""Statistical primitives (P9, P29-30, P43). Pure stdlib; no fabrication —
every function returns None/empty on insufficient data instead of guessing."""

from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


def mean(xs: Sequence[float]) -> Optional[float]:
    return sum(xs) / len(xs) if xs else None


def variance(xs: Sequence[float]) -> Optional[float]:
    if len(xs) < 2:
        return None
    m = sum(xs) / len(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def stdev(xs: Sequence[float]) -> Optional[float]:
    v = variance(xs)
    return math.sqrt(v) if v is not None else None


def percentile(xs: Sequence[float], p: float) -> Optional[float]:
    """Linear-interpolation percentile, p in [0, 100]."""
    if not xs:
        return None
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * (p / 100.0)
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return s[lo]
    frac = k - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def latency_profile(xs: Sequence[float]) -> Dict[str, Optional[float]]:
    """P9 full reporting block: mean/median/P50/P90/P95/P99/min/max/std."""
    return {
        "n": len(xs),
        "mean": mean(xs),
        "median": percentile(xs, 50),
        "p50": percentile(xs, 50),
        "p90": percentile(xs, 90),
        "p95": percentile(xs, 95),
        "p99": percentile(xs, 99),
        "min": min(xs) if xs else None,
        "max": max(xs) if xs else None,
        "stdev": stdev(xs),
    }


def ci95(xs: Sequence[float]) -> Tuple[Optional[float], Optional[float]]:
    """Normal-approximation 95% confidence interval of the mean."""
    n = len(xs)
    if n < 2:
        return (None, None)
    m = mean(xs)
    half = 1.96 * (stdev(xs) or 0.0) / math.sqrt(n)
    return (m - half, m + half)


def _welch_t(a: Sequence[float], b: Sequence[float]) -> Optional[float]:
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return None
    va, vb = variance(a), variance(b)
    if (va or 0) == 0 and (vb or 0) == 0:
        return 0.0
    denom = math.sqrt((va or 0) / na + (vb or 0) / nb)
    if denom == 0:
        return None
    return (mean(a) - mean(b)) / denom


def welch_pvalue_two_sided(a: Sequence[float],
                           b: Sequence[float]) -> Optional[float]:
    """p-value via Welch t with conservative min-df approximation.

    Stdlib only: uses a normal approximation to t for df>=2. Reported as an
    approximation and never as exact inference (P14 report-uncertainty rule).
    """
    t = _welch_t(a, b)
    if t is None:
        return None
    # two-sided normal tail approximation
    z = abs(t)
    return 2.0 * (1.0 - _norm_cdf(z))


def cohens_d(a: Sequence[float], b: Sequence[float]) -> Optional[float]:
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return None
    sp = math.sqrt((((na - 1) * (variance(a) or 0)) +
                    ((nb - 1) * (variance(b) or 0))) / (na + nb - 2))
    if sp == 0:
        return None
    return (mean(a) - mean(b)) / sp


def significant(a: Sequence[float], b: Sequence[float],
                alpha: float = 0.05) -> Optional[bool]:
    p = welch_pvalue_two_sided(a, b)
    return None if p is None else p < alpha


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def proportion_ci95(passes: int, total: int) -> Tuple[Optional[float],
                                                      Optional[float]]:
    """Wilson score interval for a binomial proportion."""
    if total <= 0:
        return (None, None)
    z = 1.96
    p = passes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    spread = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))
    return (max(0.0, centre - spread), min(1.0, centre + spread))
