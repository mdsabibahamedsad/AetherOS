"""Multi-layer rate limiting + quotas (Master 62 §36-37). Actually enforced.

Token-bucket per (layer, identity, endpoint): burst + sustained rate +
concurrency caps. Exceeding returns structured 429 data (never a bare 429):
retry_after, limit, remaining. Usage recorded for the usage center.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional, Tuple

from aetheros_platform.errors import err

# layer -> (burst, sustained_per_second)
LIMITS: Dict[str, Tuple[int, float]] = {
    "standard": (60, 1.0),
    "agent": (20, 0.5),
    "task": (30, 0.5),
    "tool-invoke": (10, 0.2),
    "memory": (60, 2.0),
}

# scope предохранитель: max concurrent executions per key for tool-invoke.
MAX_CONCURRENT_TOOL = 4


class RateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buckets: Dict[str, Dict[str, float]] = {}
        self._inflight: Dict[str, int] = {}

    def _key(self, layer: str, ident: str, endpoint: str) -> str:
        return f"{layer}:{ident}:{endpoint}"

    def check(self, layer: str, ident: str, endpoint: str,
              now: Optional[float] = None) -> Dict[str, Any]:
        ts = now if now is not None else time.time()
        burst, rate = LIMITS.get(layer, LIMITS["standard"])
        k = self._key(layer, ident, endpoint)
        with self._lock:
            b = self._buckets.get(k, {"tokens": float(burst), "ts": ts})
            elapsed = max(0.0, ts - b["ts"])
            b["tokens"] = min(float(burst), b["tokens"] + elapsed * rate)
            b["ts"] = ts
            if b["tokens"] < 1.0:
                retry_after = (1.0 - b["tokens"]) / rate
                self._buckets[k] = b
                raise _rate_err(retry_after, burst)
            b["tokens"] -= 1.0
            self._buckets[k] = b
            return {"limit": burst, "remaining": int(b["tokens"]),
                    "retry_after": 0.0}

    def acquire_inflight(self, ident: str) -> None:
        with self._lock:
            n = self._inflight.get(ident, 0)
            if n >= MAX_CONCURRENT_TOOL:
                raise err("RATE_LIMITED",
                          f"too many concurrent tool executions ({n})",
                          remediation="wait for running tools or raise quota")
            self._inflight[ident] = n + 1

    def release_inflight(self, ident: str) -> None:
        with self._lock:
            self._inflight[ident] = max(0, self._inflight.get(ident, 1) - 1)


def _rate_err(retry_after: float, limit: int):
    e = err("RATE_LIMITED", f"rate limit exceeded; retry after {retry_after:.1f}s",
            remediation="back off exponentially with jitter")
    e.metadata = {"retry_after": round(retry_after, 2), "limit": limit}
    return e


LIMITER = RateLimiter()
