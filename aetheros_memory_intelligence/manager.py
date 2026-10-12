"""MemoryIntelligence — the fabric facade.

Wires the modules together into a single, testable entry point:

    MemoryIntelligence(root) -> store + pipeline + retriever + context +
                                audit + transfer + backup + retention

All high-level operations go through this facade so consumers (CLI, tools,
agent integrations) have ONE way to talk to the fabric, and every operation
is audited and boundary-checked.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_memory_intelligence.audit import MemoryAudit
from aetheros_memory_intelligence.backup import FabricBackupService
from aetheros_memory_intelligence.boundaries import AccessContext, BoundaryPolicy, MemoryBoundaries
from aetheros_memory_intelligence.cache import ScopeIsolatedCache
from aetheros_memory_intelligence.config import MemoryIntelligenceConfig
from aetheros_memory_intelligence.context_engine import ContextAssembler
from aetheros_memory_intelligence.dedup import DedupEngine
from aetheros_memory_intelligence.defense import InjectionDefense
from aetheros_memory_intelligence.grounding import GroundingEngine
from aetheros_memory_intelligence.loop_guard import RetrievalLoopGuard
from aetheros_memory_intelligence.provenance import ProvenanceRecord
from aetheros_memory_intelligence.retention import RetentionManager, RetentionPolicy
from aetheros_memory_intelligence.retrieval import RetrievalResult, SecureRetriever
from aetheros_memory_intelligence.schema import MemoryEntry, MemoryEntryBuilder, validate_entry
from aetheros_memory_intelligence.store import MemoryStore
from aetheros_memory_intelligence.trust import TrustModel
from aetheros_memory_intelligence.types import (
    MemoryBoundary,
    MemoryOrigin,
    MemoryState,
    MemoryType,
    TrustLevel,
    VerificationLevel,
)
from aetheros_memory_intelligence.versioning import ConflictDetector, VersionHistory
from aetheros_memory_intelligence.write_pipeline import WriteOutcome, WritePipeline


class MemoryIntelligence:
    """Facade over the fabric.  Composes the modules and audits operations."""

    def __init__(
        self,
        config: Optional[MemoryIntelligenceConfig] = None,
        *,
        store: Optional[MemoryStore] = None,
        audit: Optional[MemoryAudit] = None,
    ) -> None:
        self._config = config or MemoryIntelligenceConfig()
        self._root = Path(self._config.effective_storage_dir)

        # Composable store/audit (tests inject alternatives).
        self._store = store or MemoryStore()
        self._audit = audit or MemoryAudit(enabled=self._config.audit_enabled)

        # Boundaries.
        self._boundaries = MemoryBoundaries(BoundaryPolicy())
        self._trust = TrustModel(decay_half_life_days=self._config.retention_decay_days)
        self._defense = InjectionDefense(scan_secrets=self._config.secret_scan_enabled)
        self._dedup = DedupEngine(enabled=self._config.dedup_enabled)
        self._conflicts = ConflictDetector(enabled=self._config.conflict_detection_enabled)
        self._versions = VersionHistory()
        self._retention = RetentionManager(RetentionPolicy(enabled=self._config.retention_enabled))

        self._pipeline = WritePipeline(
            self._store,
            boundaries=self._boundaries,
            defense=self._defense,
            dedup=self._dedup,
            conflicts=self._conflicts,
            versions=self._versions,
            retention=self._retention,
            enabled_flags={
                "poison_defense_enabled": self._config.poison_defense_enabled,
                "secret_scan_enabled": self._config.secret_scan_enabled,
                "dedup_enabled": self._config.dedup_enabled,
                "versioning_enabled": self._config.versioning_enabled,
            },
        )

        self._retriever = SecureRetriever(
            self._store,
            boundaries=self._boundaries,
            trust=self._trust,
            top_k=self._config.retrieval_top_k,
            min_score=self._config.retrieval_min_score,
        )
        self._grounding = GroundingEngine(min_confidence=self._config.grounding_min_confidence)
        self._assembler = ContextAssembler(budget_tokens=self._config.context_token_budget)
        self._cache = ScopeIsolatedCache(ttl_seconds=self._config.cache_ttl_seconds)
        self._loop_guard = RetrievalLoopGuard(enabled=self._config.loop_guard_enabled)
        self._transfer = None  # lazy (needs root)
        self._fabric_backup = None
        self._initialized = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self, root: Optional[Path] = None) -> None:
        if root is not None:
            self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._store.initialize(self._root / "store")
        self._audit.initialize(self._root / "audit")
        self._initialized = True

    @property
    def config(self) -> MemoryIntelligenceConfig:
        return self._config

    @property
    def store(self) -> MemoryStore:
        return self._store

    @property
    def pipeline(self) -> WritePipeline:
        return self._pipeline

    @property
    def boundaries(self) -> MemoryBoundaries:
        return self._boundaries

    @property
    def trust_model(self) -> TrustModel:
        return self._trust

    @property
    def conflicts(self) -> ConflictDetector:
        return self._conflicts

    @property
    def versions(self) -> VersionHistory:
        return self._versions

    @property
    def retention(self) -> RetentionManager:
        return self._retention

    @property
    def audit(self) -> MemoryAudit:
        return self._audit

    def _require_init(self) -> None:
        if not self._initialized:
            raise RuntimeError("MemoryIntelligence not initialized; call initialize() first")

    def _log_audit(self, operation: str, entry_id: str = "", actor: str = "", **detail: Any) -> None:
        self._audit.record(operation=operation, entry_id=entry_id, actor=actor, detail=detail)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def remember(
        self,
        content: str,
        actor: AccessContext,
        *,
        memory_type: MemoryType = MemoryType.SEMANTIC,
        boundary: Optional[MemoryBoundary] = None,
        origin: MemoryOrigin = MemoryOrigin.CONVERSATION,
        summary: str = "",
        tags: Optional[List[str]] = None,
        source: str = "",
        source_uri: str = "",
        confidence: float = 0.0,
        trust: float = 0.0,
        ttl: float = 0.0,
        provenance: Optional[ProvenanceRecord] = None,
        metadata: Optional[Dict[str, Any]] = None,
        semantic_key: str = "",
    ) -> WriteOutcome:
        self._require_init()
        boundary = boundary or MemoryBoundary(self._config.default_boundary)
        if not provenance:
            provenance = ProvenanceRecord(
                origin=origin,
                source=source,
                source_uri=source_uri,
                agent=actor.agent_id or actor.user_id or "memory",
            )
        if trust <= 0:
            trust = self._trust.initial_trust(origin.default_trust)
        if confidence <= 0:
            confidence = trust  # initial confidence mirrors initial trust
        meta = dict(metadata or {})
        if semantic_key:
            meta["semantic_key"] = semantic_key

        builder = MemoryEntryBuilder()
        entry = (
            builder
            .type(memory_type)
            .boundary(boundary)
            .origin(origin)
            .content(content)
            .summary(summary)
            .tags(tags or [])
            .scope(user_id=actor.user_id, workspace_id=actor.workspace_id,
                   session_id=actor.session_id, agent_id=actor.agent_id)
            .provenance(source=source, source_uri=source_uri,
                        confidence=confidence, trust=trust,
                        verification=VerificationLevel.UNVERIFIED.value)
            .ttl(ttl or self._config.retention_default_ttl)
            .metadata(meta)
            .build()
        )
        entry.confidence = confidence
        entry.trust = trust
        entry.corroborated_by = list(provenance.corroborating_sources)

        outcome = self._pipeline.process(entry, actor, provenance=provenance)
        self._audit.record(
            operation="write",
            entry_id=entry.id,
            actor=actor.user_id or actor.agent_id,
            detail={"action": outcome.action},
        )
        if outcome.entry is not None:
            self._cache.invalidate([outcome.entry.id])
        return outcome

    def forget(self, entry_id: str, actor: AccessContext) -> bool:
        self._require_init()
        entry = self._store.get(entry_id)
        if entry is None:
            return False
        if not self._boundaries.can_write(entry, actor):
            self._audit.record(operation="forget_denied", entry_id=entry_id,
                               actor=actor.user_id or actor.agent_id)
            raise PermissionError("boundary denied for forget")
        removed = self._store.delete(entry_id)
        if removed:
            self._cache.invalidate([entry_id])
            self._audit.record(operation="forget", entry_id=entry_id,
                               actor=actor.user_id or actor.agent_id)
        return removed

    # ------------------------------------------------------------------
    # Read / retrieval
    # ------------------------------------------------------------------

    def recall(
        self,
        query: str,
        actor: AccessContext,
        *,
        top_k: Optional[int] = None,
        use_cache: bool = True,
    ) -> RetrievalResult:
        self._require_init()
        if self._config.cache_enabled and use_cache:
            cached = self._cache.get(actor, query, str(top_k or self._config.retrieval_top_k))
            if cached is not None:
                cached.used_cache = True
                return cached
        result = self._retriever.retrieve(query, actor, top_k=top_k)
        if self._config.cache_enabled:
            self._cache.put(actor, query, result, str(top_k or self._config.retrieval_top_k))
        self._audit.record(operation="recall", actor=actor.user_id or actor.agent_id,
                           detail={"query": query[:80], "found": result.total_found})
        return result

    def retrieve_with_loop_guard(
        self,
        query: str,
        actor: AccessContext,
        *,
        top_k: Optional[int] = None,
        use_cache: bool = True,
    ) -> RetrievalResult:
        """recall() guarded against retrieval loops."""
        decision = self._loop_guard.check(
            query,
            user_id=actor.user_id, workspace_id=actor.workspace_id,
            session_id=actor.session_id, agent_id=actor.agent_id,
        )
        if not decision.allowed:
            result = RetrievalResult(query=query, memories=[])
            result.total_found = 0
            result.loop_guard_reason = decision.reason
            return result
        return self.recall(query, actor, top_k=top_k, use_cache=use_cache)

    def assemble_context(self, query: str, actor: AccessContext, *, budget_tokens: Optional[int] = None) -> Any:
        """Retrieve + ground + frame into a cache-safe context block."""
        result = self.retrieve_with_loop_guard(query, actor)
        assembler = self._assembler
        if budget_tokens is not None:
            from aetheros_memory_intelligence.context_engine import ContextAssembler as CA
            assembler = CA(budget_tokens=budget_tokens)
        return assembler.assemble(result.memories)

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def run_retention(self, actor: AccessContext) -> Dict[str, Any]:
        """Apply TTL/archive/purge policy; archive-eligible entries set ARCHIVED."""
        self._require_init()
        keep, forget = self._retention.apply(self._store.all(), self._trust.trust_for)
        purged = 0
        archived = 0
        for entry in forget:
            if self._store.delete(entry.id):
                purged += 1
        for entry in keep:
            if entry.state == MemoryState.ARCHIVED:
                self._store.save(entry)
                archived += 1
        self._audit.record(operation="retention", actor=actor.user_id or actor.agent_id,
                           detail={"purged": purged, "archived": archived})
        return {"purged": purged, "archived": archived}

    def integrity_check(self) -> Dict[str, Any]:
        self._require_init()
        report = self._store.integrity_scan()
        chain_valid = self._audit.verify_chain()
        report["audit_chain_valid"] = chain_valid
        return report

    def memory2(self):
        """Master 41 MemoryService bound to this fabric's root (agent integration).

        Sections 30-32: planners call ``get_context(task)`` before planning;
        computer/research flows call ``retrieve``/``research_reuse`` first.
        """
        from aetheros_memory_intelligence.service import MemoryService
        if getattr(self, "_memory2", None) is None:
            self._memory2 = MemoryService(root=self._root / "memory2")
            self._memory2.initialize()
            try:
                migrated = self._memory2.migrate_entries(self._store.all())
                if migrated.get("migrated"):
                    self._audit.record(operation="memory2_migrate",
                                       detail=migrated)
            except Exception:
                pass
        return self._memory2

    def status(self) -> Dict[str, Any]:
        self._require_init()
        return {
            "initialized": self._initialized,
            "store": self._store.stats(),
            "audit": self._audit.stats(),
            "cache": self._cache.stats(),
            "conflicts": len(self._conflicts.all_conflicts()),
            "config": self._config.to_dict(),
        }

    def export(self, destination: Path, *, include_archived: bool = False) -> Any:
        self._require_init()
        from aetheros_memory_intelligence.transfer import TransferService
        svc = TransferService(self._store, defense=self._defense)
        result = svc.export(destination, include_archived=include_archived)
        self._audit.record(operation="export", detail={"path": str(destination)})
        return result

    def import_bundle(self, source: Path) -> Any:
        self._require_init()
        from aetheros_memory_intelligence.transfer import TransferService
        svc = TransferService(self._store, defense=self._defense)
        report = svc.import_bundle(source)
        self._cache.invalidate_all()
        self._audit.record(operation="import",
                           detail={"imported": report.imported, "rejected": report.rejected})
        return report

    def fabric_backup(self, destination: Path, *, include_archived: bool = False) -> Any:
        self._require_init()
        svc = FabricBackupService(self._store)
        result = svc.create(destination, include_archived=include_archived)
        self._audit.record(operation="backup", detail={"path": str(destination)})
        return result

    def fabric_restore(self, source: Path, *, overwrite: bool = True) -> Dict[str, Any]:
        self._require_init()
        svc = FabricBackupService(self._store)
        report = svc.restore(source, overwrite=overwrite)
        self._cache.invalidate_all()
        self._audit.record(operation="restore", detail=report)
        return report

    def full_home_backup(self) -> Optional[Any]:
        from aetheros_memory_intelligence.backup import full_home_backup as fhb
        entry = fhb()
        self._audit.record(operation="full_home_backup",
                           detail={"entry_id": getattr(entry, "backup_id", "")})
        return entry