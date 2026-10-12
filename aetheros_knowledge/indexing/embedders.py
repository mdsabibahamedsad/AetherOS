"""Embedding providers."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from typing import Any, Optional

logger = logging.getLogger(__name__)

_EMBEDDING_DIMENSIONS = {
    "openai": 1536, "cohere": 1024, "jina": 768, "voyage": 1024,
    "ollama": 768, "sentence-transformers": 384, "local": 384,
}


class BaseEmbedder:
    name: str = "base"
    dimension: int = 384

    def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class SentenceTransformersEmbedder(BaseEmbedder):
    name = "sentence-transformers"
    dimension = 384

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                self.dimension = self._model.get_sentence_embedding_dimension()
            except ImportError:
                logger.warning("sentence-transformers not installed, using random embeddings")

    def embed(self, text: str) -> list[float]:
        self._load()
        if self._model:
            return self._model.encode(text, normalize_embeddings=True).tolist()
        return _random_embedding(self.dimension)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self._load()
        if self._model:
            emb = self._model.encode(texts, normalize_embeddings=True,
                                      show_progress_bar=False)
            return emb.tolist()
        return [_random_embedding(self.dimension) for _ in texts]


class OpenAIEmbedder(BaseEmbedder):
    name = "openai"
    dimension = 1536

    def __init__(self, api_key: str = None, model: str = "text-embedding-3-small"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                logger.warning("openai not installed")

    def embed(self, text: str) -> list[float]:
        self._get_client()
        if self._client:
            try:
                r = self._client.embeddings.create(input=text, model=self.model)
                return r.data[0].embedding
            except Exception as e:
                logger.warning("OpenAI embedding error: %s", e)
        return _random_embedding(self.dimension)


class OllamaEmbedder(BaseEmbedder):
    name = "ollama"
    dimension = 768

    def __init__(self, base_url: str = None, model: str = "nomic-embed-text"):
        self.base_url = (base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")
                         ).rstrip("/")
        self.model = model

    def embed(self, text: str) -> list[float]:
        try:
            import httpx
            r = httpx.post(f"{self.base_url}/api/embeddings",
                           json={"model": self.model, "prompt": text},
                           timeout=30)
            r.raise_for_status()
            return r.json()["embedding"]
        except Exception as e:
            logger.warning("Ollama embedding error: %s", e)
            return _random_embedding(self.dimension)


class LocalEmbedder(BaseEmbedder):
    name = "local"
    dimension = 384

    def __init__(self):
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._vectorizer = TfidfVectorizer(max_features=384)
            self._fitted = False
        except ImportError:
            self._vectorizer = None

    def embed(self, text: str) -> list[float]:
        if self._vectorizer:
            if not self._fitted:
                self._vectorizer.fit([text])
                self._fitted = True
            vec = self._vectorizer.transform([text]).toarray()[0]
            norm = sum(v * v for v in vec) ** 0.5
            if norm > 0:
                vec = [v / norm for v in vec]
            return vec.tolist()
        return _random_embedding(self.dimension)


EMBEDDER_MAP = {
    "sentence-transformers": SentenceTransformersEmbedder,
    "openai": OpenAIEmbedder,
    "cohere": lambda: OpenAIEmbedder(model="embed-english-v3.0"),
    "jina": lambda: OpenAIEmbedder(model="jina-embeddings-v3"),
    "voyage": lambda: OpenAIEmbedder(model="voyage-2"),
    "ollama": OllamaEmbedder,
    "local": LocalEmbedder,
}


def get_embedder(name: str = "sentence-transformers",
                  **kwargs) -> BaseEmbedder:
    cls = EMBEDDER_MAP.get(name, SentenceTransformersEmbedder)
    return cls(**kwargs)


def _random_embedding(dim: int = 384) -> list[float]:
    import random
    random.seed(0)
    vec = [random.gauss(0, 1) for _ in range(dim)]
    norm = sum(v * v for v in vec) ** 0.5
    return [v / norm for v in vec]
