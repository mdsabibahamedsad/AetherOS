"""
Developer Tools for AetherOS
============================

Tools for extension development:
    - Live Reload: Hot reload extensions during development
    - Extension Inspector: Debug and inspect extensions
    - Performance Monitor: Monitor extension performance
    - Memory Usage: Track memory usage
    - Logs: View extension logs
    - Error Viewer: View extension errors

Usage::

    from aetheros_developer_platform.developer_tools import DevToolsManager

    tools = DevToolsManager()
    tools.enable_live_reload("/path/to/extension")
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExtensionInfo:
    """Information about a loaded extension."""
    name: str
    version: str
    state: str
    loaded_at: Optional[float] = None
    memory_usage: int = 0
    cpu_time: float = 0.0
    error_count: int = 0
    last_error: Optional[str] = None


@dataclass
class LogEntry:
    """A log entry."""
    timestamp: float
    level: str
    message: str
    extension: str = ""
    source: str = ""


@dataclass
class PerformanceMetrics:
    """Performance metrics for an extension."""
    extension: str
    total_calls: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    max_time: float = 0.0
    min_time: float = float("inf")
    error_rate: float = 0.0


class DevToolsManager:
    """Developer tools for AetherOS extensions.

    Usage::

        tools = DevToolsManager()

        # Enable live reload
        tools.enable_live_reload("/path/to/extension")

        # View logs
        logs = tools.get_logs(extension="my-plugin")

        # Get performance metrics
        metrics = tools.get_performance_metrics("my-plugin")
    """

    def __init__(self) -> None:
        self._extensions: Dict[str, ExtensionInfo] = {}
        self._logs: List[LogEntry] = []
        self._metrics: Dict[str, PerformanceMetrics] = {}
        self._live_reload_watchers: Dict[str, Any] = {}
        self._inspector_data: Dict[str, Dict[str, Any]] = {}

    def enable_live_reload(self, extension_path: str) -> bool:
        """Enable live reload for an extension."""
        path = Path(extension_path)
        if not path.exists():
            logger.error("Extension path does not exist: %s", extension_path)
            return False

        # In a real implementation, this would set up file watchers
        self._live_reload_watchers[extension_path] = {
            "path": str(path),
            "enabled": True,
            "last_modified": time.time(),
        }
        logger.info("Enabled live reload for: %s", extension_path)
        return True

    def disable_live_reload(self, extension_path: str) -> bool:
        """Disable live reload for an extension."""
        if extension_path in self._live_reload_watchers:
            del self._live_reload_watchers[extension_path]
            logger.info("Disabled live reload for: %s", extension_path)
            return True
        return False

    def get_live_reload_status(self) -> Dict[str, Any]:
        """Get live reload status."""
        return {
            "watchers": len(self._live_reload_watchers),
            "paths": list(self._live_reload_watchers.keys()),
        }

    def register_extension(self, info: ExtensionInfo) -> None:
        """Register an extension for monitoring."""
        self._extensions[info.name] = info

    def update_extension(self, name: str, **kwargs: Any) -> bool:
        """Update extension info."""
        if name in self._extensions:
            for key, value in kwargs.items():
                if hasattr(self._extensions[name], key):
                    setattr(self._extensions[name], key, value)
            return True
        return False

    def get_extension_info(self, name: str) -> Optional[ExtensionInfo]:
        """Get extension info."""
        return self._extensions.get(name)

    def list_extensions(self) -> List[ExtensionInfo]:
        """List all registered extensions."""
        return list(self._extensions.values())

    def log(
        self,
        level: str,
        message: str,
        extension: str = "",
        source: str = "",
    ) -> None:
        """Add a log entry."""
        entry = LogEntry(
            timestamp=time.time(),
            level=level,
            message=message,
            extension=extension,
            source=source,
        )
        self._logs.append(entry)

        # Keep only last 10000 entries
        if len(self._logs) > 10000:
            self._logs = self._logs[-10000:]

    def get_logs(
        self,
        extension: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 100,
    ) -> List[LogEntry]:
        """Get log entries."""
        logs = self._logs

        if extension:
            logs = [l for l in logs if l.extension == extension]
        if level:
            logs = [l for l in logs if l.level == level]

        return logs[-limit:]

    def clear_logs(self, extension: Optional[str] = None) -> int:
        """Clear log entries."""
        if extension:
            before = len(self._logs)
            self._logs = [l for l in self._logs if l.extension != extension]
            return before - len(self._logs)
        else:
            count = len(self._logs)
            self._logs.clear()
            return count

    def record_metric(
        self,
        extension: str,
        call_time: float,
        error: bool = False,
    ) -> None:
        """Record a performance metric."""
        if extension not in self._metrics:
            self._metrics[extension] = PerformanceMetrics(extension=extension)

        metrics = self._metrics[extension]
        metrics.total_calls += 1
        metrics.total_time += call_time
        metrics.avg_time = metrics.total_time / metrics.total_calls
        metrics.max_time = max(metrics.max_time, call_time)
        metrics.min_time = min(metrics.min_time, call_time)

        if error:
            metrics.error_rate = (
                (metrics.error_rate * (metrics.total_calls - 1) + 1)
                / metrics.total_calls
            )

    def get_performance_metrics(
        self,
        extension: Optional[str] = None,
    ) -> List[PerformanceMetrics]:
        """Get performance metrics."""
        if extension:
            metrics = self._metrics.get(extension)
            return [metrics] if metrics else []
        return list(self._metrics.values())

    def clear_metrics(self, extension: Optional[str] = None) -> int:
        """Clear performance metrics."""
        if extension:
            if extension in self._metrics:
                del self._metrics[extension]
                return 1
            return 0
        else:
            count = len(self._metrics)
            self._metrics.clear()
            return count

    def set_inspector_data(
        self,
        extension: str,
        data: Dict[str, Any],
    ) -> None:
        """Set inspector data for an extension."""
        self._inspector_data[extension] = data

    def get_inspector_data(
        self,
        extension: str,
    ) -> Optional[Dict[str, Any]]:
        """Get inspector data for an extension."""
        return self._inspector_data.get(extension)

    def clear_inspector_data(self, extension: Optional[str] = None) -> int:
        """Clear inspector data."""
        if extension:
            if extension in self._inspector_data:
                del self._inspector_data[extension]
                return 1
            return 0
        else:
            count = len(self._inspector_data)
            self._inspector_data.clear()
            return count

    def get_memory_usage(self) -> Dict[str, int]:
        """Get memory usage for all extensions."""
        return {
            name: info.memory_usage
            for name, info in self._extensions.items()
        }

    def get_total_memory_usage(self) -> int:
        """Get total memory usage across all extensions."""
        return sum(info.memory_usage for info in self._extensions.values())

    def get_errors(
        self,
        extension: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get error logs."""
        errors = [
            {
                "timestamp": l.timestamp,
                "message": l.message,
                "extension": l.extension,
                "source": l.source,
            }
            for l in self._logs
            if l.level == "error"
        ]

        if extension:
            errors = [e for e in errors if e["extension"] == extension]

        return errors[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get developer tools statistics."""
        return {
            "extensions": len(self._extensions),
            "logs": len(self._logs),
            "metrics": len(self._metrics),
            "live_reload_watchers": len(self._live_reload_watchers),
            "inspector_data": len(self._inspector_data),
            "total_memory_usage": self.get_total_memory_usage(),
        }


# Global developer tools manager
_dev_tools: Optional[DevToolsManager] = None


def get_dev_tools() -> DevToolsManager:
    """Return the global DevToolsManager singleton."""
    global _dev_tools
    if _dev_tools is None:
        _dev_tools = DevToolsManager()
    return _dev_tools
