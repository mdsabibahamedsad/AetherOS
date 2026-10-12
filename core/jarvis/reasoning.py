from __future__ import annotations

import re
import time
import json
import logging
from typing import Optional, Any
from dataclasses import dataclass, field

from core.jarvis.observer import ObserverEvent, EventType

logger = logging.getLogger(__name__)


@dataclass
class ReasoningSuggestion:
    title: str
    description: str
    priority: int = 5
    category: str = "general"
    action: Optional[str] = None
    action_params: dict = field(default_factory=dict)


@dataclass
class ReasoningResult:
    event_type: str
    triggered: bool
    confidence: float
    suggestions: list[ReasoningSuggestion] = field(default_factory=list)
    summary: str = ""
    context: dict = field(default_factory=dict)


class ReasoningEngine:
    def __init__(self):
        self._rules: list[dict] = self._build_default_rules()
        self._history: list[dict] = []

    def _build_default_rules(self) -> list[dict]:
        return [
            {
                "event": EventType.USER_CLIPBOARD,
                "condition": lambda data: data.get("is_code", False) and data.get("length", 0) > 50,
                "reason": "User copied code - may want explanation or refactoring",
                "suggestions": [
                    ReasoningSuggestion(
                        "Review copied code",
                        "Analyze the copied code for improvements",
                        priority=7, category="code",
                        action="analyze_code",
                        action_params={"content_key": "content"},
                    ),
                    ReasoningSuggestion(
                        "Explain this code",
                        "Provide explanation of what the code does",
                        priority=5, category="code",
                        action="explain_code",
                        action_params={"content_key": "content"},
                    ),
                ],
            },
            {
                "event": EventType.USER_CLIPBOARD,
                "condition": lambda data: data.get("length", 0) > 200 and not data.get("is_code", False),
                "reason": "User copied substantial text - may need summarization",
                "suggestions": [
                    ReasoningSuggestion(
                        "Summarize text",
                        "Provide a concise summary of the copied text",
                        priority=6, category="research",
                        action="summarize",
                        action_params={"content_key": "content"},
                    ),
                ],
            },
            {
                "event": EventType.APP_OPENED,
                "condition": lambda data: data.get("friendly") in ("vscode", "terminal"),
                "reason": "User opened development environment",
                "suggestions": [
                    ReasoningSuggestion(
                        "Check project status",
                        "Scan the current project for issues",
                        priority=5, category="development",
                        action="scan_project",
                    ),
                    ReasoningSuggestion(
                        "Ready to assist",
                        "I'm here to help with development tasks",
                        priority=3, category="development",
                    ),
                ],
            },
            {
                "event": EventType.PROJECT_DETECTED,
                "condition": lambda data: bool(data.get("path")),
                "reason": "Git repository detected - may want code review or status",
                "suggestions": [
                    ReasoningSuggestion(
                        "Review recent changes",
                        "Check recent git commits for issues",
                        priority=6, category="development",
                        action="review_commits",
                        action_params={"path_key": "path"},
                    ),
                    ReasoningSuggestion(
                        "Offer code analysis",
                        "Analyze the repository architecture",
                        priority=5, category="development",
                        action="analyze_repo",
                        action_params={"path_key": "path"},
                    ),
                ],
            },
            {
                "event": EventType.APP_OPENED,
                "condition": lambda data: data.get("friendly") == "chrome",
                "reason": "User opened browser - may need browsing assistance",
                "suggestions": [
                    ReasoningSuggestion(
                        "Browser automation ready",
                        "I can help with web research or automation",
                        priority=3, category="browser",
                    ),
                ],
            },
            {
                "event": EventType.SYSTEM_LOAD,
                "condition": lambda data: data.get("cpu", 0) > 80,
                "reason": "High CPU usage detected",
                "suggestions": [
                    ReasoningSuggestion(
                        "High resource usage",
                        "High CPU usage detected - may want to check running processes",
                        priority=8, category="system",
                        action="check_processes",
                    ),
                ],
            },
            {
                "event": EventType.SYSTEM_LOAD,
                "condition": lambda data: data.get("memory_percent", 0) > 85,
                "reason": "High memory usage detected",
                "suggestions": [
                    ReasoningSuggestion(
                        "Low memory warning",
                        "High memory usage detected - consider closing some applications",
                        priority=7, category="system",
                    ),
                ],
            },
            {
                "event": EventType.USER_IDLE,
                "condition": lambda data: data.get("duration", 0) > 300,
                "reason": "System idle for a while",
                "suggestions": [
                    ReasoningSuggestion(
                        "Background maintenance",
                        "Run maintenance tasks while system is idle",
                        priority=4, category="system",
                        action="run_maintenance",
                    ),
                ],
            },
        ]

    def add_rule(self, event_type: EventType | str, condition: callable, reason: str,
                 suggestions: list[ReasoningSuggestion]):
        self._rules.append({
            "event": event_type if isinstance(event_type, EventType) else EventType(event_type),
            "condition": condition,
            "reason": reason,
            "suggestions": suggestions,
        })

    def reason(self, event: ObserverEvent) -> Optional[ReasoningResult]:
        event_key = event.type.value if isinstance(event.type, EventType) else event.type
        matching_suggestions: list[ReasoningSuggestion] = []

        for rule in self._rules:
            rule_event = rule["event"]
            rule_key = rule_event.value if isinstance(rule_event, EventType) else rule_event
            if rule_key == event_key:
                try:
                    if rule["condition"](event.data):
                        matching_suggestions.extend(rule["suggestions"])
                except Exception as e:
                    logger.debug(f"Rule condition error: {e}")

        if matching_suggestions:
            matching_suggestions.sort(key=lambda s: s.priority, reverse=True)
            result = ReasoningResult(
                event_type=event_key,
                triggered=True,
                confidence=min(0.5 + len(matching_suggestions) * 0.1, 0.95),
                suggestions=matching_suggestions[:5],
                summary=matching_suggestions[0].title if matching_suggestions else "",
                context={
                    "event_data": event.data,
                    "event_time": event.timestamp,
                    "suggestion_count": len(matching_suggestions),
                },
            )

            self._history.append({
                "timestamp": time.time(),
                "event_type": event_key,
                "suggestions": [s.title for s in matching_suggestions],
            })
            self._history = self._history[-100:]

            return result

        return None

    def get_rules(self) -> list[dict]:
        return [
            {
                "event": r["event"].value if isinstance(r["event"], EventType) else r["event"],
                "reason": r["reason"],
                "suggestion_count": len(r["suggestions"]),
            }
            for r in self._rules
        ]

    def get_history(self, limit: int = 20) -> list[dict]:
        return self._history[-limit:]
