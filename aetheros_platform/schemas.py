"""Canonical schemas — single source of truth (Master 62 §6, §47).

Every public object has a JSON Schema here. Python dataclasses mirror them.
TypeScript types are GENERATED from this module (`tsgen.py`), never
hand-duplicated. Validation uses `jsonschema` (Draft 2020-12).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "1.0.0"

AGENT_STATES = ("REGISTERED", "CREATED", "READY", "RUNNING", "WAITING",
                "PAUSED", "COMPLETED", "FAILED", "CANCELLED", "QUARANTINED",
                "TERMINATED")

TASK_STATES = ("PENDING", "RUNNING", "WAITING_APPROVAL", "PAUSED",
               "COMPLETED", "FAILED", "CANCELLED")

RISK_LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")

STABILITY = ("PUBLIC", "INTERNAL", "EXPERIMENTAL", "DEPRECATED", "PRIVATE", "UNSTABLE")


def _obj(required: List[str], props: Dict[str, Any],
         additional: bool = False) -> Dict[str, Any]:
    return {"type": "object", "required": required, "properties": props,
            "additionalProperties": additional,
            "$schema": "https://json-schema.org/draft/2020-12/schema"}


SCHEMAS: Dict[str, Dict[str, Any]] = {}

SCHEMAS["Agent"] = _obj(["name", "version"], {
    "name": {"type": "string", "minLength": 1, "maxLength": 64,
             "pattern": "^[a-z0-9][a-z0-9-_]*$"},
    "version": {"type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"},
    "description": {"type": "string", "maxLength": 500},
    "capabilities": {"type": "array", "items": {"type": "string"}, "maxItems": 64},
    "inputs": {"type": "object"}, "outputs": {"type": "object"},
    "tools": {"type": "array", "items": {"type": "string"}},
    "skills": {"type": "array", "items": {"type": "string"}},
    "models": {"type": "object"},
    "memoryPolicy": {"type": "object"}, "artifactPolicy": {"type": "object"},
    "networkPolicy": {"type": "object"}, "filesystemPolicy": {"type": "object"},
    "dataPolicy": {"type": "object"}, "approvalPolicy": {"type": "object"},
    "resourceLimits": {"type": "object"},
    "tenant": {"type": "object"},
})

SCHEMAS["AgentTask"] = _obj(["agent", "input"], {
    "agent": {"type": "string"}, "input": {"type": "object"},
    "idempotencyKey": {"type": "string", "maxLength": 128},
    "model": {"type": "object"}, "tenant": {"type": "object"},
})

SCHEMAS["AgentResult"] = _obj(["taskId", "state"], {
    "taskId": {"type": "string"}, "state": {"type": "string", "enum": list(TASK_STATES)},
    "output": {"type": "object"}, "artifacts": {"type": "array", "items": {"type": "string"}},
    "usage": {"type": "object"},
})

SCHEMAS["Tool"] = _obj(["name", "version", "inputSchema"], {
    "name": {"type": "string", "pattern": "^[a-z0-9][a-z0-9-_./]*$"},
    "version": {"type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"},
    "description": {"type": "string", "maxLength": 1000},
    "inputSchema": {"type": "object"}, "outputSchema": {"type": "object"},
    "capabilities": {"type": "array", "items": {"type": "string"}},
    "riskLevel": {"type": "string", "enum": list(RISK_LEVELS)},
    "sideEffects": {"type": "array", "items": {"type": "string"}},
    "idempotent": {"type": "boolean"},
    "safety": {"type": "object", "properties": {
        "readsData": {"type": "boolean"}, "writesData": {"type": "boolean"},
        "deletesData": {"type": "boolean"}, "sendsMessages": {"type": "boolean"},
        "executesCode": {"type": "boolean"}, "accessesNetwork": {"type": "boolean"},
        "accessesCredentials": {"type": "boolean"}, "modifiesExternal": {"type": "boolean"},
        "financialLegalPhysical": {"type": "boolean"}, "reversible": {"type": "boolean"},
        "idempotent": {"type": "boolean"}}},
    "timeoutSeconds": {"type": "number", "minimum": 1, "maximum": 3600},
})

SCHEMAS["Skill"] = _obj(["name", "version"], {
    "name": {"type": "string", "pattern": "^[a-z0-9][a-z0-9-_]*$"},
    "version": {"type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"},
    "description": {"type": "string", "maxLength": 500},
    "inputs": {"type": "object"}, "outputs": {"type": "object"},
    "capabilities": {"type": "array", "items": {"type": "string"}},
    "dependencies": {"type": "object"},
    "tools": {"type": "array", "items": {"type": "string"}},
    "policies": {"type": "object"},
})

SCHEMAS["AgentCard"] = _obj(["name", "version", "protocolVersion", "capabilities"], {
    "name": {"type": "string", "minLength": 1},
    "version": {"type": "string"},
    "protocolVersion": {"type": "string"},
    "description": {"type": "string", "maxLength": 1000},
    "capabilities": {"type": "array", "items": {"type": "string"}},
    "endpoint": {"type": "string", "maxLength": 500},
    "authentication": {"type": "object"},
    "trust": {"type": "string", "enum": ["untrusted", "known", "trusted"]},
})

SCHEMAS["MCPServer"] = _obj(["name", "version", "transport"], {
    "name": {"type": "string", "pattern": "^[a-z0-9][a-z0-9-_]*$"},
    "version": {"type": "string"},
    "transport": {"type": "string", "enum": ["stdio", "sse", "streamable-http"]},
    "command": {"type": "string"}, "tools": {"type": "array", "items": {"type": "string"}},
})

SCHEMAS["Automation"] = _obj(["name", "trigger"], {
    "name": {"type": "string", "minLength": 1},
    "trigger": {"type": "object"}, "actions": {"type": "array"},
    "enabled": {"type": "boolean"},
})

SCHEMAS["MemoryRecord"] = _obj(["content"], {
    "content": {"type": "string", "minLength": 1, "maxLength": 20000},
    "scope": {"type": "string"}, "sensitivity": {"type": "string"},
})

SCHEMAS["Artifact"] = _obj(["artifactId", "hash"], {
    "artifactId": {"type": "string"}, "hash": {"type": "string"},
    "type": {"type": "string"}, "size": {"type": "integer", "minimum": 0},
    "creator": {"type": "string"}, "taskId": {"type": "string"},
    "provenance": {"type": "object"}, "securityClassification": {"type": "string"},
    "parentArtifacts": {"type": "array", "items": {"type": "string"}},
})

SCHEMAS["APIKey"] = _obj(["name"], {
    "name": {"type": "string", "minLength": 1},
    "scopes": {"type": "array", "items": {"type": "string"}},
    "expiresInDays": {"type": "integer", "minimum": 1, "maximum": 365},
})

SCHEMAS["Webhook"] = _obj(["url", "events"], {
    "url": {"type": "string", "pattern": "^https?://"},
    "events": {"type": "array", "items": {"type": "string"}, "minItems": 1},
})

SCHEMAS["Package"] = _obj(["name", "version", "kind"], {
    "name": {"type": "string"}, "version": {"type": "string"},
    "kind": {"type": "string",
             "enum": ["agent", "skill", "tool", "extension", "mcp"]},
    "aetherosVersion": {"type": "string"},
})

SCHEMAS["AgentEvent"] = _obj(["type"], {
    "type": {"type": "string", "enum": [
        "AgentStarted", "AgentCompleted", "TaskCreated", "TaskUpdated",
        "ToolInvoked", "ToolCompleted", "ApprovalRequested", "ApprovalResolved",
        "MemoryWritten", "ResearchEvidenceAdded", "ArtifactCreated",
        "AutomationTriggered", "PolicyDenied", "SecurityAlert",
        "ModelInvocation", "MCPRequest", "A2ARequest"]},
    "eventId": {"type": "string"}, "timestamp": {"type": "number"},
    "source": {"type": "string"}, "task": {"type": "string"},
    "agent": {"type": "string"}, "correlationId": {"type": "string"},
    "causationId": {"type": "string"}, "schemaVersion": {"type": "string"},
    "payload": {"type": "object"},
    "securityClassification": {"type": "string",
                               "enum": ["public", "internal", "confidential"]},
})

SCHEMAS["Capability"] = _obj(["name"], {
    "name": {"type": "string", "pattern": "^[a-z0-9]+\\.[a-z0-9_]+$"},
    "risk": {"type": "string", "enum": list(RISK_LEVELS)},
    "description": {"type": "string", "maxLength": 500},
})

SCHEMAS["Intent"] = _obj(["capability"], {
    "capability": {"type": "string"}, "actor": {"type": "string"},
    "args": {"type": "object"}, "grants": {"type": "array",
                                           "items": {"type": "string"}},
    "idempotencyKey": {"type": "string", "maxLength": 128},
    "prompt_context": {"type": "string", "maxLength": 20000},
    "side_effects_irreversible": {"type": "boolean"},
})

SCHEMAS["Policy"] = _obj(["effect"], {
    "effect": {"type": "string", "enum": ["allow", "deny", "require_approval",
                                          "require_sandbox",
                                          "require_credential"]},
    "capabilities": {"type": "array", "items": {"type": "string"}},
    "principals": {"type": "array", "items": {"type": "string"}},
    "conditions": {"type": "object"},
})

SCHEMAS["Approval"] = _obj(["requestId", "intent"], {
    "requestId": {"type": "string"}, "intent": {"type": "object"},
    "status": {"type": "string", "enum": ["pending", "approved", "denied",
                                          "cancelled", "expired"]},
    "requestedBy": {"type": "string"}, "resolvedBy": {"type": "string"},
    "resolvedAt": {"type": "number"},
})

SCHEMAS["ResearchTask"] = _obj(["query"], {
    "query": {"type": "string", "minLength": 1, "maxLength": 2000},
    "depth": {"type": "string", "enum": ["quick", "standard", "deep"]},
    "maxSources": {"type": "integer", "minimum": 1, "maximum": 100},
})

SCHEMAS["ResearchEvidence"] = _obj(["url", "excerpt"], {
    "url": {"type": "string", "maxLength": 2000},
    "title": {"type": "string", "maxLength": 500},
    "excerpt": {"type": "string", "maxLength": 5000},
    "retrievedAt": {"type": "number"}, "sourceRank": {"type": "integer"},
})

SCHEMAS["Model"] = _obj(["name"], {
    "name": {"type": "string", "minLength": 1},
    "provider": {"type": "string"}, "contextLength": {"type": "integer"},
    "supportsStreaming": {"type": "boolean"},
    "supportsTools": {"type": "boolean"},
    "supportsVision": {"type": "boolean"},
    "supportsStructuredOutput": {"type": "boolean"},
})

SCHEMAS["MCPTool"] = _obj(["name", "inputSchema"], {
    "name": {"type": "string", "minLength": 1, "maxLength": 200},
    "description": {"type": "string", "maxLength": 2000},
    "inputSchema": {"type": "object"},
    "server": {"type": "string"},
    "trust": {"type": "string", "enum": ["untrusted", "known", "trusted"]},
})

SCHEMAS["CredentialReference"] = _obj(["reference"], {
    "reference": {"type": "string", "pattern": "^cred://[A-Za-z0-9/_-]+$"},
    "scope": {"type": "string"},
})

SCHEMAS["User"] = _obj(["userId"], {
    "userId": {"type": "string", "minLength": 1},
    "displayName": {"type": "string", "maxLength": 200},
    "organization": {"type": "string"}, "workspace": {"type": "string"},
})

SCHEMAS["Workspace"] = _obj(["workspace"], {
    "organization": {"type": "string"}, "workspace": {"type": "string"},
})

SCHEMAS["Project"] = _obj(["name"], {
    "name": {"type": "string", "minLength": 1, "maxLength": 100},
    "workspace": {"type": "string"}, "description": {"type": "string"},
})

SCHEMAS["Device"] = _obj(["deviceId"], {
    "deviceId": {"type": "string", "minLength": 1},
    "kind": {"type": "string"}, "owner": {"type": "string"},
})

SCHEMAS["Session"] = _obj(["sessionId"], {
    "sessionId": {"type": "string", "minLength": 1},
    "agent": {"type": "string"}, "state": {"type": "string"},
    "createdAt": {"type": "number"},
})

SCHEMAS["Error"] = _obj(["category", "message"], {
    "category": {"type": "string"}, "message": {"type": "string"},
    "code": {"type": "string"}, "retryable": {"type": "boolean"},
    "requestId": {"type": "string"}, "remediation": {"type": "string"},
})

SCHEMAS["Trace"] = _obj(["traceId", "spans"], {
    "traceId": {"type": "string"}, "spans": {"type": "array"},
    "taskId": {"type": "string"}, "agent": {"type": "string"},
})

SCHEMAS["Usage"] = _obj(["actor", "timestamp"], {
    "actor": {"type": "string"}, "workspace": {"type": "string"},
    "model": {"type": "string"}, "tokens": {"type": "integer", "minimum": 0},
    "toolCalls": {"type": "integer", "minimum": 0},
    "runtime_s": {"type": "number", "minimum": 0},
    "timestamp": {"type": "number"},
})

SCHEMAS["Quota"] = _obj(["scope", "limit"], {
    "scope": {"type": "string"}, "resource": {"type": "string"},
    "limit": {"type": "number"}, "used": {"type": "number"},
    "window_s": {"type": "number"},
})

SCHEMAS["Extension"] = _obj(["name", "version", "entrypoint"], {
    "name": {"type": "string", "pattern": "^[a-z0-9][a-z0-9-_]*$"},
    "version": {"type": "string",
                "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"},
    "entrypoint": {"type": "string", "maxLength": 500},
    "permissions": {"type": "array", "items": {"type": "string"}},
    "dependencies": {"type": "object"},
})


def validate(schema_name: str, payload: Dict[str, Any]) -> List[str]:
    """Return a list of validation error strings (empty = valid)."""
    import jsonschema
    schema = SCHEMAS.get(schema_name)
    if schema is None:
        return [f"unknown schema {schema_name}"]
    try:
        jsonschema.validate(payload, schema)
    except jsonschema.ValidationError as exc:
        return [f"{'/'.join(str(p) for p in exc.absolute_path)}: {exc.message}"[:300]]
    return []


# -- Python mirrors (typed dataclasses for SDK/runtime use) ------------------

@dataclass
class AgentManifest:
    name: str
    version: str
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    models: Dict[str, Any] = field(default_factory=dict)
    resourceLimits: Dict[str, Any] = field(default_factory=dict)
    approvalPolicy: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ToolManifest:
    name: str
    version: str
    description: str = ""
    inputSchema: Dict[str, Any] = field(default_factory=dict)
    outputSchema: Dict[str, Any] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    riskLevel: str = "LOW"
    sideEffects: List[str] = field(default_factory=list)
    idempotent: bool = False
    timeoutSeconds: float = 60.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def schema_json() -> str:
    return json.dumps({"schemaVersion": SCHEMA_VERSION, "schemas": SCHEMAS}, indent=2)
