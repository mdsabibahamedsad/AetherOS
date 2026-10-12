"""Filesystem Runtime.

Provides comprehensive filesystem operations:
- Read, write, append, move, rename, delete
- Search, watch, index
- Compress, extract
- Checksum, metadata
"""

from __future__ import annotations

from tool_runtime.filesystem.tools import FilesystemRuntime

__all__ = ["FilesystemRuntime"]
