"""
AI-assisted analysis guardrails + Security Copilot.

AI (the model running inside the agent) is a *triage assistant*, never an
authority.  Guardrails:

    - every AI claim carries a confidence label: OBSERVED / INFERRED /
      HYPOTHESIS / UNKNOWN;
    - AI can NEVER: close a critical incident, grant permissions, disable
      security controls, delete evidence, or declare a system safe;
    - a request that violates a never-action is refused with a reason;
    - analysis output is always attached to an incident as evidence with the
      confidence label so it can't be mistaken for ground truth.

The copilot is deterministic plumbing: it accepts an incident + a prompt,
produces a structured analysis envelope, and enforces the guardrails.
The *content* of the analysis is the caller's to supply (from a model or a
human analyst); the guardrails ensure it is labeled and never authoritative.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .incidents import EvidenceEntry, IncidentStatus, SecOpsIncident

logger = logging.getLogger(__name__)


class Confidence(Enum):
    OBSERVED = "observed"       # directly seen in evidence
    INFERRED = "inferred"       # derived deterministically from evidence
    HYPOTHESIS = "hypothesis"   # model reasoning, unverified
    UNKNOWN = "unknown"


class NeverAction(Enum):
    CLOSE_CRITICAL = "close_critical_incident"
    GRANT_PERMISSION = "grant_permission"
    DISABLE_CONTROL = "disable_security_control"
    DELETE_EVIDENCE = "delete_evidence"
    DECLARE_SAFE = "declare_safe"


#: Never-actions that may never be performed by AI, at any confidence.
_NEVER_ACTIONS = {action for action in NeverAction}


@dataclass
class AnalysisClaim:
    claim: str
    confidence: Confidence
    evidence_refs: List[str] = field(default_factory=list)
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim,
            "confidence": self.confidence.value,
            "evidence_refs": list(self.evidence_refs),
            "detail": self.detail,
        }


@dataclass
class AnalysisEnvelope:
    """A guardrailed analysis result."""

    envelope_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    incident_id: str = ""
    prompt: str = ""
    claims: List[AnalysisClaim] = field(default_factory=list)
    refused: bool = False
    refusal_reason: str = ""
    produced_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "envelope_id": self.envelope_id,
            "incident_id": self.incident_id,
            "prompt": self.prompt,
            "claims": [c.to_dict() for c in self.claims],
            "refused": self.refused,
            "refusal_reason": self.refusal_reason,
            "produced_at": self.produced_at,
        }


class AnalysisGuard:
    """Enforces AI never-actions."""

    def check_prompt(self, prompt: str) -> Optional[str]:
        """Return a refusal reason when the prompt requests a never-action."""
        lower = prompt.lower()
        checks = [
            (NeverAction.CLOSE_CRITICAL,
             ("close", "resolve", "dismiss"),
             ("incident",)),
            (NeverAction.GRANT_PERMISSION,
             ("grant", "allow", "approve", "escalate", "authorize"),
             ("permission", "access", "privilege", "scope")),
            (NeverAction.DISABLE_CONTROL,
             ("disable", "turn off", "stop", "bypass"),
             ("monitoring", "audit", "authz", "authorization", "detection",
              "kill switch", "security control", "self-protection")),
            (NeverAction.DELETE_EVIDENCE,
             ("delete", "remove", "erase", "clear"),
             ("evidence", "log", "audit trail", "forensics")),
            (NeverAction.DECLARE_SAFE,
             ("declare", "confirm", "conclude"),
             ("safe", "secure", "no risk", "benign")),
        ]
        for action, verbs, nouns in checks:
            if any(v in lower for v in verbs) and any(n in lower for n in nouns):
                return (
                    f"refused: AI may not {action.value} (never-action "
                    f"{action.value})")
        return None

    def check_claims(self, claims: List[AnalysisClaim]) -> Optional[str]:
        """Refuse any claim that asserts a never-action was/is being done."""
        for claim in claims:
            text = claim.claim.lower()
            if "close" in text and "incident" in text:
                return "refused: AI may not close an incident"
            if ("grant" in text or "authorize" in text) and "permission" in text:
                return "refused: AI may not grant permissions"
            if ("disable" in text or "bypass" in text) and any(
                    k in text for k in ("monitoring", "audit", "authz", "detection")):
                return "refused: AI may not disable security controls"
            if "delete" in text and any(k in text for k in ("evidence", "log")):
                return "refused: AI may not delete evidence"
            if "safe" in text and "declare" in text:
                return "refused: AI may not declare a system safe"
        return None


class SecurityCopilot:
    """Guardrailed analysis service for security incidents.

    Usage::

        copilot = SecurityCopilot()
        envelope = copilot.analyze(
            incident, prompt="What happened?",
            claims=[AnalysisClaim("credential stuffing",
                                  Confidence.HYPOTHESIS)],
        )
    """

    def __init__(self) -> None:
        self._guard = AnalysisGuard()

    def analyze(self, incident: SecOpsIncident, *, prompt: str = "",
                claims: Optional[List[AnalysisClaim]] = None) -> AnalysisEnvelope:
        """Build a guardrailed analysis envelope for an incident."""
        envelope = AnalysisEnvelope(incident_id=incident.incident_id,
                                    prompt=prompt or "analysis request")
        # Prompt-level refusal first.
        refusal = self._guard.check_prompt(envelope.prompt)
        if refusal:
            envelope.refused = True
            envelope.refusal_reason = refusal
            return envelope
        # Claim-level guardrails.
        claims = list(claims or [])
        refusal = self._guard.check_claims(claims)
        if refusal:
            envelope.refused = True
            envelope.refusal_reason = refusal
            return envelope
        envelope.claims = claims
        # Attach the envelope as evidence with its confidence labels.
        incident.add_evidence(EvidenceEntry(
            kind="analysis",
            source="security_copilot",
            data=envelope.to_dict(),
        ))
        return envelope

    def analyze_text(self, incident: SecOpsIncident, *, text: str,
                     confidence: Confidence = Confidence.HYPOTHESIS,
                     evidence_refs: Optional[List[str]] = None) -> AnalysisEnvelope:
        """Convenience: wrap free-form analysis text into a labeled claim."""
        return self.analyze(
            incident,
            prompt=text,
            claims=[AnalysisClaim(claim=text, confidence=confidence,
                                  evidence_refs=list(evidence_refs or []))],
        )


# Global copilot
_security_copilot: Optional[SecurityCopilot] = None


def get_security_copilot() -> SecurityCopilot:
    """Return the process-wide SecurityCopilot singleton."""
    global _security_copilot
    if _security_copilot is None:
        _security_copilot = SecurityCopilot()
    return _security_copilot