"""AetherOS Integrations — provider base and registry.

Every integration (messaging, email, calendar, storage, devops, knowledge,
productivity, crm, database) implements the same ``BaseProvider`` interface
and registers through the shared registry. One architecture, real
implementations, honest availability.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from aetheros_integrations.models import (
    HealthStatus,
    IntegrationCategory,
    ProviderDefinition,
)

logger = logging.getLogger(__name__)


class BaseProvider:
    """Contract every provider adapter implements.

    Subclasses define ``definition`` and implement at least ``ping`` plus
    the capability methods their ``capabilities`` list advertises. Methods
    the provider cannot perform must raise ``NotImplementedError`` (not fake
    success) or return an honest error dict.
    """

    definition: ProviderDefinition

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    # -- health / introspection -------------------------------------------

    def ping(self) -> HealthStatus:
        """Return health by actually probing the remote service when possible."""
        raise NotImplementedError

    def availability(self) -> Dict[str, Any]:
        """Honest capability report: what this provider can do right now."""
        return {
            "key": self.definition.key,
            "available": self.is_available(),
            "health": self.ping().value,
            "capabilities": self.definition.capabilities,
        }

    def is_available(self) -> bool:
        try:
            return self.ping() in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
        except NotImplementedError:
            return False

    # -- credential plumbing ----------------------------------------------

    def set_credentials(self, auth_header: Dict[str, str]) -> None:
        self.config["_auth_header"] = auth_header

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": "AetherOS-Integrations/1.0"}
        auth = self.config.get("_auth_header") or {}
        headers.update(auth)
        if extra:
            headers.update(extra)
        return headers

    # -- capability methods (override per provider) -----------------------

    def send_message(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError

    def read_messages(self, **kwargs) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def list_events(self, **kwargs) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def list_files(self, **kwargs) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def upload_file(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError

    def list_repos(self, **kwargs) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def search_documents(self, **kwargs) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def create_record(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError

    def run_query(self, **kwargs) -> List[Dict[str, Any]]:
        raise NotImplementedError


class RESTProvider(BaseProvider):
    """Base for REST-based providers. Uses the shared AuthEngine headers."""

    def _url(self, path: str) -> str:
        base = self.definition.base_url.rstrip("/")
        return base + path


_registry_lock = object()


class ProviderRegistry:
    """Global registry of provider adapters, keyed by provider key."""

    def __init__(self):
        self._providers: Dict[str, type] = {}
        self._instances: Dict[str, BaseProvider] = {}

    def register(self, provider_cls: type) -> type:
        key = provider_cls.definition.key
        if key in self._providers:
            logger.debug("Provider %s re-registered (last wins)", key)
        self._providers[key] = provider_cls
        return provider_cls

    def get_class(self, key: str) -> type:
        try:
            return self._providers[key]
        except KeyError as exc:
            raise KeyError(f"Unknown provider: {key}") from exc

    def get(self, key: str, config: Optional[Dict[str, Any]] = None) -> BaseProvider:
        cls = self.get_class(key)
        if config is not None or key not in self._instances:
            return cls(config or {})
        return self._instances[key]

    def list_definitions(self, category: Optional[IntegrationCategory] = None) -> List[ProviderDefinition]:
        defs = [p.definition for p in self._providers.values()]
        if category:
            defs = [d for d in defs if d.category == category]
        return sorted(defs, key=lambda d: d.display_name)

    def has(self, key: str) -> bool:
        return key in self._providers

    def categories(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for p in self._providers.values():
            counts[p.definition.category.value] = counts.get(p.definition.category.value, 0) + 1
        return counts


registry = ProviderRegistry()


def register_provider(cls: type) -> type:
    return registry.register(cls)
