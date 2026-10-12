"""Structured logging — JSON-formatted log entries with levels and metadata."""

from __future__ import annotations

import json
import logging
import sys
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional


@dataclass
class LogEntry:
    message: str
    level: str = "INFO"
    logger: str = ""
    timestamp: str = ""
    module: str = ""
    function: str = ""
    line: int = 0
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        if not d["timestamp"]:
            d["timestamp"] = datetime.utcnow().isoformat() + "Z"
        return {k: v for k, v in d.items() if v}


class StructuredLogger:
    def __init__(self, name: str = "aetheros"):
        self.name = name
        self._handlers: list[callable] = []
        self._min_level = logging.DEBUG
        self._lock = threading.Lock()

    def add_handler(self, handler: callable):
        self._handlers.append(handler)

    def set_level(self, level: int):
        self._min_level = level

    def _log(self, level: int, message: str, **kwargs):
        if level < self._min_level:
            return
        import traceback
        frame = sys._getframe(2) if sys._getframe(1) else None
        entry = LogEntry(
            message=message,
            level=logging.getLevelName(level),
            logger=self.name,
            timestamp=datetime.utcnow().isoformat() + "Z",
            module=frame.f_globals.get("__name__", "") if frame else "",
            function=frame.f_code.co_name if frame else "",
            line=frame.f_lineno if frame else 0,
            extra=kwargs,
        )
        self._emit(entry)

    def _emit(self, entry: LogEntry):
        with self._lock:
            for handler in self._handlers:
                try:
                    handler(entry)
                except Exception:
                    pass

    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)

    def json_handler(self, entry: LogEntry):
        print(json.dumps(entry.to_dict(), default=str), file=sys.stderr)

    def file_handler(self, filepath: str):
        def handler(entry: LogEntry):
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), default=str) + "\n")
        self.add_handler(handler)

    def console_handler(self, entry: LogEntry):
        level_colors = {
            "DEBUG": "\033[36m", "INFO": "\033[32m",
            "WARNING": "\033[33m", "ERROR": "\033[31m",
            "CRITICAL": "\033[35m",
        }
        color = level_colors.get(entry.level, "")
        reset = "\033[0m" if color else ""
        print(f"{color}[{entry.level}]{reset} {entry.message}",
              file=sys.stderr)
