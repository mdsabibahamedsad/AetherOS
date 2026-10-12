"""Agent Marketplace — catalog, install, update, uninstall, ratings, and reviews."""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Any, Optional

from aetheros_constants import get_aetheros_home
from agents.models import AgentConfig, AgentRole, Personality, ReasoningLevel, MemoryScope
from agents import store

logger = logging.getLogger(__name__)

# =============================================================================
# Built-in marketplace catalog
# =============================================================================

MARKETPLACE_CATEGORIES = {
    "coding": "Coding",
    "research": "Research",
    "business": "Business",
    "automation": "Automation",
    "education": "Education",
    "cybersecurity": "Cybersecurity",
    "devops": "DevOps",
    "writing": "Writing",
    "creative": "Creative",
    "general": "General",
}


FEATURED_AGENTS = [
    {
        "id": "featured-developer",
        "name": "Developer Agent",
        "description": "Full-stack software engineering assistant with code generation, debugging, and architecture design capabilities.",
        "category": "coding",
        "role": "software_engineer",
        "personality": "technical",
        "reasoning": "deep",
        "tools": ["filesystem", "terminal", "python", "git", "github", "web_search", "browser"],
        "permissions": ["read_files", "write_files", "execute_terminal", "internet_access", "git_push"],
        "featured": True,
        "rating": 4.8,
        "installs": 15200,
        "version": "2.1.0",
        "author": "Aetheros",
        "prompt": "You are a world-class software engineer. Write clean, maintainable, well-tested code. Think step by step and explain your design decisions.",
    },
    {
        "id": "featured-research",
        "name": "Research Agent",
        "description": "Deep research assistant with web search, paper analysis, data synthesis, and citation management.",
        "category": "research",
        "role": "researcher",
        "personality": "research",
        "reasoning": "deep",
        "tools": ["web_search", "browser", "filesystem", "vision"],
        "permissions": ["read_files", "write_files", "internet_access"],
        "featured": True,
        "rating": 4.7,
        "installs": 12100,
        "version": "1.8.0",
        "author": "Aetheros",
        "prompt": "You are a thorough research assistant. Find accurate information, cite sources, synthesize findings, and produce well-structured reports.",
    },
    {
        "id": "featured-devops",
        "name": "DevOps Agent",
        "description": "Infrastructure automation, Docker management, CI/CD pipelines, cloud orchestration, and monitoring.",
        "category": "devops",
        "role": "devops",
        "personality": "technical",
        "reasoning": "balanced",
        "tools": ["terminal", "filesystem", "web_search", "git"],
        "permissions": ["read_files", "write_files", "execute_terminal", "internet_access", "docker"],
        "featured": True,
        "rating": 4.6,
        "installs": 8900,
        "version": "1.5.0",
        "author": "Aetheros",
        "prompt": "You are a DevOps engineer specializing in infrastructure as code, containerization, CI/CD, and cloud services. Provide production-ready configurations.",
    },
    {
        "id": "featured-security",
        "name": "Security Agent",
        "description": "Vulnerability assessment, code audit, threat modeling, and security best practices enforcement.",
        "category": "cybersecurity",
        "role": "cyber_security",
        "personality": "technical",
        "reasoning": "deep",
        "tools": ["filesystem", "terminal", "web_search", "git"],
        "permissions": ["read_files", "internet_access"],
        "featured": True,
        "rating": 4.5,
        "installs": 7600,
        "version": "1.3.0",
        "author": "Aetheros",
        "prompt": "You are a cybersecurity expert. Analyze code for vulnerabilities, identify security risks, and recommend mitigations following industry standards.",
    },
    {
        "id": "featured-teacher",
        "name": "Teacher Agent",
        "description": "Patient educator explaining concepts from basics to advanced, with exercises and progress tracking.",
        "category": "education",
        "role": "teacher",
        "personality": "friendly",
        "reasoning": "balanced",
        "tools": ["web_search", "filesystem"],
        "permissions": ["read_files", "internet_access"],
        "featured": True,
        "rating": 4.9,
        "installs": 18400,
        "version": "2.0.0",
        "author": "Aetheros",
        "prompt": "You are a patient, knowledgeable teacher. Explain concepts clearly, provide examples, ask questions to verify understanding, and adapt to the learner's pace.",
    },
    {
        "id": "featured-jarvis",
        "name": "Jarvis",
        "description": "Your all-purpose AI assistant — manages tasks, answers questions, controls your desktop, and automates workflows.",
        "category": "general",
        "role": "general_assistant",
        "personality": "professional",
        "reasoning": "balanced",
        "tools": ["filesystem", "terminal", "web_search", "browser", "email", "calendar"],
        "permissions": ["read_files", "write_files", "execute_terminal", "internet_access"],
        "featured": True,
        "rating": 4.9,
        "installs": 32100,
        "version": "3.0.0",
        "author": "Aetheros",
        "prompt": "You are Jarvis, an intelligent AI assistant. Help manage tasks, automate workflows, answer questions, and control the system efficiently.",
    },
]

