"""Typed SDK errors + retry/timeout policies (M62 §7, §98-99)."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class SDKError(Exception):
    code: str = "INTERNAL_ERROR"
    message: str = ""
    category: str = "INTERNAL_ERROR"
    retryable: bool = False
    requestId: str = ""
    remediation: str = ""
    status: int = 500

    @classmethod
    def from_response(cls, status: int, payload: Any) -> "SDKError":
        if isinstance(payload, dict):
            return cls(code=payload.get("code", f"HTTP_{status}"),
                       message=str(payload.get("message", ""))[:500],
                       category=payload.get("category", "INTERNAL_ERROR"),
                       retryable=bool(payload.get("retryable", False)),
                       requestId=payload.get("requestId", ""),
                       remediation=payload.get("remediation", ""),
                       status=status)
        return cls(message=str(payload)[:500], status=status)


@dataclass
class RetryPolicy:
    max_attempts: int = 4
    base_delay_s: float = 0.5
    max_delay_s: float = 8.0
    jitter: bool = True

    def delay(self, attempt: int) -> float:
        d = min(self.max_delay_s, self.base_delay_s * (2 ** attempt))
        return d * (0.5 + random.random() * 0.5) if self.jitter else d


@dataclass
class TimeoutPolicy:
    connect_s: float = 5.0
    request_s: float = 30.0
    stream_idle_s: float = 30.0
    total_deadline_s: float = 300.0
