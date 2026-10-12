"""
Agent Communication Fabric — observability (master spec steps 56 and 57).

Records message counts, latency, delivery failures, retries, authorization
denials, signature failures, schema failures, timeouts, circuit-breaker and
fallback events, and the agent communication graph. The graph never exposes
payload contents.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any, Dict, List

from .transport import TransportState


class FabricMetrics:
    """Thread-safe counters and latency aggregates for the fabric."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._counters: Dict[str, int] = defaultdict(int)
        self._latency: Dict[str, List[float]] = defaultdict(list)
        self._max_latency_samples = 1000

    def increment(self, name: str, by: int = 1) -> None:
        with self._lock:
            self._counters[name] += by

    def record_latency(self, name: str, seconds: float) -> None:
        with self._lock:
            samples = self._latency[name]
            samples.append(seconds)
            if len(samples) > self._max_latency_samples:
                self._latency[name] = samples[-self._max_latency_samples:]

    def get(self, name: str) -> int:
        with self._lock:
            return self._counters.get(name, 0)

    def _latency_stats(self, name: str) -> Dict[str, float]:
        with self._lock:
            samples = self._latency.get(name, [])
            if not samples:
                return {"count": 0, "avg_ms": 0.0, "max_ms": 0.0}
            return {
                "count": len(samples),
                "avg_ms": (sum(samples) / len(samples)) * 1000.0,
                "max_ms": max(samples) * 1000.0,
            }

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            counters = dict(self._counters)
        latencies = {name: self._latency_stats(name) for name in self._latency}
        return {"counters": counters, "latencies": latencies}


class CommunicationGraph:
    """Directed graph of agent-to-agent communication (step 57).

    Edges are aggregates only: frequency, latency, error count, and whether
    the edge crosses a trust boundary. Payload contents are never stored.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._edges: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(
            lambda: defaultdict(
                lambda: {"count": 0, "errors": 0,
                         "latency_total_ms": 0.0, "trust_boundary": False,
                         "last_seen": 0.0}))

    def record(self, sender: str, receiver: str, latency_ms: float,
               *, error: bool = False, trust_boundary: bool = False) -> None:
        now = time.time()
        with self._lock:
            edge = self._edges[sender][receiver or "*"]
            edge["count"] += 1
            edge["latency_total_ms"] += latency_ms
            edge["last_seen"] = now
            edge["trust_boundary"] = edge["trust_boundary"] or trust_boundary
            if error:
                edge["errors"] += 1

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            nodes = sorted({s for s, targets in self._edges.items()
                            for _ in targets} |
                           {t for targets in self._edges.values()
                            for t in targets})
            edges = []
            for sender, targets in self._edges.items():
                for receiver, stats in targets.items():
                    count = stats["count"]
                    edges.append({
                        "from": sender,
                        "to": receiver,
                        "count": count,
                        "errors": stats["errors"],
                        "avg_latency_ms": round(
                            stats["latency_total_ms"] / count, 2) if count else 0.0,
                        "trust_boundary_crossed": stats["trust_boundary"],
                        "last_seen": stats["last_seen"],
                    })
            return {"nodes": nodes, "edges": edges}

    def clear(self) -> None:
        with self._lock:
            self._edges.clear()