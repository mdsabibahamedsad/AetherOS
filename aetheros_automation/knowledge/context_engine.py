from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ContextSource(str, Enum):
    MEMORY = "memory"
    FILE = "file"
    CONVERSATION = "conversation"
    PROJECT = "project"
    DOCUMENT = "document"
    KNOWLEDGE = "knowledge"
    RECENT_ACTIVITY = "recent_activity"
    TASK = "task"
    MESSAGE = "message"
    RESEARCH = "research"
    NOTE = "note"


class ContextRelevance(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class RelevantItem:
    id: str
    title: str
    summary: str
    source: ContextSource
    relevance: ContextRelevance = ContextRelevance.MEDIUM
    score: float = 0.0
    date: str = ""
    url: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "source": self.source.value,
            "relevance": self.relevance.value,
            "score": self.score,
            "date": self.date,
            "url": self.url,
            "metadata": self.metadata,
        }


@dataclass
class AgentContext:
    task: str = ""
    relevant_items: list[RelevantItem] = field(default_factory=list)
    recent_conversations: list[dict] = field(default_factory=list)
    current_project: Optional[dict] = None
    user_preferences: dict[str, Any] = field(default_factory=dict)
    active_goals: list[str] = field(default_factory=list)
    context_summary: str = ""

    def to_dict(self) -> dict:
        return {
            "task": self.task,
            "relevant_items": [i.to_dict() for i in self.relevant_items],
            "recent_conversations": self.recent_conversations,
            "current_project": self.current_project,
            "user_preferences": self.user_preferences,
            "active_goals": self.active_goals,
            "context_summary": self.context_summary,
        }


class ContextEngine:
    def __init__(self):
        self._activity_log: list[dict] = []

    def record_activity(self, activity_type: str, title: str, description: str = "",
                        source: str = "", entity_id: str = "", metadata: dict | None = None):
        self._activity_log.append({
            "type": activity_type,
            "title": title,
            "description": description,
            "source": source,
            "entity_id": entity_id,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        })
        if len(self._activity_log) > 1000:
            self._activity_log = self._activity_log[-500:]

    def get_recent_activity(self, limit: int = 20, activity_types: list[str] | None = None) -> list[dict]:
        results = list(self._activity_log)
        if activity_types:
            results = [r for r in results if r["type"] in activity_types]
        return sorted(results, key=lambda x: x["timestamp"], reverse=True)[:limit]

    def build_context(self, task: str, relevant_items: list[RelevantItem] | None = None,
                      recent_conversations: list[dict] | None = None,
                      current_project: dict | None = None,
                      user_preferences: dict | None = None,
                      active_goals: list[str] | None = None,
                      max_items: int = 15) -> AgentContext:
        items = relevant_items or []
        sorted_items = sorted(items, key=lambda x: (
            {"critical": 3, "high": 2, "medium": 1, "low": 0}.get(x.relevance.value, 0),
            x.score,
        ), reverse=True)[:max_items]
        summary_parts = []
        high_priority = [i for i in sorted_items if i.relevance in (ContextRelevance.CRITICAL, ContextRelevance.HIGH)]
        if high_priority:
            summary_parts.append(f"Found {len(high_priority)} high-priority items")
        project_name = current_project.get("name", "") if current_project else ""
        if project_name:
            summary_parts.append(f"Current project: {project_name}")
        if active_goals:
            summary_parts.append(f"Active goals: {', '.join(active_goals[:3])}")
        if recent_conversations:
            summary_parts.append(f"Recent conversations: {len(recent_conversations)}")
        context = AgentContext(
            task=task,
            relevant_items=sorted_items,
            recent_conversations=recent_conversations or [],
            current_project=current_project,
            user_preferences=user_preferences or {},
            active_goals=active_goals or [],
            context_summary=". ".join(summary_parts) if summary_parts else "No specific context found",
        )
        self.record_activity("context_built", f"Context for: {task[:50]}", source="context_engine")
        return context

    def filter_by_relevance(self, items: list[RelevantItem], min_score: float = 0.3) -> list[RelevantItem]:
        return [i for i in items if i.score >= min_score]

    def prioritize_items(self, items: list[RelevantItem], focus_keywords: list[str] | None = None) -> list[RelevantItem]:
        if not focus_keywords:
            return items
        kw_lower = [k.lower() for k in focus_keywords]
        scored = []
        for item in items:
            bonus = 0.0
            item_text = f"{item.title} {item.summary}".lower()
            for kw in kw_lower:
                if kw in item_text:
                    bonus += 0.2
            scored.append((item.score + bonus, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored]

    def summarize_context(self, context: AgentContext, max_length: int = 500) -> str:
        parts = [f"Task: {context.task[:100]}"]
        if context.current_project:
            parts.append(f"Project: {context.current_project.get('name', 'Unknown')}")
        if context.active_goals:
            parts.append(f"Goals: {', '.join(context.active_goals[:3])}")
        critical = [i for i in context.relevant_items if i.relevance == ContextRelevance.CRITICAL]
        if critical:
            parts.append(f"Critical context ({len(critical)} items):")
            for item in critical[:3]:
                parts.append(f"  - {item.title}: {item.summary[:100]}")
        high = [i for i in context.relevant_items if i.relevance == ContextRelevance.HIGH]
        if high:
            parts.append(f"Important context ({len(high)} items)")
        summary = "\n".join(parts)
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        return summary

    def clear_activity(self):
        self._activity_log.clear()
