"""
Policy Management for AetherOS
==============================

Load, validate, and apply security policies from YAML/JSON policy files.

A policy is a declarative document that configures the permission engine,
sandbox defaults, and network rules for a workspace, agent, or plugin.

Example policy file (``policy.yaml``)::

    version: 1
    workspace: default
    default_permission: deny

    permissions:
      filesystem:
        read: true
        write:
          - "~/Documents"
        execute: false
      network:
        connect: true
      terminal:
        execute: true

    sandbox:
      mode: standard
      max_memory_mb: 512
      network_access: false

    network:
      allowed_hosts: ["api.openai.com", "api.anthropic.com"]
      denied_hosts: ["localhost"]

Usage::

    from aetheros_security.policy import PolicyManager

    manager = PolicyManager()
    manager.load_policy("workspace", Path("policy.yaml"))
    rules = manager.rules_for("workspace")
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


class PolicyError(Exception):
    """Raised when a policy cannot be parsed or validated."""


# Categories that a policy may grant permissions for. Keys must stay aligned
# with aetheros_security.PERMISSION_CATEGORIES.
_VALID_CATEGORIES = {
    "filesystem", "clipboard", "browser", "terminal", "network", "camera",
    "microphone", "location", "notifications", "desktop", "keyboard",
    "mouse", "voice", "memory", "knowledge", "cloud", "git", "docker",
    "ssh", "api",
}


class PolicyManager:
    """Loads and applies declarative security policies.

    Usage::

        manager = PolicyManager()
        manager.load_policy("workspace", "policy.yaml")
        rules = manager.rules_for("workspace")
        audit_entries = manager.get_loaded_policies()
    """

    def __init__(self) -> None:
        self._policies: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_policy(self, name: str, source) -> Dict[str, Any]:
        """Load a policy from a YAML/JSON file or a dict.

        Args:
            name: Policy name (workspace/agent id).
            source: Path, str path, or dict of policy content.

        Returns:
            The validated policy.

        Raises:
            PolicyError: On parse or validation failure.
        """
        data = self._read(source)
        self._validate(data)
        self._policies[name] = data
        logger.info("Policy loaded: %s", name)
        return data

    def _read(self, source) -> Dict[str, Any]:
        if isinstance(source, dict):
            return source
        path = Path(source)
        try:
            text = path.read_text("utf-8")
        except OSError as exc:
            raise PolicyError(f"Cannot read policy file {path}: {exc}") from exc
        if path.suffix.lower() in (".json",):
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                raise PolicyError(f"Invalid JSON policy {path}: {exc}") from exc
        if yaml is None:
            raise PolicyError("YAML support unavailable (install pyyaml)")
        try:
            loaded = yaml.safe_load(text)
        except Exception as exc:
            raise PolicyError(f"Invalid YAML policy {path}: {exc}") from exc
        if not isinstance(loaded, dict):
            raise PolicyError(f"Policy root must be a mapping: {path}")
        return loaded

    def _validate(self, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise PolicyError("Policy must be a mapping")
        version = data.get("version", 1)
        if version != 1:
            raise PolicyError(f"Unsupported policy version: {version}")

        perms = data.get("permissions")
        if perms is not None:
            if not isinstance(perms, dict):
                raise PolicyError("'permissions' must be a mapping")
            unknown = set(perms) - _VALID_CATEGORIES
            if unknown:
                raise PolicyError(
                    f"Unknown permission categories: {sorted(unknown)}"
                )
            for category, actions in perms.items():
                if not isinstance(actions, dict):
                    raise PolicyError(
                        f"Permission '{category}' must be a mapping of actions"
                    )

        sandbox = data.get("sandbox")
        if sandbox is not None and not isinstance(sandbox, dict):
            raise PolicyError("'sandbox' must be a mapping")

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def rules_for(self, name: str) -> Dict[str, Any]:
        """Return the raw policy rules for a workspace/agent.

        Falls back to the ``"default"`` policy when a specific one is absent.
        """
        if name in self._policies:
            return self._policies[name]
        if "default" in self._policies:
            return self._policies["default"]
        return {}

    def check_permission(self, policy_name: str, permission: str) -> bool:
        """Evaluate a ``category:action`` permission against a policy.

        Default posture is deny. ``true`` grants the action for everyone in
        scope; a list limits it to the listed values; anything else denies.
        """
        permission = permission.lower()
        if ":" in permission:
            category, action = permission.split(":", 1)
        else:
            category, action = permission, "*"
        rules = self.rules_for(policy_name)
        category_rules = rules.get("permissions", {}).get(category, {})
        default = rules.get("default_permission", "deny")

        if action in category_rules:
            return bool(category_rules[action])
        if "*" in category_rules:
            return bool(category_rules["*"])
        return default == "allow"

    def sandbox_rules(self, policy_name: str) -> Dict[str, Any]:
        """Return sandbox configuration from a policy (or empty dict)."""
        return self.rules_for(policy_name).get("sandbox", {})

    def network_rules(self, policy_name: str) -> Dict[str, Any]:
        """Return network rules from a policy (or empty dict)."""
        return self.rules_for(policy_name).get("network", {})

    def get_loaded_policies(self) -> List[Dict[str, Any]]:
        """List loaded policy names."""
        return [
            {"name": name, "workspace": data.get("workspace", "")}
            for name, data in self._policies.items()
        ]

    def unload(self, name: str) -> bool:
        """Remove a loaded policy."""
        if name in self._policies:
            del self._policies[name]
            return True
        return False


# Global policy manager
_policy_manager: PolicyManager | None = None


def get_policy_manager() -> PolicyManager:
    """Return the global PolicyManager singleton."""
    global _policy_manager
    if _policy_manager is None:
        _policy_manager = PolicyManager()
    return _policy_manager
