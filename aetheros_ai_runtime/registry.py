"""Unified model registry (sections 6, 10-11, 33-36, 50, 72-74, 87-89).

Canonical provider/model/version identity, multi-source catalogs with
trust levels, allow/block lists (block wins), favorites/pins, version
pinning, deprecation notices, license metadata, embedding-dimension
compatibility guard. Atomic JSON persistence (sibling-store pattern).
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aetheros_ai_runtime.models import (
    AudioModel, EmbeddingModel, ModelRecord, ProviderRecord,
    RerankerModel, VisionModel,
)

SOURCE_TRUST = ("verified", "known", "community", "untrusted")


class ModelRegistry:
    def __init__(self, root: Optional[Path] = None) -> None:
        self._root = Path(root) if root else None
        self._lock = threading.RLock()
        self._providers: Dict[str, ProviderRecord] = {}
        self._models: Dict[str, ModelRecord] = {}
        self._embeddings: Dict[str, EmbeddingModel] = {}
        self._rerankers: Dict[str, RerankerModel] = {}
        self._vision: Dict[str, VisionModel] = {}
        self._audio: Dict[str, AudioModel] = {}
        self._sources: Dict[str, Dict[str, Any]] = {}
        self._allow_providers: List[str] = []
        self._block_providers: List[str] = []
        self._allow_models: List[str] = []
        self._block_models: List[str] = []
        self._pins: Dict[str, str] = {}  # task/model -> canonical_id

    def initialize(self, root: Optional[Path] = None) -> None:
        if root is not None:
            self._root = Path(root)
        if self._root is None:
            self._root = Path("./ai_registry")
        self._root.mkdir(parents=True, exist_ok=True)
        self._load()

    # -- providers -------------------------------------------------------
    def upsert_provider(self, rec: ProviderRecord) -> ProviderRecord:
        with self._lock:
            self._providers[rec.provider_id] = rec
            self._persist()
            return rec

    def get_provider(self, pid: str) -> Optional[ProviderRecord]:
        with self._lock:
            return self._providers.get(pid)

    def list_providers(self) -> List[ProviderRecord]:
        with self._lock:
            return sorted(self._providers.values(),
                          key=lambda p: p.provider_id)

    def provider_allowed(self, pid: str) -> bool:
        with self._lock:
            if pid in self._block_providers:
                return False
            if self._allow_providers and pid not in self._allow_providers:
                return False
            return True

    # -- models ------------------------------------------------------------
    def upsert_model(self, rec: ModelRecord) -> ModelRecord:
        with self._lock:
            self._models[rec.canonical_id] = rec
            self._persist()
            return rec

    def get_model(self, canonical_id: str) -> Optional[ModelRecord]:
        with self._lock:
            return self._models.get(canonical_id)

    def list_models(self, *, provider_id: str = "", local_only: bool = False,
                    capability: str = "", query: str = "",
                    include_blocked: bool = False) -> List[ModelRecord]:
        with self._lock:
            out = list(self._models.values())
        if provider_id:
            out = [m for m in out if m.provider_id == provider_id]
        if local_only:
            out = [m for m in out if m.locality == "local"]
        if capability:
            out = [m for m in out if bool(getattr(m, capability, False))]
        if query:
            q = query.lower()
            out = [m for m in out if q in (
                m.model_id + " " + m.display_name + " " + m.family).lower()]
        if not include_blocked:
            out = [m for m in out if not m.blocked
                   and self.provider_allowed(m.provider_id)]
        return sorted(out, key=lambda m: m.canonical_id)

    def model_allowed(self, canonical_id: str) -> bool:
        with self._lock:
            if canonical_id in self._block_models:
                return False
            if self._allow_models and canonical_id not in self._allow_models:
                return False
            m = self._models.get(canonical_id)
            if m is None or m.blocked or m.deprecated:
                return False
            return self.provider_allowed(m.provider_id)

    # -- specialty registries --------------------------------------------------
    def upsert_embedding(self, e: EmbeddingModel) -> None:
        with self._lock:
            self._embeddings[f"{e.provider_id}/{e.model_id}"] = e
            self._persist()

    def check_embedding_compat(self, current_dims: int,
                               candidate_id: str) -> Dict[str, Any]:
        """Never silently mix incompatible vectors (section 87)."""
        with self._lock:
            cand = self._embeddings.get(candidate_id)
            if cand is None:
                return {"ok": False, "reason": "unknown embedding model"}
            if cand.dimensions != current_dims:
                return {"ok": False, "reason": (
                    f"dimension mismatch {current_dims} vs {cand.dimensions}; "
                    "reindex or dual-index migration required"),
                    "migration": ["reindex", "dual-index"]}
            return {"ok": True, "reason": "dimensions match"}

    def upsert_reranker(self, r: RerankerModel) -> None:
        with self._lock:
            self._rerankers[f"{r.provider_id}/{r.model_id}"] = r
            self._persist()

    def upsert_vision(self, v: VisionModel) -> None:
        with self._lock:
            self._vision[f"{v.provider_id}/{v.model_id}"] = v
            self._persist()

    def upsert_audio(self, a: AudioModel) -> None:
        with self._lock:
            self._audio[f"{a.provider_id}/{a.model_id}"] = a
            self._persist()

    # -- policy state ------------------------------------------------------------
    def set_policy(self, *, allow_providers=None, block_providers=None,
                   allow_models=None, block_models=None,
                   pins=None) -> None:
        with self._lock:
            if allow_providers is not None:
                self._allow_providers = list(allow_providers)
            if block_providers is not None:
                self._block_providers = list(block_providers)
            if allow_models is not None:
                self._allow_models = list(allow_models)
            if block_models is not None:
                self._block_models = list(block_models)
            if pins is not None:
                self._pins = dict(pins)
            self._persist()

    def pinned(self, key: str) -> Optional[str]:
        with self._lock:
            return self._pins.get(key)

    def add_source(self, name: str, *, kind: str, trust: str,
                   ref: str = "") -> None:
        if trust not in SOURCE_TRUST:
            raise ValueError(f"unknown source trust: {trust}")
        with self._lock:
            self._sources[name] = {"kind": kind, "trust": trust,
                                   "ref": ref, "at": time.time()}
            self._persist()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {"providers": len(self._providers),
                    "models": len(self._models),
                    "embeddings": len(self._embeddings),
                    "rerankers": len(self._rerankers),
                    "vision": len(self._vision), "audio": len(self._audio),
                    "sources": dict(self._sources)}

    # -- persistence -------------------------------------------------------
    def _path(self) -> Path:
        assert self._root is not None
        return self._root / "registry.json"

    def _persist(self) -> None:
        if self._root is None:
            return
        data = {
            "providers": {k: v.to_dict() for k, v in self._providers.items()},
            "models": {k: v.to_dict() for k, v in self._models.items()},
            "embeddings": {k: vars(v) for k, v in self._embeddings.items()},
            "rerankers": {k: vars(v) for k, v in self._rerankers.items()},
            "vision": {k: vars(v) for k, v in self._vision.items()},
            "audio": {k: vars(v) for k, v in self._audio.items()},
            "sources": self._sources,
            "allow_providers": self._allow_providers,
            "block_providers": self._block_providers,
            "allow_models": self._allow_models,
            "block_models": self._block_models,
            "pins": self._pins,
        }
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
        for k, raw in (data.get("providers") or {}).items():
            try:
                rec = ProviderRecord()
                for f in ("provider_id", "name", "kind", "endpoint",
                          "auth_kind", "has_credential", "region",
                          "data_retention", "privacy_policy", "health",
                          "last_checked", "latency_ms",
                          "consecutive_failures", "circuit",
                          "circuit_opened_at"):
                    if f in raw:
                        setattr(rec, f, raw[f])
                rec.rate_limits = dict(raw.get("rate_limits", {}))
                rec.metadata = dict(raw.get("metadata", {}))
                self._providers[k] = rec
            except (ValueError, KeyError, TypeError):
                continue
        for k, raw in (data.get("models") or {}).items():
            try:
                self._models[k] = ModelRecord.from_dict(raw)
            except (ValueError, KeyError, TypeError):
                continue
        for k, raw in (data.get("embeddings") or {}).items():
            try:
                self._embeddings[k] = EmbeddingModel(**{f: raw.get(f, 0 if f in ("dimensions", "max_input") else "")
                                                        for f in ("model_id", "provider_id", "dimensions", "max_input", "modality", "locality", "version")})
            except TypeError:
                continue
        for k, raw in (data.get("rerankers") or {}).items():
            try:
                self._rerankers[k] = RerankerModel(**{f: raw.get(f, "") for f in (
                    "model_id", "provider_id", "locality", "version")}, max_input=int(raw.get("max_input", 0)))
            except TypeError:
                continue
        for k, raw in (data.get("vision") or {}).items():
            try:
                self._vision[k] = VisionModel(**{f: bool(raw.get(f, False)) for f in (
                    "vision_input", "ocr", "ui_grounding", "native_computer_control")},
                    model_id=str(raw.get("model_id", "")), provider_id=str(raw.get("provider_id", "")),
                    version=str(raw.get("version", "")))
            except TypeError:
                continue
        for k, raw in (data.get("audio") or {}).items():
            try:
                self._audio[k] = AudioModel(
                    model_id=str(raw.get("model_id", "")), provider_id=str(raw.get("provider_id", "")),
                    stt=bool(raw.get("stt", False)), tts=bool(raw.get("tts", False)),
                    understanding=bool(raw.get("understanding", False)),
                    version=str(raw.get("version", "")))
            except TypeError:
                continue
        self._sources = dict(data.get("sources", {}))
        self._allow_providers = list(data.get("allow_providers", []))
        self._block_providers = list(data.get("block_providers", []))
        self._allow_models = list(data.get("allow_models", []))
        self._block_models = list(data.get("block_models", []))
        self._pins = dict(data.get("pins", {}))
