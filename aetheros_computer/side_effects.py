"""
Side-effect classification and routing (Master 15 Phases 19, 53, 68).

Maps every registered action to an effect class:

    READ, WRITE, SEND, PUBLISH, DELETE, PURCHASE, DEPLOY,
    PERMISSION_CHANGE, ACCOUNT_CHANGE, NONE

Routing rules (enforced via :func:`requires_confirmation`):
- SEND / PUBLISH / PURCHASE / DEPLOY / PERMISSION_CHANGE / ACCOUNT_CHANGE
  always require explicit confirmation regardless of numeric risk tier.
- DELETE requires confirmation unless idempotency-keyed AND verified.
- Automatic retry (Phase 68) is forbidden for the same set plus DELETE.

This is policy DATA + pure functions; enforcement lives in
``approval.UnifiedApprovalEngine`` and ``dispatcher.RecoveryEngine`` which
consult it.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional


class SideEffect(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    SEND = "SEND"
    PUBLISH = "PUBLISH"
    DELETE = "DELETE"
    PURCHASE = "PURCHASE"
    DEPLOY = "DEPLOY"
    PERMISSION_CHANGE = "PERMISSION_CHANGE"
    ACCOUNT_CHANGE = "ACCOUNT_CHANGE"
    NONE = "NONE"


# Actions that always need confirmation before first execution.
_CONFIRM_ALWAYS = frozenset({
    SideEffect.SEND, SideEffect.PUBLISH, SideEffect.PURCHASE,
    SideEffect.DEPLOY, SideEffect.PERMISSION_CHANGE, SideEffect.ACCOUNT_CHANGE,
})

# Actions that must NEVER be auto-retried after failure.
_NO_AUTO_RETRY = frozenset({
    SideEffect.SEND, SideEffect.PUBLISH, SideEffect.PURCHASE,
    SideEffect.DELETE, SideEffect.DEPLOY,
    SideEffect.PERMISSION_CHANGE, SideEffect.ACCOUNT_CHANGE,
})

_ACTION_EFFECT: Dict[str, SideEffect] = {
    # browser
    "browser.navigate": SideEffect.READ,
    "browser.snapshot": SideEffect.READ,
    "browser.scroll": SideEffect.READ,
    "browser.back": SideEffect.READ,
    "browser.forward": SideEffect.READ,
    "browser.switch_tab": SideEffect.READ,
    "browser.wait": SideEffect.READ,
    "browser.click": SideEffect.WRITE,
    "browser.type": SideEffect.WRITE,
    "browser.form_fill": SideEffect.WRITE,
    "browser.submit": SideEffect.SEND,
    "browser.download": SideEffect.WRITE,
    "browser.upload": SideEffect.SEND,
    "browser.execute_js": SideEffect.WRITE,
    "browser.close_tab": SideEffect.WRITE,
    "browser.new_tab": SideEffect.READ,
    "browser.dialog": SideEffect.WRITE,
    # desktop
    "desktop.capture": SideEffect.READ,
    "desktop.ocr": SideEffect.READ,
    "desktop.find_text": SideEffect.READ,
    "desktop.list_windows": SideEffect.READ,
    "desktop.get_active_window": SideEffect.READ,
    "desktop.list_apps": SideEffect.READ,
    "desktop.read_clipboard": SideEffect.READ,
    "desktop.move_mouse": SideEffect.READ,
    "desktop.wait": SideEffect.READ,
    "desktop.click": SideEffect.WRITE,
    "desktop.double_click": SideEffect.WRITE,
    "desktop.right_click": SideEffect.WRITE,
    "desktop.drag": SideEffect.WRITE,
    "desktop.scroll": SideEffect.WRITE,
    "desktop.type": SideEffect.WRITE,
    "desktop.key": SideEffect.WRITE,
    "desktop.set_value": SideEffect.WRITE,
    "desktop.copy_clipboard": SideEffect.WRITE,
    "desktop.clear_clipboard": SideEffect.WRITE,
    "desktop.focus_window": SideEffect.WRITE,
    "desktop.minimize_window": SideEffect.WRITE,
    "desktop.maximize_window": SideEffect.WRITE,
    "desktop.focus_app": SideEffect.WRITE,
    "desktop.launch_app": SideEffect.WRITE,
    "desktop.close_window": SideEffect.DELETE,
    "desktop.close_app": SideEffect.DELETE,
    # terminal
    "terminal.execute": SideEffect.WRITE,
    "terminal.background": SideEffect.WRITE,
    "terminal.poll": SideEffect.READ,
    "terminal.wait": SideEffect.READ,
    "terminal.sudo": SideEffect.PERMISSION_CHANGE,
    "terminal.kill": SideEffect.DELETE,
    # vision
    "vision.analyze": SideEffect.READ,
    "vision.ocr": SideEffect.READ,
    "vision.capture": SideEffect.READ,
    "vision.document_extract": SideEffect.READ,
    "vision.understand": SideEffect.READ,
    "video.analyze": SideEffect.READ,
    # filesystem
    "filesystem.read": SideEffect.READ,
    "filesystem.search": SideEffect.READ,
    "filesystem.write": SideEffect.WRITE,
    "filesystem.patch": SideEffect.WRITE,
    "filesystem.move": SideEffect.WRITE,
    "filesystem.delete": SideEffect.DELETE,
}


def classify_effect(action: str) -> SideEffect:
    return _ACTION_EFFECT.get((action or "").lower(), SideEffect.NONE)


def requires_confirmation(action: str) -> bool:
    """True when policy demands explicit confirmation regardless of tier."""
    return classify_effect(action) in _CONFIRM_ALWAYS


def auto_retry_forbidden(action: str) -> bool:
    return classify_effect(action) in _NO_AUTO_RETRY


def effect_of_registered_action(name: str) -> Optional[SideEffect]:
    from aetheros_computer.action import get_action_definition

    if get_action_definition(name) is None:
        return None
    return classify_effect(name)


__all__ = [
    "SideEffect",
    "classify_effect",
    "requires_confirmation",
    "auto_retry_forbidden",
    "effect_of_registered_action",
]
