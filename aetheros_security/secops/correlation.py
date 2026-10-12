"""
Security event correlation.

The correlation engine turns *sets of related events* into a single higher
severity signal.  A correlation rule matches events sharing an actor
(principal), a resource, or a correlation id within a sliding window, and
raises a correlated alert when a threshold is met.

Correlation is deterministic and window-based (no ML).  Each rule has a
version so rule changes are trackable and gated through the learning loop.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .events import SecurityEvent, SecurityEventType, normalize_event_type
from .severity import SecuritySeverity, parse_severity


@dataclass
class CorrelationRule:
    """A deterministic correlation rule."""

    name: str
    event_types: List[Any]          # event types that participate
    window_seconds: float = 60.0
    min_events: int = 2
    group_by: str = "principal"     # principal | resource | correlation_id
    severity: Any = SecuritySeverity.WARNING
    title: str = ""
    description: str = ""
    version: int = 1


@dataclass
class CorrelationMatch:
    """A raised correlation."""

    rule: str
    title: str
    description: str
    severity: SecuritySeverity
    key: str                        # dedup key (rule + group value)
    event_ids: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    correlation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule": self.rule,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "key": self.key,
            "event_ids": list(self.event_ids),
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "version": self.version,
        }


class CorrelationEngine:
    """Windowed deterministic correlation engine.

    Usage::

        engine = CorrelationEngine()
        engine.add_rule(CorrelationRule(
            "repeated_auth_failures",
            event_types=[SecurityEventType.AUTH_FAILURE],
            window_seconds=60, min_events=5,
            group_by="principal", severity="warning",
            title="Repeated auth failures",
        ))
        engine.consume(event)  # fed every bus event
        matches = engine.poll()
    """

    def __init__(self, *, window_default: float = 60.0) -> None:
        self._lock = threading.RLock()
        self._rules: List[CorrelationRule] = []
        self._events_by_key: Dict[str, List[SecurityEvent]] = {}
        self._matches: List[CorrelationMatch] = []
        self._window_default = window_default

    def add_rule(self, rule: CorrelationRule) -> None:
        with self._lock:
            self._rules.append(rule)

    def remove_rule(self, name: str) -> bool:
        with self._lock:
            before = len(self._rules)
            self._rules = [r for r in self._rules if r.name != name]
            return len(self._rules) != before

    def clear_rules(self) -> None:
        with self._lock:
            self._rules.clear()

    def list_rules(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "name": r.name,
                    "event_types": [normalize_event_type(t).value for t in r.event_types],
                    "window_seconds": r.window_seconds,
                    "min_events": r.min_events,
                    "group_by": r.group_by,
                    "severity": parse_severity(r.severity).value,
                    "title": r.title,
                    "version": r.version,
                }
                for r in self._rules
            ]

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def _group_value(self, rule: CorrelationRule, event: SecurityEvent) -> str:
        if rule.group_by == "resource":
            return event.resource or event.component or "unknown"
        if rule.group_by == "correlation_id":
            return event.correlation_id or "none"
        return event.principal or event.source or "unknown"

    def consume(self, event: SecurityEvent) -> None:
        """Feed an event; evaluate correlation rules against the window."""
        now = time.time()
        raised: List[CorrelationMatch] = []
        with self._lock:
            for rule in list(self._rules):
                want = {normalize_event_type(t) for t in rule.event_types}
                if event.event_type not in want:
                    continue
                gval = self._group_value(rule, event)
                key = f"{rule.name}|{gval}"
                bucket = self._events_by_key.setdefault(key, [])
                bucket.append(event)
                # Prune stale events outside the window.
                cutoff = now - rule.window_seconds
                bucket[:] = [e for e in bucket if e.timestamp >= cutoff]
                if len(bucket) >= rule.min_events:
                    match = CorrelationMatch(
                        rule=rule.name,
                        title=rule.title or rule.name,
                        description=rule.description or (
                            f"{len(bucket)} correlated {rule.name} events"),
                        severity=parse_severity(rule.severity),
                        key=key,
                        event_ids=[e.event_id for e in bucket[-rule.min_events:]],
                        version=rule.version,
                    )
                    raised.append(match)
                    # Reset the bucket so a single match doesn't re-fire
                    # on every subsequent event in the same window.
                    del self._events_by_key[key]
        self._matches.extend(raised)
        return

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def poll(self, limit: int = 100) -> List[CorrelationMatch]:
        """Return and clear pending matches."""
        with self._lock:
            pending = list(self._matches[:limit])
            self._matches = self._matches[limit:]
        return pending

    def recent_matches(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [m.to_dict() for m in self._matches[-limit:]]

    def clear(self) -> int:
        with self._lock:
            count = len(self._matches)
            self._matches.clear()
            self._events_by_key.clear()
            return count

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "rules": len(self._rules),
                "pending_matches": len(self._matches),
                "active_windows": len(self._events_by_key),
            }


# Global correlation engine
_correlation_engine: Optional[CorrelationEngine] = None


def get_correlation_engine() -> CorrelationEngine:
    """Return the process-wide CorrelationEngine singleton."""
    global _correlation_engine
    if _correlation_engine is None:
        _correlation_engine = CorrelationEngine()
    return _correlation_engine