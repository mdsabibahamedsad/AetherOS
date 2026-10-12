"""AetherOS minimal startup banner — clean, premium, with ASCII art wolf logo.

Pure display functions with no AetherosCLI state dependency.
"""

import json
import logging
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlparse
from aetheros_constants import get_aetheros_home
from typing import TYPE_CHECKING, Dict, List, Optional

# Import ASCII art logo
try:
    from aetheros_cli.ascii_logo import (
        WOLF_LOGO_DETAILED,
        WOLF_LOGO_COMPACT,
        get_brand_text,
        get_tagline,
        get_full_banner,
        get_compact_banner,
    )
except ImportError:
    # Fallback if ascii_logo module not available
    WOLF_LOGO_DETAILED = ""
    WOLF_LOGO_COMPACT = ""
    get_brand_text = lambda: "AetherOS"
    get_tagline = lambda: "AI Operating System"
    get_full_banner = lambda **kwargs: "AetherOS"
    get_compact_banner = lambda: "AetherOS"

if TYPE_CHECKING:
    from rich.console import Console

logger = logging.getLogger(__name__)


# =========================================================================
# ANSI building blocks
# =========================================================================

_BOLD = "\033[1m"
_DIM = "\033[2m"
_RST = "\033[0m"
_BLUE = "\033[38;2;88;166;255m"
_GRAY = "\033[38;2;139;148;158m"
_WHITE = "\033[38;2;230;237;243m"
_CYAN = "\033[38;2;57;210;192m"
_PURPLE = "\033[38;2;188;140;255m"


def cprint(text: str):
    """Print ANSI-colored text through prompt_toolkit's renderer."""
    from prompt_toolkit import print_formatted_text as _pt_print
    from prompt_toolkit.formatted_text import ANSI as _PT_ANSI
    _pt_print(_PT_ANSI(text))


# =========================================================================
# Skin-aware color helpers
# =========================================================================

def _skin_color(key: str, fallback: str) -> str:
    """Get a color from the active skin, or return fallback."""
    try:
        from aetheros_cli.skin_engine import get_active_skin
        return get_active_skin().get_color(key, fallback)
    except Exception:
        return fallback


# =========================================================================
# Skills scanning (preserved for system functionality)
# =========================================================================

def get_available_skills() -> Dict[str, List[str]]:
    """Return skills grouped by category, filtered by platform and disabled state."""
    try:
        from tools.skills_tool import _find_all_skills
        all_skills = _find_all_skills()
    except Exception:
        return {}

    skills_by_category: Dict[str, List[str]] = {}
    for skill in all_skills:
        category = skill.get("category") or "general"
        skills_by_category.setdefault(category, []).append(skill["name"])
    return skills_by_category


# =========================================================================
# Update check (preserved for system functionality)
# =========================================================================

_UPDATE_CHECK_CACHE_SECONDS = 6 * 3600
UPDATE_AVAILABLE_NO_COUNT = -1
_UPSTREAM_REPO_URL = "https://github.com/aetheros/aetheros.git"
_OFFICIAL_REPO_CANONICAL = "github.com/aetheros/aetheros"


def _canonical_github_remote(url: str | None) -> str:
    if not url:
        return ""
    value = url.strip()
    if value.startswith("git@github.com:"):
        value = "github.com/" + value[len("git@github.com:"):]
    elif value.startswith("ssh://git@github.com/"):
        value = "github.com/" + value[len("ssh://git@github.com/"):]
    else:
        parsed = urlparse(value)
        if parsed.netloc and parsed.path:
            value = f"{parsed.netloc}{parsed.path}"
    value = value.strip().rstrip("/")
    if value.endswith(".git"):
        value = value[:-4]
    return value.lower()


def _is_ssh_remote(url: str | None) -> bool:
    if not url:
        return False
    return url.strip().lower().startswith("git@") or url.strip().lower().startswith("ssh://")


def _is_official_ssh_remote(url: str | None) -> bool:
    return _is_ssh_remote(url) and _canonical_github_remote(url) == _OFFICIAL_REPO_CANONICAL


def _git_stdout(args: list[str], *, cwd: Path, timeout: int = 5) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd),
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    return (result.stdout or "").strip()


