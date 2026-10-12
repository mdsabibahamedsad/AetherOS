"""Provenance graph + hash-chained audit log (§33-35).

Append-only JSONL audit with ``prev_hash → hash`` chaining and an
integrity verifier. Documents the real threat model: hash chaining
detects tampering of retained records but cannot prevent deletion by a
storage administrator (no cryptographic immutability claimed, §35/§103).
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def _hash(record: dict) -> str:
    return hashlib.sha256(
        json.dumps(record, sort_keys=True).encode()).hexdigest()


@dataclass
class AuditEvent:
    type: str
    correlation: dict = field(default_factory=dict)
    data: dict = field(default_factory=dict)
    at: float = field(default_factory=time.time)
    prev_hash: str = "GENESIS"
    hash: str = ""


class AuditLog:
    def __init__(self, path: Optional[Path] = None):
        self.path = path
        self._events: List[AuditEvent] = []
        if path and path.exists():
            self._load()

    def _load(self) -> None:
        assert self.path is not None
        for line in self.path.read_text("utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                self._events.append(AuditEvent(**d))

    def emit(self, type: str, correlation: Optional[dict] = None,
             data: Optional[dict] = None) -> AuditEvent:
        prev = self._events[-1].hash if self._events else "GENESIS"
        ev = AuditEvent(type=type, correlation=correlation or {},
                        data=data or {}, prev_hash=prev)
        ev.hash = _hash({"type": ev.type, "correlation": ev.correlation,
                         "data": ev.data, "at": ev.at,
                         "prev_hash": ev.prev_hash})
        self._events.append(ev)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", "utf-8") as f:
                f.write(json.dumps(ev.__dict__, sort_keys=True) + "\n")
        return ev

    def verify(self) -> tuple[bool, str]:
        prev = "GENESIS"
        for ev in self._events:
            if ev.prev_hash != prev:
                return False, f"chain break at {ev.type}"
            expect = _hash({"type": ev.type, "correlation": ev.correlation,
                            "data": ev.data, "at": ev.at,
                            "prev_hash": ev.prev_hash})
            if expect != ev.hash:
                return False, f"tamper detected at {ev.type}"
            prev = ev.hash
        return True, f"ok: {len(self._events)} events chained"

    def query(self, **filters: Any) -> List[AuditEvent]:
        out = []
        for ev in self._events:
            blob = {"type": ev.type, **ev.correlation, **ev.data}
            if all(blob.get(k) == v for k, v in filters.items()):
                out.append(ev)
        return out

    def __len__(self) -> int:
        return len(self._events)


# ---------------------------------------------------------------------------
# Provenance graph (§33): User→Task→Agent→Delegation→Model→Tool→Resource→
# Action→Artifact→Verification. Queryable nodes.
# ---------------------------------------------------------------------------

class ProvenanceGraph:
    def __init__(self) -> None:
        self.nodes: Dict[str, dict] = {}
        self.edges: List[tuple[str, str, str]] = []

    def add(self, node_id: str, kind: str, attrs: Optional[dict] = None) -> str:
        self.nodes[node_id] = {"kind": kind, "attrs": attrs or {},
                               "at": time.time()}
        return node_id

    def link(self, src: str, rel: str, dst: str) -> None:
        self.edges.append((src, rel, dst))

    def lineage(self, node_id: str) -> List[tuple[str, str, str]]:
        """All edges touching node_id (ancestors + descendants)."""
        return [e for e in self.edges if e[0] == node_id or e[2] == node_id]

    def who_created(self, artifact_id: str) -> List[dict]:
        out = []
        for s, rel, d in self.edges:
            if d == artifact_id and rel in ("created", "modified"):
                out.append({"agent": s, **self.nodes.get(s, {})})
        return out
