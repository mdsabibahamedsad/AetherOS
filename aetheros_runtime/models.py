"""Canonical records (Master 45 sections 3-4, 11, 33-36, 74, 96).

ModelRecord / ProviderRecord / EmbeddingModel / RerankerModel /
VisionModel / AudioModel with provenance on every metadata claim
(anti-spoofing). Capabilities are explicit booleans, never inferred.
Unknown cost/pricing stays UNKNOWN (never invented).
"""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class ProviderKind(str, enum.Enum):
    CLOUD = "cloud"
    LOCAL = "local"
    SELF_HOSTED = "self_hosted"
    ON_PREMISE = "on_premise"
    LAN = "lan"
    REMOTE = "remote"
    DISTRIBUTED = "distributed"


class HealthState(str, enum.Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    AUTH_ERROR = "auth_error"
    RATE_LIMITED = "rate_limited"
    OVERLOADED = "overloaded"
    MISCONFIGURED = "misconfigured"
    NOT_INSTALLED = "not_installed"


class DataClass(str, enum.Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PRIVATE = "private"
    SENSITIVE = "sensitive"
    HIGHLY_SENSITIVE = "highly_sensitive"


class CircuitState(str, enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class Provenance:
    source: str = ""  # discovery|provider_api|local_runtime|config|extension|fallback_hint
    at: float = field(default_factory=time.time)
    by: str = ""


@dataclass
class Pricing:
    input_per_1k: Optional[float] = None
    output_per_1k: Optional[float] = None
    currency: str = "USD"
    version: str = "1"
    unknown: bool = True


@dataclass
class ModelRecord:
    model_id: str = ""
    provider_id: str = ""
    version: str = ""
    display_name: str = ""
    family: str = ""
    modality: List[str] = field(default_factory=list)
    context_window: int = 0
    output_limit: int = 0
    reasoning: bool = False
    reasoning_effort: List[str] = field(default_factory=list)
    tool_calling: bool = False
    parallel_tools: bool = False
    structured_output: bool = False
    vision: bool = False
    audio_in: bool = False
    audio_out: bool = False
    embeddings: bool = False
    streaming: bool = False
    batch: bool = False
    locality: str = "remote"  # local|remote (verified, not assumed)
    region: str = ""
    license: str = ""
    license_source_note: str = "License information provided by source"
    quantization: str = ""
    hardware_gb: float = 0.0
    pricing: Pricing = field(default_factory=Pricing)
    capabilities_provenance: Dict[str, Provenance] = field(default_factory=dict)
    status: str = HealthState.UNKNOWN.value
    last_checked: float = 0.0
    benchmark: Dict[str, Any] = field(default_factory=dict)
    privacy_note: str = ""
    deprecated: bool = False
    replacement: str = ""
    pinned: bool = False
    favorite: bool = False
    blocked: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def canonical_id(self) -> str:
        base = f"{self.provider_id}/{self.model_id}"
        return f"{base}@{self.version}" if self.version else base

    def to_dict(self) -> Dict[str, Any]:
        d = {k: getattr(self, k) for k in (
            "model_id", "provider_id", "version", "display_name",
            "family", "modality", "context_window", "output_limit",
            "reasoning", "reasoning_effort", "tool_calling",
            "parallel_tools", "structured_output", "vision", "audio_in",
            "audio_out", "embeddings", "streaming", "batch", "locality",
            "region", "license", "license_source_note", "quantization",
            "hardware_gb", "status", "last_checked", "benchmark",
            "privacy_note", "deprecated", "replacement", "pinned",
            "favorite", "blocked", "metadata")}
        d["canonical_id"] = self.canonical_id
        d["pricing"] = {"input_per_1k": self.pricing.input_per_1k,
                        "output_per_1k": self.pricing.output_per_1k,
                        "currency": self.pricing.currency,
                        "version": self.pricing.version,
                        "unknown": self.pricing.unknown}
        d["provenance"] = {k: {"source": v.source, "at": v.at, "by": v.by}
                           for k, v in self.capabilities_provenance.items()}
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ModelRecord":
        m = cls()
        for k in ("model_id", "provider_id", "version", "display_name",
                  "family", "context_window", "output_limit", "reasoning",
                  "tool_calling", "parallel_tools", "structured_output",
                  "vision", "audio_in", "audio_out", "embeddings",
                  "streaming", "batch", "locality", "region", "license",
                  "quantization", "hardware_gb", "status", "last_checked",
                  "privacy_note", "deprecated", "replacement", "pinned",
                  "favorite", "blocked"):
            if k in d:
                setattr(m, k, d[k])
        for k in ("modality", "reasoning_effort"):
            if k in d:
                setattr(m, k, list(d[k] or []))
        p = d.get("pricing", {})
        m.pricing = Pricing(input_per_1k=p.get("input_per_1k"),
                            output_per_1k=p.get("output_per_1k"),
                            currency=p.get("currency", "USD"),
                            version=str(p.get("version", "1")),
                            unknown=bool(p.get("unknown", True)))
        for k, v in (d.get("provenance") or {}).items():
            m.capabilities_provenance[k] = Provenance(
                source=str(v.get("source", "")), at=float(v.get("at", 0.0)),
                by=str(v.get("by", "")))
        m.benchmark = dict(d.get("benchmark", {}))
        m.metadata = dict(d.get("metadata", {}))
        return m


@dataclass
class ProviderRecord:
    provider_id: str = ""
    name: str = ""
    kind: str = ProviderKind.CLOUD.value
    endpoint: str = ""
    auth_kind: str = "api_key"  # api_key|oauth|env|none|org
    has_credential: bool = False  # boolean only; never the secret
    region: str = ""
    data_retention: str = "unknown"
    privacy_policy: str = "unknown"
    rate_limits: Dict[str, Any] = field(default_factory=dict)
    health: str = HealthState.UNKNOWN.value
    last_checked: float = 0.0
    latency_ms: float = 0.0
    consecutive_failures: int = 0
    circuit: str = CircuitState.CLOSED.value
    circuit_opened_at: float = 0.0
    provenance: Provenance = field(default_factory=Provenance)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {k: getattr(self, k) for k in (
            "provider_id", "name", "kind", "endpoint", "auth_kind",
            "has_credential", "region", "data_retention",
            "privacy_policy", "rate_limits", "health", "last_checked",
            "latency_ms", "consecutive_failures", "circuit",
            "circuit_opened_at", "metadata")}
        d["provenance"] = {"source": self.provenance.source,
                           "at": self.provenance.at, "by": self.provenance.by}
        return d


@dataclass
class EmbeddingModel:
    model_id: str = ""
    provider_id: str = ""
    dimensions: int = 0
    max_input: int = 0
    modality: str = "text"
    locality: str = "remote"
    version: str = ""


@dataclass
class RerankerModel:
    model_id: str = ""
    provider_id: str = ""
    locality: str = "remote"
    version: str = ""
    max_input: int = 0


@dataclass
class VisionModel:
    model_id: str = ""
    provider_id: str = ""
    vision_input: bool = False
    ocr: bool = False
    ui_grounding: bool = False
    native_computer_control: bool = False  # never implied by vision
    version: str = ""


@dataclass
class AudioModel:
    model_id: str = ""
    provider_id: str = ""
    stt: bool = False
    tts: bool = False
    understanding: bool = False
    version: str = ""