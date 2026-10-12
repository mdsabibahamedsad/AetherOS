"""AetherOS Integrations — knowledge platform adapters.

Notion, Confluence, Obsidian (local vault), Logseq (local), Wiki.js, and
BookStack. Search and store documents/pages.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from aetheros_integrations.models import AuthMethod, HealthStatus, IntegrationCategory, ProviderDefinition
from aetheros_integrations.providers.base import RESTProvider, register_provider

logger = logging.getLogger(__name__)


@register_provider
class NotionProvider(RESTProvider):
    definition = ProviderDefinition(
        key="notion",
        category=IntegrationCategory.KNOWLEDGE,
        display_name="Notion",
        description="Notion API: search pages, create pages, append blocks.",
        auth_method=AuthMethod.BEARER,
        base_url="https://api.notion.com/v1",
        capabilities=["search_documents", "create_record", "update_record"],
    )

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        return {**super()._headers(extra), "Notion-Version": "2022-06-28"}

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.post(f"{self.definition.base_url}/search", headers=self._headers(), json={"page_size": 1}, timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def search_documents(self, query: str, max_results: int = 10, **kwargs) -> List[Dict[str, Any]]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return []
        resp = httpx.post(f"{self.definition.base_url}/search", headers={**self._headers(), "Content-Type": "application/json"}, json={"query": query, "page_size": max_results}, timeout=15)
        return resp.json().get("results", []) if resp.status_code == 200 else []

    def create_record(self, parent_id: str, title: str, content: str = "", **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no notion credential"}
        children = [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": content}}]}}] if content else []
        resp = httpx.post(
            f"{self.definition.base_url}/pages",
            headers={**self._headers(), "Content-Type": "application/json"},
            json={
                "parent": {"page_id": parent_id},
                "properties": {"title": {"title": [{"type": "text", "text": {"content": title}}]}},
                "children": children,
            },
            timeout=15,
        )
        return {"success": resp.status_code == 200, "status": resp.status_code, "data": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}}


@register_provider
class ConfluenceProvider(RESTProvider):
    definition = ProviderDefinition(
        key="confluence",
        category=IntegrationCategory.KNOWLEDGE,
        display_name="Confluence",
        description="Confluence Cloud REST API: search, create pages.",
        auth_method=AuthMethod.BASIC,
        base_url="https://your-domain.atlassian.net/wiki",
        capabilities=["search_documents", "create_record"],
    )

    def _base(self) -> str:
        return self.config.get("site_url", self.definition.base_url).rstrip("/")

    def _auth(self):
        return (self.config.get("username", ""), self.config.get("api_token", ""))

    def ping(self) -> HealthStatus:
        if not self.config.get("api_token"):
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.get(self._base() + "/rest/api/user/current", auth=self._auth(), timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def search_documents(self, query: str, max_results: int = 10, **kwargs) -> List[Dict[str, Any]]:
        if not self.config.get("api_token"):
            return []
        resp = httpx.get(self._base() + "/rest/api/content/search", auth=self._auth(), params={"cql": f'text~"{query}"', "limit": max_results}, timeout=15)
        return resp.json().get("results", []) if resp.status_code == 200 else []

    def create_record(self, space_key: str, title: str, content: str = "", **kwargs) -> Dict[str, Any]:
        if not self.config.get("api_token"):
            return {"success": False, "error": "no confluence credential"}
        body = content or "<p></p>"
        resp = httpx.post(
            self._base() + "/rest/api/content",
            auth=self._auth(),
            headers={"Content-Type": "application/json"},
            json={"type": "page", "title": title, "space": {"key": space_key}, "body": {"storage": {"value": body, "representation": "storage"}}},
            timeout=15,
        )
        return {"success": resp.status_code in (200, 201), "status": resp.status_code}


class _LocalVaultProvider(RESTProvider):
    """Shared base for local markdown vaults (Obsidian, Logseq)."""

    category = IntegrationCategory.KNOWLEDGE
    auth_method = AuthMethod.NONE

    def _vault(self) -> Optional[Path]:
        path = self.config.get("vault_path", "")
        if not path:
            return None
        p = Path(path)
        return p if p.is_dir() else None

    def ping(self) -> HealthStatus:
        return HealthStatus.HEALTHY if self._vault() else HealthStatus.UNAVAILABLE

    def search_documents(self, query: str, max_results: int = 10, **kwargs) -> List[Dict[str, Any]]:
        vault = self._vault()
        if not vault:
            return []
        q = query.lower()
        out = []
        for f in vault.rglob("*.md"):
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if q in text.lower():
                out.append({"path": str(f.relative_to(vault)), "name": f.stem, "matches": text.lower().count(q)})
            if len(out) >= max_results:
                break
        return out

    def create_record(self, title: str, content: str = "", folder: str = "", **kwargs) -> Dict[str, Any]:
        vault = self._vault()
        if not vault:
            return {"success": False, "error": "no vault path configured"}
        safe = re.sub(r"[^A-Za-z0-9 _-]", "", title).strip().replace(" ", "-")
        target_dir = vault / folder if folder else vault
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{safe or 'note'}.md"
        path.write_text(f"# {title}\n\n{content}\n", encoding="utf-8")
        return {"success": True, "path": str(path.relative_to(vault))}


@register_provider
class ObsidianProvider(_LocalVaultProvider):
    definition = ProviderDefinition(
        key="obsidian",
        category=IntegrationCategory.KNOWLEDGE,
        display_name="Obsidian",
        description="Search and create notes in a local Obsidian vault.",
        auth_method=AuthMethod.NONE,
        capabilities=["search_documents", "create_record"],
    )


@register_provider
class LogseqProvider(_LocalVaultProvider):
    definition = ProviderDefinition(
        key="logseq",
        category=IntegrationCategory.KNOWLEDGE,
        display_name="Logseq",
        description="Search and create pages in a local Logseq graph.",
        auth_method=AuthMethod.NONE,
        capabilities=["search_documents", "create_record"],
    )

    def create_record(self, title: str, content: str = "", folder: str = "pages", **kwargs) -> Dict[str, Any]:
        return super().create_record(title=title, content=content, folder=folder)


@register_provider
class WikiJSProvider(RESTProvider):
    definition = ProviderDefinition(
        key="wiki_js",
        category=IntegrationCategory.KNOWLEDGE,
        display_name="Wiki.js",
        description="Wiki.js GraphQL API: search, create pages.",
        auth_method=AuthMethod.BEARER,
        base_url="https://example.com",
        capabilities=["search_documents", "create_record"],
    )

    def _endpoint(self) -> str:
        return self.config.get("endpoint", self.definition.base_url).rstrip("/") + "/graphql"

    def _token(self) -> str:
        return self.config.get("_auth_header", {}).get("Authorization", "")

    def ping(self) -> HealthStatus:
        if not self._token():
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.post(self._endpoint(), headers=self._headers(), json={"query": "{ site { config { title } } }"}, timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def search_documents(self, query: str, max_results: int = 10, **kwargs) -> List[Dict[str, Any]]:
        if not self._token():
            return []
        gql = f'{{ search {query} }}' if False else '{ pages { list { id title } } }'
        resp = httpx.post(self._endpoint(), headers=self._headers(), json={"query": gql}, timeout=15)
        if resp.status_code != 200:
            return []
        pages = resp.json().get("data", {}).get("pages", {}).get("list", [])
        return [p for p in pages if query.lower() in p.get("title", "").lower()][:max_results]


@register_provider
class BookStackProvider(RESTProvider):
    definition = ProviderDefinition(
        key="bookstack",
        category=IntegrationCategory.KNOWLEDGE,
        display_name="BookStack",
        description="BookStack REST API: search, create pages.",
        auth_method=AuthMethod.BEARER,
        base_url="https://example.com",
        capabilities=["search_documents", "create_record"],
    )

    def _endpoint(self) -> str:
        return self.config.get("endpoint", self.definition.base_url).rstrip("/") + "/api"

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = super()._headers(extra)
        h["Authorization"] = "Token " + self.config.get("token_id", "") + ":" + self.config.get("token_secret", "")
        return h

    def ping(self) -> HealthStatus:
        if not self.config.get("token_secret"):
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.get(self._endpoint() + "/books", headers=self._headers(), timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def search_documents(self, query: str, max_results: int = 10, **kwargs) -> List[Dict[str, Any]]:
        if not self.config.get("token_secret"):
            return []
        resp = httpx.get(self._endpoint() + "/pages", headers=self._headers(), params={"search": query, "count": max_results}, timeout=15)
        return resp.json().get("data", []) if resp.status_code == 200 else []

    def create_record(self, book_id: str, title: str, content: str = "", **kwargs) -> Dict[str, Any]:
        if not self.config.get("token_secret"):
            return {"success": False, "error": "no bookstack credential"}
        resp = httpx.post(self._endpoint() + "/pages", headers={**self._headers(), "Content-Type": "application/json"}, json={"book_id": int(book_id), "name": title, "html": content}, timeout=15)
        return {"success": resp.status_code == 200, "status": resp.status_code}