MARKETPLACE_CATALOG: list[dict] = [
    {
        "id": "code-reviewer",
        "name": "Code Reviewer",
        "description": "Automated code review with best-practice enforcement, style checking, and security scanning.",
        "category": "coding",
        "role": "software_engineer",
        "personality": "technical",
        "reasoning": "balanced",
        "tools": ["filesystem", "git", "github"],
        "permissions": ["read_files", "git_push"],
        "featured": False,
        "rating": 4.4,
        "installs": 5400,
        "version": "1.2.0",
        "author": "Aetheros",
    },
    {
        "id": "debugger",
        "name": "Debugger",
        "description": "Root-cause analysis, stack trace reading, and bug-fixing specialist.",
        "category": "coding",
        "role": "software_engineer",
        "personality": "analytical",
        "reasoning": "deep",
        "tools": ["filesystem", "terminal", "python", "git"],
        "permissions": ["read_files", "write_files", "execute_terminal"],
        "featured": False,
        "rating": 4.3,
        "installs": 4200,
        "version": "1.1.0",
        "author": "Aetheros",
    },
    {
        "id": "data-scientist",
        "name": "Data Scientist",
        "description": "Data analysis, visualization, machine learning, and statistical modeling expert.",
        "category": "research",
        "role": "researcher",
        "personality": "research",
        "reasoning": "deep",
        "tools": ["filesystem", "terminal", "python", "web_search", "vision"],
        "permissions": ["read_files", "write_files", "execute_terminal", "internet_access"],
        "featured": False,
        "rating": 4.6,
        "installs": 6700,
        "version": "1.4.0",
        "author": "Aetheros",
    },
    {
        "id": "architect",
        "name": "Software Architect",
        "description": "System design, architecture planning, tech stack decisions, and design document creation.",
        "category": "coding",
        "role": "software_engineer",
        "personality": "professional",
        "reasoning": "deep",
        "tools": ["filesystem", "web_search", "browser", "vision"],
        "permissions": ["read_files", "write_files", "internet_access"],
        "featured": False,
        "rating": 4.5,
        "installs": 3800,
        "version": "1.0.0",
        "author": "Aetheros",
    },
    {
        "id": "writer-agent",
        "name": "Writer",
        "description": "Content creation, editing, copywriting, blog posts, documentation, and creative writing.",
        "category": "writing",
        "role": "writer",
        "personality": "creative",
        "reasoning": "balanced",
        "tools": ["filesystem", "web_search"],
        "permissions": ["read_files", "write_files", "internet_access"],
        "featured": False,
        "rating": 4.7,
        "installs": 9100,
        "version": "2.2.0",
        "author": "Aetheros",
    },
    {
        "id": "creative-designer",
        "name": "Creative Designer",
        "description": "Visual design, UI/UX, brainstorming, mood boards, and design system creation.",
        "category": "creative",
        "role": "writer",
        "personality": "creative",
        "reasoning": "balanced",
        "tools": ["filesystem", "web_search", "browser", "vision"],
        "permissions": ["read_files", "write_files", "internet_access"],
        "featured": False,
        "rating": 4.2,
        "installs": 2900,
        "version": "1.0.0",
        "author": "Aetheros",
    },
    {
        "id": "automation-engineer",
        "name": "Automation Engineer",
        "description": "Workflow automation, scripting, scheduled tasks, and process optimization.",
        "category": "automation",
        "role": "devops",
        "personality": "technical",
        "reasoning": "balanced",
        "tools": ["filesystem", "terminal", "python", "git", "web_search"],
        "permissions": ["read_files", "write_files", "execute_terminal", "internet_access"],
        "featured": False,
        "rating": 4.3,
        "installs": 5100,
        "version": "1.2.0",
        "author": "Aetheros",
    },
    {
        "id": "business-analyst",
        "name": "Business Analyst",
        "description": "Market analysis, business strategy, financial modeling, and competitive research.",
        "category": "business",
        "role": "business",
        "personality": "professional",
        "reasoning": "balanced",
        "tools": ["filesystem", "web_search", "browser", "vision"],
        "permissions": ["read_files", "write_files", "internet_access"],
        "featured": False,
        "rating": 4.4,
        "installs": 3300,
        "version": "1.1.0",
        "author": "Aetheros",
    },
    {
        "id": "marketing-agent",
        "name": "Marketing Agent",
        "description": "Campaign planning, SEO, content strategy, social media, and analytics.",
        "category": "business",
        "role": "marketing",
        "personality": "creative",
        "reasoning": "balanced",
        "tools": ["filesystem", "web_search", "browser"],
        "permissions": ["read_files", "write_files", "internet_access"],
        "featured": False,
        "rating": 4.1,
        "installs": 2600,
        "version": "1.0.0",
        "author": "Aetheros",
    },
]


