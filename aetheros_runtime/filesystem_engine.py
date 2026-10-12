"""File System Engine — read, write, move, rename, delete, search, index, watch.

Permission-aware filesystem operations with change tracking.
"""

from __future__ import annotations

import enum
import hashlib
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("aetheros_runtime.fs")


class FileChange(enum.Enum):
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    MOVED = "moved"


@dataclass
class FileInfo:
    path: Path
    name: str
    size: int = 0
    is_dir: bool = False
    is_file: bool = True
    is_symlink: bool = False
    modified_at: float = 0.0
    created_at: float = 0.0
    extension: str = ""
    permissions: str = ""
    hash: str = ""
    encoding: str = ""

    @classmethod
    def from_path(cls, path: Path) -> "FileInfo":
        try:
            stat = path.stat()
            return cls(
                path=path,
                name=path.name,
                size=stat.st_size,
                is_dir=path.is_dir(),
                is_file=path.is_file(),
                is_symlink=path.is_symlink(),
                modified_at=stat.st_mtime,
                created_at=getattr(stat, "st_ctime", 0),
                extension=path.suffix.lower(),
                permissions=oct(stat.st_mode)[-3:],
            )
        except OSError:
            return cls(path=path, name=path.name)


FileChangeWatcher = Callable[[Path, FileChange], None]


