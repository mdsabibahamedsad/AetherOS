"""Conversation Engine — unlimited chats, folders, pin, archive, import/export.

Supports full CRUD on conversations with folders, pinning, archiving,
renaming, duplication, and export to Markdown / JSON / HTML / PDF.
"""

from __future__ import annotations

import enum
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("aetheros_runtime.conversation")


class ExportFormat(enum.Enum):
    MARKDOWN = "md"
    JSON = "json"
    HTML = "html"
    PDF = "pdf"


@dataclass
class ConversationFolder:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    parent_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    color: str = ""
    icon: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
            "created_at": self.created_at,
            "color": self.color,
            "icon": self.icon,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationFolder":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Message:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "tool_calls": self.tool_calls,
            "tool_result": self.tool_result,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Conversation:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "New Chat"
    messages: List[Message] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    folder_id: Optional[str] = None
    is_pinned: bool = False
    is_archived: bool = False
    model: str = ""
    provider: str = ""
    token_count: int = 0
    message_count: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str, **kw: Any) -> Message:
        msg = Message(role=role, content=content, **kw)
        self.messages.append(msg)
        self.message_count = len(self.messages)
        self.updated_at = time.time()
        return msg

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "folder_id": self.folder_id,
            "is_pinned": self.is_pinned,
            "is_archived": self.is_archived,
            "model": self.model,
            "provider": self.provider,
            "token_count": self.token_count,
            "message_count": self.message_count,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        messages = [Message.from_dict(m) for m in data.pop("messages", [])]
        conv = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__ and k != "messages"})
        conv.messages = messages
        conv.message_count = len(messages)
        return conv


