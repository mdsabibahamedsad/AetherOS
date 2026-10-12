"""Jarvis Mode — voice command registry.

Maps spoken phrases to runtime actions: open application, search files,
create note, run workflow, start browser task, send message, summarize
project, switch model, switch provider. Commands are registered with explicit
handlers and required permission levels; handlers run only when the
permission layer allows.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Command name -> (phrases, required permission, action type)
_COMMANDS: Dict[str, Dict[str, Any]] = {
    "open_app": {"phrases": ["open application", "open app", "launch"], "permission": "system:change", "action": "open_app"},
    "search_files": {"phrases": ["search files", "find file", "find files"], "permission": "filesystem:read", "action": "search_files"},
    "create_note": {"phrases": ["create note", "make a note", "new note"], "permission": "filesystem:write", "action": "create_note"},
    "run_workflow": {"phrases": ["run workflow", "start workflow", "execute workflow"], "permission": "mission:execute", "action": "run_workflow"},
    "browser_task": {"phrases": ["browser task", "start browser", "browse"], "permission": "browser:automate", "action": "browser_task"},
    "send_message": {"phrases": ["send message", "message"], "permission": "message:send", "action": "send_message"},
    "summarize_project": {"phrases": ["summarize project", "project summary"], "permission": "filesystem:read", "action": "summarize_project"},
    "switch_model": {"phrases": ["switch model", "change model", "use model"], "permission": "system:change", "action": "switch_model"},
    "switch_provider": {"phrases": ["switch provider", "change provider", "use provider"], "permission": "system:change", "action": "switch_provider"},
    "help": {"phrases": ["help", "what can you do", "commands"], "permission": "", "action": "help"},
}


class VoiceCommandRegistry:
    """Resolves spoken text to a registered command and executes it."""

    def __init__(self, permission_layer: Any = None) -> None:
        self._permissions = permission_layer
        self._handlers: Dict[str, Callable[..., Any]] = {}
        self._lock = threading.RLock()
        self._execution_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, name: str, handler: Callable[..., Any], *, phrases: Optional[List[str]] = None, permission: str = "") -> None:
        with self._lock:
            self._handlers[name] = handler
            if name not in _COMMANDS:
                _COMMANDS[name] = {
                    "phrases": phrases or [name.replace("_", " ")],
                    "permission": permission,
                    "action": name,
                }
            elif phrases:
                _COMMANDS[name]["phrases"] = phrases
            if permission:
                _COMMANDS[name]["permission"] = permission

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def match(self, text: str) -> Optional[Dict[str, Any]]:
        lower = (text or "").lower().strip()
        if not lower:
            return None
        best: Optional[Dict[str, Any]] = None
        best_score = 0
        for name, cmd in _COMMANDS.items():
            for phrase in cmd["phrases"]:
                if phrase in lower:
                    score = len(phrase)
                    if score > best_score:
                        best_score = score
                        best = {"name": name, "action": cmd["action"], "permission": cmd.get("permission", "")}
        return best

    def command_names(self) -> List[str]:
        return list(_COMMANDS.keys())

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, text: str, *, requester: str = "jarvis") -> Dict[str, Any]:
        match = self.match(text)
        if match is None:
            return {"ok": False, "command": None, "error": "No matching command"}
        name = match["name"]

        permission = match.get("permission", "")
        if permission and self._permissions is not None:
            allowed = self._permissions.require(permission, requester=requester, reason=f"voice command: {name}", action=name, target=text)
            if not allowed:
                self._log(name, False, "permission denied")
                return {"ok": False, "command": name, "error": "Permission denied"}

        handler = self._handlers.get(name)
        if handler is None:
            self._log(name, False, "no handler")
            return {"ok": False, "command": name, "error": "No handler registered"}

        try:
            result = handler(text=text, command=name)
            self._log(name, True, "")
            return {"ok": True, "command": name, "result": result}
        except Exception as exc:
            logger.warning("Voice command %s failed: %s", name, exc)
            self._log(name, False, str(exc))
            return {"ok": False, "command": name, "error": str(exc)}

    def _log(self, command: str, ok: bool, detail: str) -> None:
        with self._lock:
            self._execution_log.append({"command": command, "ok": ok, "detail": detail})
            self._execution_log = self._execution_log[-100:]

    def execution_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._execution_log[-limit:])
