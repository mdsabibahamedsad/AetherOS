"""Unified Hub marketplace — single catalog across plugins, MCP, skills, themes, agents, workflows."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Optional

from aetheros_constants import get_aetheros_home
from hub.store import HubStore
from hub.models import (HubCategory, HubItem, HubAuthor, HubVersion,
                         HubDependency, HubReview, Permission,
                         PublisherVerification, InstallStatus)

logger = logging.getLogger(__name__)


CATALOG: list[dict] = [
    # ── Featured Plugins ──
    {"id": "plugin_dev_tools", "name": "Dev Tools", "description": "Essential developer tools — lint, format, test, deploy",
     "category": "plugins", "author": "Aetheros", "version": "2.1.0", "official": True,
     "featured": True, "trending": True, "rating": 4.8, "downloads": 12500,
     "tags": ["development", "tools", "productivity"],
     "permissions": ["filesystem", "terminal"], "icon_url": "🔧"},
    {"id": "plugin_web_scraper", "name": "Web Scraper", "description": "Extract structured data from any website",
     "category": "plugins", "author": "Aetheros", "version": "1.3.0", "official": False,
     "trending": True, "rating": 4.5, "downloads": 8700,
     "tags": ["web", "scraping", "data"],
     "permissions": ["network", "filesystem"], "icon_url": "🕸️"},
    {"id": "plugin_git_manager", "name": "Git Manager", "description": "Advanced Git operations — branches, PRs, merge conflict resolution",
     "category": "plugins", "author": "Aetheros", "version": "1.0.0", "official": True,
     "editors_choice": True, "rating": 4.9, "downloads": 15000,
     "tags": ["git", "version-control", "development"],
     "permissions": ["git", "terminal"], "icon_url": "🔀"},
    {"id": "plugin_docker_manager", "name": "Docker Manager", "description": "Manage Docker containers, images, compose, and registries",
     "category": "plugins", "author": "Aetheros", "version": "1.2.0", "official": False,
     "rating": 4.6, "downloads": 6300,
     "tags": ["docker", "containers", "devops"],
     "permissions": ["docker", "terminal"], "icon_url": "🐳"},
    {"id": "plugin_clipboard_manager", "name": "Clipboard History", "description": "Persistent clipboard history with search and snippets",
     "category": "plugins", "author": "Aetheros", "version": "1.0.0", "official": False,
     "rating": 4.3, "downloads": 4200,
     "tags": ["clipboard", "productivity", "utility"],
     "permissions": ["clipboard"], "icon_url": "📋"},
    {"id": "plugin_notion_sync", "name": "Notion Sync", "description": "Two-way sync between AetherOS and Notion workspaces",
     "category": "plugins", "author": "Aetheros", "version": "1.0.0", "official": False,
     "rating": 4.4, "downloads": 5100,
     "tags": ["notion", "sync", "productivity"],
     "permissions": ["network"], "icon_url": "📝"},

    # ── MCP Servers (selected highlights, rest in mcp_marketplace) ──
    {"id": "mcp_filesystem", "name": "Filesystem MCP", "description": "Secure file system access",
     "category": "mcp_servers", "author": "Aetheros", "version": "1.1.0", "official": True,
     "featured": True, "rating": 4.7, "downloads": 20000,
     "tags": ["filesystem", "storage"],
     "permissions": ["filesystem"], "icon_url": "📁"},
    {"id": "mcp_github", "name": "GitHub MCP", "description": "GitHub API — repos, issues, PRs",
     "category": "mcp_servers", "author": "Aetheros", "version": "1.0.0", "official": True,
     "featured": True, "trending": True, "rating": 4.8, "downloads": 18000,
     "tags": ["github", "development"],
     "permissions": ["network", "git"], "icon_url": "🐙"},

    # ── Skill Packs ──
    {"id": "skill_engineering", "name": "Software Engineering", "description": "Full-stack dev skills — coding, debugging, architecture",
     "category": "skills", "author": "Aetheros", "version": "2.0.0", "official": True,
     "featured": True, "rating": 4.9, "downloads": 22000,
     "tags": ["engineering", "development", "coding"], "icon_url": "💻"},
    {"id": "skill_research", "name": "Research", "description": "Academic and technical research — papers, analysis, citations",
     "category": "skills", "author": "Aetheros", "version": "1.5.0", "official": True,
     "rating": 4.6, "downloads": 12000,
     "tags": ["research", "academic", "analysis"], "icon_url": "🔬"},
    {"id": "skill_cybersecurity", "name": "Cybersecurity", "description": "Security analysis, penetration testing, threat modeling",
     "category": "skills", "author": "Aetheros", "version": "1.2.0", "official": True,
     "rating": 4.7, "downloads": 9500,
     "tags": ["security", "pentest", "cybersecurity"], "icon_url": "🛡️"},
    {"id": "skill_devops", "name": "DevOps", "description": "CI/CD, infrastructure as code, cloud management, monitoring",
     "category": "skills", "author": "Aetheros", "version": "1.8.0", "official": True,
     "trending": True, "rating": 4.5, "downloads": 11000,
     "tags": ["devops", "ci-cd", "cloud"], "icon_url": "⚙️"},
    {"id": "skill_business", "name": "Business", "description": "Strategy, analytics, reporting, project management",
     "category": "skills", "author": "Aetheros", "version": "1.0.0", "official": True,
     "rating": 4.3, "downloads": 7800,
     "tags": ["business", "analytics", "management"], "icon_url": "📊"},
    {"id": "skill_writing", "name": "Writing", "description": "Creative and professional writing — articles, docs, scripts",
     "category": "skills", "author": "Aetheros", "version": "1.3.0", "official": True,
     "rating": 4.4, "downloads": 8900,
     "tags": ["writing", "content", "creative"], "icon_url": "✍️"},
    {"id": "skill_automation", "name": "Automation", "description": "Workflow automation, scripting, batch processing",
     "category": "skills", "author": "Aetheros", "version": "1.1.0", "official": True,
     "rating": 4.6, "downloads": 10500,
     "tags": ["automation", "scripts", "productivity"], "icon_url": "🤖"},
    {"id": "skill_data_science", "name": "Data Science", "description": "Data analysis, ML, visualization, statistics",
     "category": "skills", "author": "Aetheros", "version": "1.4.0", "official": True,
     "editors_choice": True, "rating": 4.8, "downloads": 14000,
     "tags": ["data-science", "ml", "analytics"], "icon_url": "📈"},
    {"id": "skill_education", "name": "Education", "description": "Teaching, tutoring, curriculum design, assessment",
     "category": "skills", "author": "Aetheros", "version": "1.0.0", "official": True,
     "rating": 4.2, "downloads": 5600,
     "tags": ["education", "teaching", "learning"], "icon_url": "🎓"},

    # ── Themes ──
    {"id": "theme_dark", "name": "Dark", "description": "Classic dark theme",
     "category": "themes", "author": "Aetheros", "version": "1.0.0", "official": True,
     "featured": True, "rating": 4.5, "downloads": 30000, "tags": ["dark"], "icon_url": "🌙"},
    {"id": "theme_cyberpunk", "name": "Cyberpunk", "description": "Neon aesthetic",
     "category": "themes", "author": "Aetheros", "version": "1.0.0", "official": True,
     "trending": True, "rating": 4.8, "downloads": 25000, "tags": ["cyberpunk", "neon"], "icon_url": "⚡"},

    # ── Workflows ──
    {"id": "wf_daily_report", "name": "Daily Report", "description": "Automated daily report with web research",
     "category": "workflows", "author": "Aetheros", "version": "1.0.0", "official": True,
     "featured": True, "rating": 4.6, "downloads": 8000, "tags": ["report", "daily"], "icon_url": "📰"},
    {"id": "wf_code_review", "name": "Code Review", "description": "AI-powered code review pipeline",
     "category": "workflows", "author": "Aetheros", "version": "1.1.0", "official": True,
     "rating": 4.7, "downloads": 9500, "tags": ["code", "review"], "icon_url": "👁️"},

    # ── Agents ──
    {"id": "agent_developer", "name": "Developer Agent", "description": "Full-stack development assistant",
     "category": "ai_agents", "author": "Aetheros", "version": "1.0.0", "official": True,
     "featured": True, "rating": 4.8, "downloads": 16000, "tags": ["developer", "coding"], "icon_url": "👨‍💻"},
    {"id": "agent_researcher", "name": "Research Agent", "description": "Deep research and analysis specialist",
     "category": "ai_agents", "author": "Aetheros", "version": "1.0.0", "official": True,
     "trending": True, "rating": 4.6, "downloads": 11000, "tags": ["research", "analysis"], "icon_url": "🔬"},

    # ── Tool Packs ──
    {"id": "tools_devops", "name": "DevOps Tool Pack", "description": "Docker, K8s, Terraform, CI/CD tools",
     "category": "tool_packs", "author": "Aetheros", "version": "1.0.0", "official": True,
     "rating": 4.5, "downloads": 7000, "tags": ["devops", "infrastructure"], "icon_url": "🛠️"},
    {"id": "tools_security", "name": "Security Tool Pack", "description": "Vulnerability scanners, crypto tools, network analysis",
     "category": "tool_packs", "author": "Aetheros", "version": "1.0.0", "official": False,
     "rating": 4.4, "downloads": 4500, "tags": ["security", "audit"], "icon_url": "🔐"},

    # ── Language Packs ──
    {"id": "lang_ja", "name": "Japanese", "description": "日本語  language pack",
     "category": "language_packs", "author": "Aetheros", "version": "1.0.0", "official": True,
     "rating": 4.3, "downloads": 3200, "tags": ["japanese"], "icon_url": "🇯🇵"},

    # ── Models ──
    {"id": "model_gpt4o", "name": "GPT-4o", "description": "OpenAI's flagship multimodal model",
     "category": "models", "author": "OpenAI", "version": "latest", "official": False,
     "rating": 4.9, "downloads": 50000, "tags": ["llm", "openai", "multimodal"], "icon_url": "🧠"},
    {"id": "model_claude4", "name": "Claude 4", "description": "Anthropic's most capable model",
     "category": "models", "author": "Anthropic", "version": "latest", "official": False,
     "rating": 4.8, "downloads": 45000, "tags": ["llm", "anthropic"], "icon_url": "🤖"},

    # ── Icon Packs ──
    {"id": "icons_lucide", "name": "Lucide Icons", "description": "Simple, clean SVG icon library",
     "category": "icon_packs", "author": "Lucide", "version": "1.0.0", "official": True,
     "rating": 4.6, "downloads": 12000, "tags": ["icons", "svg"], "icon_url": "🎨"},
]


class HubMarketplace:
    def __init__(self, store: Optional[HubStore] = None):
        self.store = store or HubStore()

    def get_catalog(self, category: str = None) -> list[dict]:
        if category:
            return [c for c in CATALOG if c["category"] == category]
        return list(CATALOG)

    def get_item(self, item_id: str) -> Optional[HubItem]:
        for c in CATALOG:
            if c["id"] == item_id:
                return self._dict_to_item(c)
        item = self.store.get_installed_item(item_id)
        if item:
            return self._dict_to_item({**item, "category": item.get("category", "plugins")})
        return None

    def search(self, query: str, category: str = None,
               tags: list[str] = None, sort_by: str = "") -> list[dict]:
        results = self.get_catalog(category)
        q = query.lower()
        if query:
            results = [r for r in results
                       if q in r["name"].lower()
                       or q in r["description"].lower()
                       or q in r.get("author", "").lower()
                       or any(q in t.lower() for t in r.get("tags", []))]
        if tags:
            results = [r for r in results
                       if any(t in r.get("tags", []) for t in tags)]
        if sort_by == "rating":
            results.sort(key=lambda r: r.get("rating", 0), reverse=True)
        elif sort_by == "downloads":
            results.sort(key=lambda r: r.get("downloads", 0), reverse=True)
        elif sort_by == "name":
            results.sort(key=lambda r: r["name"].lower())
        elif sort_by == "new":
            results.sort(key=lambda r: r.get("version", ""), reverse=True)
        return results

    def get_featured(self) -> list[dict]:
        return [c for c in CATALOG if c.get("featured")]

    def get_trending(self) -> list[dict]:
        return [c for c in CATALOG if c.get("trending")]

    def get_editors_choice(self) -> list[dict]:
        return [c for c in CATALOG if c.get("editors_choice")]

    def get_new(self) -> list[dict]:
        return [c for c in CATALOG if c.get("new") or True][:10]

    def get_categories(self) -> list[dict]:
        counts = {}
        for c in CATALOG:
            cat = c.get("category", "other")
            counts[cat] = counts.get(cat, 0) + 1
        return [{"id": k, "name": k.replace("_", " ").title(), "count": v}
                for k, v in sorted(counts.items())]

    def install(self, item_id: str, auto_approve: bool = False) -> dict:
        item = self.get_item(item_id)
        if not item:
            return {"success": False, "error": f"Item {item_id} not found"}
        category = item.category.value if hasattr(item.category, 'value') else item.category
        from hub.plugins import PluginManager
        from hub.mcp_marketplace import MCPMarketplace
        from hub.themes import ThemeManager
        from hub.languages import LanguagePackManager
        from hub.icons import IconPackManager

        installers = {
            "plugins": lambda: PluginManager(self.store).install(
                item_id, manifest=item.to_dict(), auto_approve=auto_approve),
            "mcp_servers": lambda: MCPMarketplace(self.store).install(item_id),
            "skills": lambda: self._install_skill(item_id, item),
            "themes": lambda: ThemeManager(self.store).install(item_id),
            "workflows": lambda: self._install_workflow(item_id, item),
            "ai_agents": lambda: self._install_agent(item_id, item),
            "tool_packs": lambda: self._install_tool_pack(item_id, item),
            "language_packs": lambda: LanguagePackManager(self.store).install(item_id),
            "models": lambda: self._install_model(item_id, item),
            "icon_packs": lambda: IconPackManager(self.store).install(item_id),
        }
        installer = installers.get(category)
        if installer:
            return installer()
        return {"success": False, "error": f"Unknown category: {category}"}

    def _install_skill(self, skill_id: str, item: HubItem) -> dict:
        self.store.install_item(skill_id, item.name, "skills", item.version,
                                description=item.description,
                                author=item.author.name,
                                tags=item.tags)
        return {"success": True, "skill_id": skill_id, "name": item.name}

    def _install_workflow(self, wf_id: str, item: HubItem) -> dict:
        from workflows.marketplace import WorkflowMarketplace
        try:
            wf_id = WorkflowMarketplace(self.store).install_from_marketplace(wf_id)
            return {"success": True, "workflow_id": wf_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _install_agent(self, agent_id: str, item: HubItem) -> dict:
        self.store.install_item(agent_id, item.name, "ai_agents", item.version,
                                description=item.description,
                                author=item.author.name,
                                tags=item.tags)
        return {"success": True, "agent_id": agent_id}

    def _install_tool_pack(self, pack_id: str, item: HubItem) -> dict:
        self.store.install_item(pack_id, item.name, "tool_packs", item.version,
                                description=item.description,
                                author=item.author.name)
        for tool_item in CATALOG:
            if tool_item.get("category") == "plugins" and pack_id in tool_item.get("tags", []):
                self.install(tool_item["id"])
        return {"success": True, "pack_id": pack_id}

    def _install_model(self, model_id: str, item: HubItem) -> dict:
        self.store.install_item(model_id, item.name, "models", item.version,
                                description=item.description,
                                author=item.author.name)
        return {"success": True, "model_id": model_id}

    def get_stats(self) -> dict:
        return {
            "total_items": len(CATALOG),
            "categories": len(self.get_categories()),
            "featured": len(self.get_featured()),
            "trending": len(self.get_trending()),
            "editors_choice": len(self.get_editors_choice()),
            "installed": self.store.get_stats().get("total_installed", 0),
        }

    def _dict_to_item(self, d: dict) -> HubItem:
        author = HubAuthor(
            name=d.get("author", "Unknown"),
            verified=PublisherVerification.OFFICIAL if d.get("official") else
                     PublisherVerification.COMMUNITY if d.get("community") else
                     PublisherVerification.UNVERIFIED,
        )
        permissions = []
        for p in d.get("permissions", []):
            try:
                permissions.append(Permission(p))
            except ValueError:
                pass
        try:
            category = HubCategory(d.get("category", "plugins"))
        except ValueError:
            category = HubCategory.PLUGINS
        return HubItem(
            id=d["id"], name=d.get("name", d["id"]),
            description=d.get("description", ""),
            category=category, author=author,
            version=d.get("version", "1.0.0"),
            tags=d.get("tags", []),
            permissions=permissions,
            downloads=d.get("downloads", 0),
            rating=d.get("rating", 0.0),
            featured=d.get("featured", False),
            trending=d.get("trending", False),
            editors_choice=d.get("editors_choice", False),
            official=d.get("official", False),
            verified=d.get("verified", d.get("official", False)),
            icon_url=d.get("icon_url", ""),
            install_status=InstallStatus.NOT_INSTALLED,
            dependencies=[HubDependency(pd.get("package_id", ""),
                                         pd.get("version", "*"),
                                         pd.get("optional", False))
                          for pd in d.get("dependencies", [])],
        )
