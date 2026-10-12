from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ProcessingLevel(str, Enum):
    LOCAL_ONLY = "local_only"
    TRUSTED_PROVIDER = "trusted_provider"
    ANY_ENABLED = "any_enabled"
    NO_EXTERNAL = "no_external"


class DataCategory(str, Enum):
    PERSONAL_INFO = "personal_info"
    WORK_DOCUMENTS = "work_documents"
    MESSAGES = "messages"
    EMAILS = "emails"
    FILES = "files"
    MEMORIES = "memories"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    SEARCH_HISTORY = "search_history"
    AGENT_CONTEXT = "agent_context"
    ALL = "all"


@dataclass
class PrivacyRule:
    id: str
    data_category: DataCategory
    processing_level: ProcessingLevel
    allowed_providers: list[str] = field(default_factory=list)
    require_consent: bool = True
    retention_days: int = 0
    description: str = ""
    enabled: bool = True
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "data_category": self.data_category.value,
            "processing_level": self.processing_level.value,
            "allowed_providers": self.allowed_providers,
            "require_consent": self.require_consent,
            "retention_days": self.retention_days,
            "description": self.description,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PrivacyRule:
        return cls(
            id=data["id"],
            data_category=DataCategory(data["data_category"]),
            processing_level=ProcessingLevel(data["processing_level"]),
            allowed_providers=data.get("allowed_providers", []),
            require_consent=data.get("require_consent", True),
            retention_days=data.get("retention_days", 0),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class PrivacyRuleManager:
    def __init__(self, storage_path: Optional[str] = None):
        self._storage_path = Path(storage_path) if storage_path else Path.cwd() / "privacy_data"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._rules: dict[str, PrivacyRule] = {}
        self._consent_log: list[dict] = []
        self._load()
        if not self._rules:
            self._init_defaults()

    def _path(self) -> Path:
        return self._storage_path / "privacy_rules.json"

    def _consent_path(self) -> Path:
        return self._storage_path / "consent_log.json"

    def _load(self):
        p = self._path()
        if p.exists():
            try:
                data = json.loads(p.read_text("utf-8"))
                for item in data:
                    rule = PrivacyRule.from_dict(item)
                    self._rules[rule.id] = rule
            except (json.JSONDecodeError, KeyError):
                pass
        cp = self._consent_path()
        if cp.exists():
            try:
                self._consent_log = json.loads(cp.read_text("utf-8"))
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        self._path().write_text(
            json.dumps([r.to_dict() for r in self._rules.values()], indent=2, default=str), "utf-8")
        self._consent_path().write_text(
            json.dumps(self._consent_log[-1000:], indent=2, default=str), "utf-8")

    def _init_defaults(self):
        defaults = [
            PrivacyRule(id="rule_personal_info", data_category=DataCategory.PERSONAL_INFO,
                        processing_level=ProcessingLevel.LOCAL_ONLY, require_consent=True,
                        description="Personal information must not be sent to external providers"),
            PrivacyRule(id="rule_messages", data_category=DataCategory.MESSAGES,
                        processing_level=ProcessingLevel.TRUSTED_PROVIDER, require_consent=True,
                        description="Messages may be processed by trusted providers with consent"),
            PrivacyRule(id="rule_emails", data_category=DataCategory.EMAILS,
                        processing_level=ProcessingLevel.TRUSTED_PROVIDER, require_consent=True,
                        description="Emails may be processed by trusted providers with consent"),
            PrivacyRule(id="rule_work_docs", data_category=DataCategory.WORK_DOCUMENTS,
                        processing_level=ProcessingLevel.ANY_ENABLED, require_consent=False,
                        description="Work documents may use any enabled provider"),
            PrivacyRule(id="rule_files", data_category=DataCategory.FILES,
                        processing_level=ProcessingLevel.ANY_ENABLED, require_consent=False,
                        description="Files may use any enabled provider"),
            PrivacyRule(id="rule_memories", data_category=DataCategory.MEMORIES,
                        processing_level=ProcessingLevel.TRUSTED_PROVIDER, require_consent=True,
                        description="Memories require trusted provider and consent"),
            PrivacyRule(id="rule_knowledge_graph", data_category=DataCategory.KNOWLEDGE_GRAPH,
                        processing_level=ProcessingLevel.LOCAL_ONLY, require_consent=True,
                        description="Knowledge graph data stays local"),
            PrivacyRule(id="rule_agent_context", data_category=DataCategory.AGENT_CONTEXT,
                        processing_level=ProcessingLevel.TRUSTED_PROVIDER, require_consent=True,
                        description="Agent context requires trusted provider and consent"),
        ]
        for rule in defaults:
            self._rules[rule.id] = rule
        self._save()

    def _generate_id(self) -> str:
        import uuid
        return f"rule_{uuid.uuid4().hex[:8]}"

    def add_rule(self, data_category: DataCategory, processing_level: ProcessingLevel,
                 allowed_providers: list[str] | None = None,
                 require_consent: bool = True, retention_days: int = 0,
                 description: str = "") -> PrivacyRule:
        now = datetime.now().isoformat()
        rule = PrivacyRule(
            id=self._generate_id(),
            data_category=data_category,
            processing_level=processing_level,
            allowed_providers=allowed_providers or [],
            require_consent=require_consent,
            retention_days=retention_days,
            description=description,
            enabled=True,
            created_at=now,
            updated_at=now,
        )
        self._rules[rule.id] = rule
        self._save()
        return rule

    def update_rule(self, rule_id: str, **updates) -> Optional[PrivacyRule]:
        rule = self._rules.get(rule_id)
        if not rule:
            return None
        for key, value in updates.items():
            if hasattr(rule, key) and key != "id":
                if key == "data_category":
                    setattr(rule, key, DataCategory(value) if isinstance(value, str) else value)
                elif key == "processing_level":
                    setattr(rule, key, ProcessingLevel(value) if isinstance(value, str) else value)
                else:
                    setattr(rule, key, value)
        rule.updated_at = datetime.now().isoformat()
        self._save()
        return rule

    def remove_rule(self, rule_id: str) -> bool:
        if rule_id not in self._rules:
            return False
        del self._rules[rule_id]
        self._save()
        return True

    def get_rules(self, category: Optional[DataCategory] = None) -> list[PrivacyRule]:
        results = list(self._rules.values())
        if category:
            results = [r for r in results if r.data_category == category]
        return results

    def check_processing_allowed(self, data_category: DataCategory, provider: str = "") -> tuple[bool, str]:
        relevant = [r for r in self._rules.values() if r.enabled and r.data_category in (data_category, DataCategory.ALL)]
        if not relevant:
            relevant = [r for r in self._rules.values() if r.enabled and r.data_category == DataCategory.ALL]
        if not relevant:
            return True, "No matching rule, processing allowed by default"
        for rule in relevant:
            if rule.processing_level == ProcessingLevel.LOCAL_ONLY:
                return False, f"Local only: {rule.description}"
            if rule.processing_level == ProcessingLevel.TRUSTED_PROVIDER:
                if provider and rule.allowed_providers and provider not in rule.allowed_providers:
                    return False, f"Provider '{provider}' not in trusted list for {rule.description}"
            if rule.processing_level == ProcessingLevel.NO_EXTERNAL:
                return False, f"No external processing: {rule.description}"
        return True, "Processing allowed"

    def requires_consent(self, data_category: DataCategory) -> bool:
        return any(r.enabled and r.require_consent and r.data_category == data_category for r in self._rules.values())

    def log_consent(self, data_category: DataCategory, provider: str, granted: bool,
                    user_id: str = "", reason: str = ""):
        self._consent_log.append({
            "data_category": data_category.value,
            "provider": provider,
            "granted": granted,
            "user_id": user_id,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        })
        self._save()

    def get_consent_history(self, limit: int = 100) -> list[dict]:
        return sorted(self._consent_log, key=lambda x: x["timestamp"], reverse=True)[:limit]

    def get_summary(self) -> dict:
        return {
            "total_rules": len(self._rules),
            "enabled_rules": sum(1 for r in self._rules.values() if r.enabled),
            "local_only_count": sum(1 for r in self._rules.values() if r.processing_level == ProcessingLevel.LOCAL_ONLY),
            "trusted_provider_count": sum(1 for r in self._rules.values() if r.processing_level == ProcessingLevel.TRUSTED_PROVIDER),
            "any_enabled_count": sum(1 for r in self._rules.values() if r.processing_level == ProcessingLevel.ANY_ENABLED),
            "no_external_count": sum(1 for r in self._rules.values() if r.processing_level == ProcessingLevel.NO_EXTERNAL),
        }
