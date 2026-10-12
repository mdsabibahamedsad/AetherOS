from __future__ import annotations

import logging
import sys
from typing import Any

_LOGGERS: dict[str, logging.Logger] = {}
_CONSOLE_HANDLER: logging.Handler | None = None


def setup_logging(config: dict | None = None) -> logging.Logger:
    global _CONSOLE_HANDLER
    cfg = config or {}
    level = getattr(logging, (cfg.get("log_level") or "INFO").upper(), logging.INFO)
    root = logging.getLogger("aetheros")
    root.setLevel(level)

    if _CONSOLE_HANDLER is None:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        fmt = cfg.get("format", "json")
        if fmt == "json":
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
        handler.setFormatter(formatter)
        root.handlers.clear()
        root.addHandler(handler)
        _CONSOLE_HANDLER = handler

    return root


def get_logger(name: str) -> logging.Logger:
    if name not in _LOGGERS:
        logger = logging.getLogger(f"aetheros.{name}")
        _LOGGERS[name] = logger
    return _LOGGERS[name]


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        import json, time
        entry: dict[str, Any] = {
            "ts": time.time(),
            "level": record.levelname,
            "name": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)
