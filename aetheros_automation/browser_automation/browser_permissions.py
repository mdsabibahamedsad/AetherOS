from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class BrowserPermissionType(Enum):
    READ_PAGE = "read_page"
    ACCESS_DOMAIN = "access_domain"
    USE_COOKIES = "use_cookies"
    DOWNLOAD_FILES = "download_files"
    UPLOAD_FILES = "upload_files"
    FILL_FORMS = "fill_forms"
    SUBMIT_FORMS = "submit_forms"
    ACCESS_CLIPBOARD = "access_clipboard"
    OPEN_POPUPS = "open_popups"
    USE_CAMERA = "use_camera"
    USE_MICROPHONE = "use_microphone"
    CONTROL_BROWSER = "control_browser"
    CONTROL_DESKTOP = "control_desktop"
    EXTERNAL_COMMUNICATION = "external_communication"
    SENSITIVE_WEBSITE = "sensitive_website"
    NAVIGATE = "navigate"
    EXECUTE_JS = "execute_js"
    SCREENSHOT = "screenshot"


REQUEST_DESCRIPTIONS = {
    BrowserPermissionType.READ_PAGE: "Read the content of the current page",
    BrowserPermissionType.ACCESS_DOMAIN: "Access this domain and its resources",
    BrowserPermissionType.USE_COOKIES: "Use cookies for this session",
    BrowserPermissionType.DOWNLOAD_FILES: "Download files to your computer",
    BrowserPermissionType.UPLOAD_FILES: "Upload files from your computer",
    BrowserPermissionType.FILL_FORMS: "Fill in form fields on this page",
    BrowserPermissionType.SUBMIT_FORMS: "Submit forms on this page",
    BrowserPermissionType.ACCESS_CLIPBOARD: "Access your clipboard",
    BrowserPermissionType.OPEN_POPUPS: "Open popup windows",
    BrowserPermissionType.USE_CAMERA: "Access your camera",
    BrowserPermissionType.USE_MICROPHONE: "Access your microphone",
    BrowserPermissionType.CONTROL_BROWSER: "Control browser navigation and settings",
    BrowserPermissionType.CONTROL_DESKTOP: "Control your desktop (mouse, keyboard)",
    BrowserPermissionType.EXTERNAL_COMMUNICATION: "Send data to external services",
    BrowserPermissionType.SENSITIVE_WEBSITE: "Access sensitive websites (banking, email)",
    BrowserPermissionType.NAVIGATE: "Navigate to new URLs",
    BrowserPermissionType.EXECUTE_JS: "Execute JavaScript on this page",
    BrowserPermissionType.SCREENSHOT: "Take screenshots of pages or desktop",
}

RISK_LEVELS = {
    BrowserPermissionType.READ_PAGE: "low",
    BrowserPermissionType.ACCESS_DOMAIN: "low",
    BrowserPermissionType.USE_COOKIES: "medium",
    BrowserPermissionType.DOWNLOAD_FILES: "medium",
    BrowserPermissionType.UPLOAD_FILES: "high",
    BrowserPermissionType.FILL_FORMS: "medium",
    BrowserPermissionType.SUBMIT_FORMS: "high",
    BrowserPermissionType.ACCESS_CLIPBOARD: "high",
    BrowserPermissionType.OPEN_POPUPS: "medium",
    BrowserPermissionType.USE_CAMERA: "high",
    BrowserPermissionType.USE_MICROPHONE: "high",
    BrowserPermissionType.CONTROL_BROWSER: "high",
    BrowserPermissionType.CONTROL_DESKTOP: "critical",
    BrowserPermissionType.EXTERNAL_COMMUNICATION: "high",
    BrowserPermissionType.SENSITIVE_WEBSITE: "critical",
    BrowserPermissionType.NAVIGATE: "low",
    BrowserPermissionType.EXECUTE_JS: "high",
    BrowserPermissionType.SCREENSHOT: "medium",
}


@dataclass
class PermissionRequest:
    permission_type: BrowserPermissionType
    url: str = ""
    reason: str = ""
    timestamp: str = ""
    status: str = "pending"


@dataclass
class PermissionGrant:
    permission_type: BrowserPermissionType
    url: str = ""
    granted: bool = False
    duration: str = "once"
    granted_at: str = ""


class BrowserPermissions:
    def __init__(self):
        self._grants: dict[str, list[PermissionGrant]] = {}
        self._pending: list[PermissionRequest] = []
        self._domain_blocklist: set[str] = set()

    def check(self, permission_type: BrowserPermissionType, url: str) -> bool:
        domain = self._extract_domain(url)
        if domain in self._domain_blocklist:
            return False

        key = self._make_key(permission_type, url)
        grants = self._grants.get(key, [])

        for grant in grants:
            if grant.granted and grant.duration in ("session", "permanent"):
                return True
            if grant.granted and grant.duration == "once":
                grants.remove(grant)
                return True

        return False

    def request(self, permission_type: BrowserPermissionType, url: str, reason: str = "") -> PermissionRequest:
        req = PermissionRequest(
            permission_type=permission_type,
            url=url,
            reason=reason or REQUEST_DESCRIPTIONS.get(permission_type, ""),
            timestamp=datetime.utcnow().isoformat(),
            status="pending",
        )
        self._pending.append(req)
        return req

    def grant(self, permission_type: BrowserPermissionType, url: str, duration: str = "once") -> bool:
        key = self._make_key(permission_type, url)
        if key not in self._grants:
            self._grants[key] = []

        self._grants[key].append(PermissionGrant(
            permission_type=permission_type,
            url=url,
            granted=True,
            duration=duration,
            granted_at=datetime.utcnow().isoformat(),
        ))

        self._pending = [p for p in self._pending if not (
            p.permission_type == permission_type and p.url == url
        )]
        return True

    def deny(self, permission_type: BrowserPermissionType, url: str) -> bool:
        self._pending = [p for p in self._pending if not (
            p.permission_type == permission_type and p.url == url
        )]
        return True

    def get_pending(self) -> list[PermissionRequest]:
        return list(self._pending)

    def get_grants(self) -> list[PermissionGrant]:
        result = []
        for grants in self._grants.values():
            result.extend(grants)
        return result

    def block_domain(self, domain: str):
        self._domain_blocklist.add(domain)

    def unblock_domain(self, domain: str):
        self._domain_blocklist.discard(domain)

    def is_domain_blocked(self, url: str) -> bool:
        domain = self._extract_domain(url)
        return domain in self._domain_blocklist

    def clear_session_grants(self):
        for key in list(self._grants.keys()):
            self._grants[key] = [g for g in self._grants[key] if g.duration not in ("once", "session")]
            if not self._grants[key]:
                del self._grants[key]

    def get_risk_level(self, permission_type: BrowserPermissionType) -> str:
        return RISK_LEVELS.get(permission_type, "medium")

    def get_description(self, permission_type: BrowserPermissionType) -> str:
        return REQUEST_DESCRIPTIONS.get(permission_type, "")

    def requires_approval(self, permission_type: BrowserPermissionType) -> bool:
        return RISK_LEVELS.get(permission_type, "low") in ("high", "critical")

    def _make_key(self, permission_type: BrowserPermissionType, url: str) -> str:
        return f"{permission_type.value}:{self._extract_domain(url)}"

    @staticmethod
    def _extract_domain(url: str) -> str:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc or url
        except Exception:
            return url
