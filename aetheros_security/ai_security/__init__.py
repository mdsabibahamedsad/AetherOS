"""
AI Security for AetherOS
========================

AI-specific security features:
    - Prompt Injection Detection
    - Tool Abuse Detection
    - Sensitive Data Detection
    - Unsafe Instruction Detection
    - Model Output Validation

Usage::

    from aetheros_security.ai_security import AISecurityManager

    manager = AISecurityManager()
    result = manager.scan_prompt("user input")
    result = manager.scan_output("model output")
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ThreatType(Enum):
    """Types of AI security threats."""
    PROMPT_INJECTION = "prompt_injection"
    TOOL_ABUSE = "tool_abuse"
    SENSITIVE_DATA = "sensitive_data"
    UNSAFE_INSTRUCTION = "unsafe_instruction"
    DATA_EXFILTRATION = "data_exfiltration"
    CODE_INJECTION = "code_injection"
    MANIPULATION = "manipulation"


class ThreatSeverity(Enum):
    """Threat severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Threat:
    """A detected threat."""
    threat_type: ThreatType
    severity: ThreatSeverity
    description: str
    confidence: float
    location: str = ""
    recommendations: List[str] = field(default_factory=list)
    timestamp: float = 0.0


@dataclass
class ScanResult:
    """Result of a security scan."""
    safe: bool
    threats: List[Threat] = field(default_factory=list)
    risk_score: float = 0.0
    scan_time: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


