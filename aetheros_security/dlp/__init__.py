"""
Data Loss Prevention for AetherOS
==================================

Detect and prevent data leakage:
    - API Keys
    - Passwords
    - Credit Cards
    - Private Keys
    - Tokens
    - Personal Data

Usage::

    from aetheros_security.dlp import DLPManager

    dlp = DLPManager()
    result = dlp.scan_text("My API key is sk-1234567890")
    if result.detected:
        print(f"Detected: {result.findings}")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DLPContentType(Enum):
    """Types of sensitive content."""
    API_KEY = "api_key"
    PASSWORD = "password"
    CREDIT_CARD = "credit_card"
    PRIVATE_KEY = "private_key"
    TOKEN = "token"
    PERSONAL_DATA = "personal_data"
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"


class DLPSeverity(Enum):
    """DLP finding severity."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DLPFinding:
    """A DLP finding."""
    content_type: DLPContentType
    severity: DLPSeverity
    matched_text: str
    position: tuple = (0, 0)
    confidence: float = 0.0
    recommendation: str = ""


@dataclass
class DLPScanResult:
    """DLP scan result."""
    detected: bool
    findings: List[DLPFinding] = field(default_factory=list)
    risk_score: float = 0.0
    scanned_length: int = 0


class DLPManager:
    """Data Loss Prevention manager.

    Usage::

        dlp = DLPManager()

        # Scan text
        result = dlp.scan_text("My API key is sk-1234567890")

        # Scan for specific types
        result = dlp.scan_text("text", content_types=[DLPContentType.API_KEY])

        # Mask sensitive data
        masked = dlp.mask_text("My key is sk-1234567890")
    """

    def __init__(self) -> None:
        self._patterns = self._load_patterns()

    def _load_patterns(self) -> Dict[DLPContentType, List[Dict[str, Any]]]:
        """Load DLP detection patterns."""
        return {
            DLPContentType.API_KEY: [
                {
                    "pattern": r"(?:api[_-]?key|apikey)\s*[=:]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
                    "severity": DLPSeverity.HIGH,
                    "confidence": 0.8,
                },
                {
                    "pattern": r"sk[_-]?[a-zA-Z0-9]{20,}",
                    "severity": DLPSeverity.HIGH,
                    "confidence": 0.9,
                },
            ],
            DLPContentType.PASSWORD: [
                {
                    "pattern": r"(?:password|passwd|pwd)\s*[=:]\s*['\"]?([^\s'\"]{8,})['\"]?",
                    "severity": DLPSeverity.CRITICAL,
                    "confidence": 0.85,
                },
            ],
            DLPContentType.CREDIT_CARD: [
                {
                    "pattern": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b",
                    "severity": DLPSeverity.CRITICAL,
                    "confidence": 0.95,
                },
            ],
            DLPContentType.PRIVATE_KEY: [
                {
                    "pattern": r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----",
                    "severity": DLPSeverity.CRITICAL,
                    "confidence": 0.99,
                },
            ],
            DLPContentType.TOKEN: [
                {
                    "pattern": r"(?:token|access[_-]?token|auth[_-]?token)\s*[=:]\s*['\"]?([a-zA-Z0-9_\-\.]{20,})['\"]?",
                    "severity": DLPSeverity.HIGH,
                    "confidence": 0.8,
                },
            ],
            DLPContentType.EMAIL: [
                {
                    "pattern": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
                    "severity": DLPSeverity.MEDIUM,
                    "confidence": 0.9,
                },
            ],
            DLPContentType.PHONE: [
                {
                    "pattern": r"\b(?:\+?1[-.]?)?\(?[0-9]{3}\)?[-.]?[0-9]{3}[-.]?[0-9]{4}\b",
                    "severity": DLPSeverity.LOW,
                    "confidence": 0.7,
                },
            ],
            DLPContentType.SSN: [
                {
                    "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
                    "severity": DLPSeverity.CRITICAL,
                    "confidence": 0.95,
                },
            ],
        }

    def scan_text(
        self,
        text: str,
        *,
        content_types: Optional[List[DLPContentType]] = None,
    ) -> DLPScanResult:
        """Scan text for sensitive content.

        Args:
            text: Text to scan.
            content_types: Specific types to scan for (None = all).

        Returns:
            Scan result.
        """
        findings = []
        types_to_scan = content_types or list(self._patterns.keys())

        for content_type in types_to_scan:
            patterns = self._patterns.get(content_type, [])
            for pattern_info in patterns:
                matches = re.finditer(
                    pattern_info["pattern"],
                    text,
                    re.IGNORECASE,
                )
                for match in matches:
                    # Mask the matched text
                    masked = self._mask_value(match.group(0))

                    findings.append(DLPFinding(
                        content_type=content_type,
                        severity=pattern_info["severity"],
                        matched_text=masked,
                        position=(match.start(), match.end()),
                        confidence=pattern_info["confidence"],
                        recommendation=self._get_recommendation(content_type),
                    ))

        risk_score = self._calculate_risk_score(findings)

        return DLPScanResult(
            detected=len(findings) > 0,
            findings=findings,
            risk_score=risk_score,
            scanned_length=len(text),
        )

    def _mask_value(self, value: str) -> str:
        """Mask a sensitive value."""
        if len(value) <= 4:
            return "*" * len(value)
        return value[:2] + "*" * (len(value) - 4) + value[-2:]

    def _get_recommendation(self, content_type: DLPContentType) -> str:
        """Get recommendation for content type."""
        recommendations = {
            DLPContentType.API_KEY: "Move to secrets manager",
            DLPContentType.PASSWORD: "Move to secrets manager",
            DLPContentType.CREDIT_CARD: "Remove or encrypt",
            DLPContentType.PRIVATE_KEY: "Move to secure storage",
            DLPContentType.TOKEN: "Move to secrets manager",
            DLPContentType.EMAIL: "Consider if sharing is necessary",
            DLPContentType.PHONE: "Consider if sharing is necessary",
            DLPContentType.SSN: "Remove immediately",
        }
        return recommendations.get(content_type, "Review and secure")

    def _calculate_risk_score(self, findings: List[DLPFinding]) -> float:
        """Calculate risk score from findings."""
        if not findings:
            return 0.0

        severity_weights = {
            DLPSeverity.LOW: 0.1,
            DLPSeverity.MEDIUM: 0.3,
            DLPSeverity.HIGH: 0.6,
            DLPSeverity.CRITICAL: 1.0,
        }

        total = sum(
            severity_weights.get(f.severity, 0.3) * f.confidence
            for f in findings
        )

        return min(1.0, total / len(findings))

    def mask_text(self, text: str) -> str:
        """Mask sensitive content in text.

        Args:
            text: Text to mask.

        Returns:
            Text with sensitive content masked.
        """
        result = text

        for content_type, patterns in self._patterns.items():
            for pattern_info in patterns:
                matches = list(re.finditer(
                    pattern_info["pattern"],
                    result,
                    re.IGNORECASE,
                ))
                # Replace in reverse order to maintain positions
                for match in reversed(matches):
                    masked = self._mask_value(match.group(0))
                    result = result[:match.start()] + masked + result[match.end():]

        return result

    def scan_file(self, file_path: str) -> DLPScanResult:
        """Scan a file for sensitive content.

        Args:
            file_path: Path to file.

        Returns:
            Scan result.
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return self.scan_text(content)
        except Exception:
            return DLPScanResult(detected=False)

    def get_summary(self, result: DLPScanResult) -> str:
        """Get human-readable summary."""
        if not result.detected:
            return "No sensitive content detected"

        type_counts = {}
        for finding in result.findings:
            t = finding.content_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        parts = [f"{count} {type}" for type, count in type_counts.items()]
        return f"Detected {len(result.findings)} sensitive items: {', '.join(parts)}"


# Global DLP manager
_dlp_manager: DLPManager | None = None


def get_dlp_manager() -> DLPManager:
    """Return the global DLPManager singleton."""
    global _dlp_manager
    if _dlp_manager is None:
        _dlp_manager = DLPManager()
    return _dlp_manager
