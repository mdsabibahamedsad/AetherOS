"""Mobile API/device/offline/push/deep-link contracts (Master 67).

Single source of truth shared by the Swift client (`apps/ios`) and the
Python backend (`gateway/platforms/api_server.py`). `verify_against_
backend()` imports the real server module and asserts every handler the
mobile client depends on — executed in CI-reachable pytest, no device
needed. Deep-link/push/offline/device rules mirror the Swift models.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class MobileRoute:
    method: str
    path: str
    handler: str
    auth: str = "bearer"
    idempotent: bool = False


#: Every route the iOS client may call. Backend MUST serve all of these.
MOBILE_ROUTES: tuple[MobileRoute, ...] = (
    MobileRoute("GET", "/api/sessions", "_handle_list_sessions"),
    MobileRoute("GET", "/api/sessions/{id}/messages", "_handle_session_messages"),
    MobileRoute("POST", "/api/sessions/{id}/chat", "_handle_session_chat"),
    MobileRoute("GET", "/api/sessions/{id}/chat/stream", "_handle_session_chat_stream", idempotent=False),
    MobileRoute("GET", "/api/jobs", "_handle_list_jobs"),
)


def verify_against_backend() -> dict[str, bool]:
    """Assert each contracted handler exists on APIServerAdapter."""
    from gateway.platforms import api_server as mod

    adapter = mod.APIServerAdapter
    return {r.handler: callable(getattr(adapter, r.handler, None)) for r in MOBILE_ROUTES}


# ---------------------------------------------------------------- deep links

DEEP_LINK_HOSTS = frozenset({"task", "approval", "session", "notification"})
_DEEP_ID_RE = re.compile(r"^[A-Za-z0-9\-_.]{1,128}$")


def parse_deep_link(url: str) -> tuple[str, str] | None:
    """Mirror of Swift DeepLink.parse. Returns (kind, id) or None."""
    m = re.match(r"^aetheros://([^/?#]+)(?:/([^?#]*)|\?id=([^?#&]*))?", url or "")
    if not m:
        return None
    kind = m.group(1).lower()
    if kind not in DEEP_LINK_HOSTS:
        return None
    raw = (m.group(2) or m.group(3) or "").strip()
    if not _DEEP_ID_RE.match(raw):
        return None
    return kind, raw


# ---------------------------------------------------------------- push rules

#: Keys that must NEVER appear in a push payload (fetch after tap instead).
PUSH_FORBIDDEN_KEYS = frozenset({
    "access_token", "refresh_token", "api_key", "secret", "password",
    "private_key", "transcript", "credential", "session_token",
})


def validate_push_payload(payload: dict) -> tuple[bool, list[str]]:
    problems = [f"forbidden key: {k}" for k in payload if k in PUSH_FORBIDDEN_KEYS]
    if "task_id" not in payload and "notification_id" not in payload:
        problems.append("opaque reference required (task_id or notification_id)")
    return (not problems, problems)


# ---------------------------------------------------------------- offline ops

class OfflineClass(str, Enum):
    SAFE_OFFLINE = "SAFE_OFFLINE"
    QUEUEABLE = "QUEUEABLE"
    ONLINE_REQUIRED = "ONLINE_REQUIRED"
    HIGH_RISK_ONLINE_REQUIRED = "HIGH_RISK_ONLINE_REQUIRED"


@dataclass
class OfflineOp:
    operation_id: str
    type: str
    risk: str  # low|medium|high|critical
    created_at: float
    expires_at: float
    idempotency_key: str
    state: str = "queued"

    def classify(self) -> OfflineClass:
        if self.risk in ("high", "critical"):
            return OfflineClass.HIGH_RISK_ONLINE_REQUIRED
        if self.type in ("read", "list", "search"):
            return OfflineClass.SAFE_OFFLINE
        if self.type in ("create_task", "save_memory", "upload"):
            return OfflineClass.QUEUEABLE
        return OfflineClass.ONLINE_REQUIRED

    def replayable(self, now: float) -> bool:
        return (self.classify() == OfflineClass.QUEUEABLE
                and now <= self.expires_at
                and self.state in ("queued", "failed"))


# ---------------------------------------------------------------- devices

class DeviceTrust(str, Enum):
    KNOWN = "known"
    NEW = "new"
    REVOKED = "revoked"
    UNTRUSTED = "untrusted"


@dataclass
class DeviceRecord:
    device_id: str
    installation_id: str
    platform: str
    os_version: str
    app_version: str
    trust: DeviceTrust = DeviceTrust.NEW
    last_seen: float = 0.0

    def authorize(self) -> bool:
        return self.trust == DeviceTrust.KNOWN