class ConversationEngine:
    """Full conversation lifecycle management.

    Supports:
    - Unlimited chats with automatic persistence
    - Folders for organization
    - Pin, archive, rename, delete, duplicate
    - Import/export in Markdown, JSON, HTML, PDF
    """

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self._lock = threading.RLock()
        self._conversations: Dict[str, Conversation] = {}
        self._folders: Dict[str, ConversationFolder] = {}
        self._storage_dir = storage_dir
        self._dirty = False
        self._save_timer: Optional[threading.Thread] = None

        if storage_dir:
            storage_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    # ------------------------------------------------------------------
    # Conversation CRUD
    # ------------------------------------------------------------------

    def create(
        self,
        title: str = "New Chat",
        folder_id: Optional[str] = None,
        model: str = "",
        provider: str = "",
    ) -> Conversation:
        conv = Conversation(
            title=title,
            folder_id=folder_id,
            model=model,
            provider=provider,
        )
        with self._lock:
            self._conversations[conv.id] = conv
            self._dirty = True
        self._save()
        logger.info("Conversation created: %s (%s)", conv.title, conv.id[:8])
        return conv

    def get(self, conversation_id: str) -> Optional[Conversation]:
        with self._lock:
            return self._conversations.get(conversation_id)

    def get_all(self, include_archived: bool = False) -> List[Conversation]:
        with self._lock:
            result = list(self._conversations.values())
        if not include_archived:
            result = [c for c in result if not c.is_archived]
        return sorted(result, key=lambda c: c.updated_at, reverse=True)

    def rename(self, conversation_id: str, title: str) -> bool:
        with self._lock:
            conv = self._conversations.get(conversation_id)
            if not conv:
                return False
            conv.title = title
            conv.updated_at = time.time()
            self._dirty = True
        self._save()
        return True

    def delete(self, conversation_id: str) -> bool:
        with self._lock:
            if conversation_id not in self._conversations:
                return False
            del self._conversations[conversation_id]
            self._dirty = True
        self._save()
        logger.info("Conversation deleted: %s", conversation_id[:8])
        return True

    def duplicate(self, conversation_id: str) -> Optional[Conversation]:
        with self._lock:
            original = self._conversations.get(conversation_id)
            if not original:
                return None
            data = original.to_dict()
            data["id"] = str(uuid.uuid4())
            data["title"] = f"{original.title} (Copy)"
            data["created_at"] = time.time()
            data["updated_at"] = time.time()
            copy = Conversation.from_dict(data)
            self._conversations[copy.id] = copy
            self._dirty = True
        self._save()
        return copy

    # ------------------------------------------------------------------
    # Pin / Archive
    # ------------------------------------------------------------------

    def toggle_pin(self, conversation_id: str) -> bool:
        with self._lock:
            conv = self._conversations.get(conversation_id)
            if not conv:
                return False
            conv.is_pinned = not conv.is_pinned
            conv.updated_at = time.time()
            self._dirty = True
        self._save()
        return conv.is_pinned

    def toggle_archive(self, conversation_id: str) -> bool:
        with self._lock:
            conv = self._conversations.get(conversation_id)
            if not conv:
                return False
            conv.is_archived = not conv.is_archived
            conv.updated_at = time.time()
            self._dirty = True
        self._save()
        return conv.is_archived

    def get_pinned(self) -> List[Conversation]:
        with self._lock:
            return sorted(
                [c for c in self._conversations.values() if c.is_pinned and not c.is_archived],
                key=lambda c: c.updated_at, reverse=True,
            )

    def get_archived(self) -> List[Conversation]:
        with self._lock:
            return sorted(
                [c for c in self._conversations.values() if c.is_archived],
                key=lambda c: c.updated_at, reverse=True,
            )

    # ------------------------------------------------------------------
    # Folders
    # ------------------------------------------------------------------

    def create_folder(self, name: str, parent_id: Optional[str] = None) -> ConversationFolder:
        folder = ConversationFolder(name=name, parent_id=parent_id)
        with self._lock:
            self._folders[folder.id] = folder
            self._dirty = True
        self._save()
        return folder

    def get_folder(self, folder_id: str) -> Optional[ConversationFolder]:
        with self._lock:
            return self._folders.get(folder_id)

    def delete_folder(self, folder_id: str) -> bool:
        with self._lock:
            if folder_id not in self._folders:
                return False
            del self._folders[folder_id]
            for conv in self._conversations.values():
                if conv.folder_id == folder_id:
                    conv.folder_id = None
            self._dirty = True
        self._save()
        return True

    def move_to_folder(self, conversation_id: str, folder_id: Optional[str]) -> bool:
        with self._lock:
            conv = self._conversations.get(conversation_id)
            if not conv:
                return False
            conv.folder_id = folder_id
            conv.updated_at = time.time()
            self._dirty = True
        self._save()
        return True

    def list_folders(self) -> List[ConversationFolder]:
        with self._lock:
            return list(self._folders.values())

    def get_conversations_in_folder(self, folder_id: str) -> List[Conversation]:
        with self._lock:
            return [
                c for c in self._conversations.values()
                if c.folder_id == folder_id and not c.is_archived
            ]

    # ------------------------------------------------------------------
    # Message management
    # ------------------------------------------------------------------

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        **kw: Any,
    ) -> Optional[Message]:
        with self._lock:
            conv = self._conversations.get(conversation_id)
            if not conv:
                return None
            msg = conv.add_message(role, content, **kw)
            self._dirty = True
        self._save()
        return msg

    def get_messages(self, conversation_id: str) -> List[Message]:
        with self._lock:
            conv = self._conversations.get(conversation_id)
            if not conv:
                return []
            return list(conv.messages)

    def clear_messages(self, conversation_id: str) -> bool:
        with self._lock:
            conv = self._conversations.get(conversation_id)
            if not conv:
                return False
            conv.messages.clear()
            conv.message_count = 0
            conv.updated_at = time.time()
            self._dirty = True
        self._save()
        return True

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def export(
        self,
        conversation_id: str,
        fmt: ExportFormat = ExportFormat.MARKDOWN,
    ) -> str:
        conv = self.get(conversation_id)
        if not conv:
            return ""

        if fmt == ExportFormat.JSON:
            return json.dumps(conv.to_dict(), indent=2, ensure_ascii=False)

        if fmt == ExportFormat.MARKDOWN:
            return self._to_markdown(conv)

        if fmt == ExportFormat.HTML:
            return self._to_html(conv)

        return self._to_markdown(conv)

    def export_to_file(
        self,
        conversation_id: str,
        output_path: Path,
        fmt: Optional[ExportFormat] = None,
    ) -> bool:
        if fmt is None:
            suffix = output_path.suffix.lower()
            fmt_map = {".md": ExportFormat.MARKDOWN, ".json": ExportFormat.JSON, ".html": ExportFormat.HTML}
            fmt = fmt_map.get(suffix, ExportFormat.MARKDOWN)

        content = self.export(conversation_id, fmt)
        if not content:
            return False
        output_path.write_text(content, encoding="utf-8")
        return True

    def import_from_json(self, data: Dict[str, Any]) -> Optional[Conversation]:
        try:
            conv = Conversation.from_dict(data)
            with self._lock:
                self._conversations[conv.id] = conv
                self._dirty = True
            self._save()
            return conv
        except Exception as exc:
            logger.error("Import failed: %s", exc)
            return None

    def import_from_file(self, file_path: Path) -> Optional[Conversation]:
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            return self.import_from_json(data)
        except Exception as exc:
            logger.error("File import failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str) -> List[Conversation]:
        query_lower = query.lower()
        results: List[Conversation] = []
        with self._lock:
            for conv in self._conversations.values():
                if conv.is_archived:
                    continue
                if query_lower in conv.title.lower():
                    results.append(conv)
                    continue
                for msg in conv.messages:
                    if query_lower in msg.content.lower():
                        results.append(conv)
                        break
        return sorted(results, key=lambda c: c.updated_at, reverse=True)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def count(self) -> int:
        with self._lock:
            return len(self._conversations)

    def total_messages(self) -> int:
        with self._lock:
            return sum(c.message_count for c in self._conversations.values())

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_conversations": len(self._conversations),
                "total_messages": sum(c.message_count for c in self._conversations.values()),
                "pinned": sum(1 for c in self._conversations.values() if c.is_pinned),
                "archived": sum(1 for c in self._conversations.values() if c.is_archived),
                "folders": len(self._folders),
            }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        if not self._storage_dir:
            return
        try:
            data = {
                "conversations": {cid: c.to_dict() for cid, c in self._conversations.items()},
                "folders": {fid: f.to_dict() for fid, f in self._folders.items()},
            }
            path = self._storage_dir / "conversations.json"
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
            self._dirty = False
        except Exception as exc:
            logger.warning("Failed to save conversations: %s", exc)

    def _load(self) -> None:
        if not self._storage_dir:
            return
        path = self._storage_dir / "conversations.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for cid, raw in data.get("conversations", {}).items():
                self._conversations[cid] = Conversation.from_dict(raw)
            for fid, raw in data.get("folders", {}).items():
                self._folders[fid] = ConversationFolder.from_dict(raw)
            logger.info("Loaded %d conversations, %d folders", len(self._conversations), len(self._folders))
        except Exception as exc:
            logger.warning("Failed to load conversations: %s", exc)

    # ------------------------------------------------------------------
    # Renderers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_markdown(conv: Conversation) -> str:
        lines = [f"# {conv.title}", f"", f"*Created: {datetime.fromtimestamp(conv.created_at).isoformat()}*", f"*Messages: {conv.message_count}*", ""]
        for msg in conv.messages:
            header = f"### {msg.role.upper()}"
            lines.append(header)
            lines.append("")
            lines.append(msg.content)
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    lines.append(f"\n> 🔧 Tool: {tc.get('name', 'unknown')}")
            if msg.tool_result:
                lines.append(f"\n> 📦 Result: {json.dumps(msg.tool_result, indent=2)[:200]}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _to_html(conv: Conversation) -> str:
        messages_html = ""
        for msg in conv.messages:
            role_class = msg.role.lower()
            messages_html += f"""
            <div class="message {role_class}">
                <div class="role-badge">{msg.role.upper()}</div>
                <div class="content">{msg.content}</div>
            </div>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{conv.title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #0d1117; color: #c9d1d9; }}
  h1 {{ border-bottom: 1px solid #30363d; padding-bottom: 8px; }}
  .message {{ margin: 16px 0; padding: 12px; border-radius: 8px; }}
  .message.user {{ background: #1f2937; }}
  .message.assistant {{ background: #0e2a3b; }}
  .message.system {{ background: #1a1a2e; }}
  .role-badge {{ font-size: 11px; font-weight: 600; color: #8b949e; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.05em; }}
  .content {{ line-height: 1.6; white-space: pre-wrap; }}
  .meta {{ color: #8b949e; font-size: 12px; margin-top: 20px; }}
</style>
</head>
<body>
<h1>{conv.title}</h1>
{messages_html}
<div class="meta">Exported from AetherOS — {conv.message_count} messages</div>
</body>
</html>"""

    def summary(self) -> str:
        s = self.stats()
        return (
            f"Conversation Engine: {s['total_conversations']} chats, "
            f"{s['total_messages']} messages, {s['folders']} folders, "
            f"{s['pinned']} pinned, {s['archived']} archived"
        )