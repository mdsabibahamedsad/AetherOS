"""Model Database — local cache, search, favorites, pinned models.

Stores model metadata fetched from provider APIs.
Supports offline cache, search, favorites, pinned models,
and recently used tracking.
"""

from __future__ import annotations

import enum
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("aetheros_providers.models")


class ModelCapability(enum.Flag):
    NONE = 0
    CHAT = 1
    VISION = 2
    TOOL_CALLING = 4
    STREAMING = 8
    REASONING = 16
    CODE = 32
    FUNCTION_CALLING = 64
    JSON_MODE = 128
    EMBEDDINGS = 256
    IMAGE_GENERATION = 512
    SPEECH = 1024
    TRANSCRIPTION = 2048


@dataclass
class ModelInfo:
    model_id: str
    provider: str
    display_name: str = ""
    context_window: int = 0
    max_output_tokens: int = 0
    input_price_per_mtok: float = 0.0
    output_price_per_mtok: float = 0.0
    capabilities: ModelCapability = ModelCapability.CHAT
    is_local: bool = False
    is_fallback: bool = False
    latency_class: str = "unknown"
    is_favorite: bool = False
    is_pinned: bool = False
    last_used: float = 0.0
    use_count: int = 0
    source: str = "api"  # api, fallback, local, manual
    fetched_at: float = field(default_factory=time.time)

    @property
    def supports_vision(self) -> bool:
        return bool(self.capabilities & ModelCapability.VISION)

    @property
    def supports_tools(self) -> bool:
        return bool(self.capabilities & ModelCapability.TOOL_CALLING)

    @property
    def supports_reasoning(self) -> bool:
        return bool(self.capabilities & ModelCapability.REASONING)

    @property
    def supports_streaming(self) -> bool:
        return bool(self.capabilities & ModelCapability.STREAMING)

    @property
    def is_chat_model(self) -> bool:
        return bool(self.capabilities & ModelCapability.CHAT)

    @property
    def is_cheap(self) -> bool:
        return self.input_price_per_mtok <= 0.50 and self.output_price_per_mtok <= 2.00

    @property
    def has_large_context(self) -> bool:
        return self.context_window >= 100000

    @property
    def is_fast(self) -> bool:
        return self.latency_class in ("fast", "very_fast")


ModelFetchFn = Callable[[], List[Dict[str, Any]]]


class ModelDatabase:
    """Local model database with caching, search, favorites, and pinned models.

    Never hardcodes models — fetches from provider APIs.
    Caches results locally for offline access.
    """

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        self._lock = threading.RLock()
        self._models: Dict[str, ModelInfo] = {}
        self._provider_models: Dict[str, Set[str]] = {}
        self._fetch_fns: Dict[str, ModelFetchFn] = {}
        self._cache_dir = cache_dir
        self._cache_ttl: float = 3600  # 1 hour
        self._last_fetch: Dict[str, float] = {}
        self._favorite_ids: Set[str] = set()
        self._pinned_ids: Set[str] = set()
        self._recently_used: List[str] = []
        self._max_recent: int = 20

        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            self._load_cache()

    # ------------------------------------------------------------------
    # Model registration
    # ------------------------------------------------------------------

    def register_provider_fetch(self, provider: str, fetch_fn: ModelFetchFn) -> None:
        with self._lock:
            self._fetch_fns[provider] = fetch_fn

    def add_model(self, model: ModelInfo) -> None:
        with self._lock:
            key = f"{model.provider}/{model.model_id}"
            self._models[key] = model
            if model.provider not in self._provider_models:
                self._provider_models[model.provider] = set()
            self._provider_models[model.provider].add(key)
            if model.is_favorite:
                self._favorite_ids.add(key)
            if model.is_pinned:
                self._pinned_ids.add(key)

    def add_models(self, provider: str, models: List[ModelInfo]) -> None:
        for model in models:
            model.provider = provider
            self.add_model(model)

    def remove_model(self, provider: str, model_id: str) -> bool:
        key = f"{provider}/{model_id}"
        with self._lock:
            if key in self._models:
                del self._models[key]
                if provider in self._provider_models:
                    self._provider_models[provider].discard(key)
                self._favorite_ids.discard(key)
                self._pinned_ids.discard(key)
                return True
            return False

    def remove_provider(self, provider: str) -> int:
        with self._lock:
            keys = list(self._provider_models.get(provider, set()))
            for key in keys:
                self._models.pop(key, None)
            self._provider_models.pop(provider, None)
            self._favorite_ids -= set(keys)
            self._pinned_ids -= set(keys)
            return len(keys)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_model(self, provider: str, model_id: str) -> Optional[ModelInfo]:
        return self._models.get(f"{provider}/{model_id}")

    def get_provider_models(self, provider: str) -> List[ModelInfo]:
        with self._lock:
            keys = self._provider_models.get(provider, set())
            return [self._models[k] for k in keys if k in self._models]

    def search(self, query: str) -> List[ModelInfo]:
        """Search models by name, provider, or capabilities."""
        query_lower = query.lower()
        results = []
        with self._lock:
            for model in self._models.values():
                if (
                    query_lower in model.model_id.lower()
                    or query_lower in model.display_name.lower()
                    or query_lower in model.provider.lower()
                ):
                    results.append(model)
        return sorted(results, key=lambda m: m.display_name)

    def filter(
        self,
        providers: Optional[List[str]] = None,
        capabilities: Optional[ModelCapability] = None,
        min_context: int = 0,
        max_input_price: float = 100.0,
        local_only: bool = False,
        cloud_only: bool = False,
        favorites_only: bool = False,
    ) -> List[ModelInfo]:
        """Filter models by criteria."""
        results = []
        with self._lock:
            for model in self._models.values():
                if providers and model.provider not in providers:
                    continue
                if capabilities and not (model.capabilities & capabilities):
                    continue
                if model.context_window < min_context:
                    continue
                if model.input_price_per_mtok > max_input_price:
                    continue
                if local_only and not model.is_local:
                    continue
                if cloud_only and model.is_local:
                    continue
                if favorites_only and not model.is_favorite:
                    continue
                results.append(model)
        return results

    def get_favorites(self) -> List[ModelInfo]:
        with self._lock:
            return [self._models[k] for k in self._favorite_ids if k in self._models]

    def get_pinned(self) -> List[ModelInfo]:
        with self._lock:
            return [self._models[k] for k in self._pinned_ids if k in self._models]

    def get_recently_used(self) -> List[ModelInfo]:
        with self._lock:
            return [
                self._models[k] for k in self._recently_used
                if k in self._models
            ]

    def get_all_models(self) -> List[ModelInfo]:
        with self._lock:
            return list(self._models.values())

    def get_model_count(self, provider: Optional[str] = None) -> int:
        with self._lock:
            if provider:
                return len(self._provider_models.get(provider, set()))
            return len(self._models)

    # ------------------------------------------------------------------
    # Favorites & Pins
    # ------------------------------------------------------------------

    def toggle_favorite(self, provider: str, model_id: str) -> bool:
        key = f"{provider}/{model_id}"
        with self._lock:
            if key in self._favorite_ids:
                self._favorite_ids.discard(key)
                if key in self._models:
                    self._models[key].is_favorite = False
                return False
            self._favorite_ids.add(key)
            if key in self._models:
                self._models[key].is_favorite = True
            return True

    def toggle_pin(self, provider: str, model_id: str) -> bool:
        key = f"{provider}/{model_id}"
        with self._lock:
            if key in self._pinned_ids:
                self._pinned_ids.discard(key)
                if key in self._models:
                    self._models[key].is_pinned = False
                return False
            self._pinned_ids.add(key)
            if key in self._models:
                self._models[key].is_pinned = True
            return True

    def mark_used(self, provider: str, model_id: str) -> None:
        key = f"{provider}/{model_id}"
        with self._lock:
            if key in self._models:
                model = self._models[key]
                model.last_used = time.time()
                model.use_count += 1
            if key in self._recently_used:
                self._recently_used.remove(key)
            self._recently_used.insert(0, key)
            if len(self._recently_used) > self._max_recent:
                self._recently_used.pop()

    # ------------------------------------------------------------------
    # Fetching
    # ------------------------------------------------------------------

    def fetch_models(self, provider: str, force: bool = False) -> List[ModelInfo]:
        """Fetch models from a provider API.

        Uses the registered fetch function. Caches results.
        Returns existing cache if fetch fails and cache exists.
        """
        now = time.time()
        last = self._last_fetch.get(provider, 0)

        if not force and (now - last) < self._cache_ttl:
            cached = self.get_provider_models(provider)
            if cached:
                return cached

        fetch_fn = self._fetch_fns.get(provider)
        if fetch_fn is None:
            return self.get_provider_models(provider)

        try:
            raw_models = fetch_fn()
            new_models = []
            for raw in raw_models:
                model = self._raw_to_model(raw, provider)
                new_models.append(model)

            self.add_models(provider, new_models)
            self._last_fetch[provider] = time.time()
            self._save_cache()
            return new_models
        except Exception as exc:
            logger.warning("Failed to fetch models for %s: %s", provider, exc)
            return self.get_provider_models(provider)

    def fetch_all(self, force: bool = False) -> Dict[str, int]:
        """Fetch models for all registered providers."""
        results = {}
        with self._lock:
            providers = list(self._fetch_fns.keys())
        for provider in providers:
            models = self.fetch_models(provider, force)
            results[provider] = len(models)
        return results

    # ------------------------------------------------------------------
    # Caching
    # ------------------------------------------------------------------

    def set_cache_ttl(self, seconds: float) -> None:
        self._cache_ttl = seconds

    def _save_cache(self) -> None:
        if not self._cache_dir:
            return
        try:
            data = {
                "models": {
                    k: {
                        "model_id": m.model_id,
                        "provider": m.provider,
                        "display_name": m.display_name,
                        "context_window": m.context_window,
                        "max_output_tokens": m.max_output_tokens,
                        "input_price_per_mtok": m.input_price_per_mtok,
                        "output_price_per_mtok": m.output_price_per_mtok,
                        "capabilities": m.capabilities.value,
                        "is_local": m.is_local,
                        "source": m.source,
                        "is_favorite": m.is_favorite,
                        "is_pinned": m.is_pinned,
                    }
                    for k, m in self._models.items()
                },
                "favorites": list(self._favorite_ids),
                "pinned": list(self._pinned_ids),
                "recently_used": self._recently_used,
            }
            cache_file = self._cache_dir / "model_cache.json"
            tmp = cache_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp.replace(cache_file)
        except Exception as exc:
            logger.warning("Failed to save model cache: %s", exc)

    def _load_cache(self) -> None:
        if not self._cache_dir:
            return
        cache_file = self._cache_dir / "model_cache.json"
        if not cache_file.exists():
            return
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            for key, raw in data.get("models", {}).items():
                model = ModelInfo(
                    model_id=raw.get("model_id", ""),
                    provider=raw.get("provider", ""),
                    display_name=raw.get("display_name", ""),
                    context_window=raw.get("context_window", 0),
                    max_output_tokens=raw.get("max_output_tokens", 0),
                    input_price_per_mtok=raw.get("input_price_per_mtok", 0.0),
                    output_price_per_mtok=raw.get("output_price_per_mtok", 0.0),
                    capabilities=ModelCapability(raw.get("capabilities", 1)),
                    is_local=raw.get("is_local", False),
                    source=raw.get("source", "cache"),
                    is_favorite=raw.get("is_favorite", False),
                    is_pinned=raw.get("is_pinned", False),
                )
                self._models[key] = model
                p = model.provider
                if p not in self._provider_models:
                    self._provider_models[p] = set()
                self._provider_models[p].add(key)
            self._favorite_ids = set(data.get("favorites", []))
            self._pinned_ids = set(data.get("pinned", []))
            self._recently_used = data.get("recently_used", [])
            logger.info("Loaded %d cached models", len(self._models))
        except Exception as exc:
            logger.warning("Failed to load model cache: %s", exc)

    def clear_cache(self) -> None:
        with self._lock:
            self._models.clear()
            self._provider_models.clear()
            self._favorite_ids.clear()
            self._pinned_ids.clear()
            self._recently_used.clear()
            self._last_fetch.clear()
        if self._cache_dir:
            cache_file = self._cache_dir / "model_cache.json"
            if cache_file.exists():
                cache_file.unlink()

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _raw_to_model(raw: Dict[str, Any], provider: str) -> ModelInfo:
        model_id = raw.get("id", "") or raw.get("model_id", "")
        return ModelInfo(
            model_id=model_id,
            provider=provider,
            display_name=raw.get("display_name", "") or raw.get("name", "") or model_id,
            context_window=raw.get("context_window", 0) or raw.get("max_context_length", 0) or 0,
            max_output_tokens=raw.get("max_output_tokens", 0) or raw.get("max_tokens", 0) or 0,
            input_price_per_mtok=float(raw.get("input_price", 0) or raw.get("pricing", {}).get("input", 0) or 0),
            output_price_per_mtok=float(raw.get("output_price", 0) or raw.get("pricing", {}).get("output", 0) or 0),
            capabilities=ModelCapability.CHAT
                | (ModelCapability.VISION if raw.get("supports_vision", False) else ModelCapability.NONE)
                | (ModelCapability.TOOL_CALLING if raw.get("supports_tools", False) else ModelCapability.NONE)
                | (ModelCapability.STREAMING if raw.get("supports_streaming", True) else ModelCapability.NONE),
            source="api",
        )

    def refresh_if_stale(self) -> int:
        """Refresh stale caches. Returns number of providers refreshed."""
        count = 0
        with self._lock:
            providers = list(self._fetch_fns.keys())
        now = time.time()
        for provider in providers:
            last = self._last_fetch.get(provider, 0)
            if (now - last) >= self._cache_ttl:
                models = self.fetch_models(provider)
                if models:
                    count += 1
        return count