"""
Knowledge SDK for AetherOS
==========================

SDK for managing knowledge providers, vector stores, embeddings, retrievers, and rerankers.

Usage::

    from aetheros_developer_platform.knowledge_sdk import KnowledgeManager

    manager = KnowledgeManager()
    manager.register_provider("my-provider", MyKnowledgeProvider())
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Types of knowledge providers."""
    VECTOR = "vector"
    EMBEDDING = "embedding"
    RETRIEVER = "retriever"
    RERANKER = "reranker"
    KNOWLEDGE = "knowledge"


@dataclass
class Document:
    """A knowledge document."""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    """A search result."""
    document: Document
    score: float
    rank: int = 0


class BaseKnowledgeProvider(ABC):
    """Base class for knowledge providers."""

    @abstractmethod
    def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search for documents."""
        ...

    @abstractmethod
    def add_document(self, document: Document) -> bool:
        """Add a document to the store."""
        ...

    @abstractmethod
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the store."""
        ...

    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get a document by ID."""
        return None

    def list_documents(self, limit: int = 100) -> List[Document]:
        """List all documents."""
        return []


class BaseEmbeddingProvider(ABC):
    """Base class for embedding providers."""

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        ...

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the embedding dimensions."""
        ...


class BaseRetriever(ABC):
    """Base class for retrievers."""

    @abstractmethod
    def retrieve(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Retrieve relevant documents."""
        ...


class BaseReranker(ABC):
    """Base class for rerankers."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        limit: int = 10,
    ) -> List[SearchResult]:
        """Rerank search results."""
        ...


class KnowledgeManager:
    """Manages knowledge providers for AetherOS.

    Usage::

        manager = KnowledgeManager()
        manager.register_provider("my-store", MyKnowledgeProvider())
        results = manager.search("my-store", "what is AetherOS?")
    """

    def __init__(self) -> None:
        self._providers: Dict[str, BaseKnowledgeProvider] = {}
        self._embedding_providers: Dict[str, BaseEmbeddingProvider] = {}
        self._retrievers: Dict[str, BaseRetriever] = {}
        self._rerankers: Dict[str, BaseReranker] = {}

    def register_provider(
        self,
        name: str,
        provider: BaseKnowledgeProvider,
    ) -> None:
        """Register a knowledge provider."""
        self._providers[name] = provider
        logger.info("Registered knowledge provider: %s", name)

    def register_embedding_provider(
        self,
        name: str,
        provider: BaseEmbeddingProvider,
    ) -> None:
        """Register an embedding provider."""
        self._embedding_providers[name] = provider
        logger.info("Registered embedding provider: %s", name)

    def register_retriever(
        self,
        name: str,
        retriever: BaseRetriever,
    ) -> None:
        """Register a retriever."""
        self._retrievers[name] = retriever
        logger.info("Registered retriever: %s", name)

    def register_reranker(
        self,
        name: str,
        reranker: BaseReranker,
    ) -> None:
        """Register a reranker."""
        self._rerankers[name] = reranker
        logger.info("Registered reranker: %s", name)

    def search(
        self,
        provider_name: str,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search using a knowledge provider."""
        provider = self._providers.get(provider_name)
        if not provider:
            raise ValueError(f"Provider '{provider_name}' not found")
        return provider.search(query, limit=limit, filters=filters)

    def embed(
        self,
        provider_name: str,
        text: str,
    ) -> List[float]:
        """Generate embedding using an embedding provider."""
        provider = self._embedding_providers.get(provider_name)
        if not provider:
            raise ValueError(f"Embedding provider '{provider_name}' not found")
        return provider.embed(text)

    def retrieve(
        self,
        retriever_name: str,
        query: str,
        limit: int = 10,
    ) -> List[SearchResult]:
        """Retrieve using a retriever."""
        retriever = self._retrievers.get(retriever_name)
        if not retriever:
            raise ValueError(f"Retriever '{retriever_name}' not found")
        return retriever.retrieve(query, limit=limit)

    def rerank(
        self,
        reranker_name: str,
        query: str,
        results: List[SearchResult],
        limit: int = 10,
    ) -> List[SearchResult]:
        """Rerank using a reranker."""
        reranker = self._rerankers.get(reranker_name)
        if not reranker:
            raise ValueError(f"Reranker '{reranker_name}' not found")
        return reranker.rerank(query, results, limit=limit)

    def list_providers(self, provider_type: Optional[ProviderType] = None) -> List[str]:
        """List all registered providers."""
        providers = []
        if provider_type is None or provider_type == ProviderType.KNOWLEDGE:
            providers.extend(self._providers.keys())
        if provider_type is None or provider_type == ProviderType.EMBEDDING:
            providers.extend(self._embedding_providers.keys())
        if provider_type is None or provider_type == ProviderType.RETRIEVER:
            providers.extend(self._retrievers.keys())
        if provider_type is None or provider_type == ProviderType.RERANKER:
            providers.extend(self._rerankers.keys())
        return providers

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge manager statistics."""
        return {
            "providers": len(self._providers),
            "embedding_providers": len(self._embedding_providers),
            "retrievers": len(self._retrievers),
            "rerankers": len(self._rerankers),
        }


# Global knowledge manager
_knowledge_manager: Optional[KnowledgeManager] = None


def get_knowledge_manager() -> KnowledgeManager:
    """Return the global KnowledgeManager singleton."""
    global _knowledge_manager
    if _knowledge_manager is None:
        _knowledge_manager = KnowledgeManager()
    return _knowledge_manager