def _check_via_rev(local_rev: str) -> Optional[int]:
    try:
        result = subprocess.run(
            ["git", "ls-remote", _UPSTREAM_REPO_URL, "refs/heads/main"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return None
    if result.returncode != 0 or not result.stdout:
        return None
    upstream_rev = result.stdout.split()[0]
    if not upstream_rev:
        return None
    return 0 if upstream_rev == local_rev else UPDATE_AVAILABLE_NO_COUNT


def _check_via_local_git(repo_dir: Path) -> Optional[int]:
    origin_url = _git_stdout(["remote", "get-url", "origin"], cwd=repo_dir)
    if _is_official_ssh_remote(origin_url):
        head_rev = _git_stdout(["rev-parse", "HEAD"], cwd=repo_dir)
        return _check_via_rev(head_rev) if head_rev else None
    try:
        subprocess.run(
            ["git", "fetch", "origin", "--quiet"],
            capture_output=True, timeout=10,
            cwd=str(repo_dir),
        )
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD..origin/main"],
            capture_output=True, text=True, timeout=5,
            cwd=str(repo_dir),
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception:
        pass
    return None


def _version_tuple(v: str) -> tuple[int, ...]:
    parts = []
    for segment in v.split("."):
        try:
            parts.append(int(segment))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _fetch_pypi_latest(package: str = "aetheros") -> Optional[str]:
    try:
        import urllib.request
        url = f"https://pypi.org/pypi/{package}/json"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("info", {}).get("version")
    except Exception:
        return None


def check_via_pypi() -> Optional[int]:
    latest = _fetch_pypi_latest()
    if latest is None:
        return None
    if latest == VERSION:
        return 0
    try:
        if _version_tuple(latest) > _version_tuple(VERSION):
            return 1
        return 0
    except Exception:
        return 1 if latest != VERSION else 0


from aetheros_cli import __version__ as VERSION, __release_date__ as RELEASE_DATE


def check_for_updates() -> Optional[int]:
    aetheros_home = get_aetheros_home()
    cache_file = aetheros_home / ".update_check"
    embedded_rev = os.environ.get("HERMES_REVISION") or None
    try:
        from aetheros_cli.config import detect_install_method
        if detect_install_method() == "docker":
            return None
    except Exception:
        pass
    now = time.time()
    try:
        if cache_file.exists():
            cached = json.loads(cache_file.read_text())
            if (
                now - cached.get("ts", 0) < _UPDATE_CHECK_CACHE_SECONDS
                and cached.get("rev") == embedded_rev
                and cached.get("ver") == VERSION
            ):
                return cached.get("behind")
    except Exception:
        pass
    if embedded_rev:
        behind = _check_via_rev(embedded_rev)
    else:
        repo_dir = Path(__file__).parent.parent.resolve()
        if not (repo_dir / ".git").exists():
            repo_dir = aetheros_home / "aetheros"
        if not (repo_dir / ".git").exists():
            behind = check_via_pypi()
        else:
            behind = _check_via_local_git(repo_dir)
    try:
        cache_file.write_text(
            json.dumps({"ts": now, "behind": behind, "rev": embedded_rev, "ver": VERSION})
        )
    except Exception:
        pass
    return behind


def _resolve_repo_dir() -> Optional[Path]:
    repo_dir = Path(__file__).parent.parent.resolve()
    if not (repo_dir / ".git").exists():
        aetheros_home = get_aetheros_home()
        repo_dir = aetheros_home / "aetheros"
    return repo_dir if (repo_dir / ".git").exists() else None


def _git_short_hash(repo_dir: Path, rev: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=8", rev],
            capture_output=True, text=True, timeout=5, cwd=str(repo_dir),
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    value = (result.stdout or "").strip()
    return value or None


def get_git_banner_state(repo_dir: Optional[Path] = None) -> Optional[dict]:
    repo_dir = repo_dir or _resolve_repo_dir()
    if repo_dir is None:
        try:
            from aetheros_cli.build_info import get_build_sha
            baked = get_build_sha(short=8)
            if baked:
                return {"upstream": baked, "local": baked, "ahead": 0}
        except Exception:
            pass
        return None
    upstream = _git_short_hash(repo_dir, "origin/main")
    local = _git_short_hash(repo_dir, "HEAD")
    if not upstream or not local:
        try:
            from aetheros_cli.build_info import get_build_sha
            baked = get_build_sha(short=8)
            if baked:
                return {"upstream": baked, "local": baked, "ahead": 0}
        except Exception:
            pass
        return None
    ahead = 0
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "origin/main..HEAD"],
            capture_output=True, text=True, timeout=5, cwd=str(repo_dir),
        )
        if result.returncode == 0:
            ahead = int((result.stdout or "0").strip() or "0")
    except Exception:
        ahead = 0
    return {"upstream": upstream, "local": local, "ahead": max(ahead, 0)}


_RELEASE_URL_BASE = "https://github.com/aetheros/aetheros/releases/tag"
_latest_release_cache: Optional[tuple] = None


def get_latest_release_tag(repo_dir: Optional[Path] = None) -> Optional[tuple]:
    global _latest_release_cache
    if _latest_release_cache is not None:
        return _latest_release_cache or None
    repo_dir = repo_dir or _resolve_repo_dir()
    if repo_dir is None:
        _latest_release_cache = ()
        return None
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True, text=True, timeout=3, cwd=str(repo_dir),
        )
    except Exception:
        _latest_release_cache = ()
        return None
    if result.returncode != 0:
        _latest_release_cache = ()
        return None
    tag = (result.stdout or "").strip()
    if not tag:
        _latest_release_cache = ()
        return None
    url = f"{_RELEASE_URL_BASE}/{tag}"
    _latest_release_cache = (tag, url)
    return _latest_release_cache


