from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import httpx

    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False


class GitAutomation:
    """Git operations via subprocess."""

    # ------------------------------------------------------------------
    # repo lifecycle
    # ------------------------------------------------------------------

    @staticmethod
    async def clone(url: str, dest_path: str, branch: str | None = None) -> str:
        cmd = f"git clone {url} {dest_path}"
        if branch:
            cmd = f"git clone -b {branch} {url} {dest_path}"
        logger.debug("clone %s -> %s (branch=%s)", url, dest_path, branch)
        result = await _run_git(cmd)
        return result["stdout"]

    @staticmethod
    async def init(path: str) -> str:
        result = await _run_git(f"git init", cwd=path)
        return result["stdout"]

    # ------------------------------------------------------------------
    # staging / commit
    # ------------------------------------------------------------------

    @staticmethod
    async def add(files: str | list[str], path: str = ".") -> str:
        if isinstance(files, list):
            files_str = " ".join(files)
        else:
            files_str = files
        result = await _run_git(f"git add {files_str}", cwd=path)
        return result["stdout"]

    @staticmethod
    async def commit(message: str, path: str = ".") -> str:
        result = await _run_git(f'git commit -m "{message}"', cwd=path)
        return result["stdout"]

    # ------------------------------------------------------------------
    # remote
    # ------------------------------------------------------------------

    @staticmethod
    async def push(remote: str = "origin", branch: str | None = None, path: str = ".") -> str:
        cmd = f"git push {remote}"
        if branch:
            cmd = f"git push {remote} {branch}"
        result = await _run_git(cmd, cwd=path)
        return result["stdout"]

    @staticmethod
    async def pull(remote: str = "origin", branch: str | None = None, path: str = ".") -> str:
        cmd = f"git pull {remote}"
        if branch:
            cmd = f"git pull {remote} {branch}"
        result = await _run_git(cmd, cwd=path)
        return result["stdout"]

    # ------------------------------------------------------------------
    # branching
    # ------------------------------------------------------------------

    @staticmethod
    async def create_branch(name: str, path: str = ".") -> str:
        result = await _run_git(f"git branch {name}", cwd=path)
        return result["stdout"]

    @staticmethod
    async def checkout(branch: str, path: str = ".") -> str:
        result = await _run_git(f"git checkout {branch}", cwd=path)
        return result["stdout"]

    @staticmethod
    async def merge(branch: str, path: str = ".") -> str:
        result = await _run_git(f"git merge {branch}", cwd=path)
        return result["stdout"]

    # ------------------------------------------------------------------
    # pull requests (GitHub API)
    # ------------------------------------------------------------------

    @staticmethod
    async def create_pr(
        title: str,
        body: str,
        head: str,
        base: str,
        remote: str = "origin",
    ) -> str:
        if not _HAS_HTTPX:
            raise ImportError("httpx is required for create_pr")
        remote_url = await _get_remote_url(remote)
        owner, repo = _parse_github_url(remote_url)
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_TOKEN or GH_TOKEN must be set")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.github.com/repos/{owner}/{repo}/pulls",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                json={"title": title, "body": body, "head": head, "base": base},
            )
            resp.raise_for_status()
            data = resp.json()
            return str(data.get("html_url", data.get("url", "")))

    # ------------------------------------------------------------------
    # inspection
    # ------------------------------------------------------------------

    @staticmethod
    async def status(path: str = ".") -> list[dict[str, Any]]:
        result = await _run_git("git status --porcelain", cwd=path)
        entries: list[dict[str, Any]] = []
        for line in result["stdout"].splitlines():
            line = line.strip()
            if not line:
                continue
            xy = line[:2].strip()
            file_path = line[3:].strip()
            entries.append({"status": xy, "file": file_path})
        return entries

    @staticmethod
    async def log(path: str = ".", max_count: int = 10) -> list[dict[str, Any]]:
        fmt = '--format={"hash":"%H","author":"%an","email":"%ae","date":"%ai","message":"%s"}'
        result = await _run_git(
            f"git log {fmt} -{max_count}", cwd=path
        )
        commits: list[dict[str, Any]] = []
        for line in result["stdout"].splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                commits.append(json.loads(line))
            except json.JSONDecodeError:
                commits.append({"raw": line})
        return commits

    @staticmethod
    async def diff(path: str = ".", ref1: str | None = None, ref2: str | None = None) -> str:
        if ref1 and ref2:
            cmd = f"git diff {ref1} {ref2}"
        elif ref1:
            cmd = f"git diff {ref1}"
        else:
            cmd = "git diff"
        result = await _run_git(cmd, cwd=path)
        return result["stdout"]

    # ------------------------------------------------------------------
    # stash
    # ------------------------------------------------------------------

    @staticmethod
    async def stash(path: str = ".") -> str:
        result = await _run_git("git stash", cwd=path)
        return result["stdout"]

    @staticmethod
    async def stash_pop(path: str = ".") -> str:
        result = await _run_git("git stash pop", cwd=path)
        return result["stdout"]


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------

async def _run_git(cmd: str, cwd: str | None = None) -> dict[str, Any]:
    from aetheros_automation.terminal.runner import TerminalRunner

    return await TerminalRunner.run(cmd, cwd=cwd)


async def _get_remote_url(remote: str = "origin") -> str:
    result = await _run_git(f"git remote get-url {remote}")
    return result["stdout"].strip()


def _parse_github_url(url: str) -> tuple[str, str]:
    """Extract owner/repo from a GitHub remote URL."""
    url = url.strip()
    if url.startswith("git@github.com:"):
        parts = url.replace("git@github.com:", "").rstrip(".git").split("/")
        return parts[0], parts[1]
    if "github.com" in url:
        parts = url.split("github.com/")[1].rstrip(".git").split("/")
        return parts[0], parts[1]
    raise ValueError(f"Not a recognised GitHub URL: {url}")
