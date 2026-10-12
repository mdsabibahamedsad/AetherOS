#!/usr/bin/env python3
"""
Memory Tool Module - Persistent Curated Memory

Provides bounded, file-backed memory that persists across sessions. Two stores:
  - MEMORY.md: agent's personal notes and observations (environment facts, project
    conventions, tool quirks, things learned)
  - USER.md: what the agent knows about the user (preferences, communication style,
    expectations, workflow habits)

Both are injected into the system prompt as a frozen snapshot at session start.
Mid-session writes update files on disk immediately (durable) but do NOT change
the system prompt -- this preserves the prefix cache for the entire session.
The snapshot refreshes on the next session start.

Entry delimiter: § (section sign). Entries can be multiline.
Character limits (not tokens) because char counts are model-independent.

Design:
- Single `memory` tool with action parameter: add, replace, remove, read
- replace/remove use short unique substring matching (not full text or IDs)
- Behavioral guidance lives in the tool schema description
- Frozen snapshot pattern: system prompt is stable, tool responses show live state
"""

import json
import logging
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from aetheros_constants import get_aetheros_home
from typing import Dict, Any, List, Optional, Union, TypedDict

from utils import atomic_replace

# fcntl is Unix-only; on Windows use msvcrt for file locking
msvcrt = None
try:
    import fcntl
except ImportError:
    fcntl = None
    try:
        import msvcrt
    except ImportError:
        pass

logger = logging.getLogger(__name__)


# Enhanced memory entry format for provenance tracking
class MemoryEntryMetadata(TypedDict, total=False):
    """Metadata for tracking provenance of memory entries."""
    source: str  # e.g., "user_input", "agent_deduction", "external_source"
    confidence: float  # 0.0 to 1.0
    timestamp: str  # ISO timestamp when entry was created
    write_origin: str  # e.g., "assistant_tool", "skill_name"
    execution_context: str  # e.g., "foreground", "background_task"
    task_id: Optional[str]  # Associated task ID if any
    tool_call_id: Optional[str]  # Associated tool call ID if any
    session_id: str  # Session where entry was created
    platform: str  # Platform where entry was created (cli, telegram, etc.)
    # Additional domain-specific metadata can be added as needed


def _is_enhanced_entry(entry: str) -> bool:
    """Check if an entry is in the enhanced JSON format."""
    if not entry.strip():
        return False
    try:
        parsed = json.loads(entry)
        return isinstance(parsed, dict) and "text" in parsed
    except (json.JSONDecodeError, TypeError):
        return False


def _parse_enhanced_entry(entry: str) -> Dict[str, Any]:
    """Parse an enhanced entry into text and metadata components.
    
    Returns:
        Dict with keys: "text" (str) and "metadata" (Dict[str, Any])
    """
    try:
        parsed = json.loads(entry)
        if isinstance(parsed, dict) and "text" in parsed:
            # Extract text and metadata
            text = parsed["text"]
            metadata = parsed.get("metadata", {})
            return {"text": text, "metadata": metadata}
    except (json.JSONDecodeError, TypeError):
        pass
    # Fallback: treat as plain text
    return {"text": entry, "metadata": {}}


