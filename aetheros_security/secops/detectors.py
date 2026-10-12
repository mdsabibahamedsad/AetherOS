"""
Detection engine and built-in detectors.

The DetectionEngine subscribes to the SecurityEventBus and runs every
registered detector against each event.  Each detector emits zero or more
``Detection`` results carrying a rule id, severity, confidence, evidence and
suggested containment.  Deterministic by construction — detectors compose the
existing AetherOS security subsystems (threat detector, AI-security scanner,
network/filesystem security, tool authz) and add rule-based analysis.

Detectors cover the SecOps threat model:
    privilege escalation, approval abuse, policy bypass, prompt / indirect
    injection, memory poisoning, tool abuse, MCP anomalies, plugin/skill
    supply chain, data exfiltration, network/filesystem/command anomalies,
    resource exhaustion, cost anomalies, agent loops, repeated failures.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .events import SecurityEvent, SecurityEventType, SecurityEventBus
from .severity import SecuritySeverity, parse_severity

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """A raised detection."""

    rule_id: str
    title: str
    description: str
    severity: SecuritySeverity
    confidence: float = 0.8            # deterministic estimate
    event_id: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    affected_components: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    detector: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "event_id": self.event_id,
            "evidence": dict(self.evidence),
            "affected_components": list(self.affected_components),
            "suggestions": list(self.suggestions),
            "timestamp": self.timestamp,
            "detector": self.detector,
        }


class Detector:
    """Base class for a detector."""

    rule_id = "base"

    def handle(self, event: SecurityEvent) -> List[Detection]:
        return []

    def reset(self) -> None:
        pass


#: Helper: build a Detection.
def make_detection(rule_id: str, *, title: str, description: str,
                   severity: Any, confidence: float = 0.8,
                   event: Optional[SecurityEvent] = None,
                   evidence: Optional[Dict[str, Any]] = None,
                   components: Optional[List[str]] = None,
                   suggestions: Optional[List[str]] = None,
                   detector: str = "") -> Detection:
    return Detection(
        rule_id=rule_id,
        title=title,
        description=description,
        severity=parse_severity(severity),
        confidence=max(0.0, min(1.0, confidence)),
        event_id=event.event_id if event else "",
        evidence=evidence or {},
        affected_components=components or [],
        suggestions=suggestions or [],
        detector=detector or rule_id,
    )


# ======================================================================
# Built-in detectors
# ======================================================================


class AuthFailureDetector(Detector):
    """Repeated auth failures from one principal."""

    rule_id = "auth.repeated_failures"

    def __init__(self, limit: int = 5, window: float = 300.0) -> None:
        self._limit = limit
        self._window = window
        self._counts: Dict[str, List[float]] = {}

    def handle(self, event: SecurityEvent) -> List[Detection]:
        if event.event_type != SecurityEventType.AUTH_FAILURE:
            return []
        principal = event.principal or event.source or "unknown"
        now = time.time()
        bucket = [t for t in self._counts.get(principal, []) if now - t <= self._window]
        bucket.append(now)
        self._counts[principal] = bucket
        if len(bucket) >= self._limit:
            self._counts.pop(principal, None)
            return [make_detection(
                self.rule_id,
                title="Repeated authentication failures",
                description=f"{principal} failed authentication {len(bucket)} times in {int(self._window)}s",
                severity=SecuritySeverity.HIGH,
                confidence=0.9,
                event=event,
                evidence={"principal": principal, "count": len(bucket), "window": self._window},
                components=["authentication"],
                suggestions=["Lock the account", "Require re-authentication"],
                detector=type(self).__name__,
            )]
        return []

    def reset(self) -> None:
        self._counts.clear()


class PrivilegeEscalationDetector(Detector):
    """A principal gains high-value privileges unusually fast (spike in grants)."""

    rule_id = "privilege.escalation"

    def __init__(self, grants_limit: int = 3, window: float = 60.0) -> None:
        self._limit = grants_limit
        self._window = window
        self._grants: Dict[str, List[float]] = {}

    def handle(self, event: SecurityEvent) -> List[Detection]:
        if event.event_type not in (
                SecurityEventType.AUTHZ_ALLOW,
                SecurityEventType.POLICY_CHANGED,
                SecurityEventType.APPROVAL_RESOLVED):
            return []
        payload = event.payload or {}
        action = payload.get("action") or event.action or ""
        resource = payload.get("resource") or event.resource or ""
        sensitive = any(k in f"{action} {resource}".lower()
                        for k in ("grant", "promote", "escalate", "root",
                                  "admin", "scope", "secret", "credential"))
        if not sensitive:
            return []
        actor = event.principal or event.source or "unknown"
        now = time.time()
        bucket = [t for t in self._grants.get(actor, []) if now - t <= self._window]
        bucket.append(now)
        self._grants[actor] = bucket
        if len(bucket) >= self._limit:
            self._grants.pop(actor, None)
            return [make_detection(
                self.rule_id,
                title="Possible privilege escalation",
                description=f"{actor} performed {len(bucket)} sensitive privilege actions in {int(self._window)}s",
                severity=SecuritySeverity.CRITICAL,
                confidence=0.75,
                event=event,
                evidence={"principal": actor, "count": len(bucket),
                          "action": action, "resource": resource},
                components=["authz", "identity"],
                suggestions=["Review recent grants", "Temporarily suspend the principal"],
                detector=type(self).__name__,
            )]
        return []

    def reset(self) -> None:
        self._grants.clear()


class ApprovalAbuseDetector(Detector):
    """Unusual volume of approval requests/resolutions by one actor."""

    rule_id = "approval.abuse"

    def __init__(self, limit: int = 8, window: float = 120.0) -> None:
        self._limit = limit
        self._window = window
        self._reqs: Dict[str, List[float]] = {}

    def handle(self, event: SecurityEvent) -> List[Detection]:
        if event.event_type not in (SecurityEventType.APPROVAL_CREATED,
                                    SecurityEventType.APPROVAL_RESOLVED,
                                    SecurityEventType.AUTHZ_APPROVAL_REQUIRED):
            return []
        actor = event.principal or event.source or "unknown"
        now = time.time()
        bucket = [t for t in self._reqs.get(actor, []) if now - t <= self._window]
        bucket.append(now)
        self._reqs[actor] = bucket
        if len(bucket) >= self._limit:
            self._reqs.pop(actor, None)
            return [make_detection(
                self.rule_id,
                title="Approval abuse detected",
                description=f"{actor} triggered {len(bucket)} approvals in {int(self._window)}s",
                severity=SecuritySeverity.HIGH,
                confidence=0.7,
                event=event,
                evidence={"principal": actor, "count": len(bucket)},
                components=["approval"],
                suggestions=["Require dual control", "Suspend automated approvals"],
                detector=type(self).__name__,
            )]
        return []

    def reset(self) -> None:
        self._reqs.clear()


class PolicyBypassDetector(Detector):
    """Repeated authorization denials hinting at policy bypass attempts."""

    rule_id = "policy.bypass"

    def __init__(self, limit: int = 5, window: float = 120.0) -> None:
        self._limit = limit
        self._window = window
        self._denials: Dict[str, List[float]] = {}

    def handle(self, event: SecurityEvent) -> List[Detection]:
        if event.event_type != SecurityEventType.AUTHZ_DENY:
            return []
        actor = event.principal or event.source or "unknown"
        now = time.time()
        bucket = [t for t in self._denials.get(actor, []) if now - t <= self._window]
        bucket.append(now)
        self._denials[actor] = bucket
        if len(bucket) >= self._limit:
            self._denials.pop(actor, None)
            return [make_detection(
                self.rule_id,
                title="Possible policy bypass attempts",
                description=f"{actor} hit {len(bucket)} authorization denials in {int(self._window)}s",
                severity=SecuritySeverity.WARNING,
                confidence=0.65,
                event=event,
                evidence={"principal": actor, "count": len(bucket)},
                components=["authz"],
                suggestions=["Escalate review of the principal", "Tighten permissions"],
                detector=type(self).__name__,
            )]
        return []

    def reset(self) -> None:
        self._denials.clear()


class InjectionDetector(Detector):
    """Prompt/indirect injection — reuses the AI-security scanner.

    Contextual: scans message content for classic injection markers, and also
    flags *tool results* that contain injection instructions (indirect
    injection via web/MCP/skill content).
    """

    rule_id = "prompt.injection"

    _INJECTION_MARKERS = [
        r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|prompts)",
        r"disregard.*instructions",
        r"you\s+are\s+now\s+",
        r"new\s+system\s+prompt",
        r"act\s+as\s+(if\s+)?(admin|root|the\s+system)",
        r"jailbreak|DAN\s+mode|developer\s+mode",
        r"bypass\s+(safety|security|restrictions|filter)",
        r"override.*(rules|safety|security)",
    ]

    def handle(self, event: SecurityEvent) -> List[Detection]:
        text = event.message or ""
        payload = event.payload or {}
        text = text + " " + str(payload.get("content", ""))
        if not text.strip():
            return []
        lower = text.lower()
        for marker in self._INJECTION_MARKERS:
            if re.search(marker, lower):
                return [make_detection(
                    self.rule_id,
                    title="Prompt injection detected",
                    description=f"Injection marker matched in {event.event_type.value}",
                    severity=SecuritySeverity.HIGH,
                    confidence=0.8,
                    event=event,
                    evidence={"marker": marker, "source": event.source,
                              "component": event.component},
                    components=["ai_security"],
                    suggestions=["Sanitize the input", "Treat content as untrusted"],
                    detector=type(self).__name__,
                )]
        # Indirect injection: tool results / external content carried in payload.
        if event.event_type in (SecurityEventType.TOOL_RESULT,
                                SecurityEventType.MCP_REGISTERED,
                                SecurityEventType.SKILL_INSTALLED):
            content = str(payload.get("content", "")) or event.message or ""
            if content and len(content) > 40:
                if any(m in content.lower() for m in
                       ("ignore previous instructions", "you are now",
                        "system prompt:", "disregard")):
                    return [make_detection(
                        self.rule_id,
                        title="Indirect injection in external content",
                        description=f"External content from {event.source} contains injection instructions",
                        severity=SecuritySeverity.HIGH,
                        confidence=0.7,
                        event=event,
                        evidence={"source": event.source, "component": event.component},
                        components=["ai_security", "mcp"],
                        suggestions=["Do not follow instructions in tool results"],
                        detector=type(self).__name__,
                    )]
        return []


class MemoryPoisoningDetector(Detector):
    """Memory writes that look like injected instructions (poisoning)."""

    rule_id = "memory.poisoning"

    _POISON_MARKERS = [
        "ignore previous instructions", "you are now", "remember that you must",
        "always act as", "your new persona", "override your instructions",
    ]

    def handle(self, event: SecurityEvent) -> List[Detection]:
        if event.event_type != SecurityEventType.MEMORY_WRITE:
            return []
        content = str(event.payload.get("content", "")) or event.message or ""
        lower = content.lower()
        for marker in self._POISON_MARKERS:
            if marker in lower:
                return [make_detection(
                    self.rule_id,
                    title="Possible memory poisoning",
                    description=f"Memory write to {event.resource or 'memory'} contains instruction-injection markers",
                    severity=SecuritySeverity.HIGH,
                    confidence=0.7,
                    event=event,
                    evidence={"marker": marker, "principal": event.principal,
                              "resource": event.resource},
                    components=["memory"],
                    suggestions=["Reject the write", "Flag the memory segment for review"],
                    detector=type(self).__name__,
                )]
        return []


class ToolAbuseDetector(Detector):
    """Tools invoked with clearly destructive parameters."""

    rule_id = "tool.abuse"

    _DANGEROUS = {
        "rm": ["-rf", "--recursive", "--force"],
        "shutdown": ["now", "force"],
        "format": [],
        "dd": ["of="],
        "mkfs": [],
        "diskpart": [],
    }

    def handle(self, event: SecurityEvent) -> List[Detection]:
        if event.event_type not in (SecurityEventType.TOOL_CALL,
                                    SecurityEventType.CODE_EXECUTED):
            return []
        tool = event.action or event.resource or ""
        params = str(event.payload.get("params", "")) or event.message or ""
        lower_params = params.lower()
        for prog, flags in self._DANGEROUS.items():
            if prog in tool.lower():
                if not flags or any(f in lower_params for f in flags):
                    return [make_detection(
                        self.rule_id,
                        title="Destructive tool call",
                        description=f"Tool '{tool}' invoked with destructive parameters",
                        severity=SecuritySeverity.HIGH,
                        confidence=0.85,
                        event=event,
                        evidence={"tool": tool, "principal": event.principal},
                        components=["tool"],
                        suggestions=["Require approval", "Block the invocation"],
                        detector=type(self).__name__,
                    )]
        return []


class MCPAnomalyDetector(Detector):
    """MCP servers that are quarantined or return invalid responses."""

    rule_id = "mcp.anomaly"

    def handle(self, event: SecurityEvent) -> List[Detection]:
        if event.event_type in (SecurityEventType.MCP_QUARANTINED,
                                SecurityEventType.MCP_RESPONSE_INVALID):
            return [make_detection(
                self.rule_id,
                title="MCP server anomaly",
                description=f"MCP event {event.event_type.value} for {event.resource or event.source}",
                severity=(SecuritySeverity.HIGH if event.event_type ==
                          SecurityEventType.MCP_QUARANTINED else SecuritySeverity.WARNING),
                confidence=0.8,
                event=event,
                evidence={"mcp": event.resource or event.source,
                          "event": event.event_type.value},
                components=["mcp"],
                suggestions=["Remove the MCP server", "Review its tool schemas"],
                detector=type(self).__name__,
            )]
        return []


class SupplyChainDetector(Detector):
    """Plugin/skill/MCP installs flagged by the supply-chain subsystem."""

    rule_id = "supply_chain.mismatch"

    def handle(self, event: SecurityEvent) -> List[Detection]:
        if event.event_type not in (SecurityEventType.PLUGIN_INSTALLED,
                                    SecurityEventType.SKILL_INSTALLED,
                                    SecurityEventType.MCP_REGISTERED,
                                    SecurityEventType.SUPPLY_CHAIN_MISMATCH):
            return []
        # Direct supply-chain mismatch signal.
        if event.event_type == SecurityEventType.SUPPLY_CHAIN_MISMATCH:
            return [make_detection(
                self.rule_id,
                title="Supply-chain integrity mismatch",
                description=event.message or "A component hash did not match the known-good value",
                severity=SecuritySeverity.CRITICAL,
                confidence=0.9,
                event=event,
                evidence=dict(event.payload),
                components=["supply_chain"],
                suggestions=["Do not load the component", "Remove it from the store"],
                detector=type(self).__name__,
            )]
        # Verify a freshly installed component against the supply-chain manager.
        payload = event.payload or {}
        name = payload.get("name") or event.resource or ""
        if not name:
            return []
        try:
            from aetheros_security.supply_chain import get_supply_chain_manager
            report = get_supply_chain_manager().verify_hashes({name: payload.get("sha256", "")})
            status = (report.get(name) or {}).get("status", "not_installed")
        except Exception:
            return []
        if status == "mismatch":
            return [make_detection(
                self.rule_id,
                title="New component hash mismatch",
                description=f"Installed {name} does not match its known-good hash",
                severity=SecuritySeverity.CRITICAL,
                confidence=0.9,
                event=event,
                evidence={"component": name, "status": status},
                components=["supply_chain"],
                suggestions=["Quarantine the component", "Roll back the install"],
                detector=type(self).__name__,
            )]
        return []


class ExfiltrationDetector(Detector):
    """Large outbound data movement (file reads -> network egress)."""

    rule_id = "exfiltration.data"

    def __init__(self, size_threshold: float = 1_000_000) -> None:
        self._threshold = size_threshold

    def handle(self, event: SecurityEvent) -> List[Detection]:
        if event.event_type == SecurityEventType.DATA_EXFILTRATION:
            return [make_detection(
                self.rule_id,
                title="Data exfiltration detected",
                description=event.message or "High-volume data leaving the boundary",
                severity=SecuritySeverity.CRITICAL,
                confidence=0.85,
                event=event,
                evidence=dict(event.payload),
                components=["dlp", "network"],
                suggestions=["Kill external network", "Block the tool"],
                detector=type(self).__name__,
            )]
        if event.event_type == SecurityEventType.NETWORK_EXFILTRATION:
            size = float(event.payload.get("bytes", 0))
            if size >= self._threshold:
                return [make_detection(
                    self.rule_id,
                    title="Network exfiltration volume",
                    description=f"Outbound transfer of {size:g} bytes",
                    severity=SecuritySeverity.HIGH,
                    confidence=0.75,
                    event=event,
                    evidence={"bytes": size, "destination": event.resource},
                    components=["network", "dlp"],
                    suggestions=["Inspect egress", "Temporarily block the destination"],
                    detector=type(self).__name__,
                )]
        return []


class NetworkAnomalyDetector(Detector):
    """Connections to hosts blocked by the network security policy."""

    rule_id = "network.anomaly"

    def handle(self, event: SecurityEvent) -> List[Detection]:
        if event.event_type not in (SecurityEventType.NETWORK_CONNECT,
                                    SecurityEventType.NETWORK_ANOMALY):
            return []
        if event.event_type == SecurityEventType.NETWORK_ANOMALY:
            return [make_detection(
                self.rule_id,
                title="Network anomaly",
                description=event.message or "Unusual network activity",
                severity=SecuritySeverity.WARNING,
                confidence=0.7,
                event=event,
                evidence=dict(event.payload),
                components=["network"],
                suggestions=["Review egress", "Rate-limit the source"],
                detector=type(self).__name__,
            )]
        host = event.resource or ""
        if not host:
            return []
        try:
            from aetheros_security.network import get_network_security_manager
            decision = get_network_security_manager().check_host(host)
            allowed = decision.allowed
        except Exception:
            return []
        if not allowed:
            return [make_detection(
                self.rule_id,
                title="Blocked host connection attempted",
                description=f"{event.principal or event.source or 'unknown'} attempted to connect to {host}",
                severity=SecuritySeverity.HIGH,
                confidence=0.9,
                event=event,
                evidence={"host": host, "principal": event.principal},
                components=["network"],
                suggestions=["Verify intent", "Quarantine the principal"],
                detector=type(self).__name__,
            )]
        return []


class FilesystemAnomalyDetector(Detector):
    """Sensitive-path access and deletion bursts (composes threat detector)."""

    rule_id = "filesystem.anomaly"

    _SENSITIVE_PATHS = (
        "/etc/passwd", "/etc/shadow", "id_rsa", ".ssh", ".aws", "credentials",
        "secrets", "keyring", "env", "token",
    )

    def __init__(self, delete_burst: int = 10, window: float = 60.0) -> None:
        self._burst = delete_burst
        self._window = window
        self._deletes: Dict[str, List[float]] = {}
        self._threat = None

    def _threat_detector(self):
        if self._threat is None:
            from aetheros_security.threat import get_threat_detector
            self._threat = get_threat_detector()
        return self._threat

    def handle(self, event: SecurityEvent) -> List[Detection]:
        if event.event_type == SecurityEventType.FILE_ACCESS:
            path = event.resource or ""
            if any(s in path.lower() for s in self._SENSITIVE_PATHS):
                return [make_detection(
                    self.rule_id,
                    title="Sensitive file access",
                    description=f"{event.principal or event.source or 'unknown'} accessed sensitive path {path}",
                    severity=SecuritySeverity.WARNING,
                    confidence=0.7,
                    event=event,
                    evidence={"path": path, "principal": event.principal},
                    components=["filesystem"],
                    suggestions=["Confirm legitimate need", "Monitor subsequent activity"],
                    detector=type(self).__name__,
                )]
            return []
        if event.event_type == SecurityEventType.FILE_DELETE:
            actor = event.principal or event.source or "unknown"
            now = time.time()
            bucket = [t for t in self._deletes.get(actor, []) if now - t <= self._window]
            bucket.append(now)
            self._deletes[actor] = bucket
            if len(bucket) >= self._burst:
                self._deletes.pop(actor, None)
                return [make_detection(
                    self.rule_id,
                    title="File deletion burst",
                    description=f"{actor} deleted {len(bucket)} files in {int(self._window)}s",
                    severity=SecuritySeverity.HIGH,
                    confidence=0.8,
                    event=event,
                    evidence={"principal": actor, "count": len(bucket)},
                    components=["filesystem"],
                    suggestions=["Verify the deletions", "Check backups"],
                    detector=type(self).__name__,
                )]
        return []


class CommandAnomalyDetector(Detector):
    """Terminal commands matching known-dangerous patterns."""

    rule_id = "command.anomaly"

    _PATTERNS = [
        r"\bchmod\s+777\b",
        r"\bsudo\s+rm\b",
        r"\brm\s+-rf\s+/",
        r"\bmv\s+.*\s+/\s*$",
        r"\bcurl\s+.*\|\s*(ba)?sh\b",
        r"wget\s+.*\|\s*(ba)?sh\b",
        r"\bdd\s+.*\bof=/dev/",
        r":\s*\(\)\s*\{\s*:\|\|:\s*&\s*\}\s*;:",
        r"\bchown\s+root\b",
        r"\bmkfs|mkfs\.\w+",
        r"\bopenssl\s+genrsa\b",
    ]

    def handle(self, event: SecurityEvent) -> List[Detection]:
        if event.event_type != SecurityEventType.CODE_EXECUTED:
            return []
        command = event.action or event.message or str(event.payload.get("command", ""))
        lower = command.lower()
        for pattern in self._PATTERNS:
            if re.search(pattern, lower):
                return [make_detection(
                    self.rule_id,
                    title="Dangerous command executed",
                    description=f"Command matched dangerous pattern: {pattern}",
                    severity=SecuritySeverity.HIGH,
                    confidence=0.8,
                    event=event,
                    evidence={"command": command, "pattern": pattern,
                              "principal": event.principal},
                    components=["terminal"],
                    suggestions=["Kill tool execution", "Require approval for commands"],
                    detector=type(self).__name__,
                )]
        return []


class ResourceExhaustionDetector(Detector):
    """Resource exhaustion signals (composes the threat detector)."""

    rule_id = "resource.exhaustion"

    def handle(self, event: SecurityEvent) -> List[Detection]:
        if event.event_type in (SecurityEventType.RESOURCE_EXHAUSTION,
                                SecurityEventType.RATE_LIMITED):
            return [make_detection(
                self.rule_id,
                title="Resource exhaustion",
                description=event.message or f"Resource limit hit: {event.event_type.value}",
                severity=SecuritySeverity.HIGH,
                confidence=0.8,
                event=event,
                evidence=dict(event.payload),
                components=["budget", "resource"],
                suggestions=["Apply budget", "Restart the consuming component"],
                detector=type(self).__name__,
            )]
        if event.event_type == SecurityEventType.RESOURCE_USAGE:
            payload = event.payload or {}
            pct = float(payload.get("percent", 0))
            if pct >= 90:
                return [make_detection(
                    self.rule_id,
                    title="Resource usage near capacity",
                    description=f"{event.resource or 'resource'} at {pct:g}%",
                    severity=SecuritySeverity.WARNING,
                    confidence=0.7,
                    event=event,
                    evidence={"percent": pct, "resource": event.resource},
                    components=["budget"],
                    suggestions=["Investigate the consumer", "Restart if leaked"],
                    detector=type(self).__name__,
                )]
        return []


class CostAnomalyDetector(Detector):
    """Model-call cost that deviates from the per-agent baseline."""

    rule_id = "cost.anomaly"

    def handle(self, event: SecurityEvent) -> List[Detection]:
        if event.event_type != SecurityEventType.COST_ANOMALY:
            return []
        payload = event.payload or {}
        return [make_detection(
            self.rule_id,
            title="Cost anomaly",
            description=event.message or f"Cost deviated for {event.principal or 'agent'}",
            severity=SecuritySeverity.WARNING,
            confidence=0.7,
            event=event,
            evidence=dict(payload),
            components=["cost", "model"],
            suggestions=["Review the agent's model usage", "Cap the budget"],
            detector=type(self).__name__,
        )]


class AgentLoopDetector(Detector):
    """A single agent generating an abnormal number of iterations/tool calls."""

    rule_id = "agent.loop"

    def __init__(self, threshold: int = 60, window: float = 300.0) -> None:
        self._threshold = threshold
        self._window = window
        self._counts: Dict[str, List[float]] = {}

    def handle(self, event: SecurityEvent) -> List[Detection]:
        if event.event_type not in (SecurityEventType.TOOL_CALL,
                                    SecurityEventType.AGENT_STARTED):
            return []
        actor = event.agent_id or event.principal or event.source or "unknown"
        now = time.time()
        bucket = [t for t in self._counts.get(actor, []) if now - t <= self._window]
        bucket.append(now)
        self._counts[actor] = bucket
        if len(bucket) >= self._threshold:
            self._counts.pop(actor, None)
            return [make_detection(
                self.rule_id,
                title="Possible agent loop",
                description=f"{actor} performed {len(bucket)} tool calls in {int(self._window)}s",
                severity=SecuritySeverity.WARNING,
                confidence=0.7,
                event=event,
                evidence={"agent": actor, "count": len(bucket)},
                components=["agent", "mission"],
                suggestions=["Interrupt the agent", "Pause the mission"],
                detector=type(self).__name__,
            )]
        return []


class RepeatedFailureDetector(Detector):
    """Borrows the existing threat detector's repeated-failure signal."""

    rule_id = "system.repeated_failures"

    def __init__(self, limit: int = 10, window: float = 300.0) -> None:
        self._limit = limit
        self._window = window
        self._counts: Dict[str, List[float]] = {}

    def handle(self, event: SecurityEvent) -> List[Detection]:
        if event.event_type not in (SecurityEventType.SYSTEM_ERROR,
                                    SecurityEventType.MODEL_FAILURE):
            return []
        actor = event.source or event.component or "unknown"
        now = time.time()
        bucket = [t for t in self._counts.get(actor, []) if now - t <= self._window]
        bucket.append(now)
        self._counts[actor] = bucket
        if len(bucket) >= self._limit:
            self._counts.pop(actor, None)
            return [make_detection(
                self.rule_id,
                title="Repeated system failures",
                description=f"{actor} failed {len(bucket)} times in {int(self._window)}s",
                severity=SecuritySeverity.WARNING,
                confidence=0.7,
                event=event,
                evidence={"source": actor, "count": len(bucket)},
                components=["system"],
                suggestions=["Restart the component", "Review error logs"],
                detector=type(self).__name__,
            )]
        return []


