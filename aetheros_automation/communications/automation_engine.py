from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class AutomationTrigger(Enum):
    MESSAGE_RECEIVED = "message_received"
    KEYWORD_DETECTED = "keyword_detected"
    SENDER_MATCH = "sender_match"
    SCHEDULE = "schedule"
    NEW_CONVERSATION = "new_conversation"
    ATTACHMENT_RECEIVED = "attachment_received"
    MENTION_DETECTED = "mention_detected"
    PRIORITY_MESSAGE = "priority_message"
    UNREAD_THRESHOLD = "unread_threshold"
    INACTIVITY = "inactivity"


class AutomationAction(Enum):
    SEND_REPLY = "send_reply"
    DRAFT_REPLY = "draft_reply"
    NOTIFY_USER = "notify_user"
    TAG_CONVERSATION = "tag_conversation"
    ARCHIVE_CONVERSATION = "archive_conversation"
    FORWARD_MESSAGE = "forward_message"
    EXTRACT_TASKS = "extract_tasks"
    SUMMARIZE = "summarize"
    CLASSIFY = "classify"
    AUTO_REPLY = "auto_reply"
    WEBHOOK = "webhook"
    RUN_AGENT = "run_agent"


@dataclass
class AutomationRule:
    id: str
    name: str
    provider: str
    trigger: AutomationTrigger
    action: AutomationAction
    trigger_config: dict[str, Any] = field(default_factory=dict)
    action_config: dict[str, Any] = field(default_factory=dict)
    conditions: list[dict] = field(default_factory=list)
    allowed_contacts: list[str] = field(default_factory=list)
    allowed_channels: list[str] = field(default_factory=list)
    time_limits: dict[str, str] = field(default_factory=dict)
    require_approval: bool = True
    enabled: bool = True
    cooldown_seconds: int = 0
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AutomationExecution:
    id: str
    rule_id: str
    rule_name: str
    provider: str
    trigger: str
    status: str
    input_message: str = ""
    output: str = ""
    error: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    required_approval: bool = False
    approved: bool = False
    approved_by: str = ""
    approved_at: Optional[datetime] = None


