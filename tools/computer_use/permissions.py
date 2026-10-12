"""Permission system for computer use.

Every computer-use action is validated against a named permission before it
is dispatched. Permissions are:

  * **Named** — a small closed vocabulary (see ``Permission``).
  * **Visible** — ``granted()`` returns the current grant set.
  * **Revocable** — ``grant()`` / ``revoke()`` at runtime or via env.
  * **Logged** — the audit layer records every check + outcome (see audit.py).
  * **Validated** — the tool dispatch refuses denied actions with a clear error.

Default policy is **allow-all** so existing behaviour is preserved: an action
is allowed unless its permission has been explicitly revoked (or strict mode
is enabled). ``AETHEROS_COMPUTER_USE_STRICT=1`` flips to allow-by-default-off,
where only explicitly granted permissions are permitted — useful for
lock-down deployments.

The mapping ``ACTION_PERMISSIONS`` binds each tool action to the permission
that governs it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class Permission(str, Enum):
    """The closed set of computer-use permissions."""

    SCREEN_READ = "screen_read"              # capture / screenshot / find_text
    SYSTEM_INFO = "system_info"              # get_capabilities / system_info (read-only)
    MOUSE_CONTROL = "mouse_control"          # click / drag / scroll / move_mouse
    KEYBOARD_CONTROL = "keyboard_control"    # type / key
    WINDOW_CONTROL = "window_control"        # focus/minimize/maximize/close window
    CLIPBOARD_READ = "clipboard_read"        # read_clipboard
    CLIPBOARD_WRITE = "clipboard_write"      # copy_clipboard / clear_clipboard
    APPLICATION_CONTROL = "application_control"  # focus_app / list_apps / launch / close
    ACCESSIBILITY_CONTROL = "accessibility_control"  # AX/SOM element access


# ── Action → permission binding ─────────────────────────────────────────

ACTION_PERMISSIONS: Dict[str, Permission] = {
    "capture": Permission.SCREEN_READ,
    "capture_region": Permission.SCREEN_READ,
    "get_screen_size": Permission.SCREEN_READ,
    "find_text": Permission.SCREEN_READ,
    "click": Permission.MOUSE_CONTROL,
    "double_click": Permission.MOUSE_CONTROL,
    "right_click": Permission.MOUSE_CONTROL,
    "middle_click": Permission.MOUSE_CONTROL,
    "drag": Permission.MOUSE_CONTROL,
    "scroll": Permission.MOUSE_CONTROL,
    "move_mouse": Permission.MOUSE_CONTROL,
    "type": Permission.KEYBOARD_CONTROL,
    "key": Permission.KEYBOARD_CONTROL,
    "set_value": Permission.KEYBOARD_CONTROL,
    "read_clipboard": Permission.CLIPBOARD_READ,
    "copy_clipboard": Permission.CLIPBOARD_WRITE,
    "clear_clipboard": Permission.CLIPBOARD_WRITE,
    "list_windows": Permission.WINDOW_CONTROL,
    "get_active_window": Permission.WINDOW_CONTROL,
    "focus_window": Permission.WINDOW_CONTROL,
    "minimize_window": Permission.WINDOW_CONTROL,
    "maximize_window": Permission.WINDOW_CONTROL,
    "close_window": Permission.WINDOW_CONTROL,
    "focus_app": Permission.APPLICATION_CONTROL,
    "list_apps": Permission.APPLICATION_CONTROL,
    "launch_app": Permission.APPLICATION_CONTROL,
    "close_app": Permission.APPLICATION_CONTROL,
    "get_capabilities": Permission.SYSTEM_INFO,
    "system_info": Permission.SYSTEM_INFO,
    "wait": Permission.SCREEN_READ,
}

# Permission → short human description (used in denial messages).
PERMISSION_DESCRIPTIONS: Dict[Permission, str] = {
    Permission.SCREEN_READ: "reading the screen (screenshots / element search)",
    Permission.SYSTEM_INFO: "reading system information (OS / CPU / RAM / disk)",
    Permission.MOUSE_CONTROL: "controlling the mouse (click / drag / scroll / move)",
    Permission.KEYBOARD_CONTROL: "controlling the keyboard (type / keys / values)",
    Permission.WINDOW_CONTROL: "managing windows (focus / minimize / maximize / close)",
    Permission.CLIPBOARD_READ: "reading the clipboard",
    Permission.CLIPBOARD_WRITE: "writing to the clipboard",
    Permission.APPLICATION_CONTROL: "controlling applications (focus / launch / close)",
    Permission.ACCESSIBILITY_CONTROL: "reading the accessibility (AX/SOM) tree",
}


def permission_for_action(action: str) -> Optional[Permission]:
    """Return the permission that governs ``action``, or None if unbound."""
    return ACTION_PERMISSIONS.get(action)


@dataclass
class PermissionResult:
    """Outcome of a permission check for an action."""

    allowed: bool
    action: str
    permission: Optional[Permission] = None
    reason: str = ""


class PermissionDeniedError(Exception):
    """Raised in strict-mode programmatic flows when a permission is not granted."""

    def __init__(self, permission: Permission, action: str = ""):
        self.permission = permission
        self.action = action
        desc = PERMISSION_DESCRIPTIONS.get(permission, permission.value)
        msg = f"permission denied: {permission.value} ({desc})"
        if action:
            msg += f" for action {action!r}"
        super().__init__(msg)


class ComputerUsePermissions:
    """Visible, revocable permission store for computer-use actions.

    ``strict=False`` (default): allow everything unless explicitly revoked.
    ``strict=True``: allow only explicitly granted permissions.
    """

    def __init__(self, strict: bool = False) -> None:
        self.strict = bool(strict)
        # Explicitly granted / revoked permissions. In default mode revokes
        # win; in strict mode grants win. Empty set in default mode means
        # "everything allowed".
        self._grants: set[Permission] = set()
        self._revokes: set[Permission] = set()

    @property
    def strict_mode(self) -> bool:
        return self.strict

    def set_strict(self, strict: bool) -> None:
        self.strict = bool(strict)

    def grant(self, permission: Permission) -> None:
        """Explicitly allow ``permission`` (idempotent)."""
        p = Permission(permission)
        self._grants.add(p)
        self._revokes.discard(p)

    def revoke(self, permission: Permission) -> None:
        """Explicitly deny ``permission`` (idempotent)."""
        p = Permission(permission)
        self._revokes.add(p)
        self._grants.discard(p)

    def is_granted(self, permission: Permission) -> bool:
        """Return True if ``permission`` is currently allowed."""
        p = Permission(permission)
        if self.strict:
            return p in self._grants
        return p not in self._revokes

    def granted(self) -> set[Permission]:
        """Return the effective set of allowed permissions."""
        if self.strict:
            return set(self._grants)
        return {p for p in Permission if p not in self._revokes}

    def reset(self) -> None:
        """Clear all explicit grants/revokes (back to the default policy)."""
        self._grants.clear()
        self._revokes.clear()

    def check(self, action: str) -> PermissionResult:
        """Validate ``action`` against its bound permission.

        Returns a PermissionResult — never raises. Unbound actions are
        treated as allowed (they carry no governed surface).
        """
        perm = permission_for_action(action)
        if perm is None:
            return PermissionResult(allowed=True, action=action, permission=None,
                                    reason="no permission bound to this action")
        allowed = self.is_granted(perm)
        reason = ""
        if not allowed:
            desc = PERMISSION_DESCRIPTIONS.get(perm, perm.value)
            reason = f"action {action!r} requires {perm.value} ({desc})"
        return PermissionResult(allowed=allowed, action=action,
                                permission=perm, reason=reason)

    def require(self, action: str) -> None:
        """Raise PermissionDeniedError when ``action`` is not allowed."""
        result = self.check(action)
        if not result.allowed and result.permission is not None:
            raise PermissionDeniedError(result.permission, action=action)


def _strict_from_env() -> bool:
    val = os.environ.get("AETHEROS_COMPUTER_USE_STRICT", "").strip().lower()
    return val in {"1", "true", "yes", "on"}


# ── Process-wide singleton ───────────────────────────────────────────────

_permissions: Optional[ComputerUsePermissions] = None


def get_permissions() -> ComputerUsePermissions:
    """Return the process-wide ComputerUsePermissions store (lazy singleton)."""
    global _permissions
    if _permissions is None:
        _permissions = ComputerUsePermissions(strict=_strict_from_env())
    return _permissions


def reset_permissions_for_tests() -> None:
    """Test helper — drop the singleton and rebuild from env."""
    global _permissions
    _permissions = None
