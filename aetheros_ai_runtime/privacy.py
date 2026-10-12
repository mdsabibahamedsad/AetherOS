"""Privacy: classification, redaction filter, privacy-aware routing
(sections 15-18, 70-71, 79-80). Runtime-enforced (never UI-only):
LOCAL_ONLY never leaves the machine (NO_COMPATIBLE_LOCAL_MODEL instead
of silent cloud fallback); escalation paths recorded (what/went-where);
sensitive content never stored by the router.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from aetheros_ai_runtime.models import DataClass, ModelRecord

_SECRET_RE = re.compile(
    r"(api[_-]?key\s*[:=]\s*\S+|password\s*[:=]\s*\S+|bearer\s+\S+|"
    r"sk-(live|test|proj)-[A-Za-z0-9._-]+|ghp_[A-Za-z0-9]+|"
    r"xox[baprs]-[A-Za-z0-9-]+|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")

_SENSITIVE_HINTS = re.compile(
    r"(ssn|social security|salary|diagnosis|prescription|bank account|"
    r"credit card|passport|api[_-]?key|password|secret|token|private key|"
    r"medical|financial statement|tax return)", re.I)


def classify_text(text: str, *, user_label: str = "") -> str:
    """Classify PUBLIC..HIGHLY_SENSITIVE. Explicit user label wins."""
    if user_label:
        label = user_label.strip().lower()
        mapping = {"public": DataClass.PUBLIC.value,
                   "internal": DataClass.INTERNAL.value,
                   "private": DataClass.PRIVATE.value,
                   "sensitive": DataClass.SENSITIVE.value,
                   "highly_sensitive": DataClass.HIGHLY_SENSITIVE.value,
                   "highly-sensitive": DataClass.HIGHLY_SENSITIVE.value}
        if label in mapping:
            return mapping[label]
    if _SECRET_RE.search(text or ""):
        return DataClass.HIGHLY_SENSITIVE.value
    if _SENSITIVE_HINTS.search(text or ""):
        return DataClass.SENSITIVE.value
    if re.search(r"(my (name|address|phone|email)|internal|confidential)", text or "", re.I):
        return DataClass.PRIVATE.value
    return DataClass.INTERNAL.value


def redact_for_cloud(text: str) -> Dict[str, Any]:
    """Remove secrets/credentials/identifiers before cloud escalation."""
    redacted, n = _SECRET_RE.subn("[REDACTED]", text or "")
    return {"text": redacted, "redactions": n}


@dataclass
class PrivacyDecision:
    classification: str = DataClass.INTERNAL.value
    cloud_allowed: bool = True
    escalation: str = "auto"  # auto|ask|never
    redactions: int = 0
    reason: str = ""
    at: float = field(default_factory=time.time)


class PrivacyRouter:
    """Policy gate between classification and provider eligibility."""

    def __init__(self, *, mode: str = "ask_before_cloud",
                 approve: Optional[Callable[[Dict[str, Any]], bool]] = None) -> None:
        # local_only|ask_before_cloud|cloud_allowed|air_gapped
        self.mode = mode
        self._approve = approve or (lambda _info: False)
        self.log: List[Dict[str, Any]] = []

    def gate(self, *, classification: str, candidate: ModelRecord,
             context: str = "", task_id: str = "") -> PrivacyDecision:
        is_local = candidate.locality == "local"
        if self.mode in ("local_only", "air_gapped"):
            if not is_local:
                return self._record(PrivacyDecision(
                    classification=classification, cloud_allowed=False,
                    escalation="never",
                    reason=f"{self.mode}: cloud model {candidate.canonical_id} blocked"),
                    candidate, task_id)
            return self._record(PrivacyDecision(
                classification=classification, cloud_allowed=True,
                escalation="auto", reason="local inference"), candidate, task_id)
        if classification == DataClass.HIGHLY_SENSITIVE.value and not is_local:
            return self._record(PrivacyDecision(
                classification=classification, cloud_allowed=False,
                escalation="never",
                reason="highly_sensitive requires explicit local-only authorization"),
                candidate, task_id)
        if not is_local:
            if self.mode == "ask_before_cloud":
                info = {"model": candidate.canonical_id,
                        "provider": candidate.provider_id,
                        "classification": classification, "task_id": task_id}
                allowed = bool(self._approve(info))
                return self._record(PrivacyDecision(
                    classification=classification, cloud_allowed=allowed,
                    escalation="ask" if allowed else "never",
                    reason="user approved cloud escalation" if allowed
                           else "cloud escalation denied"), candidate, task_id)
            return self._record(PrivacyDecision(
                classification=classification, cloud_allowed=True,
                escalation="auto", reason="cloud_allowed policy"), candidate, task_id)
        return self._record(PrivacyDecision(
            classification=classification, cloud_allowed=True,
            escalation="auto", reason="local inference"), candidate, task_id)

    def redact(self, context: str) -> Dict[str, Any]:
        return redact_for_cloud(context)

    def _record(self, dec: PrivacyDecision, candidate: ModelRecord,
                task_id: str) -> PrivacyDecision:
        # Audit what policy allowed and where data would go — never content.
        self.log.append({"at": dec.at, "task_id": task_id,
                         "model": candidate.canonical_id,
                         "provider": candidate.provider_id,
                         "locality": candidate.locality,
                         "classification": dec.classification,
                         "cloud_allowed": dec.cloud_allowed,
                         "escalation": dec.escalation,
                         "reason": dec.reason})
        return dec