def _create_enhanced_entry(text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Create an enhanced memory entry JSON string from text and metadata."""
    if metadata is None:
        metadata = {}
    entry = {"text": text, "metadata": metadata}
    return json.dumps(entry, ensure_ascii=False)


def _extract_text_from_entry(entry: str) -> str:
    """Extract the text content from an entry, handling both plain and enhanced formats."""
    if _is_enhanced_entry(entry):
        parsed = _parse_enhanced_entry(entry)
        return parsed["text"]
    return entry


def _extract_metadata_from_entry(entry: str) -> Dict[str, Any]:
    """Extract metadata from an entry, returning empty dict for plain entries."""
    if _is_enhanced_entry(entry):
        parsed = _parse_enhanced_entry(entry)
        return parsed["metadata"]
    return {}

# Where memory files live — resolved dynamically so profile overrides
# (AETHEROS_HOME env var changes) are always respected.  The old module-level
# constant was cached at import time and could go stale if a profile switch
# happened after the first import.
def get_memory_dir() -> Path:
    """Return the profile-scoped memories directory."""
    return get_aetheros_home() / "memories"

ENTRY_DELIMITER = "\n§\n"


# ---------------------------------------------------------------------------
# Memory content scanning — lightweight check for injection/exfiltration
# in content that gets injected into the system prompt.
#
# Patterns live in ``tools/threat_patterns.py`` — the single source of truth
# shared with the context-file scanner and the tool-result delimiter system.
# Memory uses the "strict" scope (broadest pattern set) because:
#  - memory entries are user-curated; the user can rewrite a flagged entry
#  - memory enters the system prompt as a FROZEN snapshot, so a poisoned
#    entry persists for the entire session and across sessions until
#    explicitly removed.
# ---------------------------------------------------------------------------

from tools.threat_patterns import first_threat_message as _first_threat_message


def _scan_memory_content(content: str) -> Optional[str]:
    """Scan memory content for injection/exfil patterns. Returns error string if blocked."""
    return _first_threat_message(content, scope="strict")


def _drift_error(path: "Path", bak_path: str) -> Dict[str, Any]:
    """Build the error dict returned when external drift is detected.

    The on-disk memory file contains content that wouldn't round-trip
    through the tool's parser/serializer — flushing would discard the
    appended/edited content from a patch tool, shell append, manual edit,
    or sister-session write. We refuse the mutation, point the operator at
    the .bak.<ts> snapshot we took, and tell them what to do next.
    """
    return {
        "success": False,
        "error": (
            f"Refusing to write {path.name}: file on disk has content that "
            f"wouldn't round-trip through the memory tool (likely added by "
            f"the patch tool, a shell append, a manual edit, or a "
            f"concurrent session). A snapshot was saved to {bak_path}. "
            f"Resolve the drift first — either rewrite the file as a clean "
            f"§-delimited list of entries, or move the extra content out — "
            f"then retry. This guard exists to prevent silent data loss "
            f"(issue #26045)."
        ),
        "drift_backup": bak_path,
        "remediation": (
            "Open the .bak file, integrate the missing entries into the "
            "memory tool one at a time via memory(action=add, content=...), "
            "then remove or rewrite the original file to a clean state."
        ),
    }


class MemoryStore:
    """
    Bounded curated memory with file persistence. One instance per AIAgent.

    Maintains two parallel states:
      - _system_prompt_snapshot: frozen at load time, used for system prompt injection.
        Never mutated mid-session. Keeps prefix cache stable.
      - memory_entries / user_entries: live state, mutated by tool calls, persisted to disk.
        Tool responses always reflect this live state.
        Entries can be plain text or enhanced JSON format with metadata.
    """

    # Memory scopes definition
    MEMORY_SCOPES = {
        "global": "System-wide memories accessible to all agents/users",
        "user": "Personal memories specific to a user",
        "workspace": "Memories shared within a specific workspace/project",
        "project": "Memories specific to a particular project",
        "conversation": "Memories specific to a conversation session",
        "agent": "Memories specific to an agent instance",
        "task": "Memories specific to a task or subagent execution"
    }

    def __init__(self, memory_char_limit: int = 2200, user_char_limit: int = 1375):
        self.memory_entries: Dict[str, List[str]] = {}  # scope -> entries
        self.user_entries: Dict[str, List[str]] = {}    # scope -> entries
        self.memory_char_limit = memory_char_limit
        self.user_char_limit = user_char_limit
        # Frozen snapshot for system prompt -- set once at load_from_disk()
        self._system_prompt_snapshot: Dict[str, str] = {"memory": "", "user": ""}

    def load_from_disk(self):
        """Load entries from MEMORY.md and USER.md, capture system prompt snapshot.

        The frozen snapshot is what enters the system prompt. We scan each
        entry for injection/promptware patterns at snapshot-build time —
        ANY hit replaces the entry text in the snapshot with a placeholder
        like ``[BLOCKED: …]``, so a poisoned-on-disk memory file (supply
        chain, compromised tool, sister-session write) cannot inject into
        the system prompt.

        The live ``memory_entries`` / ``user_entries`` lists keep the
        original text (or enhanced entries) so the user can still SEE poisoned entries via
        ``memory(action=read)`` and remove them — silently dropping them
        would hide the attack from the user.

        Scanning is deterministic from disk bytes, so the snapshot remains
        stable for the entire session (prefix-cache invariant holds).
        """
        mem_dir = get_memory_dir()
        mem_dir.mkdir(parents=True, exist_ok=True)

        # Load existing files into the "default" scope for backward compatibility
        memory_data = self._read_file(mem_dir / "MEMORY.md")
        user_data = self._read_file(mem_dir / "USER.md")

        # Deduplicate entries (preserves order, keeps first occurrence)
        memory_data = list(dict.fromkeys(memory_data))
        user_data = list(dict.fromkeys(user_data))

        self.memory_entries = {"default": memory_data}
        self.user_entries = {"default": user_data}

        # Sanitize entries for the system-prompt snapshot only.  Live state
        # (memory_entries / user_entries) keeps the original text (or enhanced entries) 
        # so the user can see + remove poisoned entries via the memory tool.
        sanitized_memory = self._sanitize_entries_for_snapshot(memory_data, "MEMORY.md")
        sanitized_user = self._sanitize_entries_for_snapshot(user_data, "USER.md")

        # Extract text content for snapshot (stripping metadata if present)
        snapshot_memory_texts = [_extract_text_from_entry(e) for e in sanitized_memory]
        snapshot_user_texts = [_extract_text_from_entry(e) for e in sanitized_user]

        # Capture frozen snapshot for system prompt injection
        self._system_prompt_snapshot = {
            "memory": self._render_block("memory", snapshot_memory_texts),
            "user": self._render_block("user", snapshot_user_texts),
        }

    @staticmethod
    def _sanitize_entries_for_snapshot(entries: List[str], filename: str) -> List[str]:
        """Return ``entries`` with any threat-matching entry replaced by a placeholder.

        Each entry is scanned with the shared threat-pattern library at the
        ``"strict"`` scope (same as memory writes).  On match, the entry is
        replaced in the returned list with ``"[BLOCKED: <filename> entry
        contained threat pattern: <ids>. Removed from system prompt.]"`` —
        the placeholder enters the snapshot, the original entry stays in
        live state for the user to inspect and delete.

        Empty or already-block-marker entries pass through unchanged.
        """
        from tools.threat_patterns import scan_for_threats

        sanitized: List[str] = []
        for entry in entries:
            if not entry or entry.startswith("[BLOCKED:"):
                sanitized.append(entry)
                continue
            # For enhanced entries, scan the text content only
            text_to_scan = _extract_text_from_entry(entry)
            findings = scan_for_threats(text_to_scan, scope="strict")
            if findings:
                logger.warning(
                    "Memory entry from %s blocked at load time: %s",
                    filename, ", ".join(findings),
                )
                sanitized.append(
                    f"[BLOCKED: {filename} entry contained threat pattern(s): "
                    f"{', '.join(findings)}. Removed from system prompt; "
                    f"use memory(action=read) to inspect and memory(action=remove) "
                    f"to delete the original.]"
                )
            else:
                sanitized.append(entry)
        return sanitized

    @staticmethod
    @contextmanager
    def _file_lock(path: Path):
        """Acquire an exclusive file lock for read-modify-write safety.

        Uses a separate .lock file so the memory file itself can still be
        atomically replaced via os.replace().
        """
        lock_path = path.with_suffix(path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        if fcntl is None and msvcrt is None:
            yield
            return

        fd = open(lock_path, "a+", encoding="utf-8")
        try:
            if fcntl:
                fcntl.flock(fd, fcntl.LOCK_EX)
            else:
                fd.seek(0)
                msvcrt.locking(fd.fileno(), msvcrt.LK_LOCK, 1)
            yield
        finally:
            if fcntl:
                try:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                except (OSError, IOError):
                    pass
            elif msvcrt:
                try:
                    fd.seek(0)
                    msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
                except (OSError, IOError):
                    pass
            fd.close()

    @staticmethod
    def _path_for(target: str, scope: str = "default") -> Path:
        mem_dir = get_memory_dir()
        if target == "user":
            if scope == "default":
                return mem_dir / "USER.md"
            else:
                return mem_dir / f"USER_SCOPE_{scope}.md"
        else:
            if scope == "default":
                return mem_dir / "MEMORY.md"
            else:
                return mem_dir / f"MEMORY_SCOPE_{scope}.md"

    def _reload_target(self, target: str, scope: str = "default") -> Optional[str]:
        """Re-read entries from disk into in-memory state.

        Called under file lock to get the latest state before mutating.
        Returns the backup path if external drift was detected (the on-disk
        file contains content that wouldn't round-trip through our
        parser/serializer, OR an entry larger than the store's char limit).
        When drift is detected the caller must abort the mutation —
        flushing would discard the un-roundtrippable content.
        Returns None on clean reload.
        """
        # For backward compatibility, load the "default" scope from the standard files
        # For other scopes, load from scope-specific files
        path = self._path_for(target, scope)
        
        bak = self._detect_external_drift(target, scope)
        fresh = self._read_file(path)
        fresh = list(dict.fromkeys(fresh))  # deduplicate
        self._set_entries(target, fresh, scope)
        return bak

    def save_to_disk(self, target: str, scope: str = "default"):
        """Persist entries to the appropriate file. Called after every mutation."""
        get_memory_dir().mkdir(parents=True, exist_ok=True)
        
        # For backward compatibility, save the "default" scope to the standard files
        # For other scopes, save to scope-specific files
        self._write_file(self._path_for(target, scope), self._entries_for(target, scope))

    def _entries_for(self, target: str, scope: str = "default") -> List[str]:
        if target == "user":
            return self.user_entries.setdefault(scope, [])
        return self.memory_entries.setdefault(scope, [])

    def _set_entries(self, target: str, entries: List[str], scope: str = "default"):
        if target == "user":
            self.user_entries[scope] = entries
        else:
            self.memory_entries[scope] = entries

    def _char_count(self, target: str, scope: str = "default") -> int:
        entries = self._entries_for(target, scope)
        if not entries:
            return 0
        # Count only the text content (not metadata) toward the character limit
        text_contents = [_extract_text_from_entry(e) for e in entries]
        return len(ENTRY_DELIMITER.join(text_contents))

    def _char_limit(self, target: str, scope: str = "default") -> int:
        if target == "user":
            return self.user_char_limit
        return self.memory_char_limit

    def add(self, target: str, content: str, scope: str = "default", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Append a new entry. Returns error if it would exceed the char limit.
        
        Args:
            target: "memory" or "user"
            content: The text content to store
            scope: Memory scope (default, task, conversation, agent, etc.)
            metadata: Optional provenance metadata for the entry
        """
        content = content.strip()
        if not content:
            return {"success": False, "error": "Content cannot be empty."}

        # Scan for injection/exfiltration before accepting
        scan_error = _scan_memory_content(content)
        if scan_error:
            return {"success": False, "error": scan_error}

        with self._file_lock(self._path_for(target)):
            # Re-read from disk under lock to pick up writes from other sessions.
            # If external drift was detected, the file was backed up to .bak.<ts>
            # — refuse the mutation so we don't clobber the un-roundtrippable
            # content the patch tool / shell append / sister session wrote.
            bak = self._reload_target(target, scope)
            if bak:
                return _drift_error(self._path_for(target, scope), bak)

            entries = self._entries_for(target, scope)
            limit = self._char_limit(target, scope)

            # Reject exact duplicates (based on text content only)
            if content in [_extract_text_from_entry(e) for e in entries]:
                return self._success_response(target, "Entry already exists (no duplicate added).", scope)

            # Calculate what the new total would be
            entry_to_store = _create_enhanced_entry(content, metadata) if metadata is not None else content
            new_entries = entries + [entry_to_store]
            new_total = len(ENTRY_DELIMITER.join(new_entries))

            if new_total > limit:
                current = self._char_count(target, scope)
                return {
                    "success": False,
                    "error": (
                        f"Memory at {current:,}/{limit:,} chars. "
                        f"Adding this entry ({len(content)} chars) would exceed the limit. "
                        f"Consolidate now: use 'replace' to merge overlapping entries into "
                        f"shorter ones or 'remove' stale or less important entries (see "
                        f"current_entries below), then retry this add — all in this turn."
                    ),
                    "current_entries": [_extract_text_from_entry(e) for e in entries],
                    "usage": f"{current:,}/{limit:,}",
                }

            entries.append(entry_to_store)
            self._set_entries(target, entries, scope)
            self.save_to_disk(target)

        return self._success_response(target, "Entry added.", scope)

    def replace(self, target: str, old_text: str, new_content: str, scope: str = "default", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Find entry containing old_text substring, replace it with new_content.
        
        Args:
            target: "memory" or "user"
            old_text: Substring to identify the entry to replace
            new_content: New text content for the entry
            scope: Memory scope
            metadata: Optional provenance metadata for the replacement entry
        """
        old_text = old_text.strip()
        new_content = new_content.strip()
        if not old_text:
            return {"success": False, "error": "old_text cannot be empty."}
        if not new_content:
            return {"success": False, "error": "new_content cannot be empty. Use 'remove' to delete entries."}

        # Scan replacement content for injection/exfiltration
        scan_error = _scan_memory_content(new_content)
        if scan_error:
            return {"success": False, "error": scan_error}

        with self._file_lock(self._path_for(target, scope)):
            bak = self._reload_target(target, scope)
            if bak:
                return _drift_error(self._path_for(target, scope), bak)

            entries = self._entries_for(target, scope)
            matches = [(i, e) for i, e in enumerate(entries) if old_text in _extract_text_from_entry(e)]

            if not matches:
                return {"success": False, "error": f"No entry matched '{old_text}'."}

            if len(matches) > 1:
                # If all matches are identical (exact duplicates), operate on the first one
                unique_texts = {_extract_text_from_entry(e) for _, e in matches}
                if len(unique_texts) > 1:
                    previews = [e[:80] + ("..." if len(e) > 80 else "") for _, e in matches]
                    return {
                        "success": False,
                        "error": f"Multiple entries matched '{old_text}'. Be more specific.",
                        "matches": previews,
                    }
                # All identical -- safe to replace just the first

            idx = matches[0][0]
            limit = self._char_limit(target, scope)

            # Check that replacement doesn't blow the budget
            entry_to_store = _create_enhanced_entry(new_content, metadata) if metadata is not None else new_content
            test_entries = entries.copy()
            test_entries[idx] = entry_to_store
            new_total = len(ENTRY_DELIMITER.join(test_entries))

            if new_total > limit:
                current = self._char_count(target, scope)
                return {
                    "success": False,
                    "error": (
                        f"Replacement would put memory at {new_total:,}/{limit:,} chars. "
                        f"Shorten the new content, or 'remove' other stale or less important "
                        f"entries to make room (see current_entries below), then retry — all "
                        f"in this turn."
                    ),
                    "current_entries": [_extract_text_from_entry(e) for e in entries],
                    "usage": f"{current:,}/{limit:,}",
                }

            entries[idx] = entry_to_store
            self._set_entries(target, entries, scope)
            self.save_to_disk(target)

        return self._success_response(target, "Entry replaced.", scope)

    def remove(self, target: str, old_text: str, scope: str = "default") -> Dict[str, Any]:
        """Remove the entry containing old_text substring."""
        old_text = old_text.strip()
        if not old_text:
            return {"success": False, "error": "old_text cannot be empty."}

        with self._file_lock(self._path_for(target, scope)):
            bak = self._reload_target(target, scope)
            if bak:
                return _drift_error(self._path_for(target, scope), bak)

            entries = self._entries_for(target, scope)
            matches = [(i, e) for i, e in enumerate(entries) if old_text in _extract_text_from_entry(e)]

            if not matches:
                return {"success": False, "error": f"No entry matched '{old_text}'."}

            if len(matches) > 1:
                # If all matches are identical (exact duplicates), remove the first one
                unique_texts = {_extract_text_from_entry(e) for _, e in matches}
                if len(unique_texts) > 1:
                    previews = [e[:80] + ("..." if len(e) > 80 else "") for _, e in matches]
                    return {
                        "success": False,
                        "error": f"Multiple entries matched '{old_text}'. Be more specific.",
                        "matches": previews,
                    }
                # All identical -- safe to remove just the first

            idx = matches[0][0]
            entries.pop(idx)
            self._set_entries(target, entries, scope)
            self.save_to_disk(target)

        return self._success_response(target, "Entry removed.", scope)

    def search(self, target: str, query: str, scope: str = "default") -> Dict[str, Any]:
        """Search for entries that are semantically similar to the query.
        
        For the built-in memory system, we implement a simple text-based search
        that looks for entries containing the query terms. For true semantic
        search, external memory providers should be used.
        """
        if not query or not query.strip():
            return {"success": False, "error": "Query cannot be empty."}

        query = query.strip().lower()
        
        with self._file_lock(self._path_for(target)):
            # Re-read from disk under lock to pick up writes from other sessions.
            # If external drift was detected, the file was backed up to .bak.<ts>
            # — refuse the mutation so we don't clobber the un-roundtrippable
            # content the patch tool / shell append / sister session wrote.
            bak = self._reload_target(target, scope)
            if bak:
                return _drift_error(self._path_for(target, scope), bak)

            entries = self._entries_for(target, scope)
            
            # Simple text-based search - look for entries containing the query
            # For true semantic search, external memory providers should be used
            matching_entries = []
            for entry in entries:
                entry_text = _extract_text_from_entry(entry)
                if query in entry_text.lower():
                    matching_entries.append(entry)
            
            # Also try to find entries that share common words with the query
            query_words = set(query.split())
            for entry in entries:
                if entry not in matching_entries:  # Avoid duplicates
                    entry_text = _extract_text_from_entry(entry)
                    entry_words = set(entry_text.lower().split())
                    # If they share at least one word, consider it a match
                    if query_words & entry_words:
                        matching_entries.append(entry)

            return self._success_response(
                target, 
                f"Found {len(matching_entries)} matching entries.", 
                scope
            )

    def format_for_system_prompt(self, target: str) -> Optional[str]:
        """
        Return the frozen snapshot for system prompt injection.

        This returns the state captured at load_from_disk() time, NOT the live
        state. Mid-session writes do not affect this. This keeps the system
        prompt stable across all turns, preserving the prefix cache.

        Returns None if the snapshot is empty (no entries at load time).
        """
        block = self._system_prompt_snapshot.get(target, "")
        return block if block else None

    # -- Internal helpers --

    def _success_response(self, target: str, message: str = None, scope: str = "default") -> Dict[str, Any]:
        entries = self._entries_for(target, scope)
        current = self._char_count(target, scope)
        limit = self._char_limit(target, scope)
        pct = min(100, int((current / limit) * 100)) if limit > 0 else 0

        # For response, include both raw entries and extracted text for clarity
        extracted_entries = [_extract_text_from_entry(e) for e in entries]

        resp = {
            "success": True,
            "target": target,
            "entries": entries,  # Raw entries (plain or enhanced JSON)
            "extracted_entries": extracted_entries,  # Plain text only for readability
            "usage": f"{pct}% — {current:,}/{limit:,} chars",
            "entry_count": len(entries),
        }
        if message:
            resp["message"] = message
        return resp

    def _render_block(self, target: str, entries: List[str]) -> str:
        """Render a system prompt block with header and usage indicator."""
        if not entries:
            return ""

        # Use only text content for system prompt (exclude metadata)
        text_contents = [_extract_text_from_entry(e) for e in entries]
        content = ENTRY_DELIMITER.join(text_contents)
        current = len(content)
        limit = self._char_limit(target)
        pct = min(100, int((current / limit) * 100)) if limit > 0 else 0

        if target == "user":
            header = f"USER PROFILE (who the user is) [{pct}% — {current:,}/{limit:,} chars]"
        else:
            header = f"MEMORY (your personal notes) [{pct}% — {current:,}/{limit:,} chars]"

        separator = "\u2550" * 46
        return f"{separator}\n{header}\n{separator}\n{content}"

    @staticmethod
    def _read_file(path: Path) -> List[str]:
        """Read a memory file and split into entries.

        No file locking needed: _write_file uses atomic rename, so readers
        always see either the previous complete file or the new complete file.
        """
        if not path.exists():
            return []
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, IOError):
            return []

        if not raw.strip():
            return []

        # Use ENTRY_DELIMITER for consistency with _write_file. Splitting by "§"
        # alone would incorrectly split entries that contain "§" in their content.
        entries = [e.strip() for e in raw.split(ENTRY_DELIMITER)]
        return [e for e in entries if e]

    def _detect_external_drift(self, target: str, scope: str = "default") -> Optional[str]:
        """Return a backup-path string if on-disk content shows external drift.

        The memory file is supposed to be a list of small entries the tool
        wrote, joined by §. Detect drift via two signals:

        1. Round-trip mismatch — re-parsing and re-serializing the file
           doesn't produce identical bytes (rare; would catch oddly-encoded
           delimiters).
        2. Entry-size overflow — any single parsed entry exceeds the
           store's whole-file char limit. The tool budgets the ENTIRE store
           against that limit; no single tool-written entry can exceed it.
           When we see one entry larger than the limit, an external writer
           (patch tool, shell append, manual edit, sister session) appended
           free-form content into what the tool will treat as one entry.
           Flushing would then truncate that entry to the model's new
           content, discarding the appended bytes — issue #26045.

        Returns the absolute path of the .bak file when drift was found and
        backed up; returns None when the file looks tool-shaped.

        Note: this is an INSTANCE method (not static) because we need the
        per-target char_limit for signal #2.
        """
        # For backward compatibility, check the "default" scope in the standard files
        # For other scopes, check scope-specific files
        path = self._path_for(target, scope)
        
        if not path.exists():
            return None
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, IOError):
            return None
        if not raw.strip():
            return None

        parsed = [e.strip() for e in raw.split(ENTRY_DELIMITER) if e.strip()]
        roundtrip = ENTRY_DELIMITER.join(parsed)

        char_limit = self._char_limit(target, scope)
        max_entry_len = max((len(e) for e in parsed), default=0)

        drift_detected = (raw.strip() != roundtrip) or (max_entry_len > char_limit)
        if not drift_detected:
            return None

        # Drift confirmed — snapshot the file so the operator can recover
        # whatever the external writer added, then return the .bak path so
        # the caller can refuse the mutation.
        ts = int(time.time())
        bak_path = path.with_suffix(path.suffix + f".bak.{ts}")
        try:
            bak_path.write_text(raw, encoding="utf-8")
        except (OSError, IOError):
            return str(bak_path) + " (BACKUP FAILED — file unchanged on disk)"
        return str(bak_path)

    @staticmethod
    def _write_file(path: Path, entries: List[str]):
        """Write entries to a memory file using atomic temp-file + rename.

        Previous implementation used open("w") + flock, but "w" truncates the
        file *before* the lock is acquired, creating a race window where
        concurrent readers see an empty file. Atomic rename avoids this:
        readers always see either the old complete file or the new one.
        """
        content = ENTRY_DELIMITER.join(entries) if entries else ""
        try:
            # Write to temp file in same directory (same filesystem for atomic rename)
            fd, tmp_path = tempfile.mkstemp(
                dir=str(path.parent), suffix=".tmp", prefix=".mem_"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                atomic_replace(tmp_path, path)
            except BaseException:
                # Clean up temp file on any failure
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except (OSError, IOError) as e:
            raise RuntimeError(f"Failed to write memory file {path}: {e}")


def _apply_write_gate(action: str, target: str, content: Optional[str],
                      old_text: Optional[str]) -> Optional[str]:
    """Evaluate the memory write gate. Returns a JSON tool-result string when
    the write should NOT proceed normally (blocked or staged), or None when the
    caller should perform the real write.

    Only the mutating actions (add/replace/remove) are gated.
    """
    if action not in {"add", "replace", "remove"}:
        return None

    try:
        from tools import write_approval as wa
    except Exception:
        # If the gate module can't load, fail open (current behaviour) rather
        # than blocking all memory writes.
        return None

    # Build a small inline summary/detail for the foreground approval prompt.
    label = "user profile" if target == "user" else "memory"
    if action == "add":
        summary = f"add to {label}"
        detail = content or ""
    elif action == "replace":
        summary = f"replace in {label}"
        detail = f"old: {old_text}\nnew: {content}"
    else:  # remove
        summary = f"remove from {label}"
        detail = old_text or ""

    decision = wa.evaluate_gate(wa.MEMORY, inline_summary=summary, inline_detail=detail)

    if decision.allow:
        return None

    if decision.blocked:
        return tool_error(decision.message, success=False)

    # stage
    payload = {
        "action": action,
        "target": target,
        "content": content,
        "old_text": old_text,
    }
    record = wa.stage_write(
        wa.MEMORY, payload,
        summary=f"{summary}: {detail[:120]}",
        origin=wa.current_origin(),
    )
    return json.dumps(
        {"success": True, "staged": True, "pending_id": record["id"],
         "message": decision.message},
        ensure_ascii=False,
    )


def memory_tool(
    action: str,
    target: str = "memory",
    content: str = None,
    old_text: str = None,
    scope: str = "default",
    store: Optional[MemoryStore] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Single entry point for the memory tool. Dispatches to MemoryStore methods.

    Returns JSON string with results.
    """
    if store is None:
        return tool_error("Memory is not available. It may be disabled in config or this environment.", success=False)

    if target not in {"memory", "user"}:
        return tool_error(f"Invalid target '{target}'. Use 'memory' or 'user'.", success=False)

    # Validate required params BEFORE the gate so an invalid write is rejected
    # immediately instead of being staged and only failing at approve time.
    if action == "add" and not content:
        return tool_error("Content is required for 'add' action.", success=False)
    if action == "replace" and (not old_text or not content):
        missing = "old_text" if not old_text else "content"
        return tool_error(f"{missing} is required for 'replace' action.", success=False)
    if action == "remove" and not old_text:
        return tool_error("old_text is required for 'remove' action.", success=False)
    if action == "search" and not content:  # For search, query is in content parameter
        return tool_error("Query is required for 'search' action.", success=False)

    # Approval gate: when on, stages the write (background/gateway) or prompts
    # inline (interactive CLI); when off (default) passes straight through.
    gate_result = _apply_write_gate(action, target, content, old_text)
    if gate_result is not None:
        return gate_result

    if action == "add":
        result = store.add(target, content, scope, metadata)

    elif action == "replace":
        result = store.replace(target, old_text, content, scope, metadata)

    elif action == "remove":
        result = store.remove(target, old_text, scope)

    elif action == "search":
        # For search, query is in content parameter
        result = store.search(target, content, scope)

    else:
        return tool_error(f"Unknown action '{action}'. Use: add, replace, remove, search", success=False)

    return json.dumps(result, ensure_ascii=False)


def check_memory_requirements() -> bool:
    """Memory tool has no external requirements -- always available."""
    return True


def apply_memory_pending(payload: Dict[str, Any], store: "MemoryStore") -> Dict[str, Any]:
    """Replay a staged memory write directly against the store, bypassing the
    write gate. Called by the /memory approve handler.

    Returns the store's result dict.
    """
    action = payload.get("action")
    target = payload.get("target", "memory")
    content = payload.get("content") or ""
    old_text = payload.get("old_text") or ""
    metadata = payload.get("metadata")
    if action == "add":
        return store.add(target, content, metadata=metadata)
    if action == "replace":
        return store.replace(target, old_text, content, metadata=metadata)
    if action == "remove":
        return store.remove(target, old_text)
    return {"success": False, "error": f"Unknown staged action '{action}'."}
# OpenAI Function-Calling Schema
# =============================================================================

MEMORY_SCHEMA = {
    "name": "memory",
        "description": (
            "Save durable information to persistent memory that survives across sessions. "
            "Memory is injected into future turns, so keep it compact and focused on facts "
            "that will still matter later.\n\n"
            "WHEN TO SAVE (do this proactively, don't wait to be asked):\n"
            "- User corrects you or says 'remember this' / 'don't do that again'\n"
            "- User shares a preference, habit, or personal detail (name, role, timezone, coding style)\n"
            "- You discover something about the environment (OS, installed tools, project structure)\n"
            "- You learn a convention, API quirk, or workflow specific to this user's setup\n"
            "- You identify a stable fact that will be useful again in future sessions\n\n"
            "PRIORITY: User preferences and corrections > environment facts > procedural knowledge. "
            "The most valuable memory prevents the user from having to repeat themselves.\n\n"
            "Do NOT save task progress, session outcomes, completed-work logs, or temporary TODO "
            "state to memory; use session_search to recall those from past transcripts.\n"
            "If you've discovered a new way to do something, solved a problem that could be "
            "necessary later, save it as a skill with the skill tool.\n\n"
            "TWO TARGETS:\n"
            "- 'user': who the user is -- name, role, preferences, communication style, pet peeves\n"
            "- 'memory': your notes -- environment facts, project conventions, tool quirks, lessons learned\n\n"
            "ACTIONS: add (new entry), replace (update existing -- old_text identifies it), "
            "remove (delete -- old_text identifies it), "
            "search (find semantically similar memories using query).\n\n"
            "SKIP: trivial/obvious info, things easily re-discovered, raw data dumps, and temporary task state."
        ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "replace", "remove", "search"],
                "description": "The action to perform."
            },
            "target": {
                "type": "string",
                "enum": ["memory", "user"],
                "description": "Which memory store: 'memory' for personal notes, 'user' for user profile."
            },
            "content": {
                "type": "string",
                "description": "The entry content. Required for 'add' and 'replace'."
            },
            "old_text": {
                "type": "string",
                "description": "Short unique substring identifying the entry to replace or remove."
            },
            "query": {
                "type": "string",
                "description": "The search query for finding semantically similar memories. Required for 'search' action."
            },
            "metadata": {
                "type": "object",
                "description": "Optional provenance metadata for the memory entry."
            }
        },
        "required": ["action", "target"],
    },
}


# --- Registry ---
from tools.registry import registry, tool_error

registry.register(
    name="memory",
    toolset="memory",
    schema=MEMORY_SCHEMA,
    handler=lambda args, **kw: memory_tool(
        action=args.get("action", ""),
        target=args.get("target", "memory"),
        content=args.get("content"),
        old_text=args.get("old_text"),
        metadata=args.get("metadata"),
        store=kw.get("store")),
    check_fn=check_memory_requirements,
    emoji="🧠",
)




