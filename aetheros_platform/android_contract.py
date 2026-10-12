"""Android contracts (Master 68).

Backend-side rules the Android client must obey, mirroring the iOS
contract discipline: App Links validation, FCM minimal-payload rules,
WorkManager policy (no daemon emulation), manifest audit model,
intent validation. All pure + tested here; device/Gradle proof BLOCKED.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------- App Links

APP_LINK_HOSTS = frozenset({"agent", "task", "approval", "research", "memory"})
_APP_ID_RE = re.compile(r"^[A-Za-z0-9\-_.]{1,128}$")

#: Hosts whose assetlinks.json binds them to this app. Anything else is
#: rejected even if the path shape matches (anti-spoofing).
APP_LINK_DOMAINS = frozenset({"aetheros.example"})


def parse_app_link(url: str) -> tuple[str, str] | None:
    """Validate https App Link or aetheros:// fallback. Never executes."""
    m = re.match(r"^https://([A-Za-z0-9.-]+)/aetheros/([^/?#]+)/([^/?#]+)",
                 url or "")
    if m:
        if m.group(1).lower() not in APP_LINK_DOMAINS:
            return None
        kind, raw = m.group(2).lower(), m.group(3)
    else:
        m2 = re.match(r"^aetheros://([^/?#]+)/([^?#]*)", url or "")
        if not m2:
            return None
        kind, raw = m2.group(1).lower(), m2.group(2)
    if kind not in APP_LINK_HOSTS or not _APP_ID_RE.match(raw.strip()):
        return None
    return kind, raw.strip()


# ---------------------------------------------------------------- FCM rules

FCM_FORBIDDEN_KEYS = frozenset({
    "access_token", "refresh_token", "api_key", "secret", "password",
    "private_key", "transcript", "credential", "fcm_token",
})


def validate_fcm_payload(payload: dict) -> tuple[bool, list[str]]:
    problems = [f"forbidden: {k}" for k in payload if k in FCM_FORBIDDEN_KEYS]
    if "task_id" not in payload and "notification_id" not in payload:
        problems.append("opaque reference required")
    return (not problems, problems)


# ---------------------------------------------------------------- WorkManager

class WorkKind(str, Enum):
    SYNC = "sync"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    CLEANUP = "cleanup"
    RECONCILE = "reconcile"


@dataclass(frozen=True)
class WorkRequest:
    kind: WorkKind
    expedited: bool
    constraints: tuple[str, ...] = ()
    justification: str = ""


def validate_work(req: WorkRequest) -> tuple[bool, str]:
    if req.expedited and not req.justification:
        return False, "expedited work requires justification (no daemon emulation)"
    allowed = {"network", "charging", "idle", "battery_ok"}
    bad = [c for c in req.constraints if c not in allowed]
    if bad:
        return False, f"unknown constraints: {bad}"
    return True, "policy permits"


# ---------------------------------------------------------------- intent validation

INTENT_ACTIONS = frozenset({
    "android.intent.action.SEND",
    "android.intent.action.VIEW",
    "android.intent.action.OPEN_DOCUMENT",
})


def validate_intent(action: str, uri: str, mime: str, size: int,
                    max_bytes: int = 100 * 1024 * 1024) -> tuple[bool, str]:
    if action not in INTENT_ACTIONS:
        return False, f"untrusted action: {action}"
    if size < 0 or size > max_bytes:
        return False, "size out of bounds"
    if not re.match(r"^[\w.+-]+/[\w.+-]+$", mime or ""):
        return False, f"bad mime: {mime}"
    if re.search(r"[;`$]", uri or ""):
        return False, "metacharacters in uri"
    return True, "intent accepted for import (never auto-executed)"


# ---------------------------------------------------------------- manifest audit

REQUIRED_ATTRS = {"package": "com.aetheros.android",
                  "minSdk": 26, "targetSdk": 36}

DANGEROUS_PERMS = frozenset({
    "android.permission.READ_SMS", "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.CAMERA", "android.permission.RECORD_AUDIO",
    "android.permission.READ_CONTACTS", "android.permission.BIND_ACCESSIBILITY_SERVICE",
})


def audit_manifest(manifest: dict) -> tuple[bool, list[str]]:
    """Audit a manifest MODEL (parsed XML as dict). Pure + tested."""
    problems = []
    for k, v in REQUIRED_ATTRS.items():
        if manifest.get(k) != v:
            problems.append(f"{k} must be {v!r}")
    for p in manifest.get("permissions", []):
        if p in DANGEROUS_PERMS and p not in manifest.get("justified", []):
            problems.append(f"unjustified dangerous permission: {p}")
    for c in manifest.get("components", []):
        if c.get("exported") and not c.get("permission"):
            problems.append(f"exported component without permission: {c.get('name')}")
    for s in manifest.get("services", []):
        if s.get("foreground") and not s.get("foregroundServiceType"):
            problems.append(f"foreground service without type: {s.get('name')}")
    if manifest.get("debuggable") or manifest.get("cleartext"):
        problems.append("debuggable/cleartext not allowed in release")
    return (not problems, problems)
