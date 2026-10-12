from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

try:
    import httpx

    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False
    logger.warning("httpx not available; GitHub/GitLab API calls disabled")


class CIManager:
    """Trigger and monitor CI/CD pipelines via provider APIs."""

    # ------------------------------------------------------------------
    # GitHub Actions
    # ------------------------------------------------------------------

    @staticmethod
    async def trigger_github_action(
        owner: str,
        repo: str,
        workflow: str,
        ref: str = "main",
        inputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not _HAS_HTTPX:
            raise ImportError("httpx is required for GitHub Actions API")

        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_TOKEN or GH_TOKEN must be set")

        workflow_file = workflow if workflow.endswith(".yml") or workflow.endswith(".yaml") else f"{workflow}.yml"
        url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_file}/dispatches"

        payload: dict[str, Any] = {"ref": ref}
        if inputs:
            payload["inputs"] = inputs

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                json=payload,
            )
            if resp.status_code not in (204, 201, 200):
                raise RuntimeError(
                    f"GitHub dispatch failed ({resp.status_code}): {resp.text}"
                )

            # If the API returned a JSON body, parse it
            try:
                return resp.json()
            except json.JSONDecodeError:
                return {"status": "dispatched", "workflow": workflow, "ref": ref}

    @staticmethod
    async def check_github_run_status(
        owner: str,
        repo: str,
        run_id: str | int,
    ) -> dict[str, Any]:
        if not _HAS_HTTPX:
            raise ImportError("httpx is required for GitHub Actions API")

        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_TOKEN or GH_TOKEN must be set")

        url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "id": data.get("id"),
            "status": data.get("status"),
            "conclusion": data.get("conclusion"),
            "html_url": data.get("html_url"),
            "head_branch": data.get("head_branch"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "event": data.get("event"),
        }

    @staticmethod
    async def list_github_workflows(
        owner: str, repo: str
    ) -> list[dict[str, Any]]:
        if not _HAS_HTTPX:
            raise ImportError("httpx is required for GitHub Actions API")

        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_TOKEN or GH_TOKEN must be set")

        url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("workflows", [])

    # ------------------------------------------------------------------
    # GitLab CI
    # ------------------------------------------------------------------

    @staticmethod
    async def trigger_gitlab_pipeline(
        project_id: str | int,
        ref: str = "main",
        variables: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if not _HAS_HTTPX:
            raise ImportError("httpx is required for GitLab API")

        token = os.environ.get("GITLAB_TOKEN")
        if not token:
            raise RuntimeError("GITLAB_TOKEN must be set")

        url = f"https://gitlab.com/api/v4/projects/{project_id}/trigger/pipeline"
        payload: dict[str, Any] = {"ref": ref, "token": token}
        if variables:
            payload["variables"] = variables

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=payload)
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    async def check_gitlab_pipeline_status(
        project_id: str | int,
        pipeline_id: str | int,
    ) -> dict[str, Any]:
        if not _HAS_HTTPX:
            raise ImportError("httpx is required for GitLab API")

        token = os.environ.get("GITLAB_TOKEN")
        if not token:
            raise RuntimeError("GITLAB_TOKEN must be set")

        url = f"https://gitlab.com/api/v4/projects/{project_id}/pipelines/{pipeline_id}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "id": data.get("id"),
            "status": data.get("status"),
            "ref": data.get("ref"),
            "web_url": data.get("web_url"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
        }

    @staticmethod
    async def list_gitlab_pipelines(
        project_id: str | int, ref: str | None = None
    ) -> list[dict[str, Any]]:
        if not _HAS_HTTPX:
            raise ImportError("httpx is required for GitLab API")

        token = os.environ.get("GITLAB_TOKEN")
        if not token:
            raise RuntimeError("GITLAB_TOKEN must be set")

        url = f"https://gitlab.com/api/v4/projects/{project_id}/pipelines"
        params: dict[str, Any] = {}
        if ref:
            params["ref"] = ref

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )
            resp.raise_for_status()
            return resp.json()
