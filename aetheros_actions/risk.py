"""Risk classification for computer-use actions (Step 13).

Every action is assigned a :class:`~aetheros_actions.model.RiskLevel` before
it enters the permission pipeline. The classifier is target-aware: the same
``ActionType.CLICK`` is LOW on a public page but HIGH when it targets a
payment/send/delete control, and CRITICAL when it targets account security
settings.

The classifier is deterministic and testable; it never performs I/O.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from aetheros_actions.model import Action, ActionType, RiskLevel


# ── Target keyword classifiers ──────────────────────────────────────────

_PAYMENT_TERMS = re.compile(
    r"\b(pay|paypal|checkout|billing|payment|price cart|cart|checkout|stripe|wallet|"
    r"purchase|charge|invoice|confirm purchase|submit payment|buy now)\b",
    re.IGNORECASE,
)
_TRANSFER_TERMS = re.compile(
    r"\b(transfer|send money|wire|zelle|venmo|bank|withdraw|deposit|"
    r"send funds|atm)\b",
    re.IGNORECASE,
)
_SECURITY_TERMS = re.compile(
    r"\b(password|security|2fa|two[- ]factor|mfa|otp|pin code|"
    r"recovery code|trusted device|app password|security settings|"
    r"passkey|authorized user)\b",
    re.IGNORECASE,
)
_DELETE_TERMS = re.compile(
    r"\b(delete|remove|purge|wipe|clear all|discard|trash|deactivate account|"
    r"close account|revoke|uninstall)\b",
    re.IGNORECASE,
)
_SEND_TERMS = re.compile(
    r"\b(send|publish|post|submit|reply|forward|tweet|share|message|"
    r"comment|email|mail to)\b",
    re.IGNORECASE,
)
_SETTINGS_TERMS = re.compile(
    r"\b(setting|billing info|account settings|profile settings|"
    r"contact info|shipping|address book)\b",
    re.IGNORECASE,
)
_CREDENTIAL_INPUT_TERMS = re.compile(
    r"\b(password|passphrase|api[- ]key|secret|token|credential|"
    r"private key|sshkey)\b",
    re.IGNORECASE,
)
_DOWNLOAD_TERMS = re.compile(r"\b(download|save as)\b", re.IGNORECASE)
_UPLOAD_TERMS = re.compile(r"\b(upload|attach|send file)\b", re.IGNORECASE)

# Executable/payload extensions that make a DOWNLOAD high-risk.
_EXECUTABLE_EXTENSIONS = {
    ".exe", ".msi", ".bat", ".cmd", ".ps1", ".sh", ".js", ".vbs", ".dmg",
    ".pkg", ".app", ".jar", ".deb", ".rpm", ".apk", ".scr", ".com",
}

# Actions that are inherently state-changing regardless of target.
_MUTATING_TYPES = {
    ActionType.TYPE,
    ActionType.KEY_PRESS,
    ActionType.CLICK,
    ActionType.DOUBLE_CLICK,
    ActionType.DRAG,
    ActionType.MOVE,
    ActionType.CLOSE,
    ActionType.WINDOW_FOCUS,
    ActionType.COPY,
    ActionType.PASTE,
    ActionType.UPLOAD,
    ActionType.DOWNLOAD,
    ActionType.APP_LAUNCH,
    ActionType.APP_CLOSE,
    ActionType.FILE_OPEN,
    ActionType.FILE_SAVE,
    ActionType.TAB_SWITCH,
}

# Actions that never mutate state by themselves.
_READ_TYPES = {ActionType.SCREENSHOT, ActionType.WAIT, ActionType.OPEN, ActionType.SCROLL}


def _target_lower(target: str) -> str:
    return (target or "").lower()


def classify_action(action: Action) -> RiskLevel:
    """Return the risk level for ``action`` based on type + target + params.

    RULE ORDER (highest wins):
      1. CRITICAL — transfer / security settings / credential input.
      2. HIGH — send/publish/delete/purchase, download of executable content,
         system-level config writes.
      3. MEDIUM — typing non-sensitive text, ordinary downloads, uploads,
         app/file mutations, navigation to unknown hosts.
      4. LOW — read-only observation, scrolling, waiting, open public page.
    """
    atype = action.action_type
    text = " ".join(
        [action.target,
         str(action.parameters.get("text", "")),
         str(action.parameters.get("url", "")),
         str(action.parameters.get("key", "")),
         str(action.parameters.get("value", "")),
         str(action.parameters.get("app", "")),
         str(action.parameters.get("filename", "")),
         str(action.parameters.get("path", ""))]
    )
    tl = text.lower()

    # 1. Critical tier.
    if atype in _MUTATING_TYPES:
        if _SECURITY_TERMS.search(tl) and (
            _SETTINGS_TERMS.search(tl) or "settings" in tl
        ):
            return RiskLevel.CRITICAL
        if _TRANSFER_TERMS.search(tl):
            return RiskLevel.CRITICAL
        if _CREDENTIAL_INPUT_TERMS.search(tl) and atype in (
            ActionType.TYPE, ActionType.PASTE, ActionType.KEY_PRESS
        ):
            return RiskLevel.CRITICAL

    # 1b. System-level config writes.
    if atype in (ActionType.FILE_SAVE, ActionType.FILE_OPEN):
        from aetheros_actions.safety import SafetyPolicy
        policy = SafetyPolicy()
        if not policy.is_safe_path(tl):
            return RiskLevel.CRITICAL

    # 2. High tier.
    if atype in _MUTATING_TYPES:
        if _PAYMENT_TERMS.search(tl):
            return RiskLevel.HIGH
        if _SEND_TERMS.search(tl):
            return RiskLevel.HIGH
        if _DELETE_TERMS.search(tl):
            return RiskLevel.HIGH if atype != ActionType.APP_CLOSE else RiskLevel.HIGH
        if _SECURITY_TERMS.search(tl):
            return RiskLevel.HIGH
    if atype == ActionType.DOWNLOAD:
        fname = str(action.parameters.get("filename", "")).lower()
        if any(fname.endswith(ext) for ext in _EXECUTABLE_EXTENSIONS):
            return RiskLevel.HIGH
        return RiskLevel.MEDIUM
    if atype == ActionType.UPLOAD:
        return RiskLevel.HIGH
    if atype in (ActionType.APP_CLOSE, ActionType.CLOSE):
        return RiskLevel.HIGH
    if atype == ActionType.NAVIGATE:
        return RiskLevel.MEDIUM
    if atype == ActionType.APP_LAUNCH:
        return RiskLevel.MEDIUM

    # 3. Medium tier.
    if atype in (ActionType.TYPE, ActionType.PASTE) and action.target.strip():
        return RiskLevel.MEDIUM
    if atype in _MUTATING_TYPES and action.target.strip():
        return RiskLevel.MEDIUM
    if atype == ActionType.FILE_OPEN and action.target.strip():
        return RiskLevel.MEDIUM
    if atype in (ActionType.COPY, ActionType.PASTE) and action.target.strip():
        return RiskLevel.MEDIUM
    if atype == ActionType.TAB_SWITCH:
        return RiskLevel.MEDIUM

    # 4. Low tier.
    return RiskLevel.LOW


def risk_for_inputs(
    action_type: ActionType,
    target: str = "",
    parameters: Optional[Dict[str, Any]] = None,
) -> RiskLevel:
    """Convenience: classify without building a full Action."""
    act = Action(action_type=action_type, target=target, parameters=parameters or {})
    return classify_action(act)


def allowed_max_risk(autonomy_level: int) -> RiskLevel:
    """Map an autonomy level to the max risk it may proceed on (Step 44).

    Level 0 observe-only → LOW (reads only).
    Level 1..2 → MEDIUM.
    Level 3..5 → HIGH; CRITICAL always requires confirmation regardless.
    """
    if autonomy_level <= 0:
        return RiskLevel.LOW
    if autonomy_level <= 2:
        return RiskLevel.MEDIUM
    return RiskLevel.HIGH