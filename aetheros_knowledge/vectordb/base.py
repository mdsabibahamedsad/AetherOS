"""Vector database base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SearchResult:
    id: str
    score: float
    content: str
    metadata: dict = field(default_factory=dict)
    document_id: str = ""
    chunk_index: int = 0


class VectorDB(ABC):
    @abstractmethod
    def add(self, chunk_id: str, embedding: list[float],
            content: str, metadata: dict = None) -> None:
        ...

    @abstractmethod
    def add_batch(self, ids: list[str], embeddings: list[list[float]],
                   contents: list[str], metadatas: list[dict] = None) -> None:
        ...

    @abstractmethod
    def search(self, embedding: list[float], top_k: int = 10,
               filters: dict = None) -> list[SearchResult]:
        ...

    @abstractmethod
    def delete(self, chunk_id: str) -> None:
        ...

    @abstractmethod
    def delete_by_metadata(self, key: str, value: Any) -> None:
        ...

    @abstractmethod
    def count(self) -> int:
        ...

    @abstractmethod
    def close(self) -> None:
        ...
