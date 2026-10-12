"""
Embedding Provider — abstraction for generating text embeddings.

Provides a unified interface for embedding generation that can work
with various backends (local models, API services). Supports lazy
loading and caching of embeddings.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingConfig:
    """Configuration for the embedding provider.

    Attributes:
        provider: Provider name ("local", "openai", "custom")
        model: Model name for embedding generation
        dimension: Embedding dimension (auto-detected if not set)
        batch_size: Max texts per embedding request
        cache_embeddings: Whether to cache embedding vectors
        api_key: Optional API key for remote providers
        api_url: Optional API URL for remote providers
    """
    provider: str = "local"
    model: str = "text-embedding-ada-002"
    dimension: int = 1536
    batch_size: int = 20
    cache_embeddings: bool = True
    api_key: Optional[str] = None
    api_url: Optional[str] = None


class EmbeddingProvider:
    """Generates vector embeddings for text.

    Can use local models or remote API services. Embeddings are cached
    to avoid recomputation.

    Usage:
        embedder = EmbeddingProvider(config)
        vector = embedder.embed("Hello world")
        vectors = embedder.embed_batch(["Hello", "World"])
        similarity = embedder.cosine_similarity(v1, v2)
    """

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or EmbeddingConfig()
        self._lock = threading.RLock()
        self._cache: Dict[str, List[float]] = {}
        self._provider_fn: Optional[Callable] = None
        self._initialized = False

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> bool:
        """Initialize the embedding provider.

        Loads the appropriate embedding backend based on configuration.
        Returns True if initialization succeeded.
        """
        if self._initialized:
            return True

        try:
            if self.config.provider == "local":
                self._init_local()
            elif self.config.provider in ("openai", "custom"):
                self._init_api()
            else:
                self._init_simple()

            self._initialized = True
            logger.info(
                "EmbeddingProvider: initialized with %s/%s (dim=%d)",
                self.config.provider, self.config.model, self.config.dimension,
            )
            return True
        except Exception as exc:
            logger.warning("EmbeddingProvider: init failed: %s", exc)
            self._init_simple()
            self._initialized = True
            return False

    def _init_local(self) -> None:
        """Try to initialize a local embedding model."""
        try:
            # Try sentence-transformers
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(self.config.model)
            self._provider_fn = lambda texts: model.encode(texts).tolist()
            self.config.dimension = model.get_sentence_embedding_dimension()
        except ImportError:
            # Fall back to a simple hash-based embedding
            self._provider_fn = self._simple_hash_embedding
            self.config.dimension = 64

    def _init_api(self) -> None:
        """Initialize a remote API-based embedding provider."""
        try:
            import httpx

            api_url = self.config.api_url or "https://api.openai.com/v1/embeddings"
            api_key = self.config.api_key or ""

            def _api_embed(texts: List[str]) -> List[List[float]]:
                response = httpx.post(
                    api_url,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "input": texts,
                        "model": self.config.model,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return [d["embedding"] for d in data["data"]]

            self._provider_fn = _api_embed
        except ImportError:
            self._provider_fn = self._simple_hash_embedding
            self.config.dimension = 64

    def _init_simple(self) -> None:
        """Initialize a simple fallback embedding."""
        self._provider_fn = self._simple_hash_embedding
        self.config.dimension = 64

    # ------------------------------------------------------------------
    # Embedding generation
    # ------------------------------------------------------------------

    def embed(self, text: str) -> List[float]:
        """Generate an embedding vector for a single text."""
        if not self._initialized:
            self.initialize()

        # Check cache
        if self.config.cache_embeddings:
            with self._lock:
                cached = self._cache.get(text)
                if cached is not None:
                    return cached

        vectors = self._call_provider([text])
        vector = vectors[0] if vectors else self._zero_vector()

        # Cache
        if self.config.cache_embeddings:
            with self._lock:
                if len(self._cache) < 100000:
                    self._cache[text] = vector

        return vector

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for multiple texts."""
        if not texts:
            return []

        if not self._initialized:
            self.initialize()

        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []

        # Check cache
        if self.config.cache_embeddings:
            with self._lock:
                for i, text in enumerate(texts):
                    cached = self._cache.get(text)
                    if cached is not None:
                        results[i] = cached
                    else:
                        uncached_indices.append(i)
                        uncached_texts.append(text)
        else:
            uncached_indices = list(range(len(texts)))
            uncached_texts = texts

        # Generate embeddings for uncached texts
        if uncached_texts:
            vectors = self._call_provider(uncached_texts)
            if self.config.cache_embeddings:
                with self._lock:
                    for i, text in enumerate(uncached_texts):
                        if i < len(vectors):
                            self._cache[text] = vectors[i]
            for idx, vector in zip(uncached_indices, vectors):
                results[idx] = vector

        return [r if r is not None else self._zero_vector() for r in results]

    def _call_provider(self, texts: List[str]) -> List[List[float]]:
        """Call the embedding provider function."""
        if self._provider_fn is None:
            self.initialize()

        fn = self._provider_fn or self._simple_hash_embedding

        # Batch if needed
        all_vectors = []
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i:i + self.config.batch_size]
            try:
                vectors = fn(batch)
                all_vectors.extend(vectors)
            except Exception as exc:
                logger.warning("Embedding batch %d failed: %s", i, exc)
                for _ in batch:
                    all_vectors.append(self._zero_vector())

        return all_vectors

    # ------------------------------------------------------------------
    # Similarity
    # ------------------------------------------------------------------

    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _simple_hash_embedding(texts: List[str]) -> List[List[float]]:
        """Simple hash-based embedding (fallback when no model available)."""
        import hashlib

        results = []
        for text in texts:
            h = hashlib.md5(text.encode("utf-8")).hexdigest()
            vec = [int(h[i:i + 2], 16) / 255.0 for i in range(0, 32, 2)]
            # Normalize
            norm = sum(x * x for x in vec) ** 0.5
            if norm > 0:
                vec = [x / norm for x in vec]
            results.append(vec)
        return results

    @staticmethod
    def _zero_vector() -> List[float]:
        return [0.0]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            if count > 0:
                logger.debug("EmbeddingProvider: cleared %d cached vectors", count)

    def stats(self) -> Dict[str, Any]:
        """Return provider statistics."""
        with self._lock:
            return {
                "provider": self.config.provider,
                "model": self.config.model,
                "dimension": self.config.dimension,
                "initialized": self._initialized,
                "cache_size": len(self._cache),
            }
