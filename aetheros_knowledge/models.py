"""Data models for Knowledge OS."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class SourceType(str, Enum):
    MARKDOWN = "markdown"
    TXT = "txt"
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    YAML = "yaml"
    HTML = "html"
    EPUB = "epub"
    GITHUB_REPO = "github_repo"
    GITLAB_REPO = "gitlab_repo"
    LOCAL_FOLDER = "local_folder"
    NOTION_EXPORT = "notion_export"
    OBSIDIAN_VAULT = "obsidian_vault"
    WEBSITE = "website"
    RSS_FEED = "rss_feed"
    YOUTUBE_TRANSCRIPT = "youtube_transcript"
    AUDIO_TRANSCRIPT = "audio_transcript"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"
    DELETED = "deleted"


class CollectionVisibility(str, Enum):
    PRIVATE = "private"
    SHARED_READ = "shared_read"
    SHARED_WRITE = "shared_write"
    PUBLIC = "public"


class MemoryType(str, Enum):
    PERSONAL = "personal"
    WORKSPACE = "workspace"
    AGENT = "agent"
    PROJECT = "project"
    TEMPORARY = "temporary"
    LONG_TERM = "long_term"


@dataclass
class KnowledgeDocument:
    id: str
    title: str
    source_type: SourceType
    source_path: str
    collection_id: str
    status: DocumentStatus = DocumentStatus.PENDING
    content_type: str = ""
    language: str = ""
    size_bytes: int = 0
    page_count: int = 0
    word_count: int = 0
    chunk_count: int = 0
    checksum: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    indexed_at: str = ""


@dataclass
class DocumentChunk:
    id: str
    document_id: str
    content: str
    chunk_index: int
    token_count: int = 0
    embedding: list[float] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class KnowledgeCollection:
    id: str
    name: str
    description: str = ""
    icon: str = "folder"
    color: str = "#6366f1"
    parent_id: Optional[str] = None
    visibility: CollectionVisibility = CollectionVisibility.PRIVATE
    tags: list[str] = field(default_factory=list)
    document_count: int = 0
    size_bytes: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class Annotation:
    id: str
    document_id: str
    annotation_type: str  # highlight, note, comment, bookmark, pinned
    content: str = ""
    color: str = ""
    position_start: int = 0
    position_end: int = 0
    page: int = 0
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class MemoryEntry:
    id: str
    memory_type: MemoryType
    key: str
    value: Any
    scope: str = ""
    tags: list[str] = field(default_factory=list)
    importance: float = 0.5
    ttl_seconds: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    expires_at: Optional[str] = None


@dataclass
class RAGPipeline:
    id: str
    name: str
    description: str = ""
    embedder: str = "sentence-transformers"
    vector_store: str = "sqlite"
    chunk_size: int = 512
    chunk_overlap: int = 64
    ranking: str = "cosine"
    reranking: bool = False
    hybrid_search: bool = True
    top_k: int = 5
    config: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class KnowledgeSource:
    id: str
    source_type: SourceType
    uri: str
    label: str = ""
    collection_id: Optional[str] = None
    config: dict = field(default_factory=dict)
    enabled: bool = True
    auto_sync: bool = False
    sync_interval_minutes: int = 0
    last_synced: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


BUILTIN_COLLECTIONS = [
    KnowledgeCollection(id="recent", name="Recent", icon="clock", color="#8b5cf6",
                        description="Recently accessed documents"),
    KnowledgeCollection(id="documents", name="Documents", icon="file-text", color="#3b82f6",
                        description="All imported documents"),
    KnowledgeCollection(id="repositories", name="Repositories", icon="git-branch", color="#10b981",
                        description="Code repositories"),
    KnowledgeCollection(id="websites", name="Websites", icon="globe", color="#f59e0b",
                        description="Crawled websites"),
    KnowledgeCollection(id="bookmarks", name="Bookmarks", icon="bookmark", color="#ec4899",
                        description="Bookmarked content"),
    KnowledgeCollection(id="databases", name="Databases", icon="database", color="#14b8a6",
                        description="Database connections"),
    KnowledgeCollection(id="media", name="Media", icon="film", color="#ef4444",
                        description="Media files and transcripts"),
    KnowledgeCollection(id="trash", name="Trash", icon="trash-2", color="#6b7280",
                        description="Deleted documents"),
]

COLLECTION_TEMPLATES = {
    "programming": KnowledgeCollection(id="", name="Programming", icon="code", color="#10b981",
                                        description="Code and technical documentation"),
    "research": KnowledgeCollection(id="", name="Research", icon="graduation-cap", color="#8b5cf6",
                                     description="Research papers and resources"),
    "business": KnowledgeCollection(id="", name="Business", icon="briefcase", color="#3b82f6",
                                     description="Business documents"),
    "personal": KnowledgeCollection(id="", name="Personal", icon="heart", color="#ec4899",
                                     description="Personal knowledge"),
    "university": KnowledgeCollection(id="", name="University", icon="book-open", color="#f59e0b",
                                       description="Academic materials"),
    "books": KnowledgeCollection(id="", name="Books", icon="book", color="#14b8a6",
                                  description="Books and publications"),
    "projects": KnowledgeCollection(id="", name="Projects", icon="folder-kanban", color="#f97316",
                                     description="Project documentation"),
    "company_docs": KnowledgeCollection(id="", name="Company Docs", icon="building", color="#6366f1",
                                         description="Company documentation"),
}

SUPPORTED_EXTENSIONS = {
    ".md": SourceType.MARKDOWN, ".txt": SourceType.TXT, ".pdf": SourceType.PDF,
    ".docx": SourceType.DOCX, ".pptx": SourceType.PPTX, ".csv": SourceType.CSV,
    ".xlsx": SourceType.EXCEL, ".xls": SourceType.EXCEL, ".json": SourceType.JSON,
    ".yaml": SourceType.YAML, ".yml": SourceType.YAML, ".html": SourceType.HTML,
    ".htm": SourceType.HTML, ".epub": SourceType.EPUB,
}