class FileSystemEngine:
    """Permission-aware filesystem engine with operations and change watching."""

    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB default max
    BINARY_EXTENSIONS: Set[str] = {
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp",
        ".mp3", ".wav", ".mp4", ".avi", ".mov", ".mkv",
        ".zip", ".gz", ".tar", ".7z", ".rar",
        ".exe", ".dll", ".so", ".dylib", ".bin",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx",
        ".pyc", ".obj", ".o", ".a", ".lib",
    }

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._allowed_dirs: Set[Path] = set()
        self._denied_dirs: Set[Path] = set()
        self._watchers: List[FileChangeWatcher] = []
        self._max_file_size: int = self.MAX_FILE_SIZE
        self._history: List[Dict[str, Any]] = []
        self._max_history: int = 100
        self._index: Dict[str, List[Path]] = {}
        self._watch_thread: Optional[threading.Thread] = None
        self._watch_stop = threading.Event()
        self._snapshot: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    def allow_directory(self, path: Path) -> None:
        with self._lock:
            self._allowed_dirs.add(path.resolve())

    def deny_directory(self, path: Path) -> None:
        with self._lock:
            self._denied_dirs.add(path.resolve())

    def is_allowed(self, path: Path) -> bool:
        resolved = path.resolve()
        with self._lock:
            if self._denied_dirs:
                for denied in self._denied_dirs:
                    if denied in resolved.parents or denied == resolved:
                        return False
            if self._allowed_dirs:
                for allowed in self._allowed_dirs:
                    if allowed in resolved.parents or allowed == resolved:
                        return True
                return False
        return True

    # ------------------------------------------------------------------
    # Read / Write
    # ------------------------------------------------------------------

    def read(self, path: Path, encoding: str = "utf-8") -> Optional[str]:
        if not self.is_allowed(path):
            logger.warning("Read denied: %s", path)
            return None
        try:
            if not path.exists() or not path.is_file():
                return None
            if path.stat().st_size > self._max_file_size:
                logger.warning("File too large: %s (%d bytes)", path, path.stat().st_size)
                return None
            ext = path.suffix.lower()
            if ext in self.BINARY_EXTENSIONS:
                return None
            content = path.read_text(encoding=encoding, errors="replace")
            self._log_operation("read", path)
            return content
        except Exception as exc:
            logger.error("Read failed: %s: %s", path, exc)
            return None

    def write(self, path: Path, content: str, encoding: str = "utf-8") -> bool:
        if not self.is_allowed(path):
            logger.warning("Write denied: %s", path)
            return False
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding=encoding)
            self._log_operation("write", path)
            logger.info("File written: %s (%d bytes)", path, len(content))
            return True
        except Exception as exc:
            logger.error("Write failed: %s: %s", path, exc)
            return False

    def append(self, path: Path, content: str, encoding: str = "utf-8") -> bool:
        if not self.is_allowed(path):
            return False
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding=encoding) as f:
                f.write(content)
            self._log_operation("append", path)
            return True
        except Exception as exc:
            logger.error("Append failed: %s: %s", path, exc)
            return False

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def move(self, src: Path, dst: Path) -> bool:
        if not self.is_allowed(src) or not self.is_allowed(dst):
            return False
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
            self._log_operation("move", src, {"destination": str(dst)})
            self._notify_watchers(src, FileChange.MOVED)
            return True
        except Exception as exc:
            logger.error("Move failed: %s -> %s: %s", src, dst, exc)
            return False

    def rename(self, path: Path, new_name: str) -> bool:
        return self.move(path, path.parent / new_name)

    def delete(self, path: Path) -> bool:
        if not self.is_allowed(path):
            return False
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                import shutil
                shutil.rmtree(path)
            self._log_operation("delete", path)
            self._notify_watchers(path, FileChange.DELETED)
            return True
        except Exception as exc:
            logger.error("Delete failed: %s: %s", path, exc)
            return False

    def copy(self, src: Path, dst: Path) -> bool:
        if not self.is_allowed(src) or not self.is_allowed(dst):
            return False
        try:
            import shutil
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_file():
                shutil.copy2(src, dst)
            elif src.is_dir():
                shutil.copytree(src, dst)
            self._log_operation("copy", src, {"destination": str(dst)})
            return True
        except Exception as exc:
            logger.error("Copy failed: %s -> %s: %s", src, dst, exc)
            return False

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, pattern: str, root: Optional[Path] = None) -> List[Path]:
        search_root = root or Path.cwd()
        results: List[Path] = []
        try:
            for p in search_root.rglob(pattern):
                if self.is_allowed(p):
                    results.append(p)
        except (PermissionError, OSError) as exc:
            logger.warning("Search error: %s", exc)
        return sorted(results)

    def search_content(self, query: str, root: Optional[Path] = None, max_results: int = 50) -> List[Path]:
        search_root = root or Path.cwd()
        results: List[Path] = []
        try:
            for p in search_root.rglob("*"):
                if len(results) >= max_results:
                    break
                if not p.is_file() or not self.is_allowed(p):
                    continue
                if p.suffix.lower() in self.BINARY_EXTENSIONS:
                    continue
                if p.stat().st_size > self._max_file_size:
                    continue
                try:
                    content = p.read_text(encoding="utf-8", errors="replace")
                    if query.lower() in content.lower():
                        results.append(p)
                except (OSError, UnicodeDecodeError):
                    pass
        except (PermissionError, OSError):
            pass
        return results

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def index_directory(self, directory: Path) -> Dict[str, List[Path]]:
        index: Dict[str, List[Path]] = {}
        try:
            for p in directory.rglob("*"):
                if p.is_file() and self.is_allowed(p):
                    ext = p.suffix.lower() or "(no ext)"
                    if ext not in index:
                        index[ext] = []
                    index[ext].append(p)
        except (PermissionError, OSError):
            pass
        with self._lock:
            self._index = index
        return index

    def get_index(self) -> Dict[str, List[Path]]:
        with self._lock:
            return dict(self._index)

    # ------------------------------------------------------------------
    # File watching
    # ------------------------------------------------------------------

    def start_watching(self, directory: Path, interval: float = 2.0) -> None:
        with self._lock:
            self._snapshot = self._take_snapshot(directory)
        self._watch_stop.clear()
        self._watch_thread = threading.Thread(
            target=self._watch_loop, args=(directory, interval),
            daemon=True, name="fs-watcher",
        )
        self._watch_thread.start()

    def stop_watching(self) -> None:
        self._watch_stop.set()
        if self._watch_thread:
            self._watch_thread.join(timeout=5)

    def on_change(self, watcher: FileChangeWatcher) -> None:
        with self._lock:
            self._watchers.append(watcher)

    def _watch_loop(self, directory: Path, interval: float) -> None:
        while not self._watch_stop.is_set():
            time.sleep(interval)
            try:
                current = self._take_snapshot(directory)
                for path_str, mtime in current.items():
                    old_mtime = self._snapshot.get(path_str)
                    if old_mtime is None:
                        self._notify_watchers(Path(path_str), FileChange.CREATED)
                    elif old_mtime != mtime:
                        self._notify_watchers(Path(path_str), FileChange.MODIFIED)
                for path_str in self._snapshot:
                    if path_str not in current:
                        self._notify_watchers(Path(path_str), FileChange.DELETED)
                self._snapshot = current
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_info(self, path: Path) -> Optional[FileInfo]:
        if not path.exists():
            return None
        return FileInfo.from_path(path)

    def list_directory(self, path: Path) -> List[FileInfo]:
        try:
            return [FileInfo.from_path(p) for p in path.iterdir() if self.is_allowed(p)]
        except (PermissionError, OSError):
            return []

    def file_exists(self, path: Path) -> bool:
        return path.exists() and path.is_file()

    def dir_exists(self, path: Path) -> bool:
        return path.exists() and path.is_dir()

    def ensure_dir(self, path: Path) -> bool:
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except (PermissionError, OSError):
            return False

    def get_size(self, path: Path) -> int:
        if path.is_file():
            return path.stat().st_size
        total = 0
        try:
            for p in path.rglob("*"):
                if p.is_file():
                    total += p.stat().st_size
        except (PermissionError, OSError):
            pass
        return total

    def compute_hash(self, path: Path) -> str:
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest()
        except Exception:
            return ""

    def set_max_file_size(self, bytes_: int) -> None:
        self._max_file_size = bytes_

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _log_operation(self, op: str, path: Path, extra: Optional[Dict[str, Any]] = None) -> None:
        entry = {"operation": op, "path": str(path), "timestamp": time.time(), **(extra or {})}
        with self._lock:
            self._history.append(entry)
            if len(self._history) > self._max_history:
                self._history.pop(0)

    def _notify_watchers(self, path: Path, change: FileChange) -> None:
        with self._lock:
            watchers = list(self._watchers)
        for w in watchers:
            try:
                w(path, change)
            except Exception:
                pass

    @staticmethod
    def _take_snapshot(directory: Path) -> Dict[str, float]:
        snapshot: Dict[str, float] = {}
        try:
            for p in directory.rglob("*"):
                if p.is_file():
                    snapshot[str(p)] = p.stat().st_mtime
        except (PermissionError, OSError):
            pass
        return snapshot

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._history[-limit:])

    def health_check(self) -> bool:
        try:
            return Path.cwd().exists()
        except Exception:
            return False

    def summary(self) -> str:
        return f"File System Engine: watching {len(self._watchers)} watchers, {len(self._index)} file types indexed"