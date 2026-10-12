"""Checkpoints, approvals, audit, observability (sections 44-51, 86-88).

- CheckpointStore: atomic JSON persist/restore of run state (DAG, task +
  agent states, messages, budgets, decisions, verification). Resume never
  restarts verified work: completed results are carried over.
- ApprovalQueue: human-in-the-loop gate with rich request payload
  (what/why/agent/data/risk) + approve/reject; timeout -> denied-safe.
- AuditLog: append-only JSONL, immutable record of important actions.
- Tracer: spans + counters (run/agent/task/model/tool/duration/tokens/
  cost/status/error/retry) with a serializable trace tree for the UI.
- EventStream: sequenced run events (ordering-safe for the UI).
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


# -- checkpoints ---------------------------------------------------------

class CheckpointStore:
    def __init__(self, root: Optional[Path] = None) -> None:
        self._root = Path(root) if root else None

    def initialize(self, root: Optional[Path] = None) -> None:
        if root is not None:
            self._root = Path(root)
        if self._root is None:
            self._root = Path("./swarm_checkpoints")
        self._root.mkdir(parents=True, exist_ok=True)

    def save(self, run_id: str, state: Dict[str, Any]) -> Path:
        assert self._root is not None
        payload = {"run_id": run_id, "at": time.time(), "state": state}
        fd, tmp = tempfile.mkstemp(dir=str(self._root), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            dest = self._root / f"{run_id}.checkpoint.json"
            os.replace(tmp, str(dest))
            return dest
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def load(self, run_id: str) -> Optional[Dict[str, Any]]:
        assert self._root is not None
        path = self._root / f"{run_id}.checkpoint.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def list_runs(self) -> List[str]:
        assert self._root is not None
        return sorted(p.stem.replace(".checkpoint", "")
                      for p in self._root.glob("*.checkpoint.json"))


# -- approvals -------------------------------------------------------------

@dataclass
class ApprovalRequest:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str = ""
    task_id: str = ""
    agent_id: str = ""
    action: str = ""
    what: str = ""
    why: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    risk: str = "medium"
    state: str = "pending"  # pending|approved|rejected|expired
    created_at: float = field(default_factory=time.time)
    resolved_at: float = 0.0
    resolved_by: str = ""


class ApprovalQueue:
    def __init__(self, *, default_timeout_s: float = 600.0) -> None:
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._reqs: Dict[str, ApprovalRequest] = {}
        self._timeout = default_timeout_s

    def request(self, req: ApprovalRequest) -> ApprovalRequest:
        with self._lock:
            self._reqs[req.id] = req
            self._cond.notify_all()
            return req

    def resolve(self, req_id: str, approved: bool, by: str = "user") -> bool:
        with self._lock:
            req = self._reqs.get(req_id)
            if req is None or req.state != "pending":
                return False
            req.state = "approved" if approved else "rejected"
            req.resolved_at = time.time()
            req.resolved_by = by
            self._cond.notify_all()
            return True

    def await_decision(self, req_id: str, timeout: Optional[float] = None) -> ApprovalRequest:
        deadline = time.time() + (timeout if timeout is not None else self._timeout)
        with self._lock:
            while True:
                req = self._reqs.get(req_id)
                if req is None:
                    raise KeyError(req_id)
                if req.state != "pending":
                    return req
                remaining = deadline - time.time()
                if remaining <= 0:
                    req.state = "expired"  # fail-safe: expiry denies
                    return req
                self._cond.wait(timeout=min(remaining, 1.0))

    def pending(self, *, run_id: str = "") -> List[ApprovalRequest]:
        with self._lock:
            return [r for r in self._reqs.values()
                    if r.state == "pending" and (not run_id or r.run_id == run_id)]


# -- audit -----------------------------------------------------------------

class AuditLog:
    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = Path(path) if path else None
        self._lock = threading.Lock()

    def initialize(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, action: str, *, run_id: str = "", task_id: str = "",
               agent_id: str = "", detail: Optional[Dict[str, Any]] = None) -> None:
        entry = {"at": time.time(), "action": action, "run_id": run_id,
                 "task_id": task_id, "agent_id": agent_id,
                 "detail": detail or {}}
        if self._path is None:
            return
        line = json.dumps(entry, ensure_ascii=False)
        with self._lock:
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    def read(self, *, run_id: str = "", limit: int = 500) -> List[Dict[str, Any]]:
        if self._path is None or not self._path.exists():
            return []
        out = []
        with open(self._path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if run_id and e.get("run_id") != run_id:
                    continue
                out.append(e)
        return out[-limit:]


# -- tracing ---------------------------------------------------------------

@dataclass
class Span:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str = ""
    parent_id: str = ""
    name: str = ""
    agent_id: str = ""
    task_id: str = ""
    model: str = ""
    started_at: float = field(default_factory=time.time)
    ended_at: float = 0.0
    status: str = "running"
    tokens: int = 0
    cost_usd: float = 0.0
    error: str = ""
    attrs: Dict[str, Any] = field(default_factory=dict)


class Tracer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._spans: Dict[str, Span] = {}
        self._counters: Dict[str, float] = {}

    def start(self, **kw) -> Span:
        s = Span(**kw)
        with self._lock:
            self._spans[s.id] = s
        return s

    def finish(self, span: Span, *, status: str = "ok", error: str = "",
               tokens: int = 0, cost: float = 0.0) -> None:
        with self._lock:
            span.ended_at = time.time()
            span.status = status
            span.error = error
            span.tokens = tokens
            span.cost_usd = cost
            self._counters["spans"] = self._counters.get("spans", 0) + 1
            self._counters["tokens"] = self._counters.get("tokens", 0) + tokens
            self._counters["cost_usd"] = self._counters.get("cost_usd", 0) + cost
            if status != "ok":
                self._counters["errors"] = self._counters.get("errors", 0) + 1

    def count(self, name: str, value: float = 1.0) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + value

    def trace_tree(self, run_id: str) -> Dict[str, Any]:
        with self._lock:
            spans = [s for s in self._spans.values() if s.run_id == run_id]
            by_parent: Dict[str, List[Span]] = {}
            for s in spans:
                by_parent.setdefault(s.parent_id, []).append(s)

            def build(pid: str) -> List[Dict[str, Any]]:
                out = []
                for s in sorted(by_parent.get(pid, []), key=lambda x: x.started_at):
                    out.append({"id": s.id, "name": s.name, "agent_id": s.agent_id,
                                "task_id": s.task_id, "model": s.model,
                                "status": s.status, "tokens": s.tokens,
                                "cost_usd": s.cost_usd, "error": s.error,
                                "duration_s": round((s.ended_at or time.time()) - s.started_at, 3),
                                "children": build(s.id)})
                return out
            return {"run_id": run_id, "spans": build(""),
                    "counters": dict(self._counters)}


# -- sequenced event stream --------------------------------------------------

@dataclass
class RunEvent:
    kind: str
    run_id: str = ""
    task_id: str = ""
    agent_id: str = ""
    timestamp: float = field(default_factory=time.time)
    seq: int = 0
    detail: Dict[str, Any] = field(default_factory=dict)


RUN_EVENT_KINDS = ("ORCHESTRATION_STARTED", "TASK_CREATED", "AGENT_SPAWNED",
                   "AGENT_STARTED", "AGENT_MESSAGE", "TASK_COMPLETED",
                   "TASK_FAILED", "AGENT_BLOCKED", "AGENT_HANDOFF",
                   "REVIEW_STARTED", "VERIFICATION_STARTED", "CONFLICT_DETECTED",
                   "REPLAN_STARTED", "AGENT_TERMINATED", "ORCHESTRATION_COMPLETED")


class EventStream:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seq = 0
        self._events: List[RunEvent] = []
        self._subs: List[Callable[[RunEvent], None]] = []

    def emit(self, event: RunEvent) -> RunEvent:
        with self._lock:
            self._seq += 1
            event.seq = self._seq
            if not event.timestamp:
                event.timestamp = time.time()
            self._events.append(event)
            subs = list(self._subs)
        for fn in subs:
            try:
                fn(event)
            except Exception:
                continue
        return event

    def subscribe(self, fn: Callable[[RunEvent], None]) -> None:
        with self._lock:
            self._subs.append(fn)

    def for_run(self, run_id: str, *, after_seq: int = 0,
                limit: int = 500) -> List[RunEvent]:
        with self._lock:
            return [e for e in self._events
                    if e.run_id == run_id and e.seq > after_seq][-limit:]