class AISecurityManager:
    """Manages AI-specific security for AetherOS.

    Usage::

        manager = AISecurityManager()

        # Scan user input (prompt)
        result = manager.scan_prompt("user input here")

        # Scan model output
        result = manager.scan_output("model output here")

        # Scan code
        result = manager.scan_code("generated code here")
    """

    def __init__(self) -> None:
        self._patterns = self._load_patterns()
        self._blocked_terms = self._load_blocked_terms()

    def _load_patterns(self) -> Dict[ThreatType, List[str]]:
        """Load detection patterns."""
        return {
            ThreatType.PROMPT_INJECTION: [
                r"ignore previous instructions",
                r"ignore all previous",
                r"disregard.*instructions",
                r"you are now",
                r"new instructions:",
                r"system prompt:",
                r"act as if",
                r"pretend you are",
                r"ignore safety",
                r"bypass.*filter",
                r"jailbreak",
                r"DAN mode",
                r"developer mode",
            ],
            ThreatType.TOOL_ABUSE: [
                r"execute.*command",
                r"run.*shell",
                r"delete.*all",
                r"rm\s+-rf",
                r"format.*disk",
                r"access.*system",
                r"read.*password",
                r"steal.*data",
                r"exfiltrate",
            ],
            ThreatType.SENSITIVE_DATA: [
                r"api[_-]?key\s*[=:]\s*['\"]?[a-zA-Z0-9]{20,}",
                r"password\s*[=:]\s*['\"]?[^\s'\"]{8,}",
                r"secret\s*[=:]\s*['\"]?[a-zA-Z0-9]{20,}",
                r"token\s*[=:]\s*['\"]?[a-zA-Z0-9]{20,}",
                r"-----BEGIN.*PRIVATE KEY-----",
                r"credit.?card.*\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}",
                r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            ],
            ThreatType.UNSAFE_INSTRUCTION: [
                r"how to.*hack",
                r"how to.*exploit",
                r"how to.*attack",
                r"how to.*steal",
                r"how to.*bypass.*security",
                r"create.*malware",
                r"create.*virus",
                r"phishing",
            ],
            ThreatType.DATA_EXFILTRATION: [
                r"send.*to.*external",
                r"upload.*to.*server",
                r"email.*to",
                r"post.*to.*url",
                r"exfiltrate.*data",
                r"steal.*information",
            ],
            ThreatType.CODE_INJECTION: [
                r"eval\s*\(",
                r"exec\s*\(",
                r"__import__\s*\(",
                r"subprocess.*shell\s*=\s*True",
                r"os\.system\s*\(",
            ],
            ThreatType.MANIPULATION: [
                r"you must",
                r"you have to",
                r"do this now",
                r"override.*safety",
                r"bypass.*restriction",
                r"ignore.*warning",
            ],
        }

    def _load_blocked_terms(self) -> List[str]:
        """Load blocked terms."""
        return [
            "malware",
            "ransomware",
            "trojan",
            "backdoor",
            "keylogger",
            "rootkit",
        ]

    def scan_prompt(self, prompt: str) -> ScanResult:
        """Scan a user prompt for threats.

        Args:
            prompt: User prompt to scan.

        Returns:
            Scan result with detected threats.
        """
        start_time = time.time()
        threats = []

        # Check patterns
        for threat_type, patterns in self._patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, prompt, re.IGNORECASE)
                for match in matches:
                    threats.append(Threat(
                        threat_type=threat_type,
                        severity=self._get_severity(threat_type),
                        description=f"Detected pattern: {pattern}",
                        confidence=0.8,
                        location=prompt[max(0, match.start()-20):match.end()+20],
                        timestamp=time.time(),
                    ))

        # Check blocked terms
        prompt_lower = prompt.lower()
        for term in self._blocked_terms:
            if term in prompt_lower:
                threats.append(Threat(
                    threat_type=ThreatType.UNSAFE_INSTRUCTION,
                    severity=ThreatSeverity.HIGH,
                    description=f"Blocked term detected: {term}",
                    confidence=0.9,
                    timestamp=time.time(),
                ))

        risk_score = self._calculate_risk_score(threats)

        return ScanResult(
            safe=len(threats) == 0,
            threats=threats,
            risk_score=risk_score,
            scan_time=time.time() - start_time,
        )

    def scan_output(self, output: str) -> ScanResult:
        """Scan model output for threats.

        Args:
            output: Model output to scan.

        Returns:
            Scan result with detected threats.
        """
        start_time = time.time()
        threats = []

        # Check for sensitive data in output
        for pattern in self._patterns.get(ThreatType.SENSITIVE_DATA, []):
            matches = re.finditer(pattern, output, re.IGNORECASE)
            for match in matches:
                threats.append(Threat(
                    threat_type=ThreatType.SENSITIVE_DATA,
                    severity=ThreatSeverity.MEDIUM,
                    description="Potential sensitive data in output",
                    confidence=0.7,
                    location=output[max(0, match.start()-20):match.end()+20],
                    timestamp=time.time(),
                    recommendations=["Review output before sharing"],
                ))

        risk_score = self._calculate_risk_score(threats)

        return ScanResult(
            safe=len(threats) == 0,
            threats=threats,
            risk_score=risk_score,
            scan_time=time.time() - start_time,
        )

    def scan_code(self, code: str) -> ScanResult:
        """Scan generated code for threats.

        Args:
            code: Code to scan.

        Returns:
            Scan result with detected threats.
        """
        start_time = time.time()
        threats = []

        # Check for code injection patterns
        for pattern in self._patterns.get(ThreatType.CODE_INJECTION, []):
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                threats.append(Threat(
                    threat_type=ThreatType.CODE_INJECTION,
                    severity=ThreatSeverity.HIGH,
                    description="Potentially unsafe code pattern",
                    confidence=0.8,
                    location=code[max(0, match.start()-30):match.end()+30],
                    timestamp=time.time(),
                    recommendations=["Review code before execution"],
                ))

        # Check for sensitive data
        for pattern in self._patterns.get(ThreatType.SENSITIVE_DATA, []):
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                threats.append(Threat(
                    threat_type=ThreatType.SENSITIVE_DATA,
                    severity=ThreatSeverity.MEDIUM,
                    description="Potential sensitive data in code",
                    confidence=0.7,
                    location=code[max(0, match.start()-20):match.end()+20],
                    timestamp=time.time(),
                ))

        risk_score = self._calculate_risk_score(threats)

        return ScanResult(
            safe=len(threats) == 0,
            threats=threats,
            risk_score=risk_score,
            scan_time=time.time() - start_time,
        )

    def _get_severity(self, threat_type: ThreatType) -> ThreatSeverity:
        """Get severity for a threat type."""
        severity_map = {
            ThreatType.PROMPT_INJECTION: ThreatSeverity.HIGH,
            ThreatType.TOOL_ABUSE: ThreatSeverity.CRITICAL,
            ThreatType.SENSITIVE_DATA: ThreatSeverity.MEDIUM,
            ThreatType.UNSAFE_INSTRUCTION: ThreatSeverity.HIGH,
            ThreatType.DATA_EXFILTRATION: ThreatSeverity.CRITICAL,
            ThreatType.CODE_INJECTION: ThreatSeverity.HIGH,
            ThreatType.MANIPULATION: ThreatSeverity.MEDIUM,
        }
        return severity_map.get(threat_type, ThreatSeverity.MEDIUM)

    def _calculate_risk_score(self, threats: List[Threat]) -> float:
        """Calculate risk score from threats."""
        if not threats:
            return 0.0

        severity_weights = {
            ThreatSeverity.LOW: 0.1,
            ThreatSeverity.MEDIUM: 0.3,
            ThreatSeverity.HIGH: 0.6,
            ThreatSeverity.CRITICAL: 1.0,
        }

        total_weight = sum(
            severity_weights.get(t.severity, 0.3) * t.confidence
            for t in threats
        )

        return min(1.0, total_weight / len(threats))

    def get_threat_summary(self, result: ScanResult) -> str:
        """Get human-readable threat summary."""
        if result.safe:
            return "No threats detected"

        threats_by_type = {}
        for threat in result.threats:
            t = threat.threat_type.value
            threats_by_type[t] = threats_by_type.get(t, 0) + 1

        summary_parts = []
        for threat_type, count in threats_by_type.items():
            summary_parts.append(f"{count} {threat_type}")

        return f"Detected {len(result.threats)} threats: {', '.join(summary_parts)}"

    def get_recommendations(self, result: ScanResult) -> List[str]:
        """Get security recommendations."""
        recommendations = []

        if not result.safe:
            recommendations.append("Review the flagged content carefully")
            recommendations.append("Consider blocking or modifying the content")

            if result.risk_score > 0.7:
                recommendations.append("High risk detected - consider blocking entirely")

            for threat in result.threats:
                recommendations.extend(threat.recommendations)

        return list(set(recommendations))


# Global AI security manager
_ai_security_manager: AISecurityManager | None = None


def get_ai_security_manager() -> AISecurityManager:
    """Return the global AISecurityManager singleton."""
    global _ai_security_manager
    if _ai_security_manager is None:
        _ai_security_manager = AISecurityManager()
    return _ai_security_manager
