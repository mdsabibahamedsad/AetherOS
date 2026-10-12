"""Memory Intelligence Fabric configuration.

Mirrors the ``memory_intelligence`` section of ``config.yaml``.  Kept as a
standalone dataclass so the fabric can be constructed and tested without the
full AetherOS config loader, while ``load_config()`` bridges from the merged
DEFAULT_CONFIG dict used across the CLI/gateway.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from aetheros_constants import get_aetheros_home


@dataclass
class MemoryIntelligenceConfig:
    """Runtime configuration for the memory intelligence fabric."""

    enabled: bool = True
    # Storage root.  Empty -> ``<AETHEROS_HOME>/memory_intelligence``.
    storage_dir: str = ""
    # Scoping.  A query/entry is only visible within the same boundary scope
    # (see boundaries.py).  "user" is the strictest single-scope default.
    default_boundary: str = "user"
    # Write pipeline knobs.
    write_approval: bool = False          # stage writes for approval (not used by fabric store)
    poison_defense_enabled: bool = True
    secret_scan_enabled: bool = True
    dedup_enabled: bool = True
    versioning_enabled: bool = True
    conflict_detection_enabled: bool = True
    retention_enabled: bool = True
    # Retrieval knobs.
    retrieval_top_k: int = 8
    retrieval_min_score: float = 0.25
    retrieval_enable_semantic: bool = False   # requires an embedding engine
    retrieval_enable_keyword: bool = True
    grounding_min_confidence: float = 0.3     # below this, drop from context
    context_token_budget: int = 2400
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    loop_guard_enabled: bool = True
    # Retention defaults.
    retention_default_ttl: float = 0.0        # 0 = no expiry
    retention_decay_days: int = 90
    # Embedding bridge (optional).  When empty, semantic retrieval is skipped.
    embedding_provider: str = ""
    embedding_model: str = ""
    # Audit: keep an append-only audit log next to the store.
    audit_enabled: bool = True
    audit_max_entries: int = 10000

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "MemoryIntelligenceConfig":
        if not data:
            return cls()
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})

    @property
    def effective_storage_dir(self) -> Path:
        if self.storage_dir:
            return Path(self.storage_dir)
        return get_aetheros_home() / "memory_intelligence"

    def to_dict(self) -> Dict[str, Any]:
        return {f: getattr(self, f) for f in self.__dataclass_fields__}


def load_config(user_config: Optional[Dict[str, Any]] = None) -> MemoryIntelligenceConfig:
    """Build fabric config from a merged AetherOS config dict.

    The dict is expected to contain a ``memory_intelligence`` key (the deep
    merge of DEFAULT_CONFIG + user YAML).  Unknown keys are ignored so the
    fabric tolerates config sections from future versions.
    """
    if not user_config:
        return MemoryIntelligenceConfig()
    section = user_config.get("memory_intelligence") or {}
    if isinstance(section, dict):
        return MemoryIntelligenceConfig.from_dict(section)
    return MemoryIntelligenceConfig()


def default_config_section() -> Dict[str, Any]:
    """The DEFAULT_CONFIG fragment for the fabric (for aetheros_cli/config.py)."""
    return {
        # Memory & Knowledge Intelligence Fabric (aetheros_memory_intelligence).
        # Extends the built-in memory platform with provenance, trust,
        # boundaries, poisoning defense, secure retrieval and cache-safe
        # context assembly.  See aetheros_memory_intelligence/.
        "enabled": True,
        "default_boundary": "user",
        "poison_defense_enabled": True,
        "secret_scan_enabled": True,
        "dedup_enabled": True,
        "versioning_enabled": True,
        "conflict_detection_enabled": True,
        "retention_enabled": True,
        "retrieval_top_k": 8,
        "retrieval_min_score": 0.25,
        "retrieval_enable_semantic": False,
        "retrieval_enable_keyword": True,
        "grounding_min_confidence": 0.3,
        "context_token_budget": 2400,
        "cache_enabled": True,
        "cache_ttl_seconds": 300,
        "loop_guard_enabled": True,
        "retention_default_ttl": 0.0,
        "retention_decay_days": 90,
        "embedding_provider": "",
        "embedding_model": "",
        "audit_enabled": True,
        "audit_max_entries": 10000,
    }