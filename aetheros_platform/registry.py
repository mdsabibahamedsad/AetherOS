"""Machine-readable public API boundary (Master 62 §4-5).

Stability: PUBLIC | INTERNAL | EXPERIMENTAL | DEPRECATED | PRIVATE | UNSTABLE.
Internal classes are never exposed merely because they exist — every entry
here is an explicit allow-list.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

REGISTRY_VERSION = "1.0.0"


def _ep(path: str, version: str, stability: str, auth: str,
         scopes: List[str], rate: str, inp: str, out: str,
         streaming: bool = False, idempotent: bool = False,
         audit: str = "standard", deprecated: Optional[str] = None,
         sunset: Optional[str] = None) -> Dict[str, Any]:
    return {"endpoint": path, "version": version, "stability": stability,
            "authentication": auth, "authorization": "scope",
            "scopes": scopes, "rateLimit": rate, "inputSchema": inp,
            "outputSchema": out, "streaming": streaming,
            "idempotency": idempotent, "auditPolicy": audit,
            "dataClassification": "user-controlled",
            "deprecationPolicy": {"deprecated": deprecated, "sunset": sunset}}


# (method, path, entry) — the gateway builds routes from this table.
ENDPOINTS: List[Dict[str, Any]] = []

for _m, _p, _e in [
    ("POST", "/api/v1/agents", _ep("/api/v1/agents", "v1", "PUBLIC", "api-key",
                                   ["agents:write"], "agent", "Agent", "Agent", False, True)),
    ("GET", "/api/v1/agents", _ep("/api/v1/agents", "v1", "PUBLIC", "api-key",
                                  ["agents:read"], "standard", "", "", False, False)),
    ("GET", "/api/v1/agents/{id}", _ep("/api/v1/agents/{id}", "v1", "PUBLIC", "api-key",
                                       ["agents:read"], "standard", "", "Agent", False, False)),
    ("POST", "/api/v1/tasks", _ep("/api/v1/tasks", "v1", "PUBLIC", "api-key",
                                  ["tasks:write"], "task", "AgentTask", "AgentResult", False, True)),
    ("GET", "/api/v1/tasks/{id}", _ep("/api/v1/tasks/{id}", "v1", "PUBLIC", "api-key",
                                      ["tasks:read"], "standard", "", "AgentResult", False, False)),
    ("POST", "/api/v1/tasks/{id}/cancel", _ep("/api/v1/tasks/{id}/cancel", "v1", "PUBLIC",
                                              "api-key", ["tasks:write"], "task", "", "", False, True)),
    ("GET", "/api/v1/tasks/{id}/events", _ep("/api/v1/tasks/{id}/events", "v1", "PUBLIC",
                                             "api-key", ["tasks:read"], "standard", "", "AgentEvent",
                                             True, False)),
    ("POST", "/api/v1/tools", _ep("/api/v1/tools", "v1", "PUBLIC", "api-key",
                                  ["tools:write"], "tool", "Tool", "Tool", False, True)),
    ("GET", "/api/v1/tools", _ep("/api/v1/tools", "v1", "PUBLIC", "api-key",
                                 ["tools:read"], "standard", "", "", False, False)),
    ("POST", "/api/v1/tools/{id}/invoke", _ep("/api/v1/tools/{id}/invoke", "v1", "PUBLIC",
                                              "api-key", ["tools:invoke"], "tool-invoke",
                                              "Intent", "AgentResult", False, True, "full")),
    ("POST", "/api/v1/skills", _ep("/api/v1/skills", "v1", "PUBLIC", "api-key",
                                   ["skills:write"], "standard", "Skill", "Skill", False, True)),
    ("GET", "/api/v1/skills", _ep("/api/v1/skills", "v1", "PUBLIC", "api-key",
                                  ["skills:read"], "standard", "", "", False, False)),
    ("POST", "/api/v1/memory/records", _ep("/api/v1/memory/records", "v1", "PUBLIC",
                                           "api-key", ["memory:write"], "memory",
                                           "MemoryRecord", "MemoryRecord", False, True)),
    ("GET", "/api/v1/memory/search", _ep("/api/v1/memory/search", "v1", "PUBLIC",
                                         "api-key", ["memory:read"], "memory", "", "", False, False)),
    ("POST", "/api/v1/artifacts", _ep("/api/v1/artifacts", "v1", "PUBLIC", "api-key",
                                      ["artifacts:write"], "standard", "", "Artifact", False, True)),
    ("GET", "/api/v1/artifacts/{id}", _ep("/api/v1/artifacts/{id}", "v1", "PUBLIC",
                                          "api-key", ["artifacts:read"], "standard", "", "Artifact",
                                          False, False)),
    ("POST", "/api/v1/automations", _ep("/api/v1/automations", "v1", "PUBLIC", "api-key",
                                        ["automations:write"], "standard", "Automation", "Automation",
                                        False, True)),
    ("POST", "/api/v1/webhooks", _ep("/api/v1/webhooks", "v1", "PUBLIC", "api-key",
                                     ["webhooks:write"], "standard", "Webhook", "Webhook", False, True)),
    ("GET", "/api/v1/registry", _ep("/api/v1/registry", "v1", "PUBLIC", "none",
                                    [], "standard", "", "", False, False)),
    ("GET", "/api/v1/schemas", _ep("/api/v1/schemas", "v1", "PUBLIC", "none",
                                   [], "standard", "", "", False, False)),
    ("GET", "/api/v1/health", _ep("/api/v1/health", "v1", "PUBLIC", "none",
                                  [], "standard", "", "", False, False)),
    ("POST", "/api/v1/a2a/tasks", _ep("/api/v1/a2a/tasks", "v1", "EXPERIMENTAL",
                                      "api-key", ["a2a:write"], "standard", "", "", False, True)),
    ("GET", "/api/v1/a2a/card", _ep("/api/v1/a2a/card", "v1", "EXPERIMENTAL", "none",
                                    [], "standard", "", "AgentCard", False, False)),
]:
    ENDPOINTS.append({"method": _m, **_e})

# /api/v2: same contract, served with deprecation-interop headers. New clients
# use v1; v2 exists for version-negotiation tests (§5, §71).
V2_ALIAS = {"version": "v2", "stability": "PUBLIC",
            "note": "v2 alias of v1 in platform 1.0; sunset only with 6-month notice"}


def public_endpoints() -> List[Dict[str, Any]]:
    return [e for e in ENDPOINTS if e["stability"] in ("PUBLIC", "EXPERIMENTAL")]
