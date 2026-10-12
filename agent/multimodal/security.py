"""Adversarial Media Defense (Phases 66-70 of Master Prompt 10).

Media content is DATA, never AUTHORITY.  This module detects common prompt-
injection carriers inside media so extracted text is treated as untrusted
content rather than instructions.

Defenses implemented:
- Hidden / tiny / low-contrast text detection (OCR-result heuristic).
- Instruction-shaped text detection (e.g. "ignore previous instructions").
- QR-code / link / credential-phish markers.
- Audio/transcript instruction markers.
- A trust classifier that marks extracted content as DATA with an optional
  ``instructions_embedded`` flag surfaced to callers.

This module is advisory: it flags risk.  Enforcement (blocking) is the
caller's policy decision via MASTER 7 permission system.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MediaTrust(Enum):
    """Trust posture for media-derived content."""

    DATA = "data"                       # plain content; safe to reason about
    DATA_WITH_EMBEDDED_INSTRUCTIONS = "data_with_embedded_instructions"  # flagged
    SUSPICIOUS = "suspicious"           # high-risk pattern found
    UNTRUSTED = "untrusted"             # treat as hostile


@dataclass
class MediaRiskAssessment:
    trust: MediaTrust = MediaTrust.DATA
    findings: List[str] = field(default_factory=list)
    extracted_text_snippet: str = ""


# Instruction-shaped phrases (prompt-injection / jailbreak carriers).
_INSTRUCTION_PATTERNS = [
    re.compile(r"ignore (all |the |your )?(previous|prior|earlier) (instructions?|prompts?|messages?)", re.I),
    re.compile(r"disregard (all |the |your )?(previous|prior) (instructions?|prompts?)", re.I),
    re.compile(r"you (are|must|should|need to) (now|from now on|instead)", re.I),
    re.compile(r"system( prompt)?:?\s*(override|replace|forget)", re.I),
    re.compile(r"act as (a |an )?(free|unrestricted|unfiltered|evil|hypnotic)", re.I),
    re.compile(r"jailbreak|developpement mode|developer mode", re.I),
    re.compile(r"do not tell (the|your) (user|admin|developer)", re.I),
    re.compile(r"pretend (you|we)", re.I),
    re.compile(r"reveal (your|the) (system|prompt|instructions)", re.I),
    re.compile(r"what('s| is) your (prompt|instructions|system prompt)", re.I),
]

_LINK_PATTERN = re.compile(r"(https?://|bit\.ly/|tinyurl\.com/|qr\b)", re.I)
_CREDENTIAL_PATTERN = re.compile(r"(password|secret|api[_-]?key|token|credential)", re.I)


def _hidden_text_heuristics(text: str, meta: Dict[str, Any]) -> List[str]:
    """Flag carriers that are hard for humans but easy for models to read."""
    findings: List[str] = []
    try:
        if meta.get("font_size") is not None and meta.get("font_size", 100) < 6:
            findings.append("tiny text detected")
        if meta.get("font_size") is not None and meta.get("font_size", 100) > 96:
            findings.append("very large text detected (may be instruction carrier)")
        if meta.get("contrast") is not None and float(meta.get("contrast", 1.0)) < 0.1:
            findings.append("low-contrast text detected")
        if meta.get("rotation") is not None and float(meta.get("rotation", 0.0)) != 0.0:
            findings.append("rotated text detected")
        if meta.get("white_on_white") or meta.get("hidden"):
            findings.append("hidden/white-on-white text detected")
    except (TypeError, ValueError):
        pass
    return findings


def assess_extracted_text(
    text: str,
    media_type: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> MediaRiskAssessment:
    """Assess extracted text (OCR/STT/subtitle) for injection carriers."""
    if not text or not text.strip():
        return MediaRiskAssessment()
    meta = metadata or {}
    findings: List[str] = []
    clean = re.sub(r"\s+", " ", text)

    for pat in _INSTRUCTION_PATTERNS:
        if pat.search(clean):
            findings.append(f"instruction-shaped text: {pat.pattern}")
    if _LINK_PATTERN.search(clean):
        findings.append("embedded link/QR carrier")
    if _CREDENTIAL_PATTERN.search(clean) and len(clean) > 80:
        findings.append("credential-shaped content")
    findings.extend(_hidden_text_heuristics(text, meta))

    if not findings:
        return MediaRiskAssessment(trust=MediaTrust.DATA, extracted_text_snippet=clean[:500])
    if len(findings) >= 3:
        trust = MediaTrust.UNTRUSTED
    elif any("instruction-shaped" in f or "jailbreak" in f.lower() for f in findings):
        trust = MediaTrust.SUSPICIOUS
    else:
        trust = MediaTrust.DATA_WITH_EMBEDDED_INSTRUCTIONS
    return MediaRiskAssessment(trust=trust, findings=findings, extracted_text_snippet=clean[:500])


def classify_text_blocks(
    blocks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Annotate OCR blocks with a per-block trust tag (Phases 42/66)."""
    out: List[Dict[str, Any]] = []
    for block in blocks:
        text = block.get("text", "")
        meta = {
            "font_size": block.get("font_size"),
            "contrast": block.get("contrast"),
            "rotation": block.get("rotation"),
        }
        risk = assess_extracted_text(text, metadata=meta)
        annotated = dict(block)
        annotated["media_trust"] = risk.trust.value
        annotated["injection_findings"] = risk.findings
        out.append(annotated)
    return out


def is_instruction_carrier(assessment: MediaRiskAssessment) -> bool:
    """True when extracted content should be blocked or neutralized."""
    return assessment.trust in (
        MediaTrust.SUSPICIOUS,
        MediaTrust.UNTRUSTED,
    )


def neutralize(text: str, assessment: MediaRiskAssessment) -> str:
    """Return a safe paraphrase of flagged content (neutralized, not executed)."""
    if not is_instruction_carrier(assessment):
        return text
    return (
        "[content flagged as untrusted media instruction; treated as data, "
        f"not acted upon. findings={assessment.findings[:3]}]"
    )