#: Default detectors registered with every DetectionEngine.
def default_detectors() -> List[Detector]:
    return [
        AuthFailureDetector(),
        PrivilegeEscalationDetector(),
        ApprovalAbuseDetector(),
        PolicyBypassDetector(),
        InjectionDetector(),
        MemoryPoisoningDetector(),
        ToolAbuseDetector(),
        MCPAnomalyDetector(),
        SupplyChainDetector(),
        ExfiltrationDetector(),
        NetworkAnomalyDetector(),
        FilesystemAnomalyDetector(),
        CommandAnomalyDetector(),
        ResourceExhaustionDetector(),
        CostAnomalyDetector(),
        AgentLoopDetector(),
        RepeatedFailureDetector(),
    ]


# ======================================================================
# Detection engine
# ======================================================================


class DetectionEngine:
    """Orchestrates detectors over the event bus.

    Usage::

        engine = DetectionEngine()
        engine.attach(bus)   # subscribes to the bus
        detections = engine.ingest(event)   # or feed manually
        recent = engine.recent_detections()
    """

    def __init__(self, detectors: Optional[List[Detector]] = None) -> None:
        self._lock = threading.RLock()
        self._detectors: Dict[str, Detector] = {}
        self._detections: List[Detection] = []
        self._enabled = True
        self._max_detections = 2000
        for detector in (detectors if detectors is not None else default_detectors()):
            self._detectors[detector.rule_id] = detector

    def attach(self, bus: SecurityEventBus) -> None:
        """Subscribe the engine to a bus so every event is evaluated."""
        bus.subscribe(self._on_event)

    def _on_event(self, event: SecurityEvent) -> None:
        if not self._enabled:
            return
        detections = self.ingest(event)
        # Detections are already stored by ingest.
        del detections

    def ingest(self, event: SecurityEvent) -> List[Detection]:
        """Run every detector against a single event; store + return results."""
        if not self._enabled:
            return []
        raised: List[Detection] = []
        with self._lock:
            detectors = list(self._detectors.values())
        for detector in detectors:
            try:
                results = detector.handle(event)
            except Exception as exc:
                logger.debug("Detector %s failed: %s", detector.rule_id, exc)
                continue
            if results:
                raised.extend(results)
        if raised:
            with self._lock:
                self._detections.extend(raised)
                if len(self._detections) > self._max_detections:
                    self._detections = self._detections[-self._max_detections:]
        return raised

    def register(self, detector: Detector) -> None:
        with self._lock:
            self._detectors[detector.rule_id] = detector

    def unregister(self, rule_id: str) -> bool:
        with self._lock:
            return self._detectors.pop(rule_id, None) is not None

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def recent_detections(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return [d.to_dict() for d in self._detections[-limit:]]

    def clear(self) -> int:
        with self._lock:
            count = len(self._detections)
            self._detections.clear()
            return count

    def list_rules(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {"rule_id": rid, "detector": type(d).__name__}
                for rid, d in self._detectors.items()
            ]

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "detectors": len(self._detectors),
                "detections_retained": len(self._detections),
                "enabled": self._enabled,
            }


# Global detection engine
_detection_engine: Optional[DetectionEngine] = None


def get_detection_engine() -> DetectionEngine:
    """Return the process-wide DetectionEngine singleton."""
    global _detection_engine
    if _detection_engine is None:
        _detection_engine = DetectionEngine()
    return _detection_engine