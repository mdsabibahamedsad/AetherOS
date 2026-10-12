"""Trust boundary and prompt-injection defense (Steps 22, 23, 45).

AetherOS treats every piece of programmatic context as *data with an origin*.
Instructions embedded in web pages, PDFs, DOCX, emails, OCR text, or model
output are **never** automatically elevated into executable agent commands.
This module provides:

* ``is_instruction_source`` — whether a source may be relied on as a command.
* ``scan_for_injection`` — heuristic detection of known injection phrasings
  in external content.
* ``safe_instruction`` — a tagged container distinguishing a trusted user
  instruction from external content that merely *references* an action.

The scanner is intentionally used as a *signal*, not an oracle: A security
event is recorded when external content matches, but the authoritative gate
remains the permission pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Sequence

from aetheros_actions.model import TrustSource


class InjectionSignal(str, Enum):
    IGNORE_PRIOR = "ignore_prior_instructions"
    DOWNLOAD_AND_RUN = "download_and_execute"
    EXFILTRATE_SECRETS = "exfiltrate_secrets"
    DISABLE_SECURITY = "disable_security"
    IMPERSONATE_USER = "impersonate_user"
    BYPASS_AUTH = "bypass_auth"
    PERSISTENCE = "persistence"


# Each signal is a list of regexes (re.IGNORECASE built in).
_INJECTION_RULES: dict[InjectionSignal, tuple[str, ...]] = {
    InjectionSignal.IGNORE_PRIOR: (
        r"ignore (all )?(previous|prior|earlier) (instructions?|prompts?|rules)",
        r"disregard (your|the) (instructions?|rules|system prompt)",
        r"forget everything (you|i) (were )?told",
        r"you are now (a|the) .*(no longer)",
        r"override (your|system) instructions",
        r"do not follow (the|your) (system )?(prompt|instructions)",
    ),
    InjectionSignal.DOWNLOAD_AND_RUN: (
        r"(download|fetch).*(and|then).*?(run|execute|install|open)",
        r"(run|execute|install).*(the|this)?\s*(download|file|script)",
        r"curl .*\|\s*(ba|z|k)?sh",
        r"powershell.*(iex|invoke-expression|start-process)",
    ),
    InjectionSignal.EXFILTRATE_SECRETS: (
        r"(paste|send|upload|exfiltrate|copy|reveal).*(api ?[_-]?key|token|password|"
        r"secret|credential|private key)",
        r"extract .*cookies",
        r"send (me|them|it) (your|the) (api key|password|token)",
        r"read .*\.env",
    ),
    InjectionSignal.DISABLE_SECURITY: (
        r"(disable|turn off|bypass|deactivate|ignore).*(security|permission|"
        r"safety|approval|firewall|sandbox)",
        r"don'?t (ask|prompt) (for )?(approval|confirmation|permission)",
        r"switch to (full )?autonomy",
        r"skip (the )?(safety|security|confirmation) (checks|steps)",
    ),
    InjectionSignal.IMPERSONATE_USER: (
        r"pretend (you are|to be) (the|an) (user|owner|administrator)",
        r"act as (the|an) (user|admin)",
    ),
    InjectionSignal.BYPASS_AUTH: (
        r"bypass (the )?(mfa|2fa|two[- ]factor|captcha|login|authentication|otp)",
        r"enter the (code|otp|pin) (without|without asking)",
        r"disable .*captcha",
    ),
    InjectionSignal.PERSISTENCE: (
        r"add (a )?(cron|startup|scheduled task)",
        r"install (a )?(service|daemon|startup item)",
        r"persist .*access",
    ),
}


def _compiled() -> dict[InjectionSignal, list[re.Pattern[str]]]:
    return {
        sig: [re.compile(pat, re.IGNORECASE) for pat in pats]
        for sig, pats in _INJECTION_RULES.items()
    }


@dataclass
class InjectionFinding:
    signal: InjectionSignal
    matched_text: str = ""

    def to_dict(self) -> dict:
        return {
            "signal": self.signal.value,
            "matched_text": self.matched_text[:200],
        }


def is_instruction_source(source: TrustSource) -> bool:
    """True only for sources whose text may be treated as commands.

    External content and model output are data; only the user, security
    policy, and system instructions are commands.
    """
    return source in (
        TrustSource.USER_INSTRUCTION,
        TrustSource.SECURITY_POLICY,
        TrustSource.SYSTEM_INSTRUCTION,
    )


def scan_for_injection(text: str) -> List[InjectionFinding]:
    """Scan ``text`` for known prompt-injection phrasings.

    Returns the matched signals. Empty list means no known signature. This
    is a heuristic — absence is NOT proof of safety, and presence should
    trigger a security event + denied/untrusted handling.
    """
    if not text:
        return []
    findings: List[InjectionFinding] = []
    for sig, patterns in _compiled().items():
        for pat in patterns:
            m = pat.search(text)
            if m:
                findings.append(InjectionFinding(signal=sig, matched_text=m.group(0)))
                break  # one finding per signal
    return findings


@dataclass
class TrustedInstruction:
    """A tagged instruction that survived trust evaluation.

    ``source`` must be an instruction source (is_instruction_source). Any
    external content that *looks* like an instruction is carried here only
    in the ``references_external`` sense — it never becomes a command.
    """

    text: str
    source: TrustSource
    findings: List[InjectionFinding] = field(default_factory=list)

    @property
    def is_trusted(self) -> bool:
        return is_instruction_source(self.source)

    def to_dict(self) -> dict:
        return {
            "text": self.text[:400],
            "source": self.source.value,
            "trusted": self.is_trusted,
            "injection_findings": [f.to_dict() for f in self.findings],
        }


def classify_text(
    text: str,
    source: TrustSource,
    *,
    scan: bool = True,
) -> TrustedInstruction:
    """Wrap ``text`` with its source and optional injection scan.

    When ``source`` is external and ``scan`` is on, findings are recorded so
    callers can emit a security event and refuse to transcribe the content
    into an actionable plan.
    """
    findings: List[InjectionFinding] = []
    if scan and TrustSource.is_external(source):
        findings = scan_for_injection(text)
    return TrustedInstruction(text=text, source=source, findings=findings)


def lowest_trust_source(sources: Sequence[TrustSource]) -> TrustSource:
    """Return the least trusted of ``sources`` (used for plan-level gating).

    ``trust_rank()`` is 0 for the most trusted (user instructions) and larger
    for less trusted sources, so the least trusted one is the ``max`` rank.
    """
    if not sources:
        return TrustSource.MODEL_OUTPUT
    return max(sources, key=lambda s: s.trust_rank())