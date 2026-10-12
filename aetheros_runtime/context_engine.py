"""Context Engine — automatically builds rich context from workspace, project, provider, memory, and system state.

Never lose context. Every provider call gets the full picture.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("aetheros_runtime.context")


@dataclass
class ContextBundle:
    system: str = ""
    workspace: str = ""
    project: str = ""
    memory: str = ""
    pinned_notes: str = ""
    open_files: str = ""
    recent_messages: str = ""
    provider_info: str = ""
    model_info: str = ""
    gateway_state: str = ""
    running_agents: str = ""
    mcp_state: str = ""
    custom_sections: Dict[str, str] = field(default_factory=dict)

    @property
    def full_context(self) -> str:
        parts = []
        for field_name in [
            "system", "workspace", "project", "memory", "pinned_notes",
            "open_files", "recent_messages", "provider_info", "model_info",
            "gateway_state", "running_agents", "mcp_state",
        ]:
            value = getattr(self, field_name, "")
            if value:
                parts.append(value)
        for name, value in self.custom_sections.items():
            if value:
                parts.append(value)
        return "\n\n".join(parts)

    @property
    def token_estimate(self) -> int:
        text = self.full_context
        return len(text) // 4

    @property
    def is_empty(self) -> bool:
        return not bool(self.full_context.strip())


ContextProviderFn = Callable[[], str]


class ContextEngine:
    """Builds comprehensive context automatically from every available source.

    Each source registers independently. The engine merges them into a
    single ContextBundle on every request, ensuring the provider always
    gets the freshest picture.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._providers: Dict[str, ContextProviderFn] = {}
        self._max_section_length: int = 8000
        self._include_empty_sections: bool = False

    # ------------------------------------------------------------------
    # Provider registration
    # ------------------------------------------------------------------

    def register_provider(self, name: str, fn: ContextProviderFn) -> None:
        with self._lock:
            self._providers[name] = fn
            logger.debug("Context provider registered: %s", name)

    def unregister_provider(self, name: str) -> bool:
        with self._lock:
            return self._providers.pop(name, None) is not None

    # ------------------------------------------------------------------
    # Built-in providers
    # ------------------------------------------------------------------

    def register_workspace_provider(self, workspace_path: Optional[Path] = None) -> None:
        path = workspace_path or Path.cwd()
        self.register_provider("workspace", lambda: self._build_workspace_context(path))

    def register_project_provider(self, project_path: Optional[Path] = None) -> None:
        path = project_path or Path.cwd()
        self.register_provider("project", lambda: self._build_project_context(path))

    def register_provider_info(self, provider_name: str = "", model: str = "") -> None:
        self.register_provider("provider_info", lambda: (
            f"Provider: {provider_name}\nModel: {model}" if provider_name else ""
        ))

    # ------------------------------------------------------------------
    # Context assembly
    # ------------------------------------------------------------------

    def build(self, sections: Optional[List[str]] = None) -> ContextBundle:
        bundle = ContextBundle()
        with self._lock:
            provider_names = sections or list(self._providers.keys())

        for name in provider_names:
            fn = self._providers.get(name)
            if not fn:
                continue
            try:
                value = fn()
                if value or self._include_empty_sections:
                    value = value[:self._max_section_length]
                    if name in self._section_map:
                        setattr(bundle, self._section_map[name], value)
                    else:
                        bundle.custom_sections[name] = value
            except Exception as exc:
                logger.warning("Context provider %s failed: %s", name, exc)

        return bundle

    def build_full(self) -> ContextBundle:
        with self._lock:
            return self.build(list(self._providers.keys()))

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_max_section_length(self, chars: int) -> None:
        self._max_section_length = chars

    def health_check(self) -> bool:
        try:
            with self._lock:
                return len(self._providers) > 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    _section_map: Dict[str, str] = {
        "system": "system",
        "workspace": "workspace",
        "project": "project",
        "memory": "memory",
        "pinned_notes": "pinned_notes",
        "open_files": "open_files",
        "recent_messages": "recent_messages",
        "provider_info": "provider_info",
        "model_info": "model_info",
        "gateway_state": "gateway_state",
        "running_agents": "running_agents",
        "mcp_state": "mcp_state",
    }

    @staticmethod
    def _build_workspace_context(workspace_path: Path) -> str:
        parts = [f"Workspace: {workspace_path}"]
        try:
            if workspace_path.exists():
                items = list(workspace_path.iterdir())[:50]
                if items:
                    parts.append("Files:")
                    for item in items:
                        suffix = "/" if item.is_dir() else ""
                        parts.append(f"  {item.name}{suffix}")
        except PermissionError:
            parts.append("  (permission denied)")
        return "\n".join(parts)

    @staticmethod
    def _build_project_context(project_path: Path) -> str:
        parts = [f"Project: {project_path}"]
        try:
            for config_file in ["AGENTS.md", "CLAUDE.md", "README.md", "pyproject.toml", "package.json"]:
                cf = project_path / config_file
                if cf.exists():
                    content = cf.read_text(encoding="utf-8", errors="replace")[:2000]
                    parts.append(f"\n--- {config_file} ---\n{content}")
        except (PermissionError, OSError):
            pass
        return "\n".join(parts)

    def summary(self) -> str:
        with self._lock:
            return f"Context Engine: {len(self._providers)} providers registered"