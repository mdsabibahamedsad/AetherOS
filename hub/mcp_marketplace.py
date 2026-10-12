"""MCP Marketplace — browse, install, configure, and test MCP server connections."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from aetheros_constants import get_aetheros_home
from hub.store import HubStore
from hub.models import HubCategory, HubItem, HubAuthor, InstallStatus
from hub.permissions import PermissionManager, Permission

logger = logging.getLogger(__name__)


BUILTIN_MCP_SERVERS: list[dict] = [
    {"id": "mcp_filesystem", "name": "Filesystem", "description": "Secure file system access with allowed directories",
     "author": "Aetheros", "version": "1.1.0", "official": True, "category": "storage",
     "repo": "https://github.com/modelcontextprotocol/filesystem-server",
     "permissions": ["filesystem"], "config_schema": {"type": "object", "properties": {"allowed_directories": {"type": "array", "items": {"type": "string"}}}},
     "install_command": "npx @modelcontextprotocol/server-filesystem"},
    {"id": "mcp_github", "name": "GitHub", "description": "GitHub API integration — repos, PRs, issues, gists",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "development",
     "repo": "https://github.com/modelcontextprotocol/github-server",
     "permissions": ["network", "git"], "install_command": "npx @modelcontextprotocol/server-github"},
    {"id": "mcp_gitlab", "name": "GitLab", "description": "GitLab API integration — projects, MRs, pipelines",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "development",
     "permissions": ["network", "git"], "install_command": "npx @modelcontextprotocol/server-gitlab"},
    {"id": "mcp_docker", "name": "Docker", "description": "Manage Docker containers, images, and compose stacks",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "infrastructure",
     "permissions": ["docker", "terminal"], "install_command": "npx @modelcontextprotocol/server-docker"},
    {"id": "mcp_browser", "name": "Browser", "description": "Headless browser automation — navigate, click, extract",
     "author": "Aetheros", "version": "1.2.0", "official": True, "category": "automation",
     "permissions": ["browser", "network"], "install_command": "npx @modelcontextprotocol/server-browser"},
    {"id": "mcp_postgres", "name": "PostgreSQL", "description": "Read-only PostgreSQL database access",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "database",
     "permissions": ["network"], "install_command": "npx @modelcontextprotocol/server-postgres"},
    {"id": "mcp_sqlite", "name": "SQLite", "description": "SQLite database exploration and queries",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "database",
     "permissions": ["filesystem"], "install_command": "npx @modelcontextprotocol/server-sqlite"},
    {"id": "mcp_slack", "name": "Slack", "description": "Slack workspace integration — messages, channels, users",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "communication",
     "permissions": ["network", "notifications"], "install_command": "npx @modelcontextprotocol/server-slack"},
    {"id": "mcp_discord", "name": "Discord", "description": "Discord bot integration — messages, channels, roles",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "communication",
     "permissions": ["network"], "install_command": "npx @modelcontextprotocol/server-discord"},
    {"id": "mcp_telegram", "name": "Telegram", "description": "Telegram bot — messages, groups, file sharing",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "communication",
     "permissions": ["network"], "install_command": "npx @modelcontextprotocol/server-telegram"},
    {"id": "mcp_google_drive", "name": "Google Drive", "description": "Google Drive file management and search",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "storage",
     "permissions": ["network"], "install_command": "npx @modelcontextprotocol/server-google-drive"},
    {"id": "mcp_notion", "name": "Notion", "description": "Notion workspace — pages, databases, search",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "productivity",
     "permissions": ["network"], "install_command": "npx @modelcontextprotocol/server-notion"},
    {"id": "mcp_jira", "name": "Jira", "description": "Jira integration — issues, sprints, projects",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "project_management",
     "permissions": ["network"], "install_command": "npx @modelcontextprotocol/server-jira"},
    {"id": "mcp_linear", "name": "Linear", "description": "Linear issue tracking — teams, cycles, issues",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "project_management",
     "permissions": ["network"], "install_command": "npx @modelcontextprotocol/server-linear"},
    {"id": "mcp_aws", "name": "AWS", "description": "AWS service management — EC2, S3, Lambda, IAM",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "cloud",
     "permissions": ["network", "terminal"], "install_command": "npx @modelcontextprotocol/server-aws"},
    {"id": "mcp_azure", "name": "Azure", "description": "Azure resource management — VMs, storage, functions",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "cloud",
     "permissions": ["network"], "install_command": "npx @modelcontextprotocol/server-azure"},
    {"id": "mcp_cloudflare", "name": "Cloudflare", "description": "Cloudflare API — zones, DNS, workers, KV",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "cloud",
     "permissions": ["network"], "install_command": "npx @modelcontextprotocol/server-cloudflare"},
    {"id": "mcp_openapi", "name": "OpenAPI", "description": "Dynamic API client from any OpenAPI spec",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "api",
     "permissions": ["network"], "install_command": "npx @modelcontextprotocol/server-openapi"},
    {"id": "mcp_redis", "name": "Redis", "description": "Redis database operations — keys, values, pub/sub",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "database",
     "permissions": ["network"], "install_command": "npx @modelcontextprotocol/server-redis"},
    {"id": "mcp_memory", "name": "Memory", "description": "Persistent memory store for cross-session context",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "ai",
     "permissions": ["memory", "filesystem"], "install_command": "npx @modelcontextprotocol/server-memory"},
    {"id": "mcp_puppeteer", "name": "Puppeteer", "description": "Browser automation with Puppeteer — screenshots, PDFs",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "automation",
     "permissions": ["browser", "screenshot"], "install_command": "npx @modelcontextprotocol/server-puppeteer"},
    {"id": "mcp_sequentialthinking", "name": "Sequential Thinking", "description": "Structured thinking tool for complex problem-solving",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "ai",
     "permissions": [], "install_command": "npx @modelcontextprotocol/server-sequential-thinking"},
    {"id": "mcp_everything", "name": "Everything", "description": "Reference MCP server with all resource/tool types for testing",
     "author": "Aetheros", "version": "1.0.0", "official": True, "category": "development",
     "permissions": [], "install_command": "npx @modelcontextprotocol/server-everything"},
]


class MCPMarketplace:
    def __init__(self, store: Optional[HubStore] = None):
        self.store = store or HubStore()
        self.permissions = PermissionManager(self.store)
        self.mcp_dir = get_aetheros_home() / "mcp"
        self.mcp_dir.mkdir(parents=True, exist_ok=True)

    def get_catalog(self, category: str = None) -> list[dict]:
        if category:
            return [s for s in BUILTIN_MCP_SERVERS if s.get("category") == category]
        return list(BUILTIN_MCP_SERVERS)

    def get_categories(self) -> list[str]:
        cats = set()
        for s in BUILTIN_MCP_SERVERS:
            cats.add(s.get("category", "other"))
        return sorted(cats)

    def get_server(self, server_id: str) -> Optional[dict]:
        for s in BUILTIN_MCP_SERVERS:
            if s["id"] == server_id:
                return dict(s)
        item = self.store.get_installed_item(server_id)
        if item:
            return dict(item)
        return None

    def install(self, server_id: str, config: dict = None) -> dict:
        existing = self.store.get_installed_item(server_id)
        if existing:
            return {"success": True, "server_id": server_id, "path": existing.get("install_path", "")}

        info = self.get_server(server_id)
        if not info:
            return {"success": False, "error": f"MCP server {server_id} not found"}

        server_dir = self.mcp_dir / server_id
        server_dir.mkdir(parents=True, exist_ok=True)

        install_cmd = info.get("install_command", "")
        if install_cmd:
            logger.info("Installing MCP server %s: %s", server_id, install_cmd)
            try:
                result = subprocess.run(install_cmd, shell=True, capture_output=True,
                                        text=True, cwd=str(server_dir), timeout=120)
                if result.returncode != 0:
                    logger.warning("MCP install stderr: %s", result.stderr)
            except subprocess.TimeoutExpired:
                logger.warning("MCP install timed out for %s", server_id)

        manifest_path = server_dir / "manifest.json"
        merged_config = {**info.get("config_schema", {})}
        if config:
            merged_config.update(config)
        manifest = {
            "name": info["name"], "version": info.get("version", "1.0.0"),
            "description": info.get("description", ""), "server_id": server_id,
            "install_command": install_cmd, "config": merged_config,
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        permissions_needed = [Permission(p) for p in info.get("permissions", [])
                              if p in [e.value for e in Permission]]
        self.permissions.request_many(server_id, permissions_needed)

        self.store.install_item(
            server_id, info["name"], "mcp_servers", info.get("version", "1.0.0"),
            description=info.get("description", ""),
            author=info.get("author", "Aetheros"),
            tags=[info.get("category", "")],
            permissions=info.get("permissions", []),
            manifest=manifest,
            install_path=str(server_dir),
        )
        logger.info("Installed MCP server: %s", server_id)
        return {"success": True, "server_id": server_id, "path": str(server_dir)}

    def uninstall(self, server_id: str) -> dict:
        server_dir = self.mcp_dir / server_id
        if server_dir.exists():
            config_path = server_dir / "config.json"
            config_backup = None
            if config_path.exists():
                config_backup = config_path.read_text()
            shutil.rmtree(server_dir, ignore_errors=True)
        self.store.remove_item(server_id)
        logger.info("Uninstalled MCP server: %s", server_id)
        return {"success": True, "server_id": server_id}

    def configure(self, server_id: str, config: dict) -> dict:
        server_dir = self.mcp_dir / server_id
        if not server_dir.exists():
            return {"success": False, "error": "Server not installed"}
        config_path = server_dir / "config.json"
        existing = {}
        if config_path.exists():
            existing = json.loads(config_path.read_text())
        existing.update(config)
        config_path.write_text(json.dumps(existing, indent=2))
        self.store.install_item(server_id, server_id, "mcp_servers", "1.0.0",
                                manifest={"config": existing})
        return {"success": True, "config": existing}

    def test_connection(self, server_id: str) -> dict:
        server_dir = self.mcp_dir / server_id
        if not server_dir.exists():
            return {"success": False, "error": "Server not installed"}
        info = self.get_server(server_id)
        install_cmd = info.get("install_command", "") if info else ""
        if install_cmd:
            try:
                result = subprocess.run(
                    f"{install_cmd} --version" if "npx" in install_cmd else install_cmd,
                    shell=True, capture_output=True, text=True, timeout=15)
                if result.returncode == 0:
                    version = result.stdout.strip() or result.stderr.strip()
                    return {"success": True, "server_id": server_id, "version": version}
                return {"success": False, "error": result.stderr.strip()}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": True, "server_id": server_id, "note": "No install command"}

    def list_installed(self) -> list[dict]:
        return self.store.get_installed("mcp_servers")

    def enable(self, server_id: str) -> bool:
        return self.store.set_enabled(server_id, True)

    def disable(self, server_id: str) -> bool:
        return self.store.set_enabled(server_id, False)

    def update(self, server_id: str) -> dict:
        return self.install(server_id)
