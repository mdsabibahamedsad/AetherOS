"""AetherOS Integrations — CRM & business adapters.

HubSpot, Salesforce, Zoho, Freshworks, Zendesk, Intercom. Contacts and
records across each platform.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from aetheros_integrations.models import AuthMethod, HealthStatus, IntegrationCategory, ProviderDefinition
from aetheros_integrations.providers.base import RESTProvider, register_provider

logger = logging.getLogger(__name__)


@register_provider
class HubSpotProvider(RESTProvider):
    definition = ProviderDefinition(
        key="hubspot",
        category=IntegrationCategory.CRM,
        display_name="HubSpot",
        description="HubSpot CRM API: contacts, deals.",
        auth_method=AuthMethod.OAUTH2,
        base_url="https://api.hubapi.com/crm/v3",
        capabilities=["create_record", "search", "list_records"],
    )

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        return HealthStatus.HEALTHY if token.startswith("Bearer") else HealthStatus.UNHEALTHY

    def create_record(self, object_type: str, properties: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no hubspot credential"}
        resp = httpx.post(f"{self.definition.base_url}/objects/{object_type}", headers={**self._headers(), "Content-Type": "application/json"}, json={"properties": properties}, timeout=15)
        return {"success": resp.status_code == 201, "status": resp.status_code}

    def search(self, object_type: str, query: str, max_results: int = 10, **kwargs) -> List[Dict[str, Any]]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return []
        resp = httpx.post(f"{self.definition.base_url}/objects/{object_type}/search", headers={**self._headers(), "Content-Type": "application/json"}, json={"query": query, "limit": max_results}, timeout=15)
        return resp.json().get("results", []) if resp.status_code == 200 else []


@register_provider
class SalesforceProvider(RESTProvider):
    definition = ProviderDefinition(
        key="salesforce",
        category=IntegrationCategory.CRM,
        display_name="Salesforce",
        description="Salesforce REST API: records, query.",
        auth_method=AuthMethod.OAUTH2,
        base_url="https://instance.salesforce.com",
        scopes=["api", "refresh_token"],
        capabilities=["create_record", "run_query"],
    )

    def _instance(self) -> str:
        return self.config.get("instance_url", self.definition.base_url).rstrip("/")

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.get(f"{self._instance()}/services/data/v58.0/sobjects", headers=self._headers(), timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def run_query(self, soql: str, **kwargs) -> List[Dict[str, Any]]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return []
        resp = httpx.get(f"{self._instance()}/services/data/v58.0/query", headers=self._headers(), params={"q": soql}, timeout=15)
        return resp.json().get("records", []) if resp.status_code == 200 else []

    def create_record(self, object_type: str, fields: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no salesforce credential"}
        resp = httpx.post(f"{self._instance()}/services/data/v58.0/sobjects/{object_type}", headers={**self._headers(), "Content-Type": "application/json"}, json=fields, timeout=15)
        return {"success": resp.status_code == 201, "status": resp.status_code}


@register_provider
class ZohoProvider(RESTProvider):
    definition = ProviderDefinition(
        key="zoho",
        category=IntegrationCategory.CRM,
        display_name="Zoho CRM",
        description="Zoho CRM API: records.",
        auth_method=AuthMethod.OAUTH2,
        base_url="https://www.zohoapis.com/crm/v7",
        scopes=["ZohoCRM.modules.ALL"],
        capabilities=["create_record", "search"],
    )

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        return HealthStatus.HEALTHY if token.startswith("Bearer") else HealthStatus.UNHEALTHY

    def create_record(self, module: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no zoho credential"}
        resp = httpx.post(f"{self.definition.base_url}/{module}", headers={**self._headers(), "Content-Type": "application/json"}, json={"data": [data]}, timeout=15)
        return {"success": resp.status_code == 201, "status": resp.status_code}


@register_provider
class FreshworksProvider(RESTProvider):
    definition = ProviderDefinition(
        key="freshworks",
        category=IntegrationCategory.CRM,
        display_name="Freshworks",
        description="Freshdesk API: tickets, contacts.",
        auth_method=AuthMethod.API_KEY,
        base_url="https://your-domain.freshdesk.com/api/v2",
        capabilities=["create_record", "search"],
    )

    def _base(self) -> str:
        return self.config.get("domain", self.definition.base_url).rstrip("/")

    def ping(self) -> HealthStatus:
        if not self.config.get("api_key"):
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.get(self._base() + "/tickets", auth=("x", self.config.get("api_key", "")), params={"per_page": 1}, timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def create_record(self, subject: str, description: str = "", **kwargs) -> Dict[str, Any]:
        if not self.config.get("api_key"):
            return {"success": False, "error": "no freshdesk credential"}
        resp = httpx.post(self._base() + "/tickets", auth=("x", self.config.get("api_key", "")), json={"subject": subject, "description": description, "status": 2, "priority": 1}, timeout=15)
        return {"success": resp.status_code == 201, "status": resp.status_code}


@register_provider
class ZendeskProvider(RESTProvider):
    definition = ProviderDefinition(
        key="zendesk",
        category=IntegrationCategory.CRM,
        display_name="Zendesk",
        description="Zendesk API: tickets.",
        auth_method=AuthMethod.BEARER,
        base_url="https://your-domain.zendesk.com/api/v2",
        capabilities=["create_record", "search"],
    )

    def _base(self) -> str:
        return self.config.get("subdomain", "").join(["https://", ".zendesk.com/api/v2"]) if self.config.get("subdomain") else self.definition.base_url

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.get(self._base().rstrip("/") + "/tickets", headers=self._headers(), params={"per_page": 1}, timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def create_record(self, subject: str, body: str = "", **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no zendesk credential"}
        resp = httpx.post(self._base().rstrip("/") + "/tickets", headers={**self._headers(), "Content-Type": "application/json"}, json={"ticket": {"subject": subject, "comment": {"body": body}, "priority": "normal"}}, timeout=15)
        return {"success": resp.status_code == 201, "status": resp.status_code}


@register_provider
class IntercomProvider(RESTProvider):
    definition = ProviderDefinition(
        key="intercom",
        category=IntegrationCategory.CRM,
        display_name="Intercom",
        description="Intercom API: contacts, conversations.",
        auth_method=AuthMethod.BEARER,
        base_url="https://api.intercom.io",
        capabilities=["create_record", "search"],
    )

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.get(f"{self.definition.base_url}/me", headers=self._headers(), timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def create_record(self, role: str = "user", email: str = "", **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no intercom credential"}
        resp = httpx.post(f"{self.definition.base_url}/contacts", headers={**self._headers(), "Content-Type": "application/json"}, json={"role": role, "email": email, "name": kwargs.get("name", "")}, timeout=15)
        return {"success": resp.status_code == 200, "status": resp.status_code}
