"""Canonical extension model (Master 44 sections 3-4, 66).

ExtensionManifest with strict fail-closed validation. 14 explicit types.
API versioning: ExtensionAPI v1 (+ capability/permission/MCP/skill/tool/UI
v1 markers). Invalid manifests fail closed with reasons.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

EXTENSION_API_VERSION = "1"
CAPABILITY_API_VERSION = "1"
PERMISSION_API_VERSION = "1"
MCP_API_VERSION = "1"
SKILL_API_VERSION = "1"
TOOL_API_VERSION = "1"
UI_API_VERSION = "1"

ENGINE_VERSION = "44"


class ExtensionType(str, enum.Enum):
    SKILL = "skill"
    TOOL_PACK = "tool_pack"
    MCP_SERVER = "mcp_server"
    MCP_TOOL_PROVIDER = "mcp_tool_provider"
    AGENT = "agent"
    MODEL_PROVIDER = "model_provider"
    BROWSER = "browser"
    COMPUTER = "computer"
    RESEARCH = "research"
    AUTOMATION = "automation"
    MEMORY_PROVIDER = "memory_provider"
    UI = "ui"
    INTEGRATION = "integration"
    WORKFLOW_COMPONENT = "workflow_component"


class LifecycleState(str, enum.Enum):
    DISCOVERED = "discovered"
    VALIDATING = "validating"
    VERIFIED = "verified"
    TRUST_PENDING = "trust_pending"
    PERMISSION_PENDING = "permission_pending"
    INSTALLING = "installing"
    INSTALLED = "installed"
    ENABLED = "enabled"
    RUNNING = "running"
    DISABLED = "disabled"
    UPDATING = "updating"
    ROLLED_BACK = "rolled_back"
    UNINSTALLED = "uninstalled"
    QUARANTINED = "quarantined"
    INSTALL_FAILED = "install_failed"
    VALIDATION_FAILED = "validation_failed"
    SIGNATURE_FAILED = "signature_failed"
    COMPATIBILITY_FAILED = "compatibility_failed"
    PERMISSION_DENIED = "permission_denied"
    SECURITY_BLOCKED = "security_blocked"
    RUNTIME_FAILED = "runtime_failed"


TERMINAL_FAILURE = frozenset({
    LifecycleState.INSTALL_FAILED, LifecycleState.VALIDATION_FAILED,
    LifecycleState.SIGNATURE_FAILED, LifecycleState.COMPATIBILITY_FAILED,
    LifecycleState.PERMISSION_DENIED, LifecycleState.SECURITY_BLOCKED,
    LifecycleState.RUNTIME_FAILED,
})

# Allowed transitions (fail-closed state machine).
_TRANSITIONS: Dict[LifecycleState, frozenset] = {
    LifecycleState.DISCOVERED: frozenset({LifecycleState.VALIDATING, LifecycleState.UNINSTALLED}),
    LifecycleState.VALIDATING: frozenset({LifecycleState.VERIFIED, LifecycleState.VALIDATION_FAILED,
                                          LifecycleState.SIGNATURE_FAILED, LifecycleState.COMPATIBILITY_FAILED,
                                          LifecycleState.SECURITY_BLOCKED, LifecycleState.QUARANTINED}),
    LifecycleState.VERIFIED: frozenset({LifecycleState.TRUST_PENDING, LifecycleState.QUARANTINED}),
    LifecycleState.TRUST_PENDING: frozenset({LifecycleState.PERMISSION_PENDING, LifecycleState.PERMISSION_DENIED,
                                             LifecycleState.QUARANTINED, LifecycleState.UNINSTALLED}),
    LifecycleState.PERMISSION_PENDING: frozenset({LifecycleState.INSTALLING, LifecycleState.PERMISSION_DENIED,
                                                  LifecycleState.QUARANTINED, LifecycleState.UNINSTALLED}),
    LifecycleState.INSTALLING: frozenset({LifecycleState.INSTALLED, LifecycleState.INSTALL_FAILED,
                                          LifecycleState.QUARANTINED}),
    LifecycleState.INSTALLED: frozenset({LifecycleState.ENABLED, LifecycleState.DISABLED,
                                         LifecycleState.UPDATING, LifecycleState.UNINSTALLED,
                                         LifecycleState.QUARANTINED}),
    LifecycleState.ENABLED: frozenset({LifecycleState.RUNNING, LifecycleState.DISABLED,
                                       LifecycleState.UPDATING, LifecycleState.UNINSTALLED,
                                       LifecycleState.QUARANTINED}),
    LifecycleState.RUNNING: frozenset({LifecycleState.DISABLED, LifecycleState.UPDATING,
                                       LifecycleState.UNINSTALLED, LifecycleState.QUARANTINED,
                                       LifecycleState.RUNTIME_FAILED, LifecycleState.ENABLED}),
    LifecycleState.DISABLED: frozenset({LifecycleState.ENABLED, LifecycleState.UNINSTALLED,
                                        LifecycleState.UPDATING, LifecycleState.QUARANTINED}),
    LifecycleState.UPDATING: frozenset({LifecycleState.ENABLED, LifecycleState.ROLLED_BACK,
                                        LifecycleState.INSTALL_FAILED, LifecycleState.QUARANTINED}),
    LifecycleState.ROLLED_BACK: frozenset({LifecycleState.ENABLED, LifecycleState.DISABLED,
                                           LifecycleState.UNINSTALLED}),
    LifecycleState.QUARANTINED: frozenset({LifecycleState.DISABLED, LifecycleState.UNINSTALLED}),
    LifecycleState.UNINSTALLED: frozenset(),
    LifecycleState.INSTALL_FAILED: frozenset({LifecycleState.DISCOVERED, LifecycleState.UNINSTALLED}),
    LifecycleState.VALIDATION_FAILED: frozenset({LifecycleState.DISCOVERED, LifecycleState.UNINSTALLED}),
    LifecycleState.SIGNATURE_FAILED: frozenset({LifecycleState.DISCOVERED, LifecycleState.UNINSTALLED}),
    LifecycleState.COMPATIBILITY_FAILED: frozenset({LifecycleState.DISCOVERED, LifecycleState.UNINSTALLED}),
    LifecycleState.PERMISSION_DENIED: frozenset({LifecycleState.DISCOVERED, LifecycleState.UNINSTALLED}),
    LifecycleState.SECURITY_BLOCKED: frozenset({LifecycleState.QUARANTINED, LifecycleState.UNINSTALLED}),
    LifecycleState.RUNTIME_FAILED: frozenset({LifecycleState.DISABLED, LifecycleState.QUARANTINED,
                                              LifecycleState.UNINSTALLED}),
}


def can_transition(frm: LifecycleState, to: LifecycleState) -> bool:
    return to in _TRANSITIONS.get(frm, frozenset())


_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,127}$")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+([-+][0-9A-Za-z.-]+)?$")


@dataclass
class ExtensionManifest:
    id: str = ""
    name: str = ""
    display_name: str = ""
    version: str = ""
    description: str = ""
    publisher: str = ""
    publisher_id: str = ""
    homepage: str = ""
    repository: str = ""
    license: str = ""
    icon: str = ""
    categories: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    engine_version: str = ""
    api_version: str = "1"
    extension_type: ExtensionType = ExtensionType.SKILL
    platforms: List[str] = field(default_factory=list)
    architectures: List[str] = field(default_factory=list)
    dependencies: Dict[str, str] = field(default_factory=dict)
    optional_dependencies: Dict[str, str] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    permissions: List[Any] = field(default_factory=list)
    entrypoints: Dict[str, str] = field(default_factory=dict)
    tools: List[Dict[str, Any]] = field(default_factory=list)
    skills: List[Dict[str, Any]] = field(default_factory=list)
    mcp_servers: List[Dict[str, Any]] = field(default_factory=list)
    agents: List[Dict[str, Any]] = field(default_factory=list)
    workflows: List[Dict[str, Any]] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    commands: List[Dict[str, Any]] = field(default_factory=list)
    events: List[str] = field(default_factory=list)
    network: Dict[str, Any] = field(default_factory=dict)
    filesystem: Dict[str, Any] = field(default_factory=dict)
    secrets: List[str] = field(default_factory=list)
    update_policy: str = "manual"

    def validate(self) -> List[str]:
        """Fail-closed validation: non-empty list == invalid."""
        problems: List[str] = []
        if not _ID_RE.match(self.id or ""):
            problems.append("id must match [a-z0-9._-]{2,128}")
        if not (self.name or "").strip():
            problems.append("name is required")
        if not _VERSION_RE.match(self.version or ""):
            problems.append("version must be semver x.y.z")
        if not (self.publisher_id or "").strip():
            problems.append("publisher_id is required")
        try:
            ExtensionType(self.extension_type)
        except ValueError:
            problems.append(f"unknown extension type: {self.extension_type}")
        if self.api_version != "1":
            problems.append(f"unsupported api_version: {self.api_version}")
        for dep, spec in {**self.dependencies, **self.optional_dependencies}.items():
            if not dep or not isinstance(spec, str) or not spec.strip():
                problems.append(f"bad dependency pin: {dep}")
        for perm in self.permissions:
            if isinstance(perm, str):
                if not perm.strip() or " " in perm:
                    problems.append(f"bad permission: {perm!r}")
            elif isinstance(perm, dict):
                if not perm.get("permission"):
                    problems.append("scoped permission missing 'permission' key")
            else:
                problems.append(f"bad permission entry: {perm!r}")
        for tool in self.tools:
            if not isinstance(tool, dict) or not tool.get("name"):
                problems.append("tool entry missing name")
        for ep, target in self.entrypoints.items():
            if not target or ".." in str(target).replace("\\", "/").split("/"):
                problems.append(f"entrypoint escapes package: {ep}")
        return problems

    def to_dict(self) -> Dict[str, Any]:
        d = {k: getattr(self, k) for k in (
            "id", "name", "display_name", "version", "description",
            "publisher", "publisher_id", "homepage", "repository",
            "license", "icon", "categories", "keywords", "engine_version",
            "api_version", "platforms", "architectures", "dependencies",
            "optional_dependencies", "capabilities", "permissions",
            "entrypoints", "tools", "skills", "mcp_servers", "agents",
            "workflows", "settings", "commands", "events", "network",
            "filesystem", "secrets", "update_policy")}
        d["extension_type"] = ExtensionType(self.extension_type).value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ExtensionManifest":
        if not isinstance(d, dict):
            raise ValueError("manifest must be an object")
        allowed = set(cls.__dataclass_fields__)
        unknown = set(d) - allowed
        if unknown:
            raise ValueError(f"unknown manifest fields: {sorted(unknown)}")
        m = cls()
        for k in allowed:
            if k in d:
                if k == "extension_type":
                    m.extension_type = ExtensionType(str(d[k]))
                else:
                    setattr(m, k, d[k])
        return m
