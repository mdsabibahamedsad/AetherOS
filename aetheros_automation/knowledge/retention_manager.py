from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class RetentionAction(str, Enum):
    DELETE = "delete"
    ARCHIVE = "archive"
    NOTIFY = "notify"


@dataclass
class DataRetentionRule:
    id: str
    entity_type: str
    max_age_days: int = 365
    action: RetentionAction = RetentionAction.ARCHIVE
    enabled: bool = True
    description: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "max_age_days": self.max_age_days,
            "action": self.action.value,
            "enabled": self.enabled,
            "description": self.description,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DataRetentionRule:
        return cls(
            id=data["id"],
            entity_type=data["entity_type"],
            max_age_days=data.get("max_age_days", 365),
            action=RetentionAction(data.get("action", "archive")),
            enabled=data.get("enabled", True),
            description=data.get("description", ""),
            created_at=data.get("created_at", ""),
        )


@dataclass
class RetentionSchedule:
    entity_type: str
    item_count: int = 0
    expired_count: int = 0
    next_expiration: str = ""
    rules: list[DataRetentionRule] = field(default_factory=list)


class RetentionManager:
    def __init__(self, storage_path: Optional[str] = None):
        self._storage_path = Path(storage_path) if storage_path else Path.cwd() / "retention_data"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._rules: dict[str, DataRetentionRule] = {}
        self._load()
        if not self._rules:
            self._init_defaults()

    def _path(self) -> Path:
        return self._storage_path / "retention_rules.json"

    def _load(self):
        p = self._path()
        if p.exists():
            try:
                data = json.loads(p.read_text("utf-8"))
                for item in data:
                    rule = DataRetentionRule.from_dict(item)
                    self._rules[rule.id] = rule
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        self._path().write_text(
            json.dumps([r.to_dict() for r in self._rules.values()], indent=2, default=str), "utf-8")

    def _init_defaults(self):
        defaults = [
            DataRetentionRule(id="ret_temporary", entity_type="temporary_memory", max_age_days=1,
                              action=RetentionAction.DELETE, description="Temporary memories expire after 1 day"),
            DataRetentionRule(id="ret_conversation", entity_type="conversation_memory", max_age_days=90,
                              action=RetentionAction.ARCHIVE, description="Conversation memories archive after 90 days"),
            DataRetentionRule(id="ret_search", entity_type="search_history", max_age_days=30,
                              action=RetentionAction.DELETE, description="Search history deleted after 30 days"),
            DataRetentionRule(id="ret_agent", entity_type="agent_memory", max_age_days=365,
                              action=RetentionAction.ARCHIVE, description="Agent memories archive after 1 year"),
            DataRetentionRule(id="ret_activity", entity_type="activity_log", max_age_days=90,
                              action=RetentionAction.DELETE, description="Activity log deleted after 90 days"),
        ]
        for rule in defaults:
            self._rules[rule.id] = rule
        self._save()

    def _generate_id(self) -> str:
        import uuid
        return f"ret_{uuid.uuid4().hex[:8]}"

    def add_rule(self, entity_type: str, max_age_days: int = 365,
                 action: RetentionAction = RetentionAction.ARCHIVE,
                 description: str = "") -> DataRetentionRule:
        rule = DataRetentionRule(
            id=self._generate_id(),
            entity_type=entity_type,
            max_age_days=max_age_days,
            action=action,
            enabled=True,
            description=description,
            created_at=datetime.now().isoformat(),
        )
        self._rules[rule.id] = rule
        self._save()
        return rule

    def update_rule(self, rule_id: str, **updates) -> Optional[DataRetentionRule]:
        rule = self._rules.get(rule_id)
        if not rule:
            return None
        for key, value in updates.items():
            if hasattr(rule, key) and key != "id":
                if key == "action":
                    setattr(rule, key, RetentionAction(value) if isinstance(value, str) else value)
                else:
                    setattr(rule, key, value)
        self._save()
        return rule

    def remove_rule(self, rule_id: str) -> bool:
        if rule_id not in self._rules:
            return False
        del self._rules[rule_id]
        self._save()
        return True

    def get_rules(self, entity_type: str = "") -> list[DataRetentionRule]:
        if entity_type:
            return [r for r in self._rules.values() if r.entity_type == entity_type and r.enabled]
        return [r for r in self._rules.values() if r.enabled]

    def check_expired(self, entity_type: str, created_at: str) -> tuple[bool, RetentionAction]:
        rules = self.get_rules(entity_type)
        if not rules or not created_at:
            return False, RetentionAction.ARCHIVE
        try:
            created = datetime.fromisoformat(created_at)
            now = datetime.now()
            age = (now - created).days
        except (ValueError, TypeError):
            return False, RetentionAction.ARCHIVE
        for rule in rules:
            if age >= rule.max_age_days:
                return True, rule.action
        return False, RetentionAction.ARCHIVE

    def apply_retention(self, entity_type: str, entries: list[dict],
                        date_field: str = "created_at") -> tuple[list[dict], list[dict]]:
        to_delete = []
        to_archive = []
        for entry in entries:
            expired, action = self.check_expired(entity_type, entry.get(date_field, ""))
            if expired:
                if action == RetentionAction.DELETE:
                    to_delete.append(entry)
                elif action == RetentionAction.ARCHIVE:
                    to_archive.append(entry)
        return to_delete, to_archive

    def get_schedule(self) -> list[RetentionSchedule]:
        types = set(r.entity_type for r in self._rules.values() if r.enabled)
        schedules = []
        now = datetime.now()
        for t in sorted(types):
            type_rules = [r for r in self._rules.values() if r.enabled and r.entity_type == t]
            min_days = min((r.max_age_days for r in type_rules), default=365)
            schedules.append(RetentionSchedule(
                entity_type=t,
                rules=type_rules,
                next_expiration=(now.isoformat()),
            ))
        return schedules
