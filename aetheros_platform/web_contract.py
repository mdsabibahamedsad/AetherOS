"""Web/server contracts (Master 69).

Canonical error model, security-headers contract, startup config
validator, pagination envelope. Pure + tested; server wiring is
explicit follow-up (documented, not faked).
"""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field


# ---------------------------------------------------------------- errors

@dataclass(frozen=True)
class ApiError:
    code: str          # MACHINE_CODE
    http_status: int
    message: str       # human-safe, no internals
    request_id: str
    retryable: bool = False
    retry_after: int = 0
    trace_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


ERROR_CATALOG = {
    "unauthenticated": 401, "forbidden": 403, "not_found": 404,
    "conflict": 409, "gone": 410, "rate_limited": 429,
    "invalid": 422, "failed": 500, "unavailable": 503, "timeout": 504,
}

_LEAK_RE = re.compile(
    r"(Traceback|File \"|sk-[A-Za-z0-9]|BEGIN .*PRIVATE KEY|"
    r"api[_-]?key\s*[:=]|password\s*[:=]|SELECT .* FROM|ssh-rsa)",
    re.IGNORECASE)


def make_error(code: str, message: str, request_id: str = "",
               retry_after: int = 0, trace_id: str = "") -> ApiError:
    if code not in ERROR_CATALOG:
        raise ValueError(f"unknown error code: {code}")
    if _LEAK_RE.search(message):
        raise ValueError("error message leaks internals/secrets")
    return ApiError(code=code, http_status=ERROR_CATALOG[code],
                    message=message,
                    request_id=request_id or f"req-{uuid.uuid4().hex[:12]}",
                    retryable=code in ("rate_limited", "unavailable", "timeout"),
                    retry_after=retry_after, trace_id=trace_id)


# ---------------------------------------------------------------- headers

SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'self'",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


def validate_security_headers(headers: dict) -> tuple[bool, list[str]]:
    missing = [k for k in SECURITY_HEADERS if k not in headers]
    return (not missing, [f"missing: {k}" for k in missing])


def cors_origin_allowed(origin: str, allowlist: list[str]) -> bool:
    if origin in allowlist:
        return True
    return any(a.startswith("*.") and origin.endswith(a[1:])
               for a in allowlist)


# ---------------------------------------------------------------- paging

@dataclass(frozen=True)
class Page:
    items: tuple
    cursor: str = ""
    limit: int = 50
    has_more: bool = False

    def __post_init__(self) -> None:
        if not 1 <= self.limit <= 200:
            raise ValueError("limit must be 1..200")


# ---------------------------------------------------------------- config

REQUIRED_PROD_KEYS = ("api_base_url", "allowed_origins", "auth_mode")


def validate_server_config(cfg: dict) -> tuple[bool, list[str]]:
    """Fail fast on bad production config. Never echoes secret values."""
    problems = []
    for k in REQUIRED_PROD_KEYS:
        if not cfg.get(k):
            problems.append(f"missing: {k}")
    for o in cfg.get("allowed_origins", []):
        if o == "*":
            problems.append("wildcard origin forbidden in production")
        elif not re.match(r"^https://[^/]+$", o) and o not in (
                "http://localhost", "http://127.0.0.1"):
            problems.append(f"origin must be https (or loopback dev): {o}")
    if cfg.get("auth_mode") not in ("loopback", "session", "oidc", "disabled-dev"):
        problems.append("unknown auth_mode")
    return (not problems, problems)
