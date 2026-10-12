"""
Secret Management
=================

Pluggable integrations for external secret managers (Bitwarden, Vault, etc.).
Supports credential references, token rotation hooks, access auditing, and
least-privilege access patterns.
"""

from __future__ import annotations

import enum
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SecretProviderType(enum.Enum):
    BITWARDEN = "bitwarden"
    VAULT = "vault"
    AWS_SECRETS = "aws_secrets"
    AZURE_KEYVAULT = "azure_keyvault"
    GCP_SECRET_MANAGER = "gcp_secret_manager"
    ENV = "env"
    FILE = "file"


@dataclass
class SecretReference:
    """A reference to a secret stored in an external provider.

    The actual secret value is never stored locally — only the reference.
    """
    path: str
    provider: SecretProviderType = SecretProviderType.ENV
    key: str = ""
    version: str = ""
    cached_value: Optional[str] = None  # Never persisted
    cached_at: Optional[datetime] = None

    def needs_refresh(self, ttl_seconds: int = 300) -> bool:
        if self.cached_value is None:
            return True
        if self.cached_at is None:
            return True
        from datetime import timedelta
        return datetime.utcnow() > self.cached_at + timedelta(seconds=ttl_seconds)


@dataclass
class SecretRotationHook:
    """A hook that runs before/after secret rotation."""
    name: str = ""
    on_before_rotate: Optional[list[Callable]] = None
    on_after_rotate: Optional[list[Callable]] = None
    on_rotation_failed: Optional[list[Callable]] = None


class SecretProvider(ABC):
    """Abstract base class for secret manager integration."""

    @abstractmethod
    def get_secret(self, ref: SecretReference) -> str:
        """Retrieve a secret value from the provider."""
        ...

    @abstractmethod
    def set_secret(self, ref: SecretReference, value: str) -> bool:
        """Store/update a secret value."""
        ...

    @abstractmethod
    def delete_secret(self, ref: SecretReference) -> bool:
        """Delete a secret."""
        ...

    @abstractmethod
    def list_secrets(self, path: str = "") -> List[SecretReference]:
        """List secrets at the given path."""
        ...

    def health_check(self) -> bool:
        """Check if the provider is accessible."""
        return True


class SecretManager:
    """Central secret manager that delegates to configured providers.

    Never stores plaintext secrets in memory longer than needed.
    Supports least-privilege access via reference-based patterns.
    """

    def __init__(self) -> None:
        self._providers: Dict[SecretProviderType, SecretProvider] = {}
        self._rotation_hooks: Dict[str, SecretRotationHook] = {}
        self._access_log: List[Dict[str, Any]] = []

    def register_provider(self, provider_type: SecretProviderType, provider: SecretProvider) -> None:
        self._providers[provider_type] = provider

    def get_provider(self, provider_type: SecretProviderType) -> Optional[SecretProvider]:
        return self._providers.get(provider_type)

    def get_secret(self, ref: SecretReference) -> Optional[str]:
        """Retrieve a secret value through the appropriate provider.

        Accesses are logged for auditing purposes.
        """
        provider = self._providers.get(ref.provider)
        if not provider:
            logger.warning("No provider registered for %s", ref.provider.value)
            return None

        value = provider.get_secret(ref)
        if value is not None:
            ref.cached_value = value
            ref.cached_at = datetime.utcnow()

        # Log access (without the actual value)
        self._access_log.append({
            "path": ref.path,
            "provider": ref.provider.value,
            "timestamp": datetime.utcnow().isoformat(),
            "action": "read",
        })
        return value

    def set_secret(self, ref: SecretReference, value: str) -> bool:
        provider = self._providers.get(ref.provider)
        if not provider:
            return False
        result = provider.set_secret(ref, value)
        if result:
            ref.cached_value = None  # Invalidate cache
            ref.cached_at = None
        return result

    def delete_secret(self, ref: SecretReference) -> bool:
        provider = self._providers.get(ref.provider)
        if not provider:
            return False
        return provider.delete_secret(ref)

    def rotate_secret(self, ref: SecretReference, new_value: str) -> bool:
        """Rotate a secret value, running configured hooks."""
        hook = self._rotation_hooks.get(ref.path)

        try:
            if hook and hook.on_before_rotate:
                for h in hook.on_before_rotate:
                    h(ref)

            self.set_secret(ref, new_value)

            if hook and hook.on_after_rotate:
                for h in hook.on_after_rotate:
                    h(ref)

            logger.info("Secret rotated: %s", ref.path)
            return True
        except Exception as exc:
            if hook and hook.on_rotation_failed:
                for h in hook.on_rotation_failed:
                    h(ref, exc)
            logger.error("Secret rotation failed: %s: %s", ref.path, exc)
            return False

    def register_rotation_hook(self, path: str, hook: SecretRotationHook) -> None:
        self._rotation_hooks[path] = hook

    def get_access_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        return list(reversed(self._access_log))[:limit]
