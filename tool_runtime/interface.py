"""Universal Tool Interface.

Every tool in AetherOS implements this interface, providing a consistent
contract for registration, validation, authorization, execution, cancellation,
status reporting, and health checking.
"""

from __future__ import annotations

import enum
import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


class ToolStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ToolRiskLevel(enum.Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    SYSTEM = "system"
    NETWORK = "network"
    CREDENTIAL = "credential"
    ADMIN = "admin"


class ToolCategory(enum.Enum):
    FILESYSTEM = "filesystem"
    TERMINAL = "terminal"
    PYTHON = "python"
    BROWSER = "browser"
    DESKTOP = "desktop"
    GIT = "git"
    REST_API = "rest_api"
    DATABASE = "database"
    PLUGIN = "plugin"
    CHAINING = "chaining"
    UTILITY = "utility"
    SYSTEM = "system"
    COMMUNICATION = "communication"


@dataclass
class ToolResult:
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    status: ToolStatus = ToolStatus.COMPLETED
    artifacts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "artifacts": self.artifacts,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)

    @classmethod
    def ok(cls, output: Any = None, **kwargs) -> "ToolResult":
        return cls(success=True, output=output, **kwargs)

    @classmethod
    def fail(cls, error: str, **kwargs) -> "ToolResult":
        return cls(success=False, error=error, status=ToolStatus.FAILED, **kwargs)

    @classmethod
    def timeout(cls, error: str = "Execution timed out") -> "ToolResult":
        return cls(success=False, error=error, status=ToolStatus.TIMEOUT)


@dataclass
class ToolMetadata:
    id: str
    name: str
    description: str
    category: ToolCategory
    risk_level: ToolRiskLevel
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    requires_approval: bool = False
    timeout_seconds: float = 30.0
    allowed_contexts: List[str] = field(default_factory=lambda: ["*"])


class ToolInterface(ABC):
    """Abstract base class that every tool runtime must implement."""

    def __init__(self, metadata: ToolMetadata):
        self._metadata = metadata
        self._execution_id: Optional[str] = None
        self._start_time: Optional[float] = None
        self._cancelled = False

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    def id(self) -> str:
        return self._metadata.id

    def name(self) -> str:
        return self._metadata.name

    def description(self) -> str:
        return self._metadata.description

    @abstractmethod
    def schema(self) -> Dict[str, Any]:
        """Return JSON Schema for this tool's parameters."""

    @abstractmethod
    def validate(self, params: Dict[str, Any]) -> List[str]:
        """Validate parameters against schema. Return list of errors (empty = valid)."""

    @abstractmethod
    def authorize(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Check if execution is authorized in the given context.
        Returns (authorized, reason_if_denied)."""

    @abstractmethod
    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        """Execute the tool with given parameters and context."""

    def cancel(self) -> bool:
        """Request cancellation of running execution. Returns True if acknowledged."""
        self._cancelled = True
        return True

    def status(self) -> ToolStatus:
        """Return current execution status."""
        if self._cancelled:
            return ToolStatus.CANCELLED
        if self._start_time is None:
            return ToolStatus.PENDING
        return ToolStatus.RUNNING

    def health(self) -> Dict[str, Any]:
        """Return health check data."""
        return {
            "id": self._metadata.id,
            "name": self._metadata.name,
            "healthy": True,
            "version": self._metadata.version,
            "category": self._metadata.category.value,
        }


class ToolRegistryAdapter:
    """Adapter that wraps existing tools/registry.py tools into ToolInterface."""

    def __init__(self, registry_module=None):
        if registry_module is None:
            from tools.registry import registry as _reg
            registry_module = _reg
        self._registry = registry_module
        self._wrapped: Dict[str, ToolInterface] = {}

    def wrap_all(self) -> Dict[str, ToolInterface]:
        entries, _ = self._registry._snapshot_state()
        for entry in entries:
            if entry.name not in self._wrapped:
                self._wrapped[entry.name] = self._wrap_entry(entry)
        return dict(self._wrapped)

    def _wrap_entry(self, entry) -> ToolInterface:
        from tool_runtime.manager import LegacyToolWrapper
        return LegacyToolWrapper(entry)

    def get(self, name: str) -> Optional[ToolInterface]:
        if name not in self._wrapped:
            entry = self._registry.get_entry(name)
            if entry:
                self._wrapped[name] = self._wrap_entry(entry)
        return self._wrapped.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": name,
                "description": tool.description(),
                "schema": tool.schema(),
                "risk_level": tool.metadata.risk_level.value,
                "category": tool.metadata.category.value,
            }
            for name, tool in self._wrapped.items()
        ]
