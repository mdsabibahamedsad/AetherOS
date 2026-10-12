"""MemoryService: clean internal API for Memory 2.0 (section 60).

Conceptual API: remember / retrieve / search / explain / update / delete /
forget / consolidate / resolve_conflicts / get_project_memory /
get_entity_graph / get_timeline / get_context / health.

Persistence: records live in ``records.json`` next to the fabric store root
(atomic JSON, same pattern as store.py); v1 MemoryEntry bridging is handled
by record.to_entry/from_entry for migration.  Temporary mode (section 58)
disables long-term writes and background consolidation for the session.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aetheros_memory_intelligence.budget import MemoryBudgetManager
from aetheros_memory_intelligence.domains import (
    ResearchReuseDecision, build_project_view, decide_research_reuse,
)
from aetheros_memory_intelligence.events import EventBus, MemoryEvent
from aetheros_memory_intelligence.graph_store import (
    Entity, GraphStore, RelationType, Relationship,
)
from aetheros_memory_intelligence.hybrid import HybridRetriever, RetrievalQuery
from aetheros_memory_intelligence.quality import (
    MemoryMetrics, health_score, run_quality_checks,
)
from aetheros_memory_intelligence.record import (
    MemoryRecord, PrivacyClass, ProvenanceKind, RecordScope, RecordStatus,
    RecordType, confidence_band_for, scope_visible,
)
from aetheros_memory_intelligence.scoring import ScoringWeights
from aetheros_memory_intelligence.writer import (
    DreamingLoop, ForgettingEngine, MemoryWriter, WriteRequest, supersede,
)


class RecordStore:
    """Atomic JSON persistence for MemoryRecord v2."""

    def __init__(self, root: Optional[Path] = None) -> None:
        self._root = Path(root) if root else None
        self._lock = threading.RLock()
        self._records: Dict[str, MemoryRecord] = {}
        self._tombstones: List[str] = []

    def initialize(self, root: Optional[Path] = None) -> None:
        if root is not None:
            self._root = Path(root)
        if self._root is None:
            self._root = Path("./temp_records")
        self._root.mkdir(parents=True, exist_ok=True)
        self._load()

    def save(self, rec: MemoryRecord) -> MemoryRecord:
        with self._lock:
            rec.updated_at = time.time()
            self._records[rec.id] = rec
            self._persist()
            return rec

    def get(self, rid: str) -> Optional[MemoryRecord]:
        with self._lock:
            return self._records.get(rid)

    def all(self) -> List[MemoryRecord]:
        with self._lock:
            return list(self._records.values())

    def tombstone(self, rid: str) -> bool:
        with self._lock:
            rec = self._records.get(rid)
            if rec is None:
                return False
            rec.status = RecordStatus.DELETED
            rec.updated_at = time.time()
            self._tombstones.append(rid)
            self._persist()
            return True

    def purge_tombstones(self) -> int:
        with self._lock:
            n = 0
            for rid in list(self._tombstones):
                if rid in self._records:
                    self._records.pop(rid)
                    n += 1
            self._tombstones = []
            self._persist()
            return n

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def _path(self) -> Path:
        assert self._root is not None
        return self._root / "records.json"

    def _persist(self) -> None:
        if self._root is None:
            return
        data = {"records": {i: r.to_dict() for i, r in self._records.items()},
                "tombstones": self._tombstones}
        fd, tmp = tempfile.mkstemp(dir=str(self._root), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, str(self._path()))
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def _load(self) -> None:
        path = self._path()
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        for raw in (data.get("records") or {}).values():
            try:
                rec = MemoryRecord.from_dict(raw)
                self._records[rec.id] = rec
            except (ValueError, KeyError):
                continue
        self._tombstones = list(data.get("tombstones") or [])


class MemoryService:
    """One entry point for agent / research / desktop / MCP consumers."""

    def __init__(self, root: Optional[Path] = None, *,
                 weights: Optional[ScoringWeights] = None,
                 budget_tokens: int = 2400,
                 temporary_mode: bool = False) -> None:
        self._root = Path(root) if root else None
        self._records = RecordStore()
        self._graph = GraphStore()
        self._events = EventBus()
        self._metrics = MemoryMetrics()
        self._forgetting = ForgettingEngine()
        self._dreaming = DreamingLoop()
        self._budget = MemoryBudgetManager(budget_tokens)
        self._weights = weights or ScoringWeights()
        self._temporary = temporary_mode
        self._writer = MemoryWriter(persist=self._records.save,
                                    existing=self._records.all)
        self._retriever = HybridRetriever(self._records.all, graph=self._graph,
                                          weights=self._weights)
        self._last_consolidation = 0.0
        self._initialized = False

    # -- lifecycle -------------------------------------------------------
    def initialize(self, root: Optional[Path] = None) -> None:
        if root is not None:
            self._root = Path(root)
        if self._root is None:
            from aetheros_constants import get_aetheros_home
            self._root = get_aetheros_home() / "memory2"
        self._root.mkdir(parents=True, exist_ok=True)
        self._records.initialize(self._root / "records")
        self._graph.initialize(self._root / "graph")
        self._initialized = True

    @property
    def events(self) -> EventBus:
        return self._events

    @property
    def metrics(self) -> MemoryMetrics:
        return self._metrics

    @property
    def graph(self) -> GraphStore:
        return self._graph

    def set_temporary_mode(self, on: bool) -> None:
        self._temporary = on

    # -- write API ---------------------------------------------------------
    def remember(self, content: str, *,
                 record_type: Optional[RecordType] = None,
                 scope: RecordScope = RecordScope.USER,
                 provenance: ProvenanceKind = ProvenanceKind.USER_STATED,
                 explicit: bool = False, user_confirmed: bool = False,
                 project_id: str = "", session_id: str = "", task_id: str = "",
                 user_id: str = "", workspace_id: str = "",
                 confidence: float = 0.0, ttl: float = 0.0,
                 metadata: Optional[Dict[str, Any]] = None,
                 actor: str = "") -> Dict[str, Any]:
        if self._temporary:
            return {"action": "refused", "reason": "temporary-mode"}
        t0 = time.time()
        out = self._writer.write(WriteRequest(
            content=content, provenance=provenance, explicit=explicit,
            user_confirmed=user_confirmed, project_id=project_id,
            session_id=session_id, task_id=task_id, user_id=user_id,
            workspace_id=workspace_id, record_type=record_type,
            confidence=confidence, ttl=ttl, metadata=metadata or {}))
        if out.record is not None:
            out.record.scope = scope
            if project_id:
                out.record.project_id = project_id
            self._records.save(out.record)
        self._metrics.observe("memory_writes")
        self._metrics.observe("write_latency_ms", (time.time() - t0) * 1000.0)
        if out.action == "stored" and out.record is not None:
            self._events.emit(MemoryEvent(kind="MEMORY_CREATED",
                                          record_id=out.record.id, actor=actor))
        return {"action": out.action, "reason": out.reason,
                "id": out.record.id if out.record else ""}

    def update(self, rid: str, *, content: str = "", summary: str = "",
               confidence: float = -1.0, actor: str = "") -> bool:
        rec = self._records.get(rid)
        if rec is None or rec.status == RecordStatus.DELETED:
            return False
        if content:
            rec.content = content
        if summary:
            rec.summary = summary
        if confidence >= 0:
            rec.confidence = confidence
            rec.confidence_band = confidence_band_for(
                explicit=rec.explicit, user_confirmed=rec.user_confirmed,
                confidence=rec.confidence)
        rec.version += 1
        self._records.save(rec)
        self._events.emit(MemoryEvent(kind="MEMORY_UPDATED", record_id=rid, actor=actor))
        return True

    def supersede_memory(self, old_id: str, new_content: str, *,
                         actor: str = "", **kw: Any) -> str:
        old = self._records.get(old_id)
        if old is None:
            raise KeyError(old_id)
        new = MemoryRecord(type=old.type, scope=old.scope, content=new_content,
                           summary=new_content[:200], provenance=old.provenance,
                           project_id=old.project_id, session_id=old.session_id,
                           task_id=old.task_id, user_id=old.user_id,
                           workspace_id=old.workspace_id,
                           confidence=kw.get("confidence", old.confidence),
                           metadata=dict(old.metadata))
        supersede(old, new)
        self._records.save(old)
        self._records.save(new)
        self._events.emit(MemoryEvent(kind="MEMORY_SUPERSEDED", record_id=new.id,
                                      actor=actor, detail={"supersedes": old_id}))
        return new.id

    def delete(self, rid: str, *, actor: str = "") -> bool:
        ok = self._records.tombstone(rid)
        if ok:
            # Cascade: drop from graph-linked entity refs is handled by
            # tombstone visibility (graph neighbors skip tombstoned nodes).
            self._events.emit(MemoryEvent(kind="MEMORY_DELETED", record_id=rid,
                                          actor=actor))
        return ok

    def forget(self, *, record_id: str = "", topic: str = "",
               project_id: str = "", all_memories: bool = False,
               actor: str = "") -> Dict[str, int]:
        """Forget one memory / topic / project / all. Tombstones + invalidates."""
        removed = 0
        for rec in self._records.all():
            if rec.status == RecordStatus.DELETED:
                continue
            hit = False
            if record_id and rec.id == record_id:
                hit = True
            elif project_id and rec.project_id == project_id:
                hit = True
            elif topic and topic.lower() in rec.content.lower():
                hit = True
            elif all_memories:
                hit = True
            if hit:
                self._records.tombstone(rec.id)
                removed += 1
        if project_id:
            for ent in self._graph.all_entities():
                if ent.project_id == project_id:
                    self._graph.delete_entity(ent.id)
        self._retriever = HybridRetriever(self._records.all, graph=self._graph,
                                          weights=self._weights)
        self._events.emit(MemoryEvent(kind="MEMORY_DELETED", actor=actor,
                                      detail={"removed": removed, "topic": topic,
                                              "project_id": project_id}))
        return {"removed": removed}

    # -- read API ------------------------------------------------------------
    def retrieve(self, query: str, *,
                 scope: RecordScope = RecordScope.USER,
                 project_id: str = "", task_id: str = "",
                 top_k: int = 8, budget: int = 0,
                 mode: str = "hybrid") -> Dict[str, Any]:
        t0 = time.time()
        results = self._retriever.retrieve(RetrievalQuery(
            text=query, scope=scope, project_id=project_id, task_id=task_id,
            top_k=top_k, mode=mode))
        budgeted = self._budget.select(results, budget or self._budget.budget_tokens)
        self._metrics.observe("memory_reads")
        self._metrics.observe("retrieval_latency_ms", (time.time() - t0) * 1000.0)
        self._events.emit(MemoryEvent(kind="MEMORY_RETRIEVED",
                                      detail={"query": query[:80],
                                              "found": len(results)}))
        return {"query": query, "included": [r.to_dict() for r in budgeted.included],
                "excluded_ids": [r.record.id for r in budgeted.excluded],
                "tokens_used": budgeted.tokens_used, "budget": budgeted.budget,
                "total_candidates": len(results)}

    search = retrieve

    def get(self, rid: str) -> Optional[Dict[str, Any]]:
        rec = self._records.get(rid)
        if rec is None or rec.status == RecordStatus.DELETED:
            return None
        return rec.to_dict()

    def explain(self, rid: str) -> Optional[Dict[str, Any]]:
        """Why was this remembered? (section 39 — only real fields)."""
        rec = self._records.get(rid)
        if rec is None:
            return None
        return {"id": rec.id, "type": rec.type.value, "scope": rec.scope.value,
                "why": f"provenance={rec.provenance.value} explicit={rec.explicit} "
                       f"importance={rec.importance:.2f}",
                "source": rec.source, "source_id": rec.source_id,
                "observed_at": rec.observed_at, "created_at": rec.created_at,
                "last_confirmed": rec.last_confirmed, "last_used": rec.last_used,
                "use_count": rec.use_count, "confidence": rec.confidence,
                "confidence_band": rec.confidence_band.value,
                "evidence_ids": rec.evidence_ids, "entity_ids": rec.entity_ids,
                "supersedes": rec.supersedes, "superseded_by": rec.superseded_by,
                "status": rec.status.value}

    def get_project_memory(self, project_id: str) -> Dict[str, Any]:
        return build_project_view(project_id, self._records.all()).to_dict()

    def get_entity_graph(self, entity_id: str = "", *, depth: int = 1,
                         project_id: str = "") -> Dict[str, Any]:
        if entity_id:
            return self._graph.neighbors(entity_id, depth=depth, project_id=project_id)
        return {"entities": [e.to_dict() for e in self._graph.all_entities()[:200]],
                "relationships": [r.to_dict() for r in self._graph.all_relationships()[:500]],
                "stats": self._graph.stats()}

    def get_timeline(self, *, project_id: str = "", record_type: str = "",
                     min_confidence: float = 0.0, days: int = 30,
                     limit: int = 100) -> List[Dict[str, Any]]:
        now = time.time()
        cutoff = now - days * 86400.0
        out = []
        for rec in sorted(self._records.all(), key=lambda r: r.created_at, reverse=True):
            if rec.status == RecordStatus.DELETED or rec.created_at < cutoff:
                continue
            if project_id and rec.project_id != project_id:
                continue
            if record_type and rec.type.value != record_type:
                continue
            if rec.confidence < min_confidence:
                continue
            out.append({"id": rec.id, "type": rec.type.value, "created_at": rec.created_at,
                        "summary": rec.summary or rec.content[:160],
                        "confidence": rec.confidence, "status": rec.status.value,
                        "project_id": rec.project_id})
            if len(out) >= limit:
                break
        return out

    def get_context(self, task: str, **kw: Any) -> Dict[str, Any]:
        """Memory-aware planning context (sections 30-32): relevant slice only."""
        return self.retrieve(task, **kw)

    # -- maintenance -----------------------------------------------------------
    def consolidate(self, *, actor: str = "") -> Dict[str, Any]:
        from aetheros_memory_intelligence.writer import Consolidator
        proposals = Consolidator().propose(self._records.all())
        created = 0
        for p in proposals[:5]:
            rec = MemoryRecord(type=p.record_type, scope=RecordScope.PROJECT,
                               content=p.summary, summary=p.summary[:200],
                               provenance=ProvenanceKind.SYSTEM_GENERATED,
                               system_generated=True,
                               project_id=p.project_id, confidence=p.confidence,
                               evidence_ids=list(p.source_ids),
                               metadata={"consolidated_from": p.source_ids})
            self._records.save(rec)
            created += 1
        self._last_consolidation = time.time()
        self._events.emit(MemoryEvent(kind="MEMORY_CONSOLIDATED", actor=actor,
                                      detail={"proposals": len(proposals),
                                              "created": created}))
        return {"proposals": len(proposals), "created": created}

    def dream(self) -> Dict[str, Any]:
        proposals = self._dreaming.run_once(self._records.all())
        return {"proposals": [{"summary": p.summary, "sources": p.source_ids,
                               "type": p.record_type.value} for p in proposals],
                "dream_status": self._dreaming.status()}

    def resolve_conflicts(self, *, actor: str = "") -> Dict[str, Any]:
        """Newest user-confirmed/user-stated wins; others superseded; ties flagged."""
        by_key: Dict[str, List[MemoryRecord]] = {}
        for rec in self._records.all():
            if rec.type != RecordType.USER_PREFERENCE or \
                    rec.status != RecordStatus.ACTIVE:
                continue
            key = rec.content.strip().lower()[:60]
            by_key.setdefault("pref", []).append(rec)
        resolved = 0
        # Pairwise: same-type preferences with low mutual lexical overlap conflict.
        prefs = by_key.get("pref", [])
        for i, rec in enumerate(prefs):
            for other in prefs[i + 1:]:
                from aetheros_memory_intelligence.scoring import lexical_relevance
                if lexical_relevance(rec.content, other) < 0.4:
                    # Genuine conflict: newer explicit/confirmed wins.
                    winner, loser = (rec, other) if (
                        (rec.user_confirmed, rec.explicit, rec.updated_at) >=
                        (other.user_confirmed, other.explicit, other.updated_at)) \
                        else (other, rec)
                    supersede(loser, winner)
                    loser.status = RecordStatus.SUPERSEDED
                    winner.status = RecordStatus.ACTIVE
                    self._records.save(loser)
                    self._records.save(winner)
                    self._events.emit(MemoryEvent(kind="MEMORY_CONFLICTED",
                                                  record_id=winner.id, actor=actor,
                                                  detail={"loser": loser.id}))
                    resolved += 1
                    break
        return {"resolved": resolved}

    def run_forgetting(self) -> Dict[str, int]:
        return self._forgetting.apply(self._records.all())

    def research_reuse(self, question: str) -> Dict[str, Any]:
        d: ResearchReuseDecision = decide_research_reuse(question, self._records.all())
        return {"action": d.action, "claim_id": d.claim_id, "reason": d.reason}

    def quality(self) -> Dict[str, Any]:
        known = {e.id for e in self._graph.all_entities()}
        from aetheros_memory_intelligence.quality import run_quality_checks
        return run_quality_checks(self._records.all(), known_entity_ids=known).to_dict()

    def health(self) -> Dict[str, Any]:
        from aetheros_memory_intelligence.quality import (
            health_score, run_quality_checks,
        )
        known = {e.id for e in self._graph.all_entities()}
        rep = run_quality_checks(self._records.all(), known_entity_ids=known)
        h = health_score(rep, self._records.count(),
                         last_consolidation=self._last_consolidation)
        return {"health": h, "metrics": self._metrics.snapshot(),
                "graph": self._graph.stats(),
                "records": self._records.count(),
                "events": self._events.counts()}

    # -- graph writes ------------------------------------------------------------
    def add_entity(self, entity: Entity, *, actor: str = "") -> Entity:
        out = self._graph.upsert_entity(entity)
        self._events.emit(MemoryEvent(kind="ENTITY_CREATED", record_id=out.id, actor=actor))
        return out

    def link(self, source_id: str, target_id: str, rel: RelationType, *,
             confidence: float = 0.5, provenance: str = "model_inferred",
             project_id: str = "", actor: str = "") -> Relationship:
        r = self._graph.add_relationship(Relationship(
            source_id=source_id, target_id=target_id, type=rel,
            confidence=confidence, provenance=provenance, project_id=project_id))
        self._events.emit(MemoryEvent(kind="RELATIONSHIP_CREATED", record_id=r.id,
                                      actor=actor))
        return r

    # -- export / import (section 56: never secrets) -------------------------------
    def export(self, path: Path) -> Dict[str, Any]:
        recs = [r.to_dict() for r in self._records.all()
                if r.privacy_class != PrivacyClass.SECRET
                and r.status != RecordStatus.DELETED]
        payload = {"format": "aetheros-memory-export/1",
                   "exported_at": time.time(),
                   "records": recs,
                   "entities": [e.to_dict() for e in self._graph.all_entities()],
                   "relationships": [r.to_dict() for r in self._graph.all_relationships()]}
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        return {"records": len(recs), "path": str(path)}

    def import_bundle(self, path: Path) -> Dict[str, Any]:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        imported, rejected = 0, 0
        for raw in data.get("records", []):
            try:
                rec = MemoryRecord.from_dict(raw)
                if rec.validate():
                    rejected += 1
                    continue
                # Tombstone-respecting idempotency: skip ids already deleted.
                if self._records.get(rec.id) is not None:
                    continue
                self._records.save(rec)
                imported += 1
            except (ValueError, KeyError):
                rejected += 1
        return {"imported": imported, "rejected": rejected}

    # -- migration from v1 fabric entries -------------------------------------------
    def migrate_entries(self, entries: list) -> Dict[str, int]:
        n = 0
        for e in entries:
            rec = MemoryRecord.from_entry(e)
            if rec.validate():
                continue
            if self._records.get(rec.id) is None:
                self._records.save(rec)
                n += 1
        return {"migrated": n}
