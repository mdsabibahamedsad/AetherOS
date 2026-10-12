"""
Plugin permissions — granular permission management for AetherOS plugins.
Controls access to system resources and user data.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)


class PermissionMode(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class PermissionCategory(str, Enum):
    FILESYSTEM = "filesystem"
    INTERNET = "internet"
    BROWSER = "browser"
    TERMINAL = "terminal"
    DOCKER = "docker"
    PYTHON = "python"
    CLIPBOARD = "clipboard"
    NOTIFICATIONS = "notifications"
    MICROPHONE = "microphone"
    CAMERA = "camera"
    WORKSPACE = "workspace"
    SECRETS = "secrets"
    SETTINGS = "settings"
    NETWORK = "network"
    MEMORY = "memory"
    MCP = "mcp"
    AUDIO = "audio"
    VISION = "vision"
    PROMPT_INJECTION = "prompt_injection"
    SYSTEM = "system"
    UI = "ui"


PERMISSION_CATEGORY_RESOURCES: Dict[PermissionCategory, List[str]] = {
    PermissionCategory.FILESYSTEM: [
        "filesystem.read", "filesystem.write", "filesystem.delete",
        "filesystem.execute",
    ],
    PermissionCategory.INTERNET: [
        "internet.connect", "internet.listen",
    ],
    PermissionCategory.BROWSER: [
        "browser.navigate", "browser.read", "browser.write",
        "browser.screenshot",
    ],
    PermissionCategory.TERMINAL: [
        "terminal.execute", "terminal.read", "terminal.write",
    ],
    PermissionCategory.DOCKER: [
        "docker.containers.list", "docker.containers.exec",
        "docker.images.pull", "docker.images.push",
    ],
    PermissionCategory.PYTHON: [
        "python.exec", "python.import", "python.eval",
    ],
    PermissionCategory.CLIPBOARD: [
        "clipboard.read", "clipboard.write",
    ],
    PermissionCategory.NOTIFICATIONS: [
        "notifications.send", "notifications.read",
    ],
    PermissionCategory.MICROPHONE: [
        "microphone.record", "microphone.stream",
    ],
    PermissionCategory.CAMERA: [
        "camera.capture", "camera.stream",
    ],
    PermissionCategory.WORKSPACE: [
        "workspace.read", "workspace.write",
        "workspace.env",
    ],
    PermissionCategory.SECRETS: [
        "secrets.read", "secrets.write",
    ],
    PermissionCategory.SETTINGS: [
        "settings.read", "settings.write",
    ],
    PermissionCategory.NETWORK: [
        "network.connect", "network.listen",
        "network.dns",
    ],
    PermissionCategory.MEMORY: [
        "memory.read", "memory.write",
        "memory.delete",
    ],
    PermissionCategory.MCP: [
        "mcp.connect", "mcp.invoke",
        "mcp.list",
    ],
    PermissionCategory.AUDIO: [
        "audio.play", "audio.record",
    ],
    PermissionCategory.VISION: [
        "vision.capture", "vision.analyze",
    ],
    PermissionCategory.PROMPT_INJECTION: [
        "prompt_injection.allowed",
    ],
    PermissionCategory.SYSTEM: [
        "system.info", "system.shutdown",
        "system.process",
    ],
    PermissionCategory.UI: [
        "ui.display", "ui.interact",
    ],
}


@dataclass
class PermissionRule:
    resource: str
    mode: PermissionMode = PermissionMode.ASK
    reason: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "resource": self.resource,
            "mode": self.mode.value,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PermissionRule:
        mode_str = data.get("mode", "ask")
        try:
            mode = PermissionMode(mode_str)
        except ValueError:
            mode = PermissionMode.ASK
        return cls(
            resource=data["resource"],
            mode=mode,
            reason=data.get("reason", ""),
        )


@dataclass
class PluginPermissionEntry:
    plugin: str
    rules: List[PermissionRule] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin": self.plugin,
            "rules": [r.to_dict() for r in self.rules],
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PluginPermissionEntry:
        return cls(
            plugin=data["plugin"],
            rules=[PermissionRule.from_dict(r) for r in data.get("rules", [])],
            enabled=data.get("enabled", True),
        )


@dataclass
class AuditEntry:
    plugin: str
    resource: str
    action: str
    granted: bool
    timestamp: str = ""
    reason: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "plugin": self.plugin,
            "resource": self.resource,
            "action": self.action,
            "granted": str(self.granted),
            "timestamp": self.timestamp,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> AuditEntry:
        return cls(
            plugin=data["plugin"],
            resource=data["resource"],
            action=data["action"],
            granted=data.get("granted", "").lower() == "true",
            timestamp=data.get("timestamp", ""),
            reason=data.get("reason", ""),
        )


@dataclass
class TrustScore:
    plugin: str
    score: float = 0.0
    downloads: int = 0
    verified_publisher: bool = False
    signature_valid: bool = False
    install_count: int = 0
    report_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin": self.plugin,
            "score": self.score,
            "downloads": self.downloads,
            "verified_publisher": self.verified_publisher,
            "signature_valid": self.signature_valid,
            "install_count": self.install_count,
            "report_count": self.report_count,
        }


@dataclass
class SandboxConfig:
    enabled: bool = False
    type: str = "subprocess"
    timeout: int = 30
    memory_limit_mb: int = 512
    cpu_quota: float = 1.0
    network_access: bool = False
    filesystem_read_paths: List[str] = field(default_factory=list)
    filesystem_write_paths: List[str] = field(default_factory=list)
    environment_vars: Dict[str, str] = field(default_factory=dict)
    allowed_syscalls: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "type": self.type,
            "timeout": self.timeout,
            "memory_limit_mb": self.memory_limit_mb,
            "cpu_quota": self.cpu_quota,
            "network_access": self.network_access,
            "filesystem_read_paths": self.filesystem_read_paths,
            "filesystem_write_paths": self.filesystem_write_paths,
            "environment_vars": self.environment_vars,
            "allowed_syscalls": self.allowed_syscalls,
        }


class PermissionDeniedError(Exception):
    pass


class PluginPermissions:
    def __init__(self):
        self._home = get_aetheros_home()
        self._permissions_dir = self._home / "security" / "permissions"
        self._rules_path = self._permissions_dir / "rules.json"
        self._audit_path = self._permissions_dir / "audit.jsonl"
        self._trust_path = self._permissions_dir / "trust.json"
        self._sandbox_config_path = self._permissions_dir / "sandbox.json"
        self._rules: Dict[str, PluginPermissionEntry] = {}
        self._audit_log: List[AuditEntry] = []
        self._trust_scores: Dict[str, TrustScore] = {}
        self._sandbox_config: SandboxConfig = SandboxConfig()
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self._permissions_dir.mkdir(parents=True, exist_ok=True)

    def _load_rules(self) -> Dict[str, PluginPermissionEntry]:
        if self._rules_path.exists():
            try:
                data = json.loads(self._rules_path.read_text(encoding="utf-8"))
                return {
                    k: PluginPermissionEntry.from_dict(v) for k, v in data.items()
                }
            except Exception as e:
                logger.warning("Failed to load permission rules: %s", e)
        return {}

    def _save_rules(self) -> None:
        self._rules_path.write_text(
            json.dumps(
                {k: v.to_dict() for k, v in self._rules.items()},
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

    def _load_trust_scores(self) -> Dict[str, TrustScore]:
        if self._trust_path.exists():
            try:
                data = json.loads(self._trust_path.read_text(encoding="utf-8"))
                return {k: TrustScore(**v) for k, v in data.items()}
            except Exception as e:
                logger.warning("Failed to load trust scores: %s", e)
        return {}

    def _save_trust_scores(self) -> None:
        self._trust_path.write_text(
            json.dumps(
                {k: v.to_dict() for k, v in self._trust_scores.items()},
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

    def _load_sandbox_config(self) -> SandboxConfig:
        if self._sandbox_config_path.exists():
            try:
                data = json.loads(
                    self._sandbox_config_path.read_text(encoding="utf-8")
                )
                return SandboxConfig(**data)
            except Exception as e:
                logger.warning("Failed to load sandbox config: %s", e)
        return SandboxConfig()

    def _save_sandbox_config(self) -> None:
        self._sandbox_config_path.write_text(
            json.dumps(self._sandbox_config.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )

    def initialize(self) -> None:
        self._rules = self._load_rules()
        self._trust_scores = self._load_trust_scores()
        self._sandbox_config = self._load_sandbox_config()
        logger.info(
            "Plugin permissions initialized (%d rules)",
            len(self._rules),
        )

    def check_permission(
        self,
        plugin: str,
        resource: str,
        action: str = "read",
    ) -> bool:
        full_resource = f"{resource}.{action}" if "." not in resource else resource

        entry = self._rules.get(plugin)
        if entry is None:
            entry = self._rules.get("*")
        if entry is None:
            self._audit(plugin, full_resource, action, False, "No rules defined")
            return False

        if not entry.enabled:
            self._audit(plugin, full_resource, action, False, "Plugin permissions disabled")
            return False

        for rule in entry.rules:
            if self._resource_matches(full_resource, rule.resource):
                if rule.mode == PermissionMode.ALLOW:
                    self._audit(plugin, full_resource, action, True, rule.reason)
                    return True
                elif rule.mode == PermissionMode.DENY:
                    self._audit(plugin, full_resource, action, False, rule.reason or "Denied by rule")
                    return False
                elif rule.mode == PermissionMode.ASK:
                    granted = self._prompt_user(plugin, full_resource, action)
                    self._audit(plugin, full_resource, action, granted, "User prompted")
                    return granted

        self._audit(plugin, full_resource, action, False, "No matching rule")
        return False

    def _resource_matches(self, actual: str, pattern: str) -> bool:
        if pattern == "*":
            return True
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return actual.startswith(prefix + ".") or actual == prefix
        return actual == pattern

    def _prompt_user(
        self, plugin: str, resource: str, action: str
    ) -> bool:
        logger.info(
            "Permission prompt: plugin='%s' resource='%s' action='%s'",
            plugin, resource, action,
        )
        try:
            response = input(
                f"Plugin '{plugin}' wants to access '{resource}'. Allow? [y/N]: "
            ).strip().lower()
            return response in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False

    def _audit(
        self,
        plugin: str,
        resource: str,
        action: str,
        granted: bool,
        reason: str = "",
    ) -> None:
        entry = AuditEntry(
            plugin=plugin,
            resource=resource,
            action=action,
            granted=granted,
            timestamp=datetime.utcnow().isoformat(),
            reason=reason,
        )
        self._audit_log.append(entry)

        try:
            with open(self._audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception as e:
            logger.warning("Failed to write audit entry: %s", e)

    def set_permission(
        self,
        plugin: str,
        resource: str,
        mode: PermissionMode,
        reason: str = "",
    ) -> None:
        if plugin not in self._rules:
            self._rules[plugin] = PluginPermissionEntry(plugin=plugin)

        existing = [
            r for r in self._rules[plugin].rules
            if r.resource != resource
        ]
        existing.append(PermissionRule(resource=resource, mode=mode, reason=reason))
        self._rules[plugin].rules = existing
        self._save_rules()
        logger.info(
            "Permission set: plugin='%s' resource='%s' mode='%s'",
            plugin, resource, mode.value,
        )

    def revoke_permission(self, plugin: str, resource: str) -> bool:
        entry = self._rules.get(plugin)
        if not entry:
            return False
        before = len(entry.rules)
        entry.rules = [r for r in entry.rules if r.resource != resource]
        if len(entry.rules) < before:
            self._save_rules()
            return True
        return False

    def get_permissions(self, plugin: str) -> List[PermissionRule]:
        entry = self._rules.get(plugin)
        return list(entry.rules) if entry else []

    def get_all_permissions(self) -> Dict[str, List[PermissionRule]]:
        return {
            name: list(entry.rules)
            for name, entry in self._rules.items()
        }

    def enable_plugin_permissions(self, plugin: str) -> bool:
        entry = self._rules.get(plugin)
        if not entry:
            return False
        entry.enabled = True
        self._save_rules()
        return True

    def disable_plugin_permissions(self, plugin: str) -> bool:
        entry = self._rules.get(plugin)
        if not entry:
            return False
        entry.enabled = False
        self._save_rules()
        return True

    def get_audit_log(
        self,
        plugin: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        if plugin:
            return [e for e in self._audit_log if e.plugin == plugin][-limit:]
        return self._audit_log[-limit:]

    def clear_audit_log(self) -> None:
        self._audit_log.clear()
        if self._audit_path.exists():
            self._audit_path.write_text("", encoding="utf-8")

    def update_trust_score(self, plugin: str) -> TrustScore:
        score = self._trust_scores.get(plugin, TrustScore(plugin=plugin))

        base = 50.0
        if score.verified_publisher:
            base += 20.0
        if score.signature_valid:
            base += 15.0
        download_bonus = min(10.0, score.downloads * 0.5)
        report_penalty = min(30.0, score.report_count * 10.0)
        score.score = max(0.0, min(100.0, base + download_bonus - report_penalty))

        self._trust_scores[plugin] = score
        self._save_trust_scores()
        return score

    def get_trust_score(self, plugin: str) -> Optional[TrustScore]:
        return self._trust_scores.get(plugin)

    def verify_digital_signature(
        self,
        plugin_path: Path,
        signature: str,
        public_key: str,
    ) -> bool:
        try:
            import base64
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding, rsa
            from cryptography.hazmat.backends import default_backend
            from cryptography.exceptions import InvalidSignature
        except ImportError:
            logger.warning(
                "cryptography library not available; signature verification skipped"
            )
            return False

        try:
            data = plugin_path.read_bytes() if plugin_path.is_file() else b""

            key_bytes = public_key.encode("utf-8")
            public_key_obj = serialization.load_pem_public_key(
                key_bytes, backend=default_backend()
            )
            if not isinstance(public_key_obj, rsa.RSAPublicKey):
                logger.warning("Public key is not RSA")
                return False

            sig_bytes = base64.b64decode(signature)
            public_key_obj.verify(
                sig_bytes,
                data,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            logger.info("Digital signature verified")
            return True
        except (InvalidSignature, Exception) as e:
            logger.warning("Signature verification failed: %s", e)
            return False

    def set_sandbox_config(self, config: SandboxConfig) -> None:
        self._sandbox_config = config
        self._save_sandbox_config()
        logger.info(
            "Sandbox config updated: enabled=%s type=%s",
            config.enabled, config.type,
        )

    def get_sandbox_config(self) -> SandboxConfig:
        return SandboxConfig(
            enabled=self._sandbox_config.enabled,
            type=self._sandbox_config.type,
            timeout=self._sandbox_config.timeout,
            memory_limit_mb=self._sandbox_config.memory_limit_mb,
            cpu_quota=self._sandbox_config.cpu_quota,
            network_access=self._sandbox_config.network_access,
            filesystem_read_paths=list(self._sandbox_config.filesystem_read_paths),
            filesystem_write_paths=list(self._sandbox_config.filesystem_write_paths),
            environment_vars=dict(self._sandbox_config.environment_vars),
            allowed_syscalls=list(self._sandbox_config.allowed_syscalls),
        )

    def enable_sandbox(self) -> None:
        self._sandbox_config.enabled = True
        self._save_sandbox_config()

    def disable_sandbox(self) -> None:
        self._sandbox_config.enabled = False
        self._save_sandbox_config()

    def get_resource_for_category(
        self, category: PermissionCategory
    ) -> List[str]:
        return PERMISSION_CATEGORY_RESOURCES.get(category, [])

    def is_action_allowed(self, plugin: str, resource: str, action: str) -> bool:
        return self.check_permission(plugin, resource, action)

    def get_default_rules(self) -> Dict[str, PermissionMode]:
        return {
            "filesystem.read": PermissionMode.ALLOW,
            "filesystem.write": PermissionMode.ASK,
            "filesystem.delete": PermissionMode.ASK,
            "internet.connect": PermissionMode.ASK,
            "workspace.read": PermissionMode.ALLOW,
            "workspace.write": PermissionMode.ASK,
            "settings.read": PermissionMode.ALLOW,
            "settings.write": PermissionMode.ASK,
        }

    def apply_default_rules(self, plugin: str) -> None:
        for resource, mode in self.get_default_rules().items():
            self.set_permission(
                plugin, resource, mode,
                reason="Default permission",
            )

    def export_policy(self) -> Dict[str, Any]:
        return {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "rules": {k: v.to_dict() for k, v in self._rules.items()},
            "sandbox": self._sandbox_config.to_dict(),
            "trust_scores": {k: v.to_dict() for k, v in self._trust_scores.items()},
        }

    def import_policy(self, data: Dict[str, Any]) -> int:
        count = 0
        rules_data = data.get("rules", {})
        for name, rule_data in rules_data.items():
            try:
                entry = PluginPermissionEntry.from_dict(rule_data)
                self._rules[name] = entry
                count += 1
            except Exception as e:
                logger.warning("Failed to import rule for '%s': %s", name, e)

        sandbox_data = data.get("sandbox")
        if sandbox_data:
            try:
                self._sandbox_config = SandboxConfig(**sandbox_data)
            except Exception as e:
                logger.warning("Failed to import sandbox config: %s", e)

        trust_data = data.get("trust_scores", {})
        for name, ts_data in trust_data.items():
            try:
                self._trust_scores[name] = TrustScore(**ts_data)
            except Exception as e:
                logger.warning("Failed to import trust score for '%s': %s", name, e)

        self._save_rules()
        self._save_sandbox_config()
        self._save_trust_scores()
        return count

    @property
    def sandbox_config(self) -> SandboxConfig:
        return SandboxConfig(
            enabled=self._sandbox_config.enabled,
            type=self._sandbox_config.type,
            timeout=self._sandbox_config.timeout,
            memory_limit_mb=self._sandbox_config.memory_limit_mb,
            cpu_quota=self._sandbox_config.cpu_quota,
            network_access=self._sandbox_config.network_access,
            filesystem_read_paths=list(self._sandbox_config.filesystem_read_paths),
            filesystem_write_paths=list(self._sandbox_config.filesystem_write_paths),
            environment_vars=dict(self._sandbox_config.environment_vars),
            allowed_syscalls=list(self._sandbox_config.allowed_syscalls),
        )