class MessageAutomationEngine:
    def __init__(self, storage_path: Optional[Path] = None):
        self._storage_path = storage_path or Path.home() / ".aetheros" / "automation" / "communications"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._rules: dict[str, AutomationRule] = {}
        self._executions: list[AutomationExecution] = []
        self._load()

    def _path(self) -> Path:
        return self._storage_path / "automation_rules.json"

    def _exec_path(self) -> Path:
        return self._storage_path / "automation_executions.json"

    def _load(self):
        for path, target in [(self._path(), self._rules), (self._exec_path(), self._executions)]:
            if path.exists():
                try:
                    data = json.loads(path.read_text())
                    for item in data:
                        obj = self._deserialize_rule(item) if target is self._rules else self._deserialize_execution(item)
                        if target is self._rules:
                            target[obj.id] = obj
                        else:
                            target.append(obj)
                except (json.JSONDecodeError, KeyError):
                    pass

    def _save_rules(self):
        data = [self._serialize_rule(r) for r in self._rules.values()]
        self._path().write_text(json.dumps(data, indent=2, default=str))

    def _save_executions(self):
        data = [self._serialize_execution(e) for e in self._executions[-500:]]
        self._exec_path().write_text(json.dumps(data, indent=2, default=str))

    def _serialize_rule(self, rule: AutomationRule) -> dict:
        return {
            "id": rule.id,
            "name": rule.name,
            "provider": rule.provider,
            "trigger": rule.trigger.value,
            "trigger_config": rule.trigger_config,
            "action": rule.action.value,
            "action_config": rule.action_config,
            "conditions": rule.conditions,
            "allowed_contacts": rule.allowed_contacts,
            "allowed_channels": rule.allowed_channels,
            "time_limits": rule.time_limits,
            "require_approval": rule.require_approval,
            "enabled": rule.enabled,
            "cooldown_seconds": rule.cooldown_seconds,
            "last_triggered": rule.last_triggered.isoformat() if rule.last_triggered else None,
            "trigger_count": rule.trigger_count,
            "created_at": rule.created_at.isoformat(),
        }

    def _deserialize_rule(self, data: dict) -> AutomationRule:
        return AutomationRule(
            id=data["id"],
            name=data.get("name", ""),
            provider=data.get("provider", "all"),
            trigger=AutomationTrigger(data["trigger"]),
            trigger_config=data.get("trigger_config", {}),
            action=AutomationAction(data["action"]),
            action_config=data.get("action_config", {}),
            conditions=data.get("conditions", []),
            allowed_contacts=data.get("allowed_contacts", []),
            allowed_channels=data.get("allowed_channels", []),
            time_limits=data.get("time_limits", {}),
            require_approval=data.get("require_approval", True),
            enabled=data.get("enabled", True),
            cooldown_seconds=data.get("cooldown_seconds", 0),
            last_triggered=datetime.fromisoformat(data["last_triggered"]) if data.get("last_triggered") else None,
            trigger_count=data.get("trigger_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    def _serialize_execution(self, ex: AutomationExecution) -> dict:
        return {
            "id": ex.id,
            "rule_id": ex.rule_id,
            "rule_name": ex.rule_name,
            "provider": ex.provider,
            "trigger": ex.trigger,
            "status": ex.status,
            "input_message": ex.input_message,
            "output": ex.output,
            "error": ex.error,
            "started_at": ex.started_at.isoformat(),
            "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
            "required_approval": ex.required_approval,
            "approved": ex.approved,
            "approved_by": ex.approved_by,
            "approved_at": ex.approved_at.isoformat() if ex.approved_at else None,
        }

    def _deserialize_execution(self, data: dict) -> AutomationExecution:
        return AutomationExecution(
            id=data["id"],
            rule_id=data["rule_id"],
            rule_name=data.get("rule_name", ""),
            provider=data.get("provider", ""),
            trigger=data.get("trigger", ""),
            status=data["status"],
            input_message=data.get("input_message", ""),
            output=data.get("output", ""),
            error=data.get("error", ""),
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            required_approval=data.get("required_approval", False),
            approved=data.get("approved", False),
            approved_by=data.get("approved_by", ""),
            approved_at=datetime.fromisoformat(data["approved_at"]) if data.get("approved_at") else None,
        )

    def add_rule(self, rule: AutomationRule):
        self._rules[rule.id] = rule
        self._save_rules()

    def update_rule(self, rule_id: str, **kwargs) -> bool:
        rule = self._rules.get(rule_id)
        if not rule:
            return False
        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        self._save_rules()
        return True

    def remove_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            del self._rules[rule_id]
            self._save_rules()
            return True
        return False

    def get_rule(self, rule_id: str) -> Optional[AutomationRule]:
        return self._rules.get(rule_id)

    def list_rules(self, provider: str = "") -> list[AutomationRule]:
        if provider:
            return [r for r in self._rules.values() if r.provider == provider or r.provider == "all"]
        return list(self._rules.values())

    def evaluate(self, provider: str, message: dict) -> list[AutomationRule]:
        matched = []
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            if rule.provider != "all" and rule.provider != provider:
                continue
            if rule.cooldown_seconds > 0 and rule.last_triggered:
                elapsed = (datetime.now() - rule.last_triggered).total_seconds()
                if elapsed < rule.cooldown_seconds:
                    continue
            if rule.time_limits:
                if not self._check_time_limits(rule.time_limits):
                    continue
            if rule.trigger == AutomationTrigger.KEYWORD_DETECTED:
                keywords = rule.trigger_config.get("keywords", [])
                content = message.get("content", "")
                if not any(k.lower() in content.lower() for k in keywords):
                    continue
            elif rule.trigger == AutomationTrigger.SENDER_MATCH:
                sender_id = message.get("sender_id", "")
                allowed = rule.trigger_config.get("sender_ids", [])
                if sender_id not in allowed:
                    continue
            if rule.allowed_contacts:
                sender_id = message.get("sender_id", "")
                if sender_id not in rule.allowed_contacts:
                    continue
            if rule.conditions:
                if not self._check_conditions(rule.conditions, message):
                    continue
            matched.append(rule)
        return matched

    def _check_time_limits(self, limits: dict) -> bool:
        now = datetime.now()
        if "start_hour" in limits and "end_hour" in limits:
            start = int(limits["start_hour"])
            end = int(limits["end_hour"])
            if not (start <= now.hour < end):
                return False
        if "days_of_week" in limits:
            days = limits["days_of_week"]
            if now.strftime("%A").lower() not in [d.lower() for d in days]:
                return False
        return True

    def _check_conditions(self, conditions: list[dict], message: dict) -> bool:
        for cond in conditions:
            field = cond.get("field", "")
            operator = cond.get("operator", "equals")
            value = cond.get("value", "")
            msg_value = message.get(field, "")
            if operator == "equals" and msg_value != value:
                return False
            elif operator == "contains" and value not in str(msg_value):
                return False
            elif operator == "not_equals" and msg_value == value:
                return False
        return True

    def record_execution(self, rule_id: str, provider: str, trigger: str, status: str, input_msg: str = "", output: str = "", error: str = "", needs_approval: bool = False) -> AutomationExecution:
        rule = self._rules.get(rule_id)
        exec = AutomationExecution(
            id=f"exec_{datetime.now().timestamp()}",
            rule_id=rule_id,
            rule_name=rule.name if rule else "Unknown",
            provider=provider,
            trigger=trigger,
            status=status,
            input_message=input_msg,
            output=output,
            error=error,
            required_approval=needs_approval,
        )
        self._executions.append(exec)
        self._save_executions()
        if rule:
            rule.last_triggered = datetime.now()
            rule.trigger_count += 1
            self._save_rules()
        return exec

    def approve_execution(self, execution_id: str, approved_by: str = "user") -> bool:
        for exec in self._executions:
            if exec.id == execution_id:
                exec.approved = True
                exec.approved_by = approved_by
                exec.approved_at = datetime.now()
                exec.status = "approved"
                self._save_executions()
                return True
        return False

    def deny_execution(self, execution_id: str) -> bool:
        for exec in self._executions:
            if exec.id == execution_id:
                exec.approved = False
                exec.status = "denied"
                self._save_executions()
                return True
        return False

    def get_recent_executions(self, limit: int = 50) -> list[AutomationExecution]:
        return sorted(self._executions, key=lambda e: e.started_at, reverse=True)[:limit]

    def get_pending_approvals(self) -> list[AutomationExecution]:
        return [e for e in self._executions if e.required_approval and not e.approved and e.status != "denied"]
