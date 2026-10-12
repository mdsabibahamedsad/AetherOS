"""Agent permission system — granular tool-level access control."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class Action(Enum):
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    EXECUTE_TERMINAL = "execute_terminal"
    INTERNET_ACCESS = "internet_access"
    INSTALL_PACKAGES = "install_packages"
    GIT_PUSH = "git_push"
    DOCKER = "docker"
    SYSTEM_COMMANDS = "system_commands"
    ASK_BEFORE_DANGEROUS = "ask_before_dangerous"


DANGEROUS_ACTIONS = {
    Action.WRITE_FILES,
    Action.EXECUTE_TERMINAL,
    Action.INSTALL_PACKAGES,
    Action.GIT_PUSH,
    Action.DOCKER,
    Action.SYSTEM_COMMANDS,
}


ACTION_TO_TOOLS = {
    Action.READ_FILES: ["read_file", "search_files"],
    Action.WRITE_FILES: ["write_file", "patch"],
    Action.EXECUTE_TERMINAL: ["terminal", "process"],
    Action.INTERNET_ACCESS: ["web_search", "web_extract", "browser_navigate",
                             "browser_snapshot", "browser_click", "browser_type"],
    Action.INSTALL_PACKAGES: ["terminal"],  # gated at call time
    Action.GIT_PUSH: ["terminal"],  # gated at call time
    Action.DOCKER: ["terminal"],  # gated at call time
    Action.SYSTEM_COMMANDS: ["terminal"],  # gated at call time
}


@dataclass
class PermissionCheck:
    action: Action
    tool_name: str
    allowed: bool
    reason: str = ""

    def to_dict(self) -> dict:
        return {"action": self.action.value, "tool_name": self.tool_name,
                "allowed": self.allowed, "reason": self.reason}


class PermissionDenied(Exception):
    def __init__(self, action: Action, tool: str, reason: str = ""):
        self.action = action
        self.tool = tool
        self.reason = reason
        super().__init__(f"Permission denied: {action.value} ({tool}) — {reason}" if reason
                         else f"Permission denied: {action.value} ({tool})")


class PermissionRegistry:
    """Central permission registry. Agents register their allowed actions here."""

    def __init__(self):
        self._agent_permissions: dict[str, set[str]] = {}
        self._hooks: list[Callable] = []
        self._danger_confirm_cache: dict[str, bool] = {}

    def register_agent(self, agent_id: str, permissions: list[str]) -> None:
        self._agent_permissions[agent_id] = set(permissions)
        logger.debug("Registered permissions for agent %s: %s", agent_id, permissions)

    def unregister_agent(self, agent_id: str) -> None:
        self._agent_permissions.pop(agent_id, None)
        self._danger_confirm_cache.pop(agent_id, None)

    def add_hook(self, hook: Callable) -> None:
        self._hooks.append(hook)

    def check(self, agent_id: str, tool_name: str, action: Action | None = None) -> PermissionCheck:
        if action is None:
            action = self._infer_action(tool_name)
        if action is None:
            return PermissionCheck(action=Action.READ_FILES, tool_name=tool_name, allowed=True)

        perms = self._agent_permissions.get(agent_id, set())

        if action.value in perms:
            return PermissionCheck(action=action, tool_name=tool_name, allowed=True)

        if action in DANGEROUS_ACTIONS and Action.ASK_BEFORE_DANGEROUS.value in perms:
            return PermissionCheck(
                action=action, tool_name=tool_name, allowed=False,
                reason=f"Dangerous action '{action.value}' requires confirmation",
            )

        for hook in self._hooks:
            result = hook(agent_id, tool_name, action)
            if result is not None:
                return result

        return PermissionCheck(action=action, tool_name=tool_name, allowed=False,
                               reason=f"Agent lacks '{action.value}' permission")

    def confirm_dangerous(self, agent_id: str, action: Action) -> bool:
        if agent_id in self._danger_confirm_cache:
            return self._danger_confirm_cache[agent_id]
        return False

    def cache_dangerous_confirmation(self, agent_id: str, action: Action, confirmed: bool) -> None:
        self._danger_confirm_cache[agent_id] = confirmed

    def _infer_action(self, tool_name: str) -> Action | None:
        for action, tools in ACTION_TO_TOOLS.items():
            if tool_name in tools:
                return action
        return None


_PERMISSION_REGISTRY: PermissionRegistry | None = None


def get_permission_registry() -> PermissionRegistry:
    global _PERMISSION_REGISTRY
    if _PERMISSION_REGISTRY is None:
        _PERMISSION_REGISTRY = PermissionRegistry()
    return _PERMISSION_REGISTRY


def reset_permission_registry() -> None:
    global _PERMISSION_REGISTRY
    _PERMISSION_REGISTRY = None
