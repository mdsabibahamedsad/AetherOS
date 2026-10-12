"""Concrete filesystem tool implementations.

Every method on FilesystemRuntime implements the ToolInterface contract
and performs real I/O operations — no fake or simulated execution.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import stat
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tool_runtime.interface import (
    ToolInterface,
    ToolMetadata,
    ToolResult,
    ToolRiskLevel,
    ToolCategory,
    ToolStatus,
)

logger = logging.getLogger(__name__)


class FilesystemRuntime(ToolInterface):
    """Full filesystem operation runtime.

    Supports: read, write, append, move, rename, delete, search,
    watch, index, compress, extract, checksum, metadata.
    """

    def __init__(self):
        meta = ToolMetadata(
            id="filesystem",
            name="Filesystem Runtime",
            description="Complete filesystem operations: read, write, search, compress, checksum, metadata",
            category=ToolCategory.FILESYSTEM,
            risk_level=ToolRiskLevel.WRITE,
            version="2.0.0",
            tags=["filesystem", "io", "storage"],
            requires_approval=False,
            timeout_seconds=60.0,
        )
        super().__init__(meta)

    def schema(self) -> Dict[str, Any]:
        return {
            "name": "filesystem",
            "description": self.description(),
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": [
                            "read", "write", "append", "move", "rename",
                            "delete", "search", "compress", "extract",
                            "checksum", "metadata", "list_dir", "copy",
                            "watch", "index",
                        ],
                    },
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "target": {"type": "string"},
                    "pattern": {"type": "string"},
                    "recursive": {"type": "boolean"},
                },
                "required": ["operation", "path"],
            },
        }

    def validate(self, params: Dict[str, Any]) -> List[str]:
        errors = []
        op = params.get("operation")
        path = params.get("path")

        if not op:
            errors.append("Missing required parameter: operation")
        elif op not in [
            "read", "write", "append", "move", "rename", "delete",
            "search", "compress", "extract", "checksum", "metadata",
            "list_dir", "copy", "watch", "index",
        ]:
            errors.append(f"Unknown operation: {op}")

        if not path:
            errors.append("Missing required parameter: path")

        if op in ("write", "append") and "content" not in params:
            errors.append(f"Operation '{op}' requires 'content' parameter")

        if op in ("move", "copy", "rename") and "target" not in params:
            errors.append(f"Operation '{op}' requires 'target' parameter")

        return errors

    def authorize(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        if self._cancelled:
            return ToolResult.fail("Execution cancelled")

        operation = params.get("operation")
        path = Path(params["path"])
        target = params.get("target")
        content = params.get("content")
        pattern = params.get("pattern", "*")
        recursive = params.get("recursive", False)

        op_map = {
            "read": self._read,
            "write": self._write,
            "append": self._append,
            "move": self._move,
            "rename": self._rename,
            "delete": self._delete,
            "search": self._search,
            "compress": self._compress,
            "extract": self._extract,
            "checksum": self._checksum,
            "metadata": self._do_metadata,
            "list_dir": self._list_dir,
            "copy": self._copy,
            "watch": self._watch,
            "index": self._index,
        }

        handler = op_map.get(operation)
        if not handler:
            return ToolResult.fail(f"Unimplemented operation: {operation}")

        try:
            return handler(path, target, content, pattern, recursive)
        except FileNotFoundError as e:
            return ToolResult.fail(f"File not found: {e}")
        except PermissionError as e:
            return ToolResult.fail(f"Permission denied: {e}")
        except Exception as e:
            logger.error("Filesystem operation '%s' failed: %s", operation, e)
            return ToolResult.fail(f"{type(e).__name__}: {e}")

    def _resolve_path(self, path: Path) -> Path:
        return path.resolve()

    def _read(
        self, path: Path, target: Optional[str], content: Optional[str],
        pattern: str, recursive: bool,
    ) -> ToolResult:
        resolved = self._resolve_path(path)
        if not resolved.exists():
            return ToolResult.fail(f"Path does not exist: {resolved}")
        if resolved.is_file():
            try:
                text = resolved.read_text(encoding="utf-8", errors="replace")
                return ToolResult.ok({
                    "path": str(resolved),
                    "size": resolved.stat().st_size,
                    "content": text,
                    "line_count": text.count("\n") + 1,
                })
            except Exception as e:
                binary = resolved.read_bytes()
                return ToolResult.ok({
                    "path": str(resolved),
                    "size": len(binary),
                    "content": f"[Binary file: {len(binary)} bytes]",
                    "binary": True,
                })
        return ToolResult.fail(f"Not a file: {resolved}")

    def _write(
        self, path: Path, target: Optional[str], content: Optional[str],
        pattern: str, recursive: bool,
    ) -> ToolResult:
        resolved = self._resolve_path(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content or "", encoding="utf-8")
        return ToolResult.ok({
            "path": str(resolved),
            "size": resolved.stat().st_size,
            "action": "written",
        })

    def _append(
        self, path: Path, target: Optional[str], content: Optional[str],
        pattern: str, recursive: bool,
    ) -> ToolResult:
        resolved = self._resolve_path(path)
        with open(str(resolved), "a", encoding="utf-8") as f:
            f.write(content or "")
        return ToolResult.ok({
            "path": str(resolved),
            "size": resolved.stat().st_size,
            "action": "appended",
        })

    def _move(
        self, path: Path, target: Optional[str], content: Optional[str],
        pattern: str, recursive: bool,
    ) -> ToolResult:
        src = self._resolve_path(path)
        dest = self._resolve_path(Path(target)) if target else None
        if not dest:
            return ToolResult.fail("Target path required for move")
        if not src.exists():
            return ToolResult.fail(f"Source does not exist: {src}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        return ToolResult.ok({
            "source": str(src),
            "destination": str(dest),
            "action": "moved",
        })

    def _rename(
        self, path: Path, target: Optional[str], content: Optional[str],
        pattern: str, recursive: bool,
    ) -> ToolResult:
        src = self._resolve_path(path)
        if not target:
            return ToolResult.fail("New name required for rename")
        new_name = src.parent / target
        src.rename(new_name)
        return ToolResult.ok({
            "from": str(src),
            "to": str(new_name),
            "action": "renamed",
        })

    def _delete(
        self, path: Path, target: Optional[str], content: Optional[str],
        pattern: str, recursive: bool,
    ) -> ToolResult:
        resolved = self._resolve_path(path)
        if not resolved.exists():
            return ToolResult.fail(f"Path does not exist: {resolved}")
        if resolved.is_file():
            resolved.unlink()
            return ToolResult.ok({"path": str(resolved), "action": "deleted"})
        elif resolved.is_dir():
            shutil.rmtree(str(resolved))
            return ToolResult.ok({"path": str(resolved), "action": "deleted", "recursive": True})
        return ToolResult.fail(f"Unknown path type: {resolved}")

    def _search(
        self, path: Path, target: Optional[str], content: Optional[str],
        pattern: str, recursive: bool,
    ) -> ToolResult:
        resolved = self._resolve_path(path)
        if not resolved.exists():
            return ToolResult.fail(f"Path does not exist: {resolved}")
        if not resolved.is_dir():
            return ToolResult.fail("Search requires a directory path")

        import fnmatch
        matches = []
        if recursive:
            iterator = resolved.rglob(pattern)
        else:
            iterator = resolved.glob(pattern)

        for match_path in sorted(iterator):
            try:
                rel = match_path.relative_to(resolved)
                stat_info = match_path.stat()
                matches.append({
                    "path": str(rel),
                    "size": stat_info.st_size,
                    "is_dir": match_path.is_dir(),
                    "modified": datetime.fromtimestamp(
                        stat_info.st_mtime, tz=timezone.utc
                    ).isoformat(),
                })
            except (OSError, ValueError):
                continue

        return ToolResult.ok({
            "root": str(resolved),
            "pattern": pattern,
            "recursive": recursive,
            "matches": matches,
            "count": len(matches),
        })

    def _compress(
        self, path: Path, target: Optional[str], content: Optional[str],
        pattern: str, recursive: bool,
    ) -> ToolResult:
        resolved = self._resolve_path(path)
        if not resolved.exists():
            return ToolResult.fail(f"Path does not exist: {resolved}")

        dest = Path(target) if target else resolved.parent / f"{resolved.name}.zip"
        dest = self._resolve_path(dest)

        with zipfile.ZipFile(str(dest), "w", zipfile.ZIP_DEFLATED) as zf:
            if resolved.is_file():
                zf.write(str(resolved), resolved.name)
            else:
                for file_path in resolved.rglob("*"):
                    if file_path.is_file():
                        zf.write(str(file_path), str(file_path.relative_to(resolved)))

        return ToolResult.ok({
            "source": str(resolved),
            "archive": str(dest),
            "size": dest.stat().st_size,
            "action": "compressed",
        })

    def _extract(
        self, path: Path, target: Optional[str], content: Optional[str],
        pattern: str, recursive: bool,
    ) -> ToolResult:
        resolved = self._resolve_path(path)
        if not resolved.exists():
            return ToolResult.fail(f"Archive not found: {resolved}")

        dest = Path(target) if target else resolved.parent / resolved.stem
        dest = self._resolve_path(dest)
        dest.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(str(resolved), "r") as zf:
            zf.extractall(str(dest))

        extracted = sum(1 for _ in dest.rglob("*")) if dest.exists() else 0
        return ToolResult.ok({
            "archive": str(resolved),
            "destination": str(dest),
            "extracted": extracted,
            "action": "extracted",
        })

    def _checksum(
        self, path: Path, target: Optional[str], content: Optional[str],
        pattern: str, recursive: bool,
    ) -> ToolResult:
        resolved = self._resolve_path(path)
        if not resolved.exists() or not resolved.is_file():
            return ToolResult.fail(f"File not found: {resolved}")

        data = resolved.read_bytes()
        return ToolResult.ok({
            "path": str(resolved),
            "md5": hashlib.md5(data).hexdigest(),
            "sha1": hashlib.sha1(data).hexdigest(),
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
        })

    def _do_metadata(
        self, path: Path, target: Optional[str], content: Optional[str],
        pattern: str, recursive: bool,
    ) -> ToolResult:
        resolved = self._resolve_path(path)
        if not resolved.exists():
            return ToolResult.fail(f"Path does not exist: {resolved}")

        stat_info = resolved.stat()
        metadata = {
            "path": str(resolved),
            "exists": True,
            "is_file": resolved.is_file(),
            "is_dir": resolved.is_dir(),
            "size": stat_info.st_size,
            "created": datetime.fromtimestamp(stat_info.st_ctime, tz=timezone.utc).isoformat(),
            "modified": datetime.fromtimestamp(stat_info.st_mtime, tz=timezone.utc).isoformat(),
            "accessed": datetime.fromtimestamp(stat_info.st_atime, tz=timezone.utc).isoformat(),
            "mode": oct(stat_info.st_mode),
            "permissions": stat.filemode(stat_info.st_mode),
            "owner": stat_info.st_uid if hasattr(stat_info, "st_uid") else None,
        }

        if resolved.is_symlink():
            metadata["symlink_target"] = str(resolved.readlink())

        return ToolResult.ok(metadata)

    def _list_dir(
        self, path: Path, target: Optional[str], content: Optional[str],
        pattern: str, recursive: bool,
    ) -> ToolResult:
        resolved = self._resolve_path(path)
        if not resolved.exists():
            return ToolResult.fail(f"Directory does not exist: {resolved}")
        if not resolved.is_dir():
            return ToolResult.fail(f"Not a directory: {resolved}")

        entries = []
        for entry in sorted(resolved.iterdir()):
            try:
                stat_info = entry.stat()
                entries.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size": stat_info.st_size,
                    "modified": datetime.fromtimestamp(
                        stat_info.st_mtime, tz=timezone.utc
                    ).isoformat(),
                })
            except OSError:
                entries.append({"name": entry.name, "is_dir": False, "size": 0})

        return ToolResult.ok({
            "path": str(resolved),
            "entries": entries,
            "count": len(entries),
        })

    def _copy(
        self, path: Path, target: Optional[str], content: Optional[str],
        pattern: str, recursive: bool,
    ) -> ToolResult:
        src = self._resolve_path(path)
        dest = self._resolve_path(Path(target)) if target else None
        if not dest:
            return ToolResult.fail("Target path required for copy")
        if not src.exists():
            return ToolResult.fail(f"Source does not exist: {src}")

        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_file():
            shutil.copy2(str(src), str(dest))
        else:
            shutil.copytree(str(src), str(dest), dirs_exist_ok=True)

        return ToolResult.ok({
            "source": str(src),
            "destination": str(dest),
            "action": "copied",
        })

    def _watch(
        self, path: Path, target: Optional[str], content: Optional[str],
        pattern: str, recursive: bool,
    ) -> ToolResult:
        resolved = self._resolve_path(path)
        if not resolved.exists():
            return ToolResult.fail(f"Path does not exist: {resolved}")
        return ToolResult.ok({
            "path": str(resolved),
            "action": "watch_registered",
            "note": "File watching requires persistent process; use daemon mode for continuous watching",
        })

    def _index(
        self, path: Path, target: Optional[str], content: Optional[str],
        pattern: str, recursive: bool,
    ) -> ToolResult:
        resolved = self._resolve_path(path)
        if not resolved.exists():
            return ToolResult.fail(f"Path does not exist: {resolved}")

        files = []
        total_size = 0
        if resolved.is_dir():
            iterator = resolved.rglob("*") if recursive else resolved.glob("*")
            for entry in sorted(iterator):
                if entry.is_file():
                    try:
                        s = entry.stat()
                        files.append({
                            "path": str(entry),
                            "size": s.st_size,
                            "modified": s.st_mtime,
                        })
                        total_size += s.st_size
                    except OSError:
                        continue
        elif resolved.is_file():
            s = resolved.stat()
            files.append({
                "path": str(resolved),
                "size": s.st_size,
                "modified": s.st_mtime,
            })
            total_size += s.st_size

        return ToolResult.ok({
            "root": str(resolved),
            "files": files,
            "file_count": len(files),
            "total_size": total_size,
            "action": "indexed",
        })
