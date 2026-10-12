"""AetherOS Integrations — productivity platform adapters.

Trello, Asana, Jira, ClickUp, Linear, Monday, Todoist. Tasks, projects, and
search across each platform.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from aetheros_integrations.models import AuthMethod, HealthStatus, IntegrationCategory, ProviderDefinition
from aetheros_integrations.providers.base import RESTProvider, register_provider

logger = logging.getLogger(__name__)


@register_provider
class TrelloProvider(RESTProvider):
    definition = ProviderDefinition(
        key="trello",
        category=IntegrationCategory.PRODUCTIVITY,
        display_name="Trello",
        description="Trello REST API: boards, cards.",
        auth_method=AuthMethod.API_KEY,
        base_url="https://api.trello.com/1",
        capabilities=["create_record", "list_records", "search"],
    )

    def _key(self) -> str:
        return self.config.get("api_key", "")

    def _token(self) -> str:
        return self.config.get("token", "")

    def ping(self) -> HealthStatus:
        if not self._key() or not self._token():
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.get(f"{self.definition.base_url}/members/me/boards", params={"key": self._key(), "token": self._token()}, timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def create_record(self, list_id: str, name: str, **kwargs) -> Dict[str, Any]:
        if not self._key() or not self._token():
            return {"success": False, "error": "no trello credential"}
        resp = httpx.post(f"{self.definition.base_url}/cards", params={"key": self._key(), "token": self._token(), "idList": list_id, "name": name, "desc": kwargs.get("content", "")}, timeout=15)
        return {"success": resp.status_code == 200, "status": resp.status_code}

    def search(self, query: str, max_results: int = 10, **kwargs) -> List[Dict[str, Any]]:
        if not self._key() or not self._token():
            return []
        resp = httpx.get(f"{self.definition.base_url}/search", params={"key": self._key(), "token": self._token(), "query": query, "modelTypes": "cards", "cards_limit": max_results}, timeout=15)
        return resp.json().get("cards", []) if resp.status_code == 200 else []


@register_provider
class AsanaProvider(RESTProvider):
    definition = ProviderDefinition(
        key="asana",
        category=IntegrationCategory.PRODUCTIVITY,
        display_name="Asana",
        description="Asana REST API: tasks, projects.",
        auth_method=AuthMethod.PAT,
        base_url="https://app.asana.com/api/1.0",
        capabilities=["create_record", "list_records", "search"],
    )

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        return HealthStatus.HEALTHY if token.startswith("Bearer") else HealthStatus.UNHEALTHY

    def create_record(self, project_gid: str, name: str, **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no asana credential"}
        resp = httpx.post(
            f"{self.definition.base_url}/tasks",
            headers={**self._headers(), "Content-Type": "application/json"},
            json={"data": {"name": name, "projects": [project_gid], "notes": kwargs.get("content", "")}},
            timeout=15,
        )
        return {"success": resp.status_code == 201, "status": resp.status_code}


@register_provider
class JiraProvider(RESTProvider):
    definition = ProviderDefinition(
        key="jira",
        category=IntegrationCategory.PRODUCTIVITY,
        display_name="Jira",
        description="Jira Cloud REST API v3: issues, projects.",
        auth_method=AuthMethod.BASIC,
        base_url="https://your-domain.atlassian.net",
        capabilities=["create_record", "list_records", "search"],
    )

    def _base(self) -> str:
        return self.config.get("site_url", self.definition.base_url).rstrip("/")

    def _auth(self):
        return (self.config.get("email", ""), self.config.get("api_token", ""))

    def ping(self) -> HealthStatus:
        if not self.config.get("api_token"):
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.get(self._base() + "/rest/api/3/myself", auth=self._auth(), timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def create_record(self, project_key: str, summary: str, **kwargs) -> Dict[str, Any]:
        if not self.config.get("api_token"):
            return {"success": False, "error": "no jira credential"}
        resp = httpx.post(
            self._base() + "/rest/api/3/issue",
            auth=self._auth(),
            headers={"Content-Type": "application/json"},
            json={"fields": {"project": {"key": project_key}, "summary": summary, "description": kwargs.get("content", ""), "issuetype": {"name": kwargs.get("issuetype", "Task")}}},
            timeout=15,
        )
        return {"success": resp.status_code == 201, "status": resp.status_code}

    def search(self, query: str, max_results: int = 10, **kwargs) -> List[Dict[str, Any]]:
        if not self.config.get("api_token"):
            return []
        resp = httpx.post(self._base() + "/rest/api/3/search/jql", auth=self._auth(), headers={"Content-Type": "application/json"}, json={"jql": f'text~"{query}"', "maxResults": max_results}, timeout=15)
        return resp.json().get("issues", []) if resp.status_code == 200 else []


@register_provider
class ClickUpProvider(RESTProvider):
    definition = ProviderDefinition(
        key="clickup",
        category=IntegrationCategory.PRODUCTIVITY,
        display_name="ClickUp",
        description="ClickUp REST API: tasks, lists.",
        auth_method=AuthMethod.PAT,
        base_url="https://api.clickup.com/api/v2",
        capabilities=["create_record", "search"],
    )

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        return HealthStatus.HEALTHY if token.startswith("Bearer") else HealthStatus.UNHEALTHY

    def create_record(self, list_id: str, name: str, **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no clickup credential"}
        resp = httpx.post(f"{self.definition.base_url}/list/{list_id}/task", headers={**self._headers(), "Content-Type": "application/json"}, json={"name": name, "description": kwargs.get("content", "")}, timeout=15)
        return {"success": resp.status_code in (200, 201), "status": resp.status_code}


@register_provider
class LinearProvider(RESTProvider):
    definition = ProviderDefinition(
        key="linear",
        category=IntegrationCategory.PRODUCTIVITY,
        display_name="Linear",
        description="Linear GraphQL API: issues.",
        auth_method=AuthMethod.PAT,
        base_url="https://api.linear.app/graphql",
        capabilities=["create_record", "search"],
    )

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        return HealthStatus.HEALTHY if token.startswith("Bearer") else HealthStatus.UNHEALTHY

    def create_record(self, team_id: str, title: str, **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no linear credential"}
        gql = f"mutation {{ issueCreate(input: {{ teamId: \"{team_id}\", title: \"{title}\", description: \"{kwargs.get('content', '')}\" }}) {{ success }} }}"
        resp = httpx.post(self.definition.base_url, headers=self._headers(), json={"query": gql}, timeout=15)
        return {"success": resp.status_code == 200, "status": resp.status_code}


@register_provider
class MondayProvider(RESTProvider):
    definition = ProviderDefinition(
        key="monday",
        category=IntegrationCategory.PRODUCTIVITY,
        display_name="Monday.com",
        description="Monday.com GraphQL API: items, boards.",
        auth_method=AuthMethod.PAT,
        base_url="https://api.monday.com/v2",
        capabilities=["create_record", "search"],
    )

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.post(self.definition.base_url, headers=self._headers(), json={"query": "{ me { id } }"}, timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def create_record(self, board_id: str, item_name: str, **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no monday credential"}
        gql = f"mutation {{ create_item (board_id: {board_id}, item_name: \"{item_name}\") {{ id }} }}"
        resp = httpx.post(self.definition.base_url, headers=self._headers(), json={"query": gql}, timeout=15)
        return {"success": resp.status_code == 200, "status": resp.status_code}


@register_provider
class TodoistProvider(RESTProvider):
    definition = ProviderDefinition(
        key="todoist",
        category=IntegrationCategory.PRODUCTIVITY,
        display_name="Todoist",
        description="Todoist REST API: tasks.",
        auth_method=AuthMethod.PAT,
        base_url="https://api.todoist.com/rest/v2",
        capabilities=["create_record", "search"],
    )

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.get(f"{self.definition.base_url}/tasks", headers=self._headers(), params={"limit": 1}, timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def create_record(self, content: str, **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no todoist credential"}
        resp = httpx.post(f"{self.definition.base_url}/tasks", headers={**self._headers(), "Content-Type": "application/json"}, json={"content": content, **({"due_string": kwargs["due_string"]} if kwargs.get("due_string") else {})}, timeout=15)
        return {"success": resp.status_code == 200, "status": resp.status_code}

    def search(self, query: str, max_results: int = 10, **kwargs) -> List[Dict[str, Any]]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return []
        resp = httpx.get(f"{self.definition.base_url}/tasks", headers=self._headers(), params={"limit": max_results}, timeout=15)
        if resp.status_code != 200:
            return []
        return [t for t in resp.json() if query.lower() in t.get("content", "").lower()]