def format_banner_version_label() -> str:
    """Return the version label for the startup display."""
    base = f"Aetheros v{VERSION} ({RELEASE_DATE})"
    state = get_git_banner_state()
    if not state:
        return base
    upstream = state.get("upstream")
    local = state.get("local")
    ahead = state.get("ahead", 0)
    if not upstream:
        return base
    if ahead == 0:
        return f"{base} · upstream {upstream}"
    return f"{base} · upstream {upstream} · local {local} · +{ahead} carried commits"


_update_result: Optional[int] = None
_update_check_done = threading.Event()


def prefetch_update_check():
    """Kick off update check in a background daemon thread."""
    def _run():
        global _update_result
        _update_result = check_for_updates()
        _update_check_done.set()
    t = threading.Thread(target=_run, daemon=True)
    t.start()


def get_update_result(timeout: float = 0.5) -> Optional[int]:
    _update_check_done.wait(timeout=timeout)
    return _update_result


# =========================================================================
# Welcome banner — minimal, premium
# =========================================================================

def _format_context_length(tokens: int) -> str:
    """Format a token count for display."""
    if tokens >= 1_000_000:
        val = tokens / 1_000_000
        rounded = round(val)
        if abs(val - rounded) < 0.05:
            return f"{rounded}M"
        return f"{val:.1f}M"
    elif tokens >= 1_000:
        val = tokens / 1_000
        rounded = round(val)
        if abs(val - rounded) < 0.05:
            return f"{rounded}K"
        return f"{val:.1f}K"
    return str(tokens)


def build_welcome_banner(console: "Console", model: str, cwd: str,
                         tools: List[dict] = None,
                         enabled_toolsets: List[str] = None,
                         session_id: str = None,
                         get_toolset_for_tool=None,
                         context_length: int = None):
    """Print a minimal, premium startup banner with ASCII art wolf logo.

    [ASCII ART WOLF LOGO]

    AetherOS
    AI Operating System

    Project
    /path/to/project

    Model
    GPT-5

    Context
    0 tokens

    Ready.
    """
    dim = _skin_color("banner_dim", "#8b949e")
    accent = _skin_color("banner_accent", "#58a6ff")
    text = _skin_color("banner_text", "#e6edf3")

    model_short = model.split("/")[-1] if "/" in model else model
    if model_short.endswith(".gguf"):
        model_short = model_short[:-5]
    if len(model_short) > 40:
        model_short = model_short[:37] + "..."

    ctx_str = str(context_length) if context_length else "?"

    # Print ASCII art wolf logo
    console.print()
    if WOLF_LOGO_DETAILED:
        console.print(WOLF_LOGO_DETAILED)
    console.print()
    
    # Brand name with gradient
    console.print(f"[bold {text}]AetherOS[/]")
    console.print(f"[dim {dim}]AI Operating System[/]")
    console.print()
    b_sec_accent = f"[{accent}]"
    r_sec_reset = f"[/]"
    b_sec_text = f"[{text}]"
    for i, (label, value) in enumerate([
        ("Project", cwd),
        ("Model", model_short),
        ("Context", f"{ctx_str} tokens"),
    ]):
        console.print(f"{b_sec_accent}{label}{r_sec_reset}")
        console.print(f"{b_sec_text}{value}{r_sec_reset}")

    if session_id:
        console.print(f"[dim {dim}]Session: {session_id}[/]")

    # Update check — show update available quietly
    try:
        behind = get_update_result(timeout=0.3)
        if behind is not None and behind != 0:
            if behind > 0:
                commits_word = "commit" if behind == 1 else "commits"
                console.print(f"[dim {dim}]{behind} {commits_word} behind — update available[/]")
            else:
                console.print(f"[dim {dim}]update available[/]")
    except Exception:
        pass

    console.print()
    try:
        from aetheros_cli.skin_engine import get_active_prompt_symbol
        symbol = get_active_prompt_symbol(">")
        console.print(f"[{dim}]Ready.[/]")
    except Exception:
        console.print(f"[{dim}]Ready.[/]")

    console.print()
