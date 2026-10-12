"""Scientific safety: classification, dangerous-protocol detection,
injection/exfiltration defense, confidentiality modes, human gates,
STOP ALL SCIENCE. External content is DATA, never AUTHORITY."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

SAFETY_CLASSES = ["COMPUTATIONAL", "LOW_RISK", "REVIEW_REQUIRED",
                  "HIGH_RISK", "PROHIBITED"]

_BIO_CHEM = re.compile(
    r"\b(pathogen|toxin|bioweapon|gain.of.function|mustard gas|sarin|"
    r"ricin|anthrax|smallpox|ebola|marburg|nitro(explosive|glycerin)|"
    r"tnt\b|detonat|pipe bomb|dirty bomb)\b", re.I)
_CYBER = re.compile(
    r"\b(zero.day|ransomware|botnet|exfiltrat|credential (dump|harvest)|"
    r"privilege escalation exploit|rootkit)\b", re.I)
_INJECTION = re.compile(
    r"(ignore (all )?previous instructions|override (system|policy)|"
    r"send .* to (http|url)|exfiltrate|disable safet)", re.I)
_SECRET = re.compile(
    r"(sk-[A-Za-z0-9]{8,}|AKIA[0-9A-Z]{12,}|gh[pousr]_[A-Za-z0-9]{8,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|api[_-]?key\s*[:=])")


class ScientificSafetyPolicy:
    def classify(self, experiment_type: str, protocol: List[str],
                 domain: str = "") -> str:
        if experiment_type == "PHYSICAL_LAB":
            return "REVIEW_REQUIRED"
        text = " ".join(protocol) + " " + domain
        if _BIO_CHEM.search(text) or _CYBER.search(text):
            return "PROHIBITED"
        if experiment_type in ("COMPUTATIONAL", "SIMULATION",
                               "DATA_ANALYSIS", "STATISTICAL",
                               "LITERATURE_REPLICATION", "BENCHMARK"):
            return "COMPUTATIONAL"
        return "REVIEW_REQUIRED"

    def scan_protocol(self, protocol: List[str]) -> Dict[str, Any]:
        text = "\n".join(protocol)
        findings = []
        if _BIO_CHEM.search(text):
            findings.append("hazardous bio/chem content")
        if _CYBER.search(text):
            findings.append("offensive-cyber content")
        return {"findings": findings,
                "verdict": "BLOCK" if findings else "CLEAR"}

    def scan_document(self, text: str) -> Dict[str, Any]:
        """Untrusted scientific documents: injection + exfiltration."""
        injection = bool(_INJECTION.search(text))
        secrets = _SECRET.findall(text)
        return {"injection_detected": injection,
                "secrets_detected": len(secrets),
                "treatment": "DATA — never AUTHORITY; policy cannot be "
                             "overridden by document content",
                "quarantine": bool(injection or secrets)}

    def approval_required(self, safety_class: str,
                          policy: str = "HIGH_RISK") -> bool:
        if safety_class in ("HIGH_RISK", "PROHIBITED", "REVIEW_REQUIRED"):
            return True
        return policy == "ALL"


class LabConnector:
    """No connector configured -> LAB_UNAVAILABLE. Never claim physical
    execution happened."""

    def __init__(self, devices: Optional[Dict[str, Any]] = None):
        self.devices = devices or {}

    @property
    def status(self) -> str:
        return "AVAILABLE" if self.devices else "LAB_UNAVAILABLE"

    def execute(self, protocol: List[str]) -> Dict[str, Any]:
        if not self.devices:
            return {"status": "LAB_UNAVAILABLE",
                    "note": "no lab connector; physical execution not "
                            "performed and not simulated-as-real"}
        return {"status": "REQUIRES_OPERATOR",
                "note": "physical execution requires validated protocol, "
                        "authorization, bounds, operator identity"}
