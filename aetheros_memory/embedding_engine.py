"""Embedding Engine — multi-provider embeddings with automatic provider selection.

Supports OpenAI, Gemini, Cohere, Jina, Voyage, and local embeddings.
Provider chosen independently from chat provider.
"""

from __future__ import annotations

import abc
import enum
import hashlib
import json
import logging
import math
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("aetheros_memory.embedding")


class EmbeddingProvider(str, enum.Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    COHERE = "cohere"
    JINA = "jina"
    VOYAGE = "voyage"
    LOCAL = "local"


@dataclass
class EmbeddingConfig:
    provider: EmbeddingProvider = EmbeddingProvider.OPENAI
    model: str = ""
    dimensions: int = 1536
    batch_size: int = 32
    max_retries: int = 3
    cache_size: int = 10000
    api_key: str = ""
    api_base: str = ""
    timeout: float = 30.0


@dataclass
class EmbeddingResult:
    vector: List[float]
    dimensions: int
    provider: EmbeddingProvider
    model: str
    latency_ms: float
    text_hash: str = ""


class BaseEmbedder(abc.ABC):
    @abc.abstractmethod
    def embed(self, text: str) -> List[float]:
        ...

    @abc.abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        ...

    @property
    @abc.abstractmethod
    def dimensions(self) -> int:
        ...

    @property
    @abc.abstractmethod
    def provider(self) -> EmbeddingProvider:
        ...

    @property
    @abc.abstractmethod
    def model(self) -> str:
        ...


class OpenAIEmbedder(BaseEmbedder):
    def __init__(self, config: EmbeddingConfig) -> None:
        self._config = config
        self._model = config.model or "text-embedding-3-small"
        self._dims = config.dimensions or 1536
        self._client: Any = None
        self._lock = threading.Lock()

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
            kwargs: Dict[str, Any] = {}
            if self._config.api_key:
                kwargs["api_key"] = self._config.api_key
            if self._config.api_base:
                kwargs["base_url"] = self._config.api_base
            self._client = OpenAI(**kwargs) if kwargs else OpenAI()
        except ImportError:
            raise ImportError("openai package not installed. Install with: pip install openai")
        return self._client

    def embed(self, text: str) -> List[float]:
        client = self._get_client()
        text = text.replace("\n", " ").strip()
        kwargs: Dict[str, Any] = {"model": self._model, "input": text}
        if self._model == "text-embedding-3-small" or self._model == "text-embedding-3-large":
            kwargs["dimensions"] = self._dims
        resp = client.embeddings.create(**kwargs)
        return resp.data[0].embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        client = self._get_client()
        cleaned = [t.replace("\n", " ").strip() for t in texts]
        kwargs: Dict[str, Any] = {"model": self._model, "input": cleaned}
        if self._model in ("text-embedding-3-small", "text-embedding-3-large"):
            kwargs["dimensions"] = self._dims
        resp = client.embeddings.create(**kwargs)
        sorted_data = sorted(resp.data, key=lambda d: d.index)
        return [d.embedding for d in sorted_data]

    @property
    def dimensions(self) -> int:
        return self._dims

    @property
    def provider(self) -> EmbeddingProvider:
        return EmbeddingProvider.OPENAI

    @property
    def model(self) -> str:
        return self._model


class GeminiEmbedder(BaseEmbedder):
    def __init__(self, config: EmbeddingConfig) -> None:
        self._config = config
        self._model = config.model or "text-embedding-004"
        self._dims = config.dimensions or 768
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import google.generativeai as genai
            if self._config.api_key:
                genai.configure(api_key=self._config.api_key)
            self._client = genai
        except ImportError:
            raise ImportError("google-generativeai package not installed.")
        return self._client

    def embed(self, text: str) -> List[float]:
        client = self._get_client()
        result = client.embed_content(model=self._model, content=text)
        return result["embedding"]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        client = self._get_client()
        result = client.embed_content(model=self._model, content=texts)
        return result["embedding"]

    @property
    def dimensions(self) -> int:
        return self._dims

    @property
    def provider(self) -> EmbeddingProvider:
        return EmbeddingProvider.GEMINI

    @property
    def model(self) -> str:
        return self._model


class CohereEmbedder(BaseEmbedder):
    def __init__(self, config: EmbeddingConfig) -> None:
        self._config = config
        self._model = config.model or "embed-english-v3.0"
        self._dims = config.dimensions or 1024
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import cohere
            kwargs: Dict[str, Any] = {}
            if self._config.api_key:
                kwargs["api_key"] = self._config.api_key
            self._client = cohere.Client(**kwargs) if kwargs else cohere.Client()
        except ImportError:
            raise ImportError("cohere package not installed.")
        return self._client

    def embed(self, text: str) -> List[float]:
        client = self._get_client()
        resp = client.embed(texts=[text], model=self._model, input_type="search_document")
        return resp.embeddings[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        client = self._get_client()
        resp = client.embed(texts=texts, model=self._model, input_type="search_document")
        return resp.embeddings

    @property
    def dimensions(self) -> int:
        return self._dims

    @property
    def provider(self) -> EmbeddingProvider:
        return EmbeddingProvider.COHERE

    @property
    def model(self) -> str:
        return self._model


class JinaEmbedder(BaseEmbedder):
    def __init__(self, config: EmbeddingConfig) -> None:
        self._config = config
        self._model = config.model or "jina-embeddings-v3"
        self._dims = config.dimensions or 1024
        self._session: Any = None

    def _get_session(self) -> Any:
        if self._session is not None:
            return self._session
        import httpx
        self._session = httpx.Client(timeout=self._config.timeout)
        return self._session

    def embed(self, text: str) -> List[float]:
        session = self._get_session()
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        resp = session.post(
            "https://api.jina.ai/v1/embeddings",
            headers=headers,
            json={"model": self._model, "input": [text]},
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        session = self._get_session()
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        resp = session.post(
            "https://api.jina.ai/v1/embeddings",
            headers=headers,
            json={"model": self._model, "input": texts},
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        sorted_data = sorted(data, key=lambda d: d["index"])
        return [d["embedding"] for d in sorted_data]

    @property
    def dimensions(self) -> int:
        return self._dims

    @property
    def provider(self) -> EmbeddingProvider:
        return EmbeddingProvider.JINA

    @property
    def model(self) -> str:
        return self._model


class VoyageEmbedder(BaseEmbedder):
    def __init__(self, config: EmbeddingConfig) -> None:
        self._config = config
        self._model = config.model or "voyage-3"
        self._dims = config.dimensions or 1024
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import voyageai
            kwargs: Dict[str, Any] = {}
            if self._config.api_key:
                kwargs["api_key"] = self._config.api_key
            self._client = voyageai.Client(**kwargs) if kwargs else voyageai.Client()
        except ImportError:
            raise ImportError("voyageai package not installed.")
        return self._client

    def embed(self, text: str) -> List[float]:
        client = self._get_client()
        result = client.embed([text], model=self._model)
        return result.embeddings[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        client = self._get_client()
        result = client.embed(texts, model=self._model)
        return result.embeddings

    @property
    def dimensions(self) -> int:
        return self._dims

    @property
    def provider(self) -> EmbeddingProvider:
        return EmbeddingProvider.VOYAGE

    @property
    def model(self) -> str:
        return self._model


class LocalEmbedder(BaseEmbedder):
    def __init__(self, config: EmbeddingConfig) -> None:
        self._config = config
        self._model = config.model or "all-MiniLM-L6-v2"
        self._dims = config.dimensions or 384
        self._model_obj: Any = None
        self._tokenizer: Any = None

    def _load(self) -> None:
        if self._model_obj is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self._model_obj = SentenceTransformer(self._model)
            self._dims = self._model_obj.get_sentence_embedding_dimension()
        except ImportError:
            raise ImportError("sentence-transformers not installed. pip install sentence-transformers")

    def embed(self, text: str) -> List[float]:
        self._load()
        vec = self._model_obj.encode(text, normalize_embeddings=True)
        return vec.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        self._load()
        vecs = self._model_obj.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]

    @property
    def dimensions(self) -> int:
        return self._dims

    @property
    def provider(self) -> EmbeddingProvider:
        return EmbeddingProvider.LOCAL

    @property
    def model(self) -> str:
        return self._model


class EmbeddingEngine:
    def __init__(self, config: Optional[EmbeddingConfig] = None) -> None:
        self._config = config or EmbeddingConfig()
        self._lock = threading.RLock()
        self._cache: Dict[str, Tuple[List[float], float]] = {}
        self._cache_max = self._config.cache_size
        self._embedder: Optional[BaseEmbedder] = None
        self._latency_history: Dict[str, List[float]] = {}

    def _get_embedder(self) -> BaseEmbedder:
        if self._embedder is not None:
            return self._embedder
        config = self._config
        provider = config.provider
        if provider == EmbeddingProvider.OPENAI:
            self._embedder = OpenAIEmbedder(config)
        elif provider == EmbeddingProvider.GEMINI:
            self._embedder = GeminiEmbedder(config)
        elif provider == EmbeddingProvider.COHERE:
            self._embedder = CohereEmbedder(config)
        elif provider == EmbeddingProvider.JINA:
            self._embedder = JinaEmbedder(config)
        elif provider == EmbeddingProvider.VOYAGE:
            self._embedder = VoyageEmbedder(config)
        elif provider == EmbeddingProvider.LOCAL:
            self._embedder = LocalEmbedder(config)
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")
        return self._embedder

    def switch_provider(self, provider: EmbeddingProvider, model: str = "") -> None:
        with self._lock:
            self._config.provider = provider
            if model:
                self._config.model = model
            self._embedder = None
            self._cache.clear()
        logger.info("Switched embedding provider to %s/%s", provider.value, model or "default")

    def embed(self, text: str) -> EmbeddingResult:
        embedder = self._get_embedder()
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        with self._lock:
            cached = self._cache.get(text_hash)
            if cached is not None:
                return EmbeddingResult(
                    vector=cached[0],
                    dimensions=len(cached[0]),
                    provider=embedder.provider,
                    model=embedder.model,
                    latency_ms=0.0,
                    text_hash=text_hash,
                )
        start = time.monotonic()
        vector = embedder.embed(text)
        elapsed = (time.monotonic() - start) * 1000
        with self._lock:
            self._cache[text_hash] = (vector, time.time())
            if len(self._cache) > self._cache_max:
                oldest = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest]
            key = f"{embedder.provider.value}/{embedder.model}"
            if key not in self._latency_history:
                self._latency_history[key] = []
            self._latency_history[key].append(elapsed)
            if len(self._latency_history[key]) > 100:
                self._latency_history[key] = self._latency_history[key][-100:]
        return EmbeddingResult(
            vector=vector,
            dimensions=len(vector),
            provider=embedder.provider,
            model=embedder.model,
            latency_ms=elapsed,
            text_hash=text_hash,
        )

    def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        if not texts:
            return []
        embedder = self._get_embedder()
        batch_size = self._config.batch_size
        results: List[EmbeddingResult] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            start = time.monotonic()
            vectors = embedder.embed_batch(batch)
            elapsed = (time.monotonic() - start) * 1000
            for j, text in enumerate(batch):
                text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
                with self._lock:
                    self._cache[text_hash] = (vectors[j], time.time())
                results.append(EmbeddingResult(
                    vector=vectors[j],
                    dimensions=len(vectors[j]),
                    provider=embedder.provider,
                    model=embedder.model,
                    latency_ms=elapsed / len(batch),
                    text_hash=text_hash,
                ))
        return results

    def clear_cache(self) -> int:
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def get_latency_stats(self) -> Dict[str, Dict[str, float]]:
        stats: Dict[str, Dict[str, float]] = {}
        with self._lock:
            for key, latencies in self._latency_history.items():
                if latencies:
                    stats[key] = {
                        "avg": sum(latencies) / len(latencies),
                        "min": min(latencies),
                        "max": max(latencies),
                        "count": len(latencies),
                    }
        return stats

    @property
    def dimensions(self) -> int:
        return self._get_embedder().dimensions

    @property
    def provider(self) -> EmbeddingProvider:
        return self._get_embedder().provider

    @property
    def model(self) -> str:
        return self._get_embedder().model


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)