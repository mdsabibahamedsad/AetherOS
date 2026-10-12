"""AetherOS Integrations — core data model.

Unified types for integrations, providers, credentials, webhooks, events,
scheduled jobs, workflows, and monitoring. One architecture across every
integration category.
"""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class IntegrationCategory(str, enum.Enum):
    MESSAGING = "messaging"
    EMAIL = "email"
    CALENDAR = "calendar"
    STORAGE = "storage"
    DEVOPS = "devops"
    KNOWLEDGE = "knowledge"
    PRODUCTIVITY = "productivity"
    CRM = "crm"
    DATABASE = "database"
    CORE = "core"


class AuthMethod(str, enum.Enum):
    API_KEY = "api_key"
    BEARER = "bearer"
    PAT = "pat"
    JWT = "jwt"
    OAUTH2 = "oauth2"
    OIDC = "oidc"
    BASIC = "basic"
    NONE = "none"


class IntegrationStatus(str, enum.Enum):
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    REMOVED = "removed"


class HealthStatus(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class EventKind(str, enum.Enum):
    WORKSPACE = "workspace"
    AGENT = "agent"
    PROVIDER = "provider"
    TOOL = "tool"
    WORKFLOW = "workflow"
    PLUGIN = "plugin"
    INTEGRATION = "integration"
    WEBHOOK = "webhook"
    SCHEDULER = "scheduler"


@dataclass
class ProviderDefinition:
    key: str
    category: IntegrationCategory
    display_name: str
    description: str = ""
    auth_method: AuthMethod = AuthMethod.OAUTH2
    auth_url: str = ""
    token_url: str = ""
    scopes: List[str] = field(default_factory=list)
    base_url: str = ""
    capabilities: List[str] = field(default_factory=list)
    docs_url: str = ""


@dataclass
class IntegrationInstance:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    provider_key: str = ""
    label: str = ""
    status: IntegrationStatus = IntegrationStatus.INSTALLED
    config: Dict[str, Any] = field(default_factory=dict)
    credentials_ref: str = ""
    scopes: List[str] = field(default_factory=list)
    permissions: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_health: HealthStatus = HealthStatus.UNKNOWN
    last_health_at: float = 0.0
    version: str = "1.0.0"

    def __post_init__(self) -> None:
        if not isinstance(self.status, IntegrationStatus):
            try:
                self.status = IntegrationStatus(self.status)
            except (ValueError, TypeError):
                self.status = IntegrationStatus.INSTALLED
        if not isinstance(self.last_health, HealthStatus):
            try:
                self.last_health = HealthStatus(self.last_health)
            except (ValueError, TypeError):
                self.last_health = HealthStatus.UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "provider_key": self.provider_key,
            "label": self.label,
            "status": self.status.value,
            "config": self.config,
            "credentials_ref": self.credentials_ref,
            "scopes": self.scopes,
            "permissions": self.permissions,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_health": self.last_health.value,
            "last_health_at": self.last_health_at,
            "version": self.version,
        }
        return d


@dataclass
class CredentialEnvelope:
    """Encrypted credential reference stored in the vault.

    ``ciphertext`` is a Fernet token; ``meta`` holds non-secret metadata.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    provider_key: str = ""
    kind: str = "oauth2"  # api_key | bearer | pat | oauth2 | basic | jwt
    ciphertext: bytes = b""
    meta: Dict[str, Any] = field(default_factory=dict)
    scopes: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "provider_key": self.provider_key,
            "kind": self.kind,
            "ciphertext": self.ciphertext.decode("utf-8", "replace"),
            "meta": self.meta,
            "scopes": self.scopes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
        }


@dataclass
class WebhookDelivery:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    direction: str = "incoming"  # incoming | outgoing
    integration_id: str = ""
    event: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    signature_valid: bool = False
    status: str = "pending"  # pending | delivered | failed | replayed | rejected
    attempts: int = 0
    max_attempts: int = 3
    last_error: str = ""
    latency_ms: float = 0.0
    created_at: float = field(default_factory=time.time)
    delivered_at: float = 0.0
    dedup_key: str = ""
    hop_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "direction": self.direction,
            "integration_id": self.integration_id,
            "event": self.event,
            "payload": self.payload,
            "signature_valid": self.signature_valid,
            "status": self.status,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "last_error": self.last_error,
            "latency_ms": self.latency_ms,
            "created_at": self.created_at,
            "delivered_at": self.delivered_at,
            "dedup_key": self.dedup_key,
            "hop_count": self.hop_count,
        }


@dataclass
class EventEnvelope:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    kind: EventKind = EventKind.WORKFLOW
    type: str = ""  # e.g. "email.received"
    source: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    dedup_key: str = ""
    timestamp: float = field(default_factory=time.time)
    delivered_to: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.kind, EventKind):
            try:
                self.kind = EventKind(self.kind)
            except (ValueError, TypeError):
                self.kind = EventKind.WORKFLOW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "type": self.type,
            "source": self.source,
            "data": self.data,
            "dedup_key": self.dedup_key,
            "timestamp": self.timestamp,
            "delivered_to": self.delivered_to,
        }


@dataclass
class ScheduledJob:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    schedule_type: str = "once"  # once | daily | weekly | monthly | cron | event | manual
    cron_expr: str = ""
    timezone: str = "UTC"
    integration_id: str = ""
    action: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    next_run_at: float = 0.0
    last_run_at: float = 0.0
    last_status: str = ""
    run_count: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "schedule_type": self.schedule_type,
            "cron_expr": self.cron_expr,
            "timezone": self.timezone,
            "integration_id": self.integration_id,
            "action": self.action,
            "params": self.params,
            "enabled": self.enabled,
            "next_run_at": self.next_run_at,
            "last_run_at": self.last_run_at,
            "last_status": self.last_status,
            "run_count": self.run_count,
            "created_at": self.created_at,
        }


@dataclass
class WorkflowStep:
    id: str = ""
    type: str = "tool"  # tool | agent | condition | loop | http | script | approval | wait | transform | notify
    name: str = ""
    provider: str = ""
    action: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    next: List[str] = field(default_factory=list)
    condition: Optional[str] = None
    loop_over: str = ""
    branch: Dict[str, Any] = field(default_factory=dict)
    on_error: str = "fail"  # fail | continue | retry

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "provider": self.provider,
            "action": self.action,
            "params": self.params,
            "next": self.next,
            "condition": self.condition,
            "loop_over": self.loop_over,
            "branch": self.branch,
            "on_error": self.on_error,
        }


@dataclass
class WorkflowDefinition:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    trigger: str = ""  # event type or cron expr
    trigger_type: str = "event"  # event | cron | manual | webhook
    steps: List[WorkflowStep] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "trigger": self.trigger,
            "trigger_type": self.trigger_type,
            "steps": [s.to_dict() for s in self.steps],
            "variables": self.variables,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class WorkflowRun:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = ""
    workflow_name: str = ""
    status: str = "running"  # running | success | failed | cancelled | awaiting_approval
    trigger_event_id: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    current_step: str = ""
    step_results: List[Dict[str, Any]] = field(default_factory=list)
    approval_required: bool = False
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status,
            "trigger_event_id": self.trigger_event_id,
            "variables": self.variables,
            "current_step": self.current_step,
            "step_results": self.step_results,
            "approval_required": self.approval_required,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
        }


@dataclass
class MonitorSample:
    integration_id: str = ""
    metric: str = ""  # latency_ms | failure | retry | quota_used | api_error | health
    value: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "integration_id": self.integration_id,
            "metric": self.metric,
            "value": self.value,
            "extra": self.extra,
            "timestamp": self.timestamp,
        }


@dataclass
class OfflineQueueItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    integration_id: str = ""
    action: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    status: str = "queued"  # queued | processing | done | dead
    attempts: int = 0
    max_attempts: int = 5
    last_error: str = ""
    dedup_key: str = ""
    created_at: float = field(default_factory=time.time)
    next_retry_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "integration_id": self.integration_id,
            "action": self.action,
            "payload": self.payload,
            "status": self.status,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "last_error": self.last_error,
            "dedup_key": self.dedup_key,
            "created_at": self.created_at,
            "next_retry_at": self.next_retry_at,
        }


@dataclass
class AuditEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    actor: str = ""
    action: str = ""  # credential.created | credential.rotated | integration.installed | ...
    target: str = ""
    detail: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "actor": self.actor,
            "action": self.action,
            "target": self.target,
            "detail": self.detail,
            "timestamp": self.timestamp,
        }
