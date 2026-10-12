"""
AetherOS First-Time Initialization Engine.

After the setup wizard completes, this module performs the complete
AI Operating System initialization: workspace creation, agent setup,
memory seeding, software detection, background service configuration,
and knowledge base initialization.

All progress is saved to config so every step is resumable and nothing
is hardcoded.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.style import Style
from rich.table import Table
from rich.text import Text

from aetheros_cli.config import (
    ensure_aetheros_home,
    get_config_path,
    load_config,
    save_config,
    save_env_value,
)
from aetheros_cli.setup_renderer import (
    C_ACCENT,
    C_BORDER,
    C_CARD_BG,
    C_CYAN,
    C_DIM,
    C_ERROR,
    C_PURPLE,
    C_SECTION_BG,
    C_SUCCESS,
    C_TEXT,
    C_WARN,
    get_console,
    icon,
    make_card,
    make_keyboard_hints,
    make_step_progress,
    make_success_screen,
)
from aetheros_constants import display_aetheros_home, get_aetheros_home

logger = logging.getLogger(__name__)

# =============================================================================
# Default AetherOS Workspace Structure
# =============================================================================

AETHEROS_WORKSPACE = "AetherOS"

WORKSPACE_DIRS = [
    "Projects",
    "Agents",
    "Memory",
    "Downloads",
    "Documents",
    "Tasks",
    "Workflows",
    "Knowledge",
    "Models",
    "Logs",
    "Temp",
    "Backups",
    "Plugins",
    "MCP",
    "Extensions",
    "Cache",
]

# =============================================================================
# Initialization Phases
# =============================================================================

INIT_PHASES = [
    ("Preparing Workspace...", "workspace", 0.4),
    ("Creating User Profile...", "profile", 0.3),
    ("Creating Agent...", "agent", 0.5),
    ("Loading Memory...", "memory", 0.4),
    ("Initializing Runtime...", "runtime", 0.3),
    ("Loading MCP...", "mcp", 0.5),
    ("Loading Extensions...", "extension", 0.3),
    ("Scanning Local Models...", "models", 0.6),
    ("Connecting Services...", "services", 0.4),
    ("Finalizing...", "finalize", 0.5),
]

PHASE_ICONS = {
    "workspace": "📁",
    "profile": "👤",
    "agent": "🤖",
    "memory": "🧠",
    "runtime": "⚙",
    "mcp": "🔗",
    "extension": "🧩",
    "models": "🖥",
    "services": "🔌",
    "finalize": "🚀",
}

# =============================================================================
# Initialization Engine
# =============================================================================


def run_initialization(config: dict) -> dict:
    """Run the full first-time initialization sequence.

    Returns the updated config dict with initialization markers set.
    """
    console = get_console(highlight=False)

    console.print()
    console.print(
        Panel(
            Align.center(
                Group(
                    Text("◆  Initializing Your AI Operating System  ◆", style=f"bold {C_PURPLE}"),
                    Text(""),
                    Text("Setting up your AetherOS environment...", style=C_DIM),
                ),
                vertical="middle",
            ),
            border_style=C_PURPLE,
            padding=(1, 4),
            box=None,
        )
    )
    time.sleep(0.5)

    results: dict[str, Any] = {}
    completed: list[str] = []

    total = len(INIT_PHASES)

    with Live(auto_refresh=False, console=console, transient=True, refresh_per_second=15) as live:
        for i, (phase_name, phase_type, duration) in enumerate(INIT_PHASES):
            pct = int((i / total) * 100)
            filled = int((i / total) * 20)
            bar = f"[{'█' * filled}{'░' * (20 - filled)}]"

            # Build status table
            table = Table.grid(padding=(0, 2))
            table.add_column("Status", width=6)
            table.add_column("Phase", width=40)
            table.add_column("Detail", width=30)

            for pn, pt, _pd in INIT_PHASES:
                ico = PHASE_ICONS.get(pt, " ")
                display = f"{ico}  {pn}"
                if pn in completed:
                    table.add_row(
                        Text("✓", style=f"bold {C_SUCCESS}"),
                        Text(display, style=f"dim {C_DIM}"),
                        Text("", style=C_DIM),
                    )
                elif pn == phase_name:
                    spinner = Spinner("dots", text="", style=C_ACCENT)
                    detail = _get_phase_detail(pn, config)
                    table.add_row(
                        spinner,
                        Text(display, style=f"bold {C_TEXT}"),
                        Text(detail, style=f"italic {C_DIM}"),
                    )
                else:
                    table.add_row(
                        Text(" ", style=C_DIM),
                        Text(display, style=f"dim {C_DIM}"),
                        Text("", style=C_DIM),
                    )

            info_line = Text(f"  {bar}  {pct}%", style=f"bold {C_CYAN}")

            combined = Table.grid(padding=(0, 1))
            combined.add_row(table)
            combined.add_row(Text(""))
            combined.add_row(info_line)

            panel = Panel(
                Align.center(combined, vertical="middle"),
                border_style=C_PURPLE,
                padding=(1, 4),
                box=None,
            )

            live.update(panel)
            live.refresh()

            # Perform actual work for this phase
            result = _execute_phase(phase_name, phase_type, config)
            if result:
                results[phase_name] = result

            time.sleep(duration)
            completed.append(phase_name)

        # ── Completion ────────────────────────────────────────────────
        # Final status
        final_table = Table.grid(padding=(0, 2))
        final_table.add_column("Status", width=6)
        final_table.add_column("Phase", width=40)
        final_table.add_column("Detail", width=30)

        for pn, pt, _pd in INIT_PHASES:
            ico = PHASE_ICONS.get(pt, " ")
            display = f"{ico}  {pn}"
            final_table.add_row(
                Text("✓", style=f"bold {C_SUCCESS}"),
                Text(display, style=f"dim {C_DIM}"),
                Text("Ready", style=f"dim {C_SUCCESS}"),
            )

        bar = "[████████████████████]"
        info_line = Text(f"  {bar}  100%  ", style=f"bold {C_SUCCESS}")

        final_combined = Table.grid(padding=(0, 1))
        final_combined.add_row(final_table)
        final_combined.add_row(Text(""))
        final_combined.add_row(info_line)
        final_combined.add_row(Text(""))
        final_combined.add_row(
            Text("  ◆  System Initialized  ◆", style=f"bold {C_PURPLE}")
        )

        final_panel = Panel(
            Align.center(final_combined, vertical="middle"),
            border_style=C_SUCCESS,
            padding=(1, 4),
            box=None,
        )

        live.update(final_panel)
        live.refresh()
        time.sleep(1.0)

    return results


def _get_phase_detail(phase_name: str, config: dict) -> str:
    """Get a real-time detail string for the active phase."""
    if phase_name == "Scanning Local Models...":
        if _detect_ollama():
            return "Ollama found"
        if _detect_lm_studio():
            return "LM Studio found"
        return "Scanning..."
    if phase_name == "Connecting Services...":
        services = config.get("onboarding", {}).get("connected_services", [])
        return f"{len(services)} service(s)"
    if phase_name == "Creating User Profile...":
        onboarding = config.get("onboarding", {})
        name = onboarding.get("profile_name") or onboarding.get("name", "")
        return f"Hi, {name}!" if name else ""
    return ""


def _execute_phase(phase_name: str, phase_type: str, config: dict) -> dict | None:
    """Execute the actual work for an initialization phase."""
    try:
        if phase_name == "Preparing Workspace...":
            return _create_workspace_structure(config)
        elif phase_name == "Creating User Profile...":
            return _finalize_profile(config)
        elif phase_name == "Creating Agent...":
            return _initialize_agent(config)
        elif phase_name == "Loading Memory...":
            return _initialize_memory(config)
        elif phase_name == "Initializing Runtime...":
            return _initialize_runtime(config)
        elif phase_name == "Loading MCP...":
            return _initialize_mcp(config)
        elif phase_name == "Loading Extensions...":
            return _initialize_extensions(config)
        elif phase_name == "Scanning Local Models...":
            return _scan_local_models(config)
        elif phase_name == "Connecting Services...":
            return _connect_services(config)
        elif phase_name == "Finalizing...":
            return _finalize(config)
    except Exception as e:
        logger.warning("Init phase '%s' failed: %s", phase_name, e)
    return None


# =============================================================================
# Phase Implementations
# =============================================================================


def _create_workspace_structure(config: dict) -> dict:
    """Create the ~/AetherOS/ workspace directory structure."""
    home = Path.home()
    workspace_root = home / AETHEROS_WORKSPACE
    workspace_root.mkdir(parents=True, exist_ok=True)

    created_dirs = []
    for subdir in WORKSPACE_DIRS:
        d = workspace_root / subdir
        d.mkdir(parents=True, exist_ok=True)
        created_dirs.append(str(d))

    # Create .gitkeep files in empty dirs
    for d in [workspace_root / "Temp", workspace_root / "Cache", workspace_root / "Backups"]:
        gitkeep = d / ".gitkeep"
        if not gitkeep.exists():
            try:
                gitkeep.write_text("")
            except Exception:
                pass

    # Update config with workspace path
    config.setdefault("terminal", {})["cwd"] = str(workspace_root)
    config.setdefault("workspace", {})["root"] = str(workspace_root)
    config.setdefault("workspace", {})["directories"] = WORKSPACE_DIRS

    # Create AETHEROS_HOME subdirs if not already present
    ensure_aetheros_home()

    return {
        "root": str(workspace_root),
        "directories": created_dirs,
    }


def _finalize_profile(config: dict) -> dict:
    """Finalize the user profile from setup data."""
    onboarding = config.setdefault("onboarding", {})
    profile = {
        "name": onboarding.get("name") or onboarding.get("profile_name", "User"),
        "username": onboarding.get("username") or onboarding.get("profile_username", ""),
        "language": onboarding.get("language") or onboarding.get("profile_language", "en"),
        "timezone": onboarding.get("timezone") or onboarding.get("profile_timezone", "UTC"),
    }
    config.setdefault("profile", {}).update(profile)
    onboarding["initialized"] = True

    return profile


def _initialize_agent(config: dict) -> dict:
    """Initialize default agent settings."""
    agent_cfg = config.setdefault("agent", {})
    onboarding = config.setdefault("onboarding", {})

    # Apply experience-level defaults
    experience = onboarding.get("experience_level", "intermediate")
    _apply_experience_preset(agent_cfg, experience)

    # Apply purpose-based tool presets
    purposes = onboarding.get("purposes", [])
    _apply_purpose_presets(config, purposes)

    return {
        "experience_level": experience,
        "purposes": purposes,
        "status": "initialized",
    }


def _apply_experience_preset(agent_cfg: dict, level: str) -> None:
    """Apply experience-level defaults to agent config."""
    presets = {
        "beginner": {
            "max_turns": 50,
            "verbose": True,
            "auto_approve": False,
        },
        "intermediate": {
            "max_turns": 90,
            "verbose": False,
            "auto_approve": False,
        },
        "advanced": {
            "max_turns": 150,
            "verbose": False,
            "auto_approve": True,
        },
        "expert": {
            "max_turns": 250,
            "verbose": False,
            "auto_approve": True,
        },
    }
    preset = presets.get(level, presets["intermediate"])
    for key, val in preset.items():
        if key not in agent_cfg or agent_cfg[key] is None:
            agent_cfg[key] = val


def _apply_purpose_presets(config: dict, purposes: list[str]) -> None:
    """Apply purpose-based tool and config presets."""
    purpose_presets = {
        "programming": ["filesystem", "terminal", "git", "browser", "web_search"],
        "research": ["browser", "web_search", "filesystem", "ocr", "pdf"],
        "business": ["filesystem", "spreadsheet", "python", "web_search"],
        "student": ["filesystem", "web_search", "browser", "python"],
        "devops": ["terminal", "docker", "git", "filesystem", "browser"],
        "cybersecurity": ["terminal", "browser", "filesystem", "python"],
        "content_creation": ["filesystem", "browser", "voice", "vision"],
        "automation": ["terminal", "python", "filesystem", "git"],
        "personal_assistant": ["filesystem", "web_search", "browser", "voice"],
        "ai_development": ["python", "terminal", "git", "docker", "filesystem"],
    }

    onboarding = config.setdefault("onboarding", {})
    existing_tools = set(onboarding.get("tools", []))
    for purpose in purposes:
        recommended = purpose_presets.get(purpose, [])
        for tool in recommended:
            if tool not in existing_tools:
                existing_tools.add(tool)
    onboarding["tools"] = list(existing_tools)


def _initialize_memory(config: dict) -> dict:
    """Initialize memory stores."""
    onboarding = config.get("onboarding", {})
    memory_types = onboarding.get("memory", [])

    # Create memory directory
    aetheros_home = get_aetheros_home()
    memory_dir = aetheros_home / "memories"
    memory_dir.mkdir(parents=True, exist_ok=True)

    # Initialize standard memory files
    memory_files = {}
    if "personal_memory" in memory_types or not memory_types:
        user_md = memory_dir / "USER.md"
        if not user_md.exists():
            name = onboarding.get("name", "User")
            user_md.write_text(
                f"# {name}'s AetherOS Profile\n\n"
                "This file stores your personal preferences and context.\n"
                "Aetheros reads this to personalize your experience.\n\n"
                "## About You\n\n"
                "Add any information you'd like Aetheros to remember about you.\n"
            )
        memory_files["user"] = str(user_md)

    if "workspace_memory" in memory_types or not memory_types:
        mem_md = memory_dir / "MEMORY.md"
        if not mem_md.exists():
            mem_md.write_text(
                "# Workspace Memory\n\n"
                "This file stores cross-session context and project state.\n"
                "Aetheros updates this as you work.\n\n"
                "## Current Context\n\n"
                "(auto-populated)\n"
            )
        memory_files["workspace"] = str(mem_md)

    # Update config
    config.setdefault("memory", {}).update({
        "memory_enabled": True,
        "user_profile_enabled": True,
        "memory_dir": str(memory_dir),
    })

    return {
        "memory_dir": str(memory_dir),
        "files": memory_files,
    }


def _initialize_runtime(config: dict) -> dict:
    """Initialize runtime configuration."""
    runtime = config.setdefault("runtime", {})

    # Default runtime settings
    runtime.setdefault("checkpoints_enabled", True)
    runtime.setdefault("auto_sync", True)
    runtime.setdefault("max_concurrent_tasks", 3)

    return {
        "status": "initialized",
        "settings": dict(runtime),
    }


def _initialize_mcp(config: dict) -> dict:
    """Initialize MCP server configuration."""
    mcp = config.setdefault("mcp_servers", {})

    # Only set if no servers are configured
    if not mcp:
        pass  # MCP servers are added manually or via setup

    return {
        "status": "ready",
        "servers": len(mcp),
    }


def _initialize_extensions(config: dict) -> dict:
    """Register initialization-complete markers."""
    config.setdefault("onboarding", {}).setdefault("extensions_loaded", True)
    return {"status": "ready"}


def _scan_local_models(config: dict) -> dict:
    """Scan for locally running AI providers and models."""
    found = {}

    if _detect_ollama():
        found["ollama"] = "http://localhost:11434"
        config.setdefault("providers", {}).setdefault(
            "ollama", {"base_url": "http://localhost:11434", "api_key": "not-required"}
        )

    if _detect_lm_studio():
        found["lm_studio"] = "http://localhost:1234"
        config.setdefault("providers", {}).setdefault(
            "lm_studio", {"base_url": "http://localhost:1234", "api_key": "not-required"}
        )

    if _detect_vllm():
        found["vllm"] = "http://localhost:8000"
        config.setdefault("providers", {}).setdefault(
            "vllm", {"base_url": "http://localhost:8000", "api_key": "not-required"}
        )

    if _detect_open_webui():
        found["open_webui"] = "http://localhost:3000"
        config.setdefault("providers", {}).setdefault(
            "open_webui", {"base_url": "http://localhost:3000", "api_key": "not-required"}
        )

    return {"detected": found}


def _detect_ollama() -> bool:
    try:
        import urllib.request
        import urllib.error

        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        req.timeout = 1
        with urllib.request.urlopen(req) as resp:
            return resp.status == 200
    except Exception:
        return False


def _detect_lm_studio() -> bool:
    try:
        import urllib.request
        import urllib.error

        req = urllib.request.Request("http://localhost:1234/v1/models", method="GET")
        req.timeout = 1
        with urllib.request.urlopen(req) as resp:
            return resp.status == 200
    except Exception:
        return False


def _detect_vllm() -> bool:
    try:
        import urllib.request
        import urllib.error

        req = urllib.request.Request("http://localhost:8000/v1/models", method="GET")
        req.timeout = 1
        with urllib.request.urlopen(req) as resp:
            return resp.status == 200
    except Exception:
        return False


def _detect_open_webui() -> bool:
    try:
        import urllib.request
        import urllib.error

        req = urllib.request.Request("http://localhost:3000/api/models", method="GET")
        req.timeout = 1
        with urllib.request.urlopen(req) as resp:
            return resp.status == 200
    except Exception:
        return False


def _connect_services(config: dict) -> dict:
    """Mark services as ready for connection."""
    onboarding = config.get("onboarding", {})
    services = onboarding.get("connected_services", [])
    return {
        "configured": services,
        "status": "ready",
    }


def _finalize(config: dict) -> dict:
    """Finalize initialization — stamp completion markers."""
    config.setdefault("onboarding", {})["initialized"] = True
    config.setdefault("onboarding", {})["init_completed_at"] = time.time()
    save_config(config)

    return {
        "status": "complete",
        "version": 1,
    }


# =============================================================================
# Software Detection
# =============================================================================


def detect_installed_software() -> dict[str, dict[str, Any]]:
    """Detect installed development tools and software."""
    detected: dict[str, dict[str, Any]] = {}

    checks = [
        ("git", "Git", _check_git),
        ("docker", "Docker", _check_docker),
        ("python", "Python", _check_python),
        ("node", "Node.js", _check_node),
        ("vscode", "VS Code", _check_vscode),
        ("cursor", "Cursor", _check_cursor),
        ("claude_code", "Claude Code", _check_claude_code),
        ("ollama", "Ollama", _check_ollama_binary),
        ("lm_studio", "LM Studio", _check_lm_studio_binary),
        ("gh", "GitHub CLI", _check_gh),
    ]

    for key, name, check_fn in checks:
        try:
            result = check_fn()
            if result:
                detected[key] = {
                    "name": name,
                    "detected": True,
                    "path": result.get("path", ""),
                    "version": result.get("version", ""),
                }
        except Exception:
            pass

    return detected


def _check_git() -> dict | None:
    path = shutil.which("git")
    if path:
        try:
            ver = subprocess.run(
                ["git", "--version"], capture_output=True, text=True, timeout=5
            ).stdout.strip()
            return {"path": path, "version": ver}
        except Exception:
            return {"path": path, "version": ""}
    return None


def _check_docker() -> dict | None:
    path = shutil.which("docker")
    if path:
        try:
            ver = subprocess.run(
                ["docker", "--version"], capture_output=True, text=True, timeout=5
            ).stdout.strip()
            return {"path": path, "version": ver}
        except Exception:
            return {"path": path, "version": ""}
    return None


def _check_python() -> dict | None:
    path = shutil.which("python") or shutil.which("python3")
    if path:
        try:
            ver = subprocess.run(
                [path, "--version"], capture_output=True, text=True, timeout=5
            ).stdout.strip()
            return {"path": path, "version": ver}
        except Exception:
            return {"path": path, "version": ""}
    return None


def _check_node() -> dict | None:
    path = shutil.which("node")
    if path:
        try:
            ver = subprocess.run(
                ["node", "--version"], capture_output=True, text=True, timeout=5
            ).stdout.strip()
            return {"path": path, "version": ver}
        except Exception:
            return {"path": path, "version": ""}
    return None


def _check_vscode() -> dict | None:
    path = shutil.which("code")
    if path:
        return {"path": path, "version": ""}
    return None


def _check_cursor() -> dict | None:
    path = shutil.which("cursor")
    if path:
        return {"path": path, "version": ""}
    return None


def _check_claude_code() -> dict | None:
    path = shutil.which("claude")
    if path:
        return {"path": path, "version": ""}
    return None


def _check_ollama_binary() -> dict | None:
    path = shutil.which("ollama")
    if path:
        try:
            ver = subprocess.run(
                ["ollama", "--version"], capture_output=True, text=True, timeout=5
            ).stdout.strip()
            return {"path": path, "version": ver}
        except Exception:
            return {"path": path, "version": ""}
    return None


def _check_lm_studio_binary() -> dict | None:
    # LM Studio may not have a CLI binary; check common install locations
    if shutil.which("lm-studio"):
        return {"path": shutil.which("lm-studio"), "version": ""}
    return None


def _check_gh() -> dict | None:
    path = shutil.which("gh")
    if path:
        try:
            ver = subprocess.run(
                ["gh", "--version"], capture_output=True, text=True, timeout=5
            ).stdout.strip()
            return {"path": path, "version": ver.split("\n")[0] if ver else ""}
        except Exception:
            return {"path": path, "version": ""}
    return None


# =============================================================================
# Software Detection Display
# =============================================================================


def show_software_detection(config: dict) -> None:
    """Display detected software and offer integration."""
    console = get_console()
    detected = detect_installed_software()

    console.print()
    progress = make_step_progress(1, 1, "Detected Software", "Found tools on your system")
    console.print(progress)
    console.print()

    table = Table.grid(padding=(0, 2))
    table.add_column("Status", width=6)
    table.add_column("Software", width=20)
    table.add_column("Version", width=30)
    table.add_column("Action", width=20)

    for key, info in detected.items():
        table.add_row(
            Text("✓", style=f"bold {C_SUCCESS}"),
            Text(info["name"], style=C_TEXT),
            Text(info.get("version", ""), style=f"dim {C_DIM}"),
            Text("Available", style=C_ACCENT),
        )

    if not detected:
        table.add_row(
            Text("", style=C_DIM),
            Text("No additional software detected", style=C_DIM),
            Text("", style=C_DIM),
            Text("", style=C_DIM),
        )

    console.print(
        Panel(
            Group(table, Text("")),
            border_style=C_SUCCESS,
            padding=(1, 2),
            box=rich_box.ROUNDED,
        )
    )
    console.print()
    console.print(make_keyboard_hints([("Enter", "Continue")]))
    from aetheros_cli.setup_wizard import _get_key
    _get_key()


from rich import box as rich_box

# =============================================================================
# Default Projects Initialization
# =============================================================================

DEFAULT_PROJECTS = [
    ("Personal", "Personal projects and experiments"),
    ("Work", "Professional and work-related projects"),
    ("Research", "Research and learning initiatives"),
    ("Learning", "Educational and skill-building projects"),
    ("Sandbox", "Testing and prototyping workspace"),
]


def initialize_default_projects(config: dict) -> dict:
    """Create default project directories."""
    workspace_root = Path(config.get("workspace", {}).get(
        "root", Path.home() / AETHEROS_WORKSPACE
    ))
    projects_dir = workspace_root / "Projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    created = []
    for project_name, description in DEFAULT_PROJECTS:
        project_path = projects_dir / project_name
        project_path.mkdir(parents=True, exist_ok=True)

        # Create a README for each project
        readme = project_path / "README.md"
        if not readme.exists():
            readme.write_text(
                f"# {project_name}\n\n{description}\n\n"
                f"Created by AetherOS on initialization.\n"
            )
        created.append({
            "name": project_name,
            "path": str(project_path),
            "description": description,
        })

    config.setdefault("workspace", {})["projects"] = created
    return {"projects": created}


# =============================================================================
# Background Services Initialization
# =============================================================================

BACKGROUND_SERVICES = [
    ("task_scheduler", "Task Scheduler", "Schedule and manage recurring tasks"),
    ("memory_indexer", "Memory Indexer", "Index and optimize memory storage"),
    ("workspace_watcher", "Workspace Watcher", "Monitor workspace for changes"),
    ("plugin_manager", "Plugin Manager", "Manage plugin lifecycle"),
    ("mcp_manager", "MCP Manager", "Manage MCP server connections"),
    ("notification_service", "Notification Service", "Handle system notifications"),
]


def initialize_background_services(config: dict) -> dict:
    """Configure background services."""
    services = config.setdefault("services", {})
    enabled = []

    for svc_id, name, description in BACKGROUND_SERVICES:
        services.setdefault(svc_id, {
            "name": name,
            "description": description,
            "enabled": True,
            "status": "initialized",
        })
        enabled.append(svc_id)

    return {"services": enabled}


# =============================================================================
# Knowledge Base Initialization
# =============================================================================

def initialize_knowledge_base(config: dict) -> dict:
    """Initialize the knowledge base directory."""
    workspace_root = Path(config.get("workspace", {}).get(
        "root", Path.home() / AETHEROS_WORKSPACE
    ))
    knowledge_dir = workspace_root / "Knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    # Create source subdirectories
    for src_type in ["Markdown", "PDF", "Documents", "Notes", "References"]:
        (knowledge_dir / src_type).mkdir(parents=True, exist_ok=True)

    config.setdefault("workspace", {})["knowledge_base"] = str(knowledge_dir)

    return {
        "knowledge_dir": str(knowledge_dir),
        "status": "ready",
    }


# =============================================================================
# Main Entry Point
# =============================================================================


def run_full_initialization(config: dict | None = None) -> dict:
    """Run the complete first-time initialization sequence.

    Creates workspace, initializes memory, detects software,
    sets up default projects, and configures background services.
    """
    if config is None:
        config = load_config()

    # Phase 1: Animated initialization
    init_results = run_initialization(config)

    # Phase 2: Default projects
    project_results = initialize_default_projects(config)

    # Phase 3: Background services
    service_results = initialize_background_services(config)

    # Phase 4: Knowledge base
    knowledge_results = initialize_knowledge_base(config)

    # Phase 5: Software detection (non-blocking display)
    show_software_detection(config)

    # Save all config changes
    save_config(config)

    return {
        "init": init_results,
        "projects": project_results,
        "services": service_results,
        "knowledge": knowledge_results,
        "config": config,
    }