def get_marketplace_catalog(category: str | None = None) -> list[dict]:
    """Get marketplace catalog, optionally filtered by category."""
    agents = FEATURED_AGENTS + MARKETPLACE_CATALOG
    if category:
        agents = [a for a in agents if a.get("category") == category]
    return agents


def get_featured_agents() -> list[dict]:
    """Get featured marketplace agents."""
    return [a for a in FEATURED_AGENTS if a.get("featured")]


def get_agent_from_catalog(package_id: str) -> dict | None:
    for agent in FEATURED_AGENTS + MARKETPLACE_CATALOG:
        if agent["id"] == package_id:
            return agent
    return None


def install_from_marketplace(package_id: str) -> AgentConfig | None:
    """Install an agent from the marketplace catalog."""
    catalog_entry = get_agent_from_catalog(package_id)
    if not catalog_entry:
        logger.warning("Marketplace agent '%s' not found in catalog", package_id)
        return None

    from agents.manager import AgentManager
    mgr = AgentManager()

    existing = mgr.get_by_name(catalog_entry["name"])
    if existing:
        logger.info("Agent '%s' already installed (id=%s), updating", catalog_entry["name"], existing.id)
        return mgr.update(existing.id, {
            "description": catalog_entry.get("description", ""),
            "role": catalog_entry.get("role", "general_assistant"),
            "personality": catalog_entry.get("personality", "professional"),
            "reasoning": catalog_entry.get("reasoning", "balanced"),
            "tools": catalog_entry.get("tools", ["filesystem", "terminal", "web_search"]),
            "permissions": catalog_entry.get("permissions", ["read_files", "internet_access"]),
            "prompt": catalog_entry.get("prompt", ""),
        })

    config = AgentConfig(
        name=catalog_entry["name"],
        description=catalog_entry.get("description", ""),
        role=catalog_entry.get("role", "general_assistant"),
        personality=catalog_entry.get("personality", "professional"),
        reasoning=catalog_entry.get("reasoning", "balanced"),
        tools=catalog_entry.get("tools", ["filesystem", "terminal", "web_search"]),
        permissions=catalog_entry.get("permissions", ["read_files", "internet_access"]),
        prompt=catalog_entry.get("prompt", ""),
        tags=[catalog_entry.get("category", "general")],
    )
    result = mgr.create(config)

    store.install_marketplace_package(package_id, catalog_entry["name"],
                                      catalog_entry.get("version", "1.0.0"))
    logger.info("Installed marketplace agent '%s' (id=%s)", catalog_entry["name"], result.id)
    return result


def uninstall_marketplace_agent(agent_id: str) -> bool:
    """Uninstall a marketplace agent."""
    from agents.manager import AgentManager
    mgr = AgentManager()
    agent = mgr.get(agent_id)
    if not agent:
        return False

    package_id = next(
        (p["package_id"] for p in store.list_installed_marketplace()
         if p.get("name", "").lower() == agent.name.lower()),
        None,
    )

    store.delete_agent(agent_id)
    if package_id:
        store.uninstall_marketplace_package(package_id)

    logger.info("Uninstalled agent '%s'", agent.name)
    return True


def get_installed_marketplace_agents() -> list[dict]:
    """Get list of installed marketplace agents with catalog metadata."""
    from agents.manager import AgentManager
    mgr = AgentManager()
    installed = store.list_installed_marketplace()
    result = []
    for pkg in installed:
        catalog = get_agent_from_catalog(pkg["package_id"])
        agent = mgr.get_by_name(pkg["name"])
        result.append({
            "package_id": pkg["package_id"],
            "name": pkg["name"],
            "version": pkg["version"],
            "installed_at": pkg["installed_at"],
            "installed": True,
            "agent_id": agent.id if agent else None,
            "catalog": catalog,
        })
    return result
