"""Auto-discovery — detect local services and tools (Ollama, Docker, Git, VS Code, etc.)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from connect.store import ConnectStore
from connect.models import (ServiceConnection, ConnectionStatus, SyncMode,
                              ServiceCategory, DiscoveryResult)

logger = logging.getLogger(__name__)


class DiscoveryService:
    def __init__(self, store: Optional[ConnectStore] = None):
        self.store = store or ConnectStore()

    async def discover_all(self) -> list[DiscoveryResult]:
        results = []
        discoverers = [
            self._discover_ollama,
            self._discover_lm_studio,
            self._discover_docker,
            self._discover_git,
            self._discover_python,
            self._discover_node,
            self._discover_github_cli,
            self._discover_vscode,
            self._discover_cursor,
            self._discover_claude_code,
        ]
        for discoverer in discoverers:
            try:
                result = await discoverer()
                results.append(result)
            except Exception as e:
                logger.debug("Discovery error: %s", e)
        return results

    async def discover_and_connect(self) -> list[dict]:
        results = await self.discover_all()
        connected = []
        for r in results:
            if r.detected:
                existing = self.store.list_connections()
                already = any(e.get("service_id") == r.service_id for e in existing)
                if not already:
                    conn = ServiceConnection(
                        id=str(uuid4())[:12],
                        service_id=r.service_id,
                        service_name=r.service_name,
                        category=ServiceCategory.LOCAL,
                        status=ConnectionStatus.CONNECTED,
                        config=r.config,
                        label=f"{r.service_name} (auto-discovered)",
                        sync_mode=SyncMode.MANUAL,
                        connected_at=datetime.utcnow().isoformat() + "Z",
                        metadata={"discovered": True, "path": r.path,
                                  "version": r.version},
                    )
                    self.store.save_connection(conn)
                    connected.append(conn)
        return connected

    async def _discover_ollama(self) -> DiscoveryResult:
        result = DiscoveryResult(service_id="ollama", service_name="Ollama")
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get("http://localhost:11434/api/tags", timeout=2)
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    result.detected = True
                    result.version = "running"
                    result.config = {"base_url": "http://localhost:11434",
                                     "models": models}
                    result.status = f"Running with {len(models)} models"
        except Exception:
            pass
        return result

    async def _discover_lm_studio(self) -> DiscoveryResult:
        result = DiscoveryResult(service_id="lm_studio", service_name="LM Studio")
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get("http://localhost:1234/v1/models", timeout=2)
                if resp.status_code == 200:
                    result.detected = True
                    result.version = "running"
                    result.config = {"base_url": "http://localhost:1234/v1"}
                    result.status = "API server running"
        except Exception:
            pass
        return result

    async def _discover_docker(self) -> DiscoveryResult:
        result = DiscoveryResult(service_id="local_docker", service_name="Docker")
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            if proc.returncode == 0:
                version = stdout.decode().strip()
                result.detected = True
                result.version = version
                result.path = shutil.which("docker") or ""
                result.status = "Available"
        except Exception:
            pass
        return result

    async def _discover_git(self) -> DiscoveryResult:
        result = DiscoveryResult(service_id="local_git", service_name="Git")
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            if proc.returncode == 0:
                version = stdout.decode().strip()
                result.detected = True
                result.version = version
                result.path = shutil.which("git") or ""
                result.status = "Available"
        except Exception:
            pass
        return result

    async def _discover_python(self) -> DiscoveryResult:
        result = DiscoveryResult(service_id="local_python", service_name="Python")
        try:
            proc = await asyncio.create_subprocess_exec(
                "python", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            if proc.returncode == 0:
                version = stdout.decode().strip()
                result.detected = True
                result.version = version
                result.path = shutil.which("python") or ""
                result.status = "Available"
        except Exception:
            pass
        return result

    async def _discover_node(self) -> DiscoveryResult:
        result = DiscoveryResult(service_id="local_node", service_name="Node.js")
        try:
            proc = await asyncio.create_subprocess_exec(
                "node", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            if proc.returncode == 0:
                version = stdout.decode().strip()
                result.detected = True
                result.version = version
                result.path = shutil.which("node") or ""
                result.status = "Available"
        except Exception:
            pass
        return result

    async def _discover_github_cli(self) -> DiscoveryResult:
        result = DiscoveryResult(service_id="local_github_cli", service_name="GitHub CLI")
        try:
            proc = await asyncio.create_subprocess_exec(
                "gh", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            if proc.returncode == 0:
                version = stdout.decode().split("\n")[0] if stdout else "installed"
                result.detected = True
                result.version = version
                result.path = shutil.which("gh") or ""
                result.status = "Available"
        except Exception:
            pass
        return result

    async def _discover_vscode(self) -> DiscoveryResult:
        result = DiscoveryResult(service_id="local_vscode", service_name="VS Code")
        code_path = shutil.which("code")
        if code_path:
            result.detected = True
            result.path = code_path
            result.status = "Installed"
            try:
                proc = await asyncio.create_subprocess_exec(
                    "code", "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE)
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
                if proc.returncode == 0:
                    lines = stdout.decode().strip().split("\n")
                    result.version = lines[0] if lines else ""
            except Exception:
                pass
        return result

    async def _discover_cursor(self) -> DiscoveryResult:
        result = DiscoveryResult(service_id="local_cursor", service_name="Cursor")
        cursor_path = shutil.which("cursor")
        if cursor_path:
            result.detected = True
            result.path = cursor_path
            result.status = "Installed"
        return result

    async def _discover_claude_code(self) -> DiscoveryResult:
        result = DiscoveryResult(service_id="local_claude_code", service_name="Claude Code")
        try:
            proc = await asyncio.create_subprocess_exec(
                "claude", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            if proc.returncode == 0:
                result.detected = True
                result.version = stdout.decode().strip()
                result.path = shutil.which("claude") or ""
                result.status = "Available"
        except Exception:
            pass
        return result
