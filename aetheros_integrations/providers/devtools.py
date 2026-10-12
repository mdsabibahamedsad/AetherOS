"""AetherOS Integrations — developer platform adapters.

GitHub, GitLab, Bitbucket, Azure DevOps. Repositories, issues, PRs, actions,
releases, projects.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from aetheros_integrations.models import AuthMethod, HealthStatus, IntegrationCategory, ProviderDefinition
from aetheros_integrations.providers.base import RESTProvider, register_provider

logger = logging.getLogger(__name__)


@register_provider
class GitHubProvider(RESTProvider):
    definition = ProviderDefinition(
        key="github",
        category=IntegrationCategory.DEVOPS,
        display_name="GitHub",
        description="GitHub REST API: repos, issues, PRs, actions, releases.",
        auth_method=AuthMethod.PAT,
        base_url="https://api.github.com",
        capabilities=["list_repos", "create_issue", "list_prs", "create_pr", "list_releases", "run_actions", "projects"],
    )

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.get(f"{self.definition.base_url}/user", headers=self._headers(), timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def _repo(self, repo: str) -> str:
        return repo if "/" in repo else f"{self.config.get('owner', '')}/{repo}".strip("/")

    def list_repos(self, owner: str = "", **kwargs) -> List[Dict[str, Any]]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return []
        user = owner or self.config.get("owner", "user")
        resp = httpx.get(f"{self.definition.base_url}/user/repos" if user == "user" else f"{self.definition.base_url}/users/{user}/repos", headers=self._headers(), params={"per_page": kwargs.get("max_results", 30)}, timeout=15)
        return resp.json() if resp.status_code == 200 else []

    def create_issue(self, repo: str, title: str, body: str = "", **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no github token"}
        payload = {"title": title, "body": body}
        if kwargs.get("labels"):
            payload["labels"] = kwargs["labels"]
        resp = httpx.post(f"{self.definition.base_url}/repos/{self._repo(repo)}/issues", headers={**self._headers(), "Content-Type": "application/json"}, json=payload, timeout=15)
        return {"success": resp.status_code == 201, "status": resp.status_code, "data": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}}

    def list_prs(self, repo: str, state: str = "open", **kwargs) -> List[Dict[str, Any]]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return []
        resp = httpx.get(f"{self.definition.base_url}/repos/{self._repo(repo)}/pulls", headers=self._headers(), params={"state": state, "per_page": kwargs.get("max_results", 30)}, timeout=15)
        return resp.json() if resp.status_code == 200 else []

    def create_pr(self, repo: str, title: str, head: str, base: str, body: str = "") -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no github token"}
        resp = httpx.post(f"{self.definition.base_url}/repos/{self._repo(repo)}/pulls", headers={**self._headers(), "Content-Type": "application/json"}, json={"title": title, "head": head, "base": base, "body": body}, timeout=15)
        return {"success": resp.status_code == 201, "status": resp.status_code}

    def list_releases(self, repo: str, **kwargs) -> List[Dict[str, Any]]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return []
        resp = httpx.get(f"{self.definition.base_url}/repos/{self._repo(repo)}/releases", headers=self._headers(), params={"per_page": kwargs.get("max_results", 10)}, timeout=15)
        return resp.json() if resp.status_code == 200 else []

    def run_actions(self, repo: str, workflow_id: str, ref: str = "main", inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no github token"}
        resp = httpx.post(
            f"{self.definition.base_url}/repos/{self._repo(repo)}/actions/workflows/{workflow_id}/dispatches",
            headers={**self._headers(), "Content-Type": "application/json", "Accept": "application/vnd.github+json"},
            json={"ref": ref, "inputs": inputs or {}},
            timeout=15,
        )
        return {"success": resp.status_code == 204, "status": resp.status_code}


@register_provider
class GitLabProvider(RESTProvider):
    definition = ProviderDefinition(
        key="gitlab",
        category=IntegrationCategory.DEVOPS,
        display_name="GitLab",
        description="GitLab REST API v4: projects, issues, MRs, pipelines.",
        auth_method=AuthMethod.PAT,
        base_url="https://gitlab.com/api/v4",
        capabilities=["list_repos", "create_issue", "list_prs", "run_actions", "releases"],
    )

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.get(f"{self.definition.base_url}/version", headers=self._headers(), timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def list_repos(self, **kwargs) -> List[Dict[str, Any]]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return []
        resp = httpx.get(f"{self.definition.base_url}/projects", headers=self._headers(), params={"membership": "true", "per_page": kwargs.get("max_results", 30), "simple": "true"}, timeout=15)
        return resp.json() if resp.status_code == 200 else []

    def create_issue(self, repo: str, title: str, body: str = "", **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no gitlab token"}
        pid = httpx.utils.quote(repo, safe="")
        resp = httpx.post(f"{self.definition.base_url}/projects/{pid}/issues", headers={**self._headers(), "Content-Type": "application/json"}, json={"title": title, "description": body}, timeout=15)
        return {"success": resp.status_code == 201, "status": resp.status_code}

    def run_actions(self, repo: str, pipeline_config: str = ".gitlab-ci.yml", ref: str = "main", **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no gitlab token"}
        pid = httpx.utils.quote(repo, safe="")
        resp = httpx.post(f"{self.definition.base_url}/projects/{pid}/pipeline", headers={**self._headers(), "Content-Type": "application/json"}, json={"ref": ref}, timeout=15)
        return {"success": resp.status_code == 201, "status": resp.status_code}


@register_provider
class BitbucketProvider(RESTProvider):
    definition = ProviderDefinition(
        key="bitbucket",
        category=IntegrationCategory.DEVOPS,
        display_name="Bitbucket",
        description="Bitbucket Cloud REST API: repos, issues, PRs.",
        auth_method=AuthMethod.BASIC,
        base_url="https://api.bitbucket.org/2.0",
        capabilities=["list_repos", "create_issue", "list_prs"],
    )

    def _workspace(self) -> str:
        return self.config.get("workspace", "")

    def _auth(self):
        return (self.config.get("username", ""), self.config.get("app_password", ""))

    def ping(self) -> HealthStatus:
        if not self._workspace():
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.get(f"{self.definition.base_url}/user", auth=self._auth(), timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def list_repos(self, **kwargs) -> List[Dict[str, Any]]:
        if not self._workspace():
            return []
        resp = httpx.get(f"{self.definition.base_url}/repositories/{self._workspace()}", auth=self._auth(), params={"pagelen": kwargs.get("max_results", 30)}, timeout=15)
        return resp.json().get("values", []) if resp.status_code == 200 else []

    def create_issue(self, repo: str, title: str, body: str = "", **kwargs) -> Dict[str, Any]:
        if not self._workspace():
            return {"success": False, "error": "no workspace"}
        resp = httpx.post(f"{self.definition.base_url}/repositories/{self._workspace()}/{repo}/issues", auth=self._auth(), json={"title": title, "content": {"raw": body}}, timeout=15)
        return {"success": resp.status_code == 201, "status": resp.status_code}


@register_provider
class AzureDevOpsProvider(RESTProvider):
    definition = ProviderDefinition(
        key="azure_devops",
        category=IntegrationCategory.DEVOPS,
        display_name="Azure DevOps",
        description="Azure DevOps REST API: repos, work items, pipelines.",
        auth_method=AuthMethod.PAT,
        base_url="https://dev.azure.com",
        capabilities=["list_repos", "create_issue", "run_actions"],
    )

    def _org(self) -> str:
        return self.config.get("organization", "")

    def _project(self) -> str:
        return self.config.get("project", "")

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token or not self._org():
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.get(f"{self.definition.base_url}/{self._org()}/_apis/projects?api-version=7.0", headers=self._headers(), timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def list_repos(self, **kwargs) -> List[Dict[str, Any]]:
        if not self._org() or not self._project():
            return []
        resp = httpx.get(f"{self.definition.base_url}/{self._org()}/{self._project()}/_apis/git/repositories?api-version=7.0", headers=self._headers(), timeout=15)
        return resp.json().get("value", []) if resp.status_code == 200 else []

    def create_issue(self, title: str, body: str = "", work_item_type: str = "Task", **kwargs) -> Dict[str, Any]:
        if not self._org() or not self._project():
            return {"success": False, "error": "no azure devops org/project"}
        patch = [{"op": "add", "path": "/fields/System.Title", "value": title}]
        if body:
            patch.append({"op": "add", "path": "/fields/System.Description", "value": body})
        resp = httpx.patch(f"{self.definition.base_url}/{self._org()}/{self._project()}/_apis/wit/workitems/${work_item_type}?api-version=7.0", headers={**self._headers(), "Content-Type": "application/json-patch+json"}, json=patch, timeout=15)
        return {"success": resp.status_code in (200, 201), "status": resp.status_code}

    def run_actions(self, pipeline_id: str, **kwargs) -> Dict[str, Any]:
        if not self._org() or not self._project():
            return {"success": False, "error": "no azure devops config"}
        resp = httpx.post(f"{self.definition.base_url}/{self._org()}/{self._project()}/_apis/build/builds?api-version=7.0", headers={**self._headers(), "Content-Type": "application/json"}, json={"definition": {"id": int(pipeline_id)}}, timeout=15)
        return {"success": resp.status_code in (200, 201), "status": resp.status_code}
