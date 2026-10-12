"""AetherOS Integrations — Integration Manager.

Register, install, update, remove, enable, disable, health-check, diagnose,
and permission integrations. Persists instances to a JSON store under the
integrations data dir. All credential material lives only in the encrypted
vault.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from aetheros_integrations.auth import AuthEngine
from aetheros_integrations.config import get_aetheros_dir, load_integrations_settings
from aetheros_integrations.models import (
    HealthStatus,
    IntegrationInstance,
    IntegrationStatus,
    ProviderDefinition,
)
from aetheros_integrations.providers import registry as provider_registry
from aetheros_integrations.security import AuditLog, CredentialVault, PermissionManager, redact_dict

logger = logging.getLogger(__name__)


class IntegrationManager:
    """Lifecycle manager for installed integrations."""

    def __init__(
        self,
        settings=None,
        vault: Optional[CredentialVault] = None,
        audit: Optional[AuditLog] = None,
        permissions: Optional[PermissionManager] = None,
        dirpath=None,
    ):
        self._settings = settings or load_integrations_settings()
        self._dir = dirpath or get_aetheros_dir(self._settings.data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._store_path = self._dir / "instances.json"
        self._lock = threading.RLock()
        self._vault = vault or CredentialVault(self._settings, dirpath=self._dir)
        self._audit = audit or AuditLog(dirpath=self._dir, settings=self._settings)
        self._perms = permissions or PermissionManager()
        self._auth = AuthEngine(self._vault, self._audit, self._settings)
        self._instances: Dict[str, IntegrationInstance] = {}
        self._load()

    def close(self) -> None:
        self._auth.close()

    # -- persistence ------------------------------------------------------

    def _load(self) -> None:
        if not self._store_path.exists():
            return
        try:
            data = json.loads(self._store_path.read_text(encoding="utf-8"))
            for item in data:
                inst = IntegrationInstance(**item)
                self._instances[inst.id] = inst
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load integration instances: %s", exc)

    def _save(self) -> None:
        payload = [i.to_dict() for i in self._instances.values()]
        self._store_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # -- registry passthrough ---------------------------------------------

    def register_provider(self, provider_cls: type) -> type:
        return provider_registry.register(provider_cls)

    def list_providers(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        from aetheros_integrations.models import IntegrationCategory

        cat = None
        if category:
            try:
                cat = IntegrationCategory(category)
            except ValueError:
                cat = None
        defs = provider_registry.list_definitions(cat)
        return [{"key": d.key, "category": d.category.value, "display_name": d.display_name, "description": d.description, "auth_method": d.auth_method.value, "capabilities": d.capabilities} for d in defs]

    def get_provider_definition(self, key: str) -> ProviderDefinition:
        return provider_registry.get_class(key).definition

    def provider_available(self, key: str) -> bool:
        try:
            provider_registry.get_class(key)
            return True
        except KeyError:
            return False

    # -- lifecycle --------------------------------------------------------

    def install(self, provider_key: str, label: str = "", config: Optional[Dict[str, Any]] = None, credential_id: str = "", scopes: Optional[List[str]] = None) -> IntegrationInstance:
        """Create an integration instance. The caller passes a credential_id
        previously minted by the AuthEngine (which stores secrets encrypted),
        never raw secrets."""
        if not self.provider_available(provider_key):
            raise KeyError(f"Unknown provider: {provider_key}")
        instance = IntegrationInstance(
            provider_key=provider_key,
            label=label or provider_key,
            status=IntegrationStatus.ENABLED if self._settings.auto_enable_on_install else IntegrationStatus.INSTALLED,
            config=config or {},
            credentials_ref=credential_id,
            scopes=scopes or self.get_provider_definition(provider_key).scopes,
        )
        with self._lock:
            self._instances[instance.id] = instance
            self._save()
        self._audit.record("integration.installed", actor="user", target=instance.id, detail={"provider": provider_key, "label": instance.label})
        return instance

    def update(self, integration_id: str, config: Optional[Dict[str, Any]] = None, label: str = "", credential_id: str = "", scopes: Optional[List[str]] = None) -> IntegrationInstance:
        instance = self.get(integration_id)
        if config is not None:
            instance.config = config
        if label:
            instance.label = label
        if credential_id:
            instance.credentials_ref = credential_id
        if scopes is not None:
            instance.scopes = scopes
        instance.updated_at = time.time()
        instance.version = _bump(instance.version)
        with self._lock:
            self._save()
        self._audit.record("integration.updated", actor="user", target=integration_id)
        return instance

    def remove(self, integration_id: str) -> bool:
        with self._lock:
            instance = self._instances.pop(integration_id, None)
            if instance is None:
                return False
            if instance.credentials_ref:
                try:
                    self._vault.delete(instance.credentials_ref)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Vault delete on remove: %s", exc)
            self._perms.remove(integration_id)
            self._save()
        self._audit.record("integration.removed", actor="user", target=integration_id)
        return True

    def enable(self, integration_id: str) -> IntegrationInstance:
        instance = self.get(integration_id)
        instance.status = IntegrationStatus.ENABLED
        instance.updated_at = time.time()
        with self._lock:
            self._save()
        self._audit.record("integration.enabled", actor="user", target=integration_id)
        return instance

    def disable(self, integration_id: str) -> IntegrationInstance:
        instance = self.get(integration_id)
        instance.status = IntegrationStatus.DISABLED
        instance.updated_at = time.time()
        with self._lock:
            self._save()
        self._audit.record("integration.disabled", actor="user", target=integration_id)
        return instance

    def get(self, integration_id: str) -> IntegrationInstance:
        with self._lock:
            instance = self._instances.get(integration_id)
            if instance is None:
                raise KeyError(f"No integration {integration_id}")
            return instance

    def list(self, provider_key: str = "", status: Optional[str] = None) -> List[IntegrationInstance]:
        with self._lock:
            out = list(self._instances.values())
        if provider_key:
            out = [i for i in out if i.provider_key == provider_key]
        if status:
            out = [i for i in out if i.status.value == status]
        return out

    def count(self) -> int:
        with self._lock:
            return len(self._instances)

    # -- provider instance factory ----------------------------------------

    def get_provider(self, integration_id: str):
        """Build a configured provider adapter for an instance."""
        instance = self.get(integration_id)
        if instance.status != IntegrationStatus.ENABLED:
            raise RuntimeError(f"Integration {integration_id} is not enabled")
        cls = provider_registry.get_class(instance.provider_key)
        config = dict(instance.config)
        if instance.credentials_ref:
            try:
                secrets = self._vault.decrypt(instance.credentials_ref)
                token = secrets.get("access_token") or secrets.get("bearer") or secrets.get("pat") or secrets.get("api_key")
                if token:
                    config["_auth_header"] = {"Authorization": f"Bearer {token}"}
                if secrets.get("refresh_token"):
                    config["_refresh_token"] = secrets["refresh_token"]
                if secrets.get("api_key") and cls.definition.auth_method.value == "api_key":
                    config["api_key"] = secrets["api_key"]
            except (KeyError, Exception) as exc:  # noqa: BLE001
                logger.debug("Credential resolution for %s: %s", integration_id, exc)
        return cls(config)

    # -- health / diagnostics ---------------------------------------------

    def health_check(self, integration_id: str) -> Dict[str, Any]:
        instance = self.get(integration_id)
        result: Dict[str, Any] = {"integration_id": integration_id, "provider": instance.provider_key, "status": instance.status.value}
        if instance.status != IntegrationStatus.ENABLED:
            result["health"] = HealthStatus.UNAVAILABLE.value
            result["detail"] = f"integration is {instance.status.value}"
            return result
        try:
            provider = self.get_provider(integration_id)
            health = provider.ping()
            instance.last_health = health
            instance.last_health_at = time.time()
            with self._lock:
                self._save()
            result["health"] = health.value
            result["detail"] = getattr(provider.definition, "display_name", provider.definition.key)
        except Exception as exc:  # noqa: BLE001
            instance.last_health = HealthStatus.UNHEALTHY
            with self._lock:
                self._save()
            result["health"] = HealthStatus.UNHEALTHY.value
            result["error"] = str(exc)
        return result

    def health_all(self) -> List[Dict[str, Any]]:
        return [self.health_check(i.id) for i in self.list()]

    def diagnostics(self, integration_id: str) -> Dict[str, Any]:
        instance = self.get(integration_id)
        provider = None
        ping_result = None
        try:
            provider = self.get_provider(integration_id)
            ping_result = provider.ping().value
        except Exception as exc:  # noqa: BLE001
            ping_result = f"error: {exc}"
        return {
            "integration_id": integration_id,
            "provider_key": instance.provider_key,
            "label": instance.label,
            "status": instance.status.value,
            "health": instance.last_health.value,
            "ping": ping_result,
            "has_credentials": bool(instance.credentials_ref),
            "scopes": instance.scopes,
            "permissions": self._perms.get_permissions(integration_id),
            "capabilities": self.get_provider_definition(instance.provider_key).capabilities if self.provider_available(instance.provider_key) else [],
            "config": redact_dict(instance.config),
            "version": instance.version,
        }

    def capabilities(self, integration_id: str) -> List[str]:
        instance = self.get(integration_id)
        return self.get_provider_definition(instance.provider_key).capabilities

    # -- permissions ------------------------------------------------------

    def set_permissions(self, integration_id: str, permissions: Dict[str, Any]) -> None:
        self.get(integration_id)
        self._perms.set_permissions(integration_id, permissions)
        with self._lock:
            instance = self._instances[integration_id]
            instance.permissions = permissions
            self._save()
        self._audit.record("integration.permissions", actor="user", target=integration_id, detail={"permissions": redact_dict(permissions)})

    def can(self, integration_id: str, action: str, resource: str = "") -> bool:
        return self._perms.can(integration_id, action, resource)


def _bump(version: str) -> str:
    try:
        parts = version.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)
    except (ValueError, IndexError):
        return version + ".1"
