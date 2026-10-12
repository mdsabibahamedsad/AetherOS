"""Desktop bridge — JSON-RPC over stdio for Electron/Tauri integration."""

from __future__ import annotations

import json
import logging
import sys
import threading
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class DesktopBridge:
    def __init__(self):
        self._handlers: dict[str, Callable] = {}
        self._running = False
        self._lock = threading.Lock()

    def handle(self, method: str):
        def decorator(fn: Callable):
            self._handlers[method] = fn
            return fn
        return decorator

    def register_handler(self, method: str, handler: Callable):
        self._handlers[method] = handler

    def start(self, stdin=None, stdout=None):
        self._running = True
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        thread = threading.Thread(
            target=self._run, args=(stdin, stdout), daemon=True)
        thread.start()
        logger.info("Desktop bridge started")

    def _run(self, stdin, stdout):
        while self._running:
            try:
                line = stdin.readline()
                if not line:
                    break
                request = json.loads(line)
                method = request.get("method", "")
                params = request.get("params", {})
                request_id = request.get("id")
                handler = self._handlers.get(method)
                if handler:
                    try:
                        result = handler(**params)
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": result,
                        }
                    except Exception as e:
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {"code": -1, "message": str(e)},
                        }
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32601, "message": "Method not found"},
                    }
                stdout.write(json.dumps(response) + "\n")
                stdout.flush()
            except json.JSONDecodeError:
                continue
            except Exception as e:
                logger.error("Bridge error: %s", e)
                break

    def send_event(self, method: str, params: dict = None,
                    stdout=None):
        stdout = stdout or sys.stdout
        event = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        try:
            stdout.write(json.dumps(event) + "\n")
            stdout.flush()
        except Exception as e:
            logger.error("Bridge send error: %s", e)

    def stop(self):
        self._running = False

    def close(self):
        self.stop()
        self._handlers.clear()
