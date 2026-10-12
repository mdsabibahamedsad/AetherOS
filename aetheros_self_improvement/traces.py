"""Trace redaction (§5) + trace store (Phase A, §113-116, §139, §142).

RedactionEngine removes/masks secrets BEFORE storage or dataset export
using the Master 50 scanners plus PII patterns. Findings carry kinds
and counts only — never secret values. TraceStore is per-tenant JSONL
with levels, retention purge, private-mode guard, and graceful
degradation (never blocks agent execution on storage failure unless
policy demands fail-closed).
"""

from __future__ import annotations

import copy
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import AgentTrace, TraceLevel

logger = logging.getLogger(__name__)

try:
    from aetheros_control_plane.data_network import (  # type: ignore
        scan_for_secrets, redact as _cp_redact)
    _HAS_CP = True
except Exception:
    _HAS_CP = False

_PII = [
    (re.compile(r"\b[\w.]+@[\w.]+\.\w+\b"), "email"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "card_candidate"),
    (re.compile(r"(?i)(ssn|social security)[ :]*\d{3}-\d{2}-\d{4}"), "ssn"),
]

_LEVEL_FIELDS = {
    "minimal": {"trace_id", "task_id", "agent_identity", "tenant",
                "final_outcome", "timestamp", "level"},
    "standard": None,  # all except debug-only extras (same shape here)
    "debug": None,
    "forensic": None,
}


class RedactionEngine:
    """Scrub a trace dict; returns (scrubbed, report)."""

    def redact_text(self, text: str) -> tuple[str, List[str]]:
        kinds: List[str] = []
        out = text
        if _HAS_CP:
            findings = scan_for_secrets(out)
            for f in findings:
                kinds.append(f.kind)
            if findings:
                out = _cp_redact(out, findings)
        for rx, kind in _PII:
            if rx.search(out):
                kinds.append(kind)
                out = rx.sub("[REDACTED]", out)
        return out, kinds

    def redact_trace(self, trace: Dict[str, Any]) -> tuple[Dict[str, Any],
                                                           Dict[str, Any]]:
        scrubbed = copy.deepcopy(trace)
        kinds: List[str] = []
        for key in ("user_intent", "normalized_intent", "final_outcome",
                    "user_feedback"):
            if isinstance(scrubbed.get(key), str):
                scrubbed[key], k = self.redact_text(scrubbed[key])
                kinds.extend(k)
        for call in scrubbed.get("tool_calls", []) or []:
            if isinstance(call, dict):
                for ak in ("args", "result", "output", "input"):
                    if isinstance(call.get(ak), str):
                        call[ak], k = self.redact_text(call[ak])
                        kinds.extend(k)
        scrubbed["redacted"] = True
        return scrubbed, {"kinds": sorted(set(kinds)),
                          "fields": ["user_intent", "final_outcome",
                                     "tool_calls"]}


class TraceStore:
    """Append-only per-tenant trace storage (§139: existing architecture —
    JSONL files under the profile home, no new DB required)."""

    def __init__(self, root: Path, default_level: str = "standard",
                 fail_closed: bool = False):
        self.root = Path(root)
        self.default_level = default_level
        self.fail_closed = fail_closed
        self.redactor = RedactionEngine()
        self.private_mode = False

    def _path(self, tenant: str) -> Path:
        safe = "".join(c for c in tenant if c.isalnum() or c in "-_")
        return self.root / f"traces_{safe or 'default'}.jsonl"

    def record(self, trace: AgentTrace,
               level: Optional[str] = None) -> Optional[str]:
        if self.private_mode:
            return None  # §116: collection constrained in private mode
        lvl = level or self.default_level
        doc = {k: v for k, v in trace.__dict__.items()
               if v not in (None, "", [], {}) or k in (
                   "trace_id", "task_id", "tenant", "final_outcome")}
        doc["level"] = lvl
        allowed = _LEVEL_FIELDS.get(lvl)
        if allowed is not None:
            doc = {k: v for k, v in doc.items() if k in allowed}
        try:
            doc, _report = self.redactor.redact_trace(doc)
        except Exception as exc:
            if self.fail_closed:
                raise
            logger.warning("redaction failed, storing minimal: %s", exc)
            doc = {"trace_id": trace.trace_id, "task_id": trace.task_id,
                   "tenant": trace.tenant, "redacted": True,
                   "redaction_error": type(exc).__name__}
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            with self._path(trace.tenant).open("a", encoding="utf-8") as f:
                f.write(json.dumps(doc, sort_keys=True, default=str)
                        + "\n")
        except Exception as exc:  # §142 backpressure: degrade gracefully
            logger.warning("trace storage unavailable: %s", exc)
            if self.fail_closed:
                raise
            return None
        return trace.trace_id

    def list(self, tenant: str, limit: int = 100) -> List[Dict[str, Any]]:
        # Tenant isolation: only this tenant's file is ever read.
        p = self._path(tenant)
        if not p.exists():
            return []
        lines = p.read_text("utf-8").splitlines()
        out = []
        for line in lines[-limit:]:
            if line.strip():
                out.append(json.loads(line))
        return out

    def purge_older_than(self, tenant: str, days: float) -> int:
        """Retention enforcement (§114). Returns rows removed."""
        p = self._path(tenant)
        if not p.exists():
            return 0
        cutoff = time.time() - days * 86400
        kept, removed = [], 0
        for line in p.read_text("utf-8").splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except Exception:
                removed += 1
                continue
            if float(d.get("timestamp", 0)) < cutoff:
                removed += 1
            else:
                kept.append(line)
        p.write_text("\n".join(kept) + ("\n" if kept else ""), "utf-8")
        return removed
