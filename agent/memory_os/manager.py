"""MemoryManager — the unified memory facade (P1).

store / retrieve / update / merge / forget / expire / archive / restore /
search / rank / summarize / link / unlink / audit — plus preference memory
(P7), explicit user commands (P19), confirmation-gated long-term writes
(P20), deletion cascade (P22-23), private mode & controls (P65-66),
export/import (P67-68), encrypted backup (P69-70), observability (P80),
and trust-ordered context assembly (P91-92).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from agent.memory_os.entities import EntityRegistry
from agent.memory_os.graph import KnowledgeGraph
from agent.memory_os.lifecycle import Lifecycle
from agent.memory_os.models import (
    Confidence,
    FeedbackKind,
    MemoryItem,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    PreferenceKind,
    RelationshipType,
    Sensitivity,
    SourceType,
)
from agent.memory_os.retrieval import RetrievalResult, Retriever, WorkingMemory
from agent.memory_os.security import (
    AccessContext,
    AccessDenied,
    ActorKind,
    check_read_access,
    pre_persist_check,
)


@dataclass
class StoreOutcome:
    item: MemoryItem
    effective_status: MemoryStatus
    classification: List[str]
    conflict_with: Optional[str] = None
    merged_into: Optional[str] = None
    needs_confirmation: bool = False


class Controls:
    """P65 toggles + P66 private mode. Defaults are conservative but usable:
    memory enabled; auto-store of trivial working/episodic context allowed;
    long-term personal retention requires approval when confirm_sensitive."""

    def __init__(self) -> None:
        self.enabled = True
        self.project_memory = True
        self.session_only = False
        self.private_mode = False
        self.confirm_personal_long_term = True

    def to_dict(self) -> Dict[str, bool]:
        return {
            "enabled": self.enabled,
            "project_memory": self.project_memory,
            "session_only": self.session_only,
            "private_mode": self.private_mode,
            "confirm_personal_long_term": self.confirm_personal_long_term,
        }


class MemoryManager:
    def __init__(self, store=None):
        from agent.memory_os.store import MemoryStore

        self.store = store or MemoryStore()
        self.controls = Controls()
        self.lifecycle = Lifecycle(self.store)
        self.entities = EntityRegistry(self.store)
        self.graph = KnowledgeGraph(self.store, self.entities)
        self.retriever = Retriever(self.store)
        self.embedding_index = None

    # ------------------------------------------------------------ semantic (P42/P71-73)

    def enable_semantic_search(self, provider=None) -> "EmbeddingIndex":
        """Activate offline vector retrieval. Default provider is the
        deterministic HashingEmbedder; any EmbeddingProvider subclasses in
        (cloud or local) plug in through the same interface."""
        from agent.memory_os.embeddings import EmbeddingIndex, SemanticScorer

        self.embedding_index = EmbeddingIndex(self.store, provider)
        scorer = self.embedding_index.scorer()
        self.retriever.set_semantic_scorer(scorer)
        return self.embedding_index

    # ------------------------------------------------------------ write path

    def remember(
        self,
        content: str,
        *,
        type_: MemoryType = MemoryType.SEMANTIC,
        source_type: SourceType = SourceType.USER_EXPLICIT,
        source_id: str = "",
        scope: MemoryScope = MemoryScope.USER,
        owner: str = "default",
        project_id: str = "",
        task_id: str = "",
        confidence: Confidence = Confidence.MEDIUM,
        importance: float = 0.5,
        sensitivity: Sensitivity = Sensitivity.INTERNAL,
        status: Optional[MemoryStatus] = None,
        preference_kind: PreferenceKind = PreferenceKind.NONE,
        semantic_key: str = "",
        tags: Optional[List[str]] = None,
        ttl_seconds: Optional[float] = None,
        valid_until: Optional[float] = None,
        allow_agents: bool = False,
        hint_only: bool = False,
        actor: str = "",
        channel: str = "",
        explicit: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ctx: Optional[AccessContext] = None,
        dedupe: bool = True,
    ) -> StoreOutcome:
        """Persist one memory through the full gate pipeline."""
        if not self.controls.enabled:
            raise AccessDenied("memory subsystem is disabled")
        if self.controls.private_mode and source_type is SourceType.USER_EXPLICIT \
                and scope in (MemoryScope.USER, MemoryScope.ORGANIZATION) \
                and sensitivity is not Sensitivity.SENSITIVE:
            # P66: private mode blocks conversation-derived LONG-TERM persistence.
            scope = MemoryScope.SESSION
        if self.controls.session_only and scope != MemoryScope.SESSION:
            scope = MemoryScope.SESSION
        if type_ is MemoryType.PROJECT and not self.controls.project_memory:
            raise AccessDenied("project memory disabled")

        item = MemoryItem(
            type=type_, content=content,
            summary=content[:120].strip(),
            source_type=source_type, source_id=source_id,
            scope=scope, owner=owner or "default",
            project_id=project_id, task_id=task_id,
            confidence=confidence, importance=max(0.0, min(1.0, importance)),
            sensitivity=sensitivity,
            preference_kind=preference_kind if type_ is MemoryType.PREFERENCE
            else PreferenceKind.NONE,
            semantic_key=semantic_key,
            tags=list(tags or []),
            allow_agents=allow_agents,
            hint_only=hint_only,
            expires_at=(time.time() + ttl_seconds) if ttl_seconds else None,
            valid_until=valid_until,
            metadata=dict(metadata or {}),
        )
        if explicit is None:
            explicit = source_type is SourceType.USER_EXPLICIT
        item.provenance.actor = actor or (
            ctx.actor_id if ctx else "unknown"
        )
        item.provenance.explicit = bool(explicit)
        item.provenance.channel = channel

        # P17 labels + firewall + secret gate decide the effective status.
        # Only explicit user statements are active by default; everything
        # else (inference/derived/external) starts as CANDIDATE (P18).
        if status is not None:
            item.status = status
        elif source_type is SourceType.USER_EXPLICIT and not hint_only:
            item.status = MemoryStatus.ACTIVE
        else:
            item.status = MemoryStatus.CANDIDATE
        effective = pre_persist_check(item)
        item.status = effective
        classification_labels = _classify(item)

        outcome = StoreOutcome(item=item, effective_status=effective,
                               classification=classification_labels)

        # P25 conflicts
        conflict = self.lifecycle.detect_conflict(item)
        if conflict is not None and effective == MemoryStatus.ACTIVE:
            outcome.conflict_with = conflict.memory_id
            item.status = MemoryStatus.CANDIDATE
            item.metadata["conflicts_with"] = conflict.memory_id

        # P48 dedup
        if dedupe and effective == MemoryStatus.ACTIVE:
            dup = self.lifecycle.find_duplicate(item)
            if dup is not None:
                self.lifecycle.merge_into(item, dup)
                outcome.merged_into = dup.memory_id
                self.store.audit.append("dedup", item.provenance.actor,
                                        target=item.memory_id,
                                        detail={"into": dup.memory_id})
                return outcome

        self.store.upsert_item(item, actor=item.provenance.actor)
        if effective == MemoryStatus.CANDIDATE and self._is_personal(item):
            outcome.needs_confirmation = True   # P20
        self.store.audit.append(
            "create", item.provenance.actor, target=item.memory_id,
            detail={"type": item.type.value, "status": item.status.value},
        )
        self.store.bump_counter("stored")
        return outcome

    @staticmethod
    def _is_personal(item: MemoryItem) -> bool:
        return item.scope in (MemoryScope.USER, MemoryScope.ORGANIZATION) and (
            item.type is MemoryType.PREFERENCE
            or item.sensitivity is Sensitivity.SENSITIVE
        )

    def confirm_candidate(self, memory_id: str, ctx: AccessContext,
                          approve: bool = True) -> Optional[MemoryItem]:
        """P18/P20 — human decision on a candidate long-term memory."""
        if ctx.kind is not ActorKind.USER:
            raise AccessDenied("only the user can approve candidates")
        item = self.store.get_item(memory_id)
        if item is None or item.status is not MemoryStatus.CANDIDATE:
            return None
        if approve:
            item.status = MemoryStatus.ACTIVE
            item.updated_at = time.time()
            self.store.upsert_item(item, actor=ctx.actor_id,
                                   note="candidate-approved")
            self.store.audit.append("confirm", ctx.actor_id, target=memory_id,
                                    detail={"approve": True})
            return item
        # denied: purge the candidate entirely
        self.store.delete_item(memory_id)
        self.store.audit.append("confirm", ctx.actor_id, target=memory_id,
                                detail={"approve": False})
        return None

    def update(self, memory_id: str, new_content: str, ctx: AccessContext,
               *, note: str = "") -> Optional[MemoryItem]:
        old = self.store.get_item(memory_id)
        if old is None or not check_read_access(old, ctx):
            return None
        new = old.with_content(new_content)
        pre_persist_check(new)  # secrets never enter via update either
        new.status = old.status
        self.store.upsert_item(old, actor=ctx.actor_id, note="pre-update")
        old.content = new.content
        old.summary = new.summary
        old.version = new.version
        old.updated_at = new.updated_at
        old.content_hash = new.content_hash
        self.store.upsert_item(old, actor=ctx.actor_id, note=note)
        self.store.audit.append("update", ctx.actor_id, target=memory_id,
                                detail={"version": new.version})
        return old

    # ------------------------------------------------------------ read path

    def search(self, query: str, ctx: AccessContext, **kw) -> RetrievalResult:
        return self.retriever.search(query, ctx, **kw)

    def get(self, memory_id: str, ctx: AccessContext) -> Optional[MemoryItem]:
        item = self.store.get_item(memory_id)
        if item is None or not check_read_access(item, ctx):
            return None
        item.touch_access()
        self.store.upsert_item(item, actor="get")
        return item

    def list(self, ctx: AccessContext, *, types=None, scopes=None,
             statuses=None, project_id=None, limit: int = 100) -> List[MemoryItem]:
        items = self.store.query_items(types=types, scopes=scopes,
                                       statuses=statuses or [
                                           MemoryStatus.ACTIVE,
                                           MemoryStatus.CANDIDATE],
                                       project_id=project_id, limit=limit)
        return [i for i in items if check_read_access(i, ctx)]

    def versions(self, memory_id: str, ctx: AccessContext) -> List[Dict[str, Any]]:
        item = self.get(memory_id, ctx)
        return self.store.versions(memory_id) if item else []

    # ------------------------------------------------------------ delete path (P22-23)

    def forget(self, memory_id: str, ctx: AccessContext) -> Dict[str, Any]:
        item = self.store.get_item(memory_id)
        deleted: Dict[str, Any] = {"memory_id": memory_id}
        if item is None or not check_read_access(item, ctx):
            deleted["deleted"] = False
            return deleted
        # cascade derived structures
        deleted["graph_edges"] = self.graph.purge_node("item", memory_id)
        deleted["versions_removed"] = len(self.store.versions(memory_id))
        ok = self.store.delete_item(memory_id)  # row + FTS + versions
        deleted["deleted"] = ok
        # verify non-resurrection
        deleted["retrievable_after"] = self.store.get_item(memory_id) is not None
        self.store.audit.append("forget", ctx.actor_id, target=memory_id,
                                detail={"ok": ok})  # tombstone w/o content
        self.store.bump_counter("forgotten")
        return deleted

    def forget_where(self, predicate: Callable[[MemoryItem], bool],
                     ctx: AccessContext) -> int:
        n = 0
        for item in self.list(ctx, statuses=list(MemoryStatus), limit=5000):
            try:
                match = predicate(item)
            except Exception:
                match = False
            if match:
                res = self.forget(item.memory_id, ctx)
                n += 1 if res.get("deleted") else 0
        return n

    # ------------------------------------------------------------ links (P12/P13)

    def link(
        self,
        src_kind: str, src_id: str,
        rel: RelationshipType,
        dst_kind: str, dst_id: str,
        *, evidence_item_id: str = "", confidence: float = 0.5,
    ) -> Dict[str, Any]:
        return self.graph.relate(src_kind, src_id, rel, dst_kind, dst_id,
                                 evidence_item_id=evidence_item_id,
                                 confidence=confidence)

    def unlink(self, edge_id: str) -> bool:
        return self.graph.unlink(edge_id)

    # ------------------------------------------------------------ summarize (P47)

    @staticmethod
    def summarize(items: List[MemoryItem]) -> str:
        """Extractive, provenance-preserving summary (heuristic, marked)."""
        if not items:
            return "(no memories)"
        parts = []
        for it in items[:10]:
            src = it.source_type.value
            when = time.strftime("%Y-%m-%d", time.localtime(it.created_at))
            text = (it.summary or it.content).replace("\n", " ")[:140]
            conf = it.confidence.value
            parts.append(f"- [{conf}/{src}/{when}] {text}")
        header = f"Summary of {len(items)} stored memories (extractive, heuristic):"
        return header + "\n" + "\n".join(parts)

    # ------------------------------------------------------------ export/import (P67-68)

    def export_items(self, path: str, ctx: AccessContext,
                     fmt: str = "json") -> Dict[str, Any]:
        items = self.list(ctx, statuses=[MemoryStatus.ACTIVE,
                                         MemoryStatus.ARCHIVED], limit=10000)
        payload = [i.to_row() | {
            "tags": i.tags,
            "provenance": i.provenance.to_dict(),
            "metadata": i.metadata,
        } for i in items]
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "jsonl":
            with out.open("w", encoding="utf-8") as fh:
                for p in payload:
                    fh.write(json.dumps(p, default=str) + "\n")
        elif fmt == "md":
            lines = ["# AetherOS memory export", ""]
            for p in payload:
                prov = p.get("provenance", {})
                lines.append(
                    f"- [{p['type']}|{p['scope']}] {p['content']}"
                    f"  _(source={p['source_type']}, actor={prov.get('actor','')},"
                    f" at={time.strftime('%Y-%m-%d', time.localtime(p['created_at']))})_"
                )
            out.write_text("\n".join(lines), encoding="utf-8")
        elif fmt == "csv":
            import csv
            with out.open("w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["memory_id", "type", "scope", "status",
                            "source_type", "created_at", "content"])
                for p in payload:
                    w.writerow([p["memory_id"], p["type"], p["scope"],
                                p["status"], p["source_type"],
                                p["created_at"], p["content"].replace("\n", "\\n")])
        else:
            out.write_text(json.dumps(payload, indent=2, default=str),
                           encoding="utf-8")
        self.store.audit.append("export", ctx.actor_id, target=str(out),
                                detail={"count": len(payload)})
        return {"path": str(out), "count": len(payload)}

    def import_items(self, path: str, ctx: AccessContext,
                     *, approve_all: bool = False) -> Dict[str, Any]:
        """P68 — validated import. Imported entries land as CANDIDATE unless
        explicitly approved by a user actor; injection-shaped content is
        quarantined; secrets are refused."""
        raw = Path(path).read_text(encoding="utf-8")
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()] \
            if path.endswith(".jsonl") else json.loads(raw)
        stats = {"total": 0, "stored": 0, "quarantined": 0, "refused": 0}
        for row in rows:
            stats["total"] += 1
            content = str(row.get("content", ""))
            try:
                outcome = self.remember(
                    content,
                    type_=MemoryType(row.get("type", "semantic")),
                    source_type=SourceType(row.get("source_type", "user_provided_file")),
                    scope=MemoryScope(row.get("scope", "user")),
                    owner=row.get("owner", ctx.actor_id),
                    project_id=row.get("project_id", ""),
                    sensitivity=Sensitivity(row.get("sensitivity", "internal")),
                    status=MemoryStatus.ACTIVE if approve_all
                    and ctx.kind is ActorKind.USER else MemoryStatus.CANDIDATE,
                    tags=[str(t) for t in row.get("tags", [])][:20],
                    actor=f"import:{ctx.actor_id}",
                    channel="import",
                )
                if outcome.effective_status is MemoryStatus.QUARANTINED:
                    stats["quarantined"] += 1
                else:
                    stats["stored"] += 1
            except Exception:
                stats["refused"] += 1
        self.store.audit.append("import", ctx.actor_id, target=path, detail=stats)
        return stats

    # ------------------------------------------------------------ backup (P69-70)

    def backup(self, path: str, encrypt: bool = False) -> Dict[str, Any]:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp_json = out.with_suffix(".tmp.json")
        payload = {
            "schema": "aetheros-memory-os-backup-v1",
            "items": [i.to_row() | {"tags": i.tags} for i in
                      self.store.query_items(statuses=list(MemoryStatus),
                                             limit=100000)],
            "entities": self.store.find_entities(),
            "edges": self.store.all_edges(),
        }
        text = json.dumps(payload, default=str)
        if encrypt:
            from aetheros_security.encryption import EncryptionManager

            em = EncryptionManager()
            out.write_text(em.encrypt(text), encoding="utf-8")
            result = {"path": str(out), "encrypted": True}
        else:
            out.write_text(text, encoding="utf-8")
            result = {"path": str(out), "encrypted": False}
        self.store.audit.append("backup", "system", target=result["path"],
                                detail={"encrypted": result["encrypted"]})
        return result

    def restore(self, path: str, *, replace: bool = False) -> Dict[str, Any]:
        src = Path(path)
        raw = src.read_text(encoding="utf-8")
        if not raw.lstrip().startswith("{"):
            from aetheros_security.encryption import EncryptionManager

            em = EncryptionManager()
            raw = em.decrypt(raw)
        payload = json.loads(raw)
        if payload.get("schema") != "aetheros-memory-os-backup-v1":
            raise ValueError("unsupported backup schema")
        count = 0
        for row in payload.get("items", []):
            item = MemoryItem.from_row(row)
            existing = self.store.get_item(item.memory_id)
            if existing is not None and not replace:
                continue  # never silently overwrite newer memory (P78)
            self.store.upsert_item(item, actor="restore")
            count += 1
        for ent in payload.get("entities", []):
            self.store.upsert_entity(ent)
        for edge in payload.get("edges", []):
            self.store.add_edge(edge)
        self.store.audit.append("restore", "system", target=str(src),
                                detail={"restored": count})
        return {"restored": count}

    # ------------------------------------------------------------ maintenance (P21, P49-50, P54, P87)

    def run_maintenance(self, *, dry_run: bool = False) -> Dict[str, Any]:
        report: Dict[str, Any] = {}
        report["expired"] = [] if dry_run else self.lifecycle.expire_sweep()
        report["stale_candidates"] = [
            i.memory_id for i in self.lifecycle.stale_candidates()]
        report["decay_candidates"] = [
            i.memory_id for i in self.lifecycle.decay_candidates()]
        consolidated = [] if dry_run else self.lifecycle.consolidate()
        report["consolidated"] = [c.memory_id for c in consolidated]
        if not dry_run:
            report["purged_expired_rows"] = self.lifecycle.purge_expired()
        self.store.audit.append("maintenance", "system", detail={"dry_run": dry_run})
        return report

    # ------------------------------------------------------------ observability (P80)

    def stats(self) -> Dict[str, Any]:
        active = self.store.query_items(statuses=[MemoryStatus.ACTIVE], limit=100000)
        candidates = self.store.query_items(statuses=[MemoryStatus.CANDIDATE],
                                            limit=100000)
        with_prov = sum(1 for i in active if i.provenance.actor)
        return {
            "active": len(active),
            "candidates": len(candidates),
            "provenance_coverage": round(with_prov / max(1, len(active)), 3),
            "queries": self.store.get_counter("queries"),
            "retrievals": self.store.get_counter("retrievals"),
            "stored": self.store.get_counter("stored"),
            "forgotten": self.store.get_counter("forgotten"),
            "db_path": str(self.store.path),
        }

    # ------------------------------------------------------------ audit access

    def audit_entries(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.store.audit.entries(limit)

    def audit_integrity(self) -> bool:
        return self.store.audit.verify()


def _classify(item: MemoryItem) -> List[str]:
    from agent.memory_os.models import classify_memory

    return classify_memory(source_type=item.source_type,
                           sensitivity=item.sensitivity,
                           status_hint=item.status)
