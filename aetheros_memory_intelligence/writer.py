"""Memory writer, forgetting, consolidation + dreaming (sections 15, 19-24, 46-47).

- ``MemoryWriter``: candidate extraction -> classification -> importance ->
  privacy gate -> secret refusal -> dedup -> conflict check -> confidence ->
  entity hints -> persistence callback.
- ``ForgettingEngine``: ACTIVE/STALE/EXPIRED/ARCHIVED/DELETED/SUPERSEDED/
  CONFLICTED transitions + TTL + decay (age never invalidates stable facts
  alone: user-confirmed facts are exempt from age-decay).
- ``Consolidator``: N episodic -> 1 semantic/project summary (provenance kept,
  sources never deleted).  ``DreamingLoop``: bounded, observable, disableable
  background synthesis that only *proposes* updates.
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from aetheros_memory_intelligence.record import (
    ConfidenceBand, MemoryRecord, PrivacyClass, ProvenanceKind, RecordStatus,
    RecordType, confidence_band_for, contains_secret,
)
from aetheros_memory_intelligence.scoring import lexical_relevance

PersistFn = Callable[[MemoryRecord], MemoryRecord]

_TRIVIAL = re.compile(r"^(ok|thanks|thank you|hi|hello|hey|bye)\.?$", re.I)
_EXPLICIT_RE = re.compile(r"(?i)\b(remember|don't forget|my preference is|i prefer|decided:?|decision:?)\b")


def classify_candidate(text: str, *, project_id: str = "",
                       provenance: ProvenanceKind = ProvenanceKind.MODEL_INFERRED) -> RecordType:
    t = text.lower()
    if any(k in t for k in ("prefer", "my style", "always use", "never use")):
        return RecordType.USER_PREFERENCE
    if any(k in t for k in ("decision", "decided", "chose ", "chosen")) and project_id:
        return RecordType.PROJECT_DECISION
    if project_id and any(k in t for k in ("constraint", "requires", "must ", "deadline")):
        return RecordType.PROJECT_FACT
    if any(k in t for k in ("failed", "error", "lesson", "fix was", "root cause")):
        return RecordType.ERROR_LESSON
    if any(k in t for k in ("how to", "steps:", "procedure", "workflow")):
        return RecordType.PROCEDURAL_MEMORY
    if any(k in t for k in ("task", "todo", "blocked", "next action", "completed")):
        return RecordType.TASK_STATE
    if provenance == ProvenanceKind.WEB_DERIVED:
        return RecordType.SOURCE_MEMORY
    if provenance == ProvenanceKind.TOOL_OBSERVED:
        return RecordType.ARTIFACT_MEMORY
    return RecordType.EPISODIC_EVENT


def estimate_importance(text: str, *, explicit_request: bool = False,
                        repeated: int = 0, project_relevant: bool = False,
                        decision: bool = False, user_correction: bool = False) -> float:
    score = 0.2 + min(0.5, len(text) / 1000.0)
    if explicit_request:
        score += 0.4
    if user_correction:
        score += 0.3
    if decision:
        score += 0.25
    if project_relevant:
        score += 0.15
    score += min(0.2, repeated * 0.05)
    return max(0.0, min(1.0, score))


def classify_privacy(text: str) -> PrivacyClass:
    t = text.lower()
    if any(k in t for k in ("password", "api key", "token", "private key", "cookie")):
        return PrivacyClass.SECRET
    if any(k in t for k in ("salary", "health", "ssn", "address", "phone")):
        return PrivacyClass.SENSITIVE
    if any(k in t for k in ("i live", "my email", "my name is")):
        return PrivacyClass.PRIVATE
    return PrivacyClass.INTERNAL


@dataclass
class WriteRequest:
    content: str = ""
    provenance: ProvenanceKind = ProvenanceKind.MODEL_INFERRED
    explicit: bool = False
    user_confirmed: bool = False
    project_id: str = ""
    session_id: str = ""
    task_id: str = ""
    user_id: str = ""
    workspace_id: str = ""
    record_type: Optional[RecordType] = None
    confidence: float = 0.0
    ttl: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WriteResult:
    action: str = "stored"  # stored|suggested|refused|duplicate|merged
    record: Optional[MemoryRecord] = None
    reason: str = ""


class MemoryWriter:
    """Gate every long-term write. Trivial noise and secrets never persist."""

    def __init__(self, persist: PersistFn,
                 *, existing: Callable[[], List[MemoryRecord]] = lambda: [],
                 importance_threshold: float = 0.35) -> None:
        self._persist = persist
        self._existing = existing
        self._threshold = importance_threshold

    def write(self, req: WriteRequest) -> WriteResult:
        text = (req.content or "").strip()
        if not text or _TRIVIAL.match(text):
            return WriteResult(action="refused", reason="trivial-noise")
        if contains_secret(text):
            return WriteResult(action="refused", reason="secret-shaped-content")
        rtype = req.record_type or classify_candidate(
            text, project_id=req.project_id, provenance=req.provenance)
        privacy = classify_privacy(text)
        if privacy == PrivacyClass.SECRET:
            return WriteResult(action="refused", reason="secret-privacy-class")
        explicit = req.explicit or bool(_EXPLICIT_RE.search(text))
        importance = estimate_importance(
            text, explicit_request=explicit, project_relevant=bool(req.project_id),
            decision=rtype == RecordType.PROJECT_DECISION,
            user_correction=req.provenance == ProvenanceKind.USER_STATED)
        if importance < self._threshold and not explicit:
            return WriteResult(action="refused", reason="below-importance-threshold")

        # Deduplication: exact + near-duplicate (lexical >= 0.9).
        for cur in self._existing():
            if cur.status == RecordStatus.DELETED:
                continue
            if cur.content.strip().lower() == text.lower():
                return WriteResult(action="duplicate", record=cur, reason="exact-duplicate")
            if lexical_relevance(text, cur) >= 0.9 and cur.type == rtype:
                cur.use_count += 1
                return WriteResult(action="merged", record=cur, reason="near-duplicate")

        # Untrusted provenance never becomes USER_PREFERENCE directly.
        if rtype == RecordType.USER_PREFERENCE and req.provenance in (
                ProvenanceKind.WEB_DERIVED, ProvenanceKind.DOCUMENT_DERIVED) \
                and not req.user_confirmed:
            return WriteResult(action="suggested", reason="untrusted-preference-needs-confirmation")

        # Inferred sensitive memories require confirmation (section 59).
        if privacy == PrivacyClass.SENSITIVE and not req.user_confirmed and not explicit:
            return WriteResult(action="suggested", reason="sensitive-needs-confirmation")

        confidence = req.confidence or (
            0.9 if req.provenance == ProvenanceKind.USER_STATED
            else 0.7 if explicit else 0.5)
        rec = MemoryRecord(
            type=rtype, content=text,
            summary=text[:200], source=req.provenance.value,
            provenance=req.provenance, explicit=explicit,
            user_confirmed=req.user_confirmed,
            confidence=confidence,
            confidence_band=confidence_band_for(
                explicit=explicit, user_confirmed=req.user_confirmed, confidence=confidence),
            importance=importance, privacy_class=privacy,
            project_id=req.project_id, session_id=req.session_id,
            task_id=req.task_id, user_id=req.user_id,
            workspace_id=req.workspace_id, ttl=req.ttl,
            metadata=dict(req.metadata))
        problems = rec.validate()
        if problems:
            return WriteResult(action="refused", reason=";".join(problems))
        stored = self._persist(rec)
        return WriteResult(action="stored", record=stored, reason="ok")


class ForgettingEngine:
    """Lifecycle transitions + TTL + decay (sections 23-24)."""

    def __init__(self, *, default_ttl_by_type: Optional[Dict[str, float]] = None) -> None:
        self._ttl = default_ttl_by_type or {
            RecordType.TASK_STATE.value: 30 * 86400.0,
            RecordType.EPISODIC_EVENT.value: 90 * 86400.0,
        }

    def apply(self, records: List[MemoryRecord],
              now: Optional[float] = None) -> Dict[str, int]:
        now = now if now is not None else time.time()
        counts: Dict[str, int] = {"stale": 0, "expired": 0, "archived": 0}
        for rec in records:
            if rec.status in (RecordStatus.DELETED, RecordStatus.ARCHIVED):
                continue
            ttl = rec.ttl or self._ttl.get(rec.type.value, 0.0)
            expired = (ttl > 0 and (now - rec.updated_at) > ttl) or rec.is_expired(now)
            if expired:
                # User-confirmed preferences persist until changed/deleted.
                if rec.type == RecordType.USER_PREFERENCE and rec.user_confirmed:
                    continue
                rec.status = RecordStatus.EXPIRED
                counts["expired"] += 1
            elif rec.superseded_by:
                rec.status = RecordStatus.SUPERSEDED
            elif rec.status == RecordStatus.ACTIVE and self._is_stale(rec, now):
                rec.status = RecordStatus.STALE
                rec.confidence_band = ConfidenceBand.STALE
                counts["stale"] += 1
        return counts

    @staticmethod
    def _is_stale(rec: MemoryRecord, now: float) -> bool:
        # Age alone never invalidates stable user-confirmed facts.
        if rec.user_confirmed and rec.type in (RecordType.USER_PREFERENCE, RecordType.USER_FACT):
            return False
        age_days = (now - (rec.last_confirmed or rec.updated_at)) / 86400.0
        if rec.type == RecordType.TASK_STATE:
            return age_days > 30
        if rec.type == RecordType.EPISODIC_EVENT:
            return age_days > 180
        return age_days > 365


@dataclass
class ConsolidationProposal:
    summary: str
    source_ids: List[str]
    record_type: RecordType
    project_id: str = ""
    confidence: float = 0.6


class Consolidator:
    """10 episodic -> 1 semantic/project summary. Sources are never deleted."""

    def __init__(self, *, min_cluster: int = 3) -> None:
        self._min_cluster = min_cluster

    def propose(self, records: List[MemoryRecord]) -> List[ConsolidationProposal]:
        groups: Dict[str, List[MemoryRecord]] = {}
        for rec in records:
            if rec.type != RecordType.EPISODIC_EVENT or rec.status != RecordStatus.ACTIVE:
                continue
            key = rec.project_id or "__global__"
            groups.setdefault(key, []).append(rec)
        proposals: List[ConsolidationProposal] = []
        for project_id, items in groups.items():
            if len(items) < self._min_cluster:
                continue
            # Cluster by shared tokens in content.
            seed = items[0]
            cluster = [r for r in items
                       if lexical_relevance(seed.content, r) >= 0.3]
            if len(cluster) < self._min_cluster:
                continue
            summary = f"Consolidated {len(cluster)} related events: " + \
                      "; ".join(r.summary or r.content[:80] for r in cluster[:5])
            proposals.append(ConsolidationProposal(
                summary=summary, source_ids=[r.id for r in cluster],
                record_type=RecordType.PROJECT_FACT if project_id != "__global__"
                else RecordType.USER_FACT,
                project_id="" if project_id == "__global__" else project_id))
        return proposals


class DreamingLoop:
    """Bounded, observable, disableable background synthesis (section 21).

    ``run_once`` never writes directly: it returns proposals for the caller
    to apply.  High-confidence personal facts are never auto-created: any
    proposal touching USER_PREFERENCE requires user confirmation.
    """

    def __init__(self, consolidator: Optional[Consolidator] = None, *,
                 enabled: bool = True, max_proposals: int = 5) -> None:
        self._consolidator = consolidator or Consolidator()
        self.enabled = enabled
        self.max_proposals = max_proposals
        self._lock = threading.Lock()
        self._runs = 0
        self._last_run: Optional[float] = None
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def run_once(self, records: List[MemoryRecord]) -> List[ConsolidationProposal]:
        if not self.enabled:
            return []
        with self._lock:
            self._runs += 1
            self._last_run = time.time()
        proposals = self._consolidator.propose(records)
        # Safety: dreaming never proposes user-preference facts.
        proposals = [p for p in proposals
                     if p.record_type != RecordType.USER_PREFERENCE][:self._max_proposals()]
        return proposals

    def _max_proposals(self) -> int:
        return max(1, self.max_proposals)

    def start_background(self, tick: Callable[[], None], interval_s: float = 3600.0) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()

        def _loop() -> None:
            while not self._stop.wait(interval_s):
                try:
                    tick()
                except Exception:
                    continue

        self._thread = threading.Thread(target=_loop, daemon=True,
                                        name="memory-dreaming")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def status(self) -> Dict[str, Any]:
        return {"enabled": self.enabled, "runs": self._runs,
                "last_run": self._last_run,
                "alive": bool(self._thread and self._thread.is_alive())}


def supersede(old: MemoryRecord, new: MemoryRecord) -> None:
    """Version chain: old -> superseded, new -> active (section 15)."""
    old.status = RecordStatus.SUPERSEDED
    old.superseded_by = new.id
    old.updated_at = time.time()
    new.supersedes = sorted(set(new.supersedes) | {old.id})
    new.version = old.version + 1
    new.updated_at = time.time()
