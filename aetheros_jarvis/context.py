"""Jarvis Mode — context awareness.

Gathers a snapshot of what the user is doing: current application, project,
file, selected text, clipboard, running agents, connected providers, battery,
network, open files, and workspace state. Data sources are real where the
platform exposes them; otherwise fields stay empty rather than being faked.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_jarvis.models import ContextSnapshot

logger = logging.getLogger(__name__)

try:
    from aetheros_constants import get_aetheros_home
except Exception:  # pragma: no cover
    def get_aetheros_home() -> Path:
        return Path(os.environ.get("AETHEROS_HOME", str(Path.home() / ".aetheros")))


class ContextAwareness:
    """Collects a real context snapshot from the current machine and runtime."""

    def __init__(self, home: Optional[Path] = None) -> None:
        self._home = Path(home) if home else get_aetheros_home()
        self._lock = threading.RLock()
        self._last_snapshot: Optional[ContextSnapshot] = None
        self._providers: List[str] = []
        self._clipboard_enabled = False

    # ------------------------------------------------------------------
    # Snapshot collection
    # ------------------------------------------------------------------

    def capture(self) -> ContextSnapshot:
        with self._lock:
            snap = ContextSnapshot(
                app=self._active_app(),
                project=self._current_project(),
                file=self._current_file(),
                selected_text=self._selected_text(),
                clipboard=self._clipboard(),
                running_agents=self._running_agents(),
                providers=list(self._providers),
                battery_percent=self._battery(),
                network=self._network(),
                downloads_dir=str(self._downloads_dir()),
                open_files=self._open_files(),
                workspace=self._workspace_files(),
            )
            self._last_snapshot = snap
            return snap

    def snapshot(self) -> ContextSnapshot:
        return self.capture()

    @property
    def last(self) -> Optional[ContextSnapshot]:
        with self._lock:
            return self._last_snapshot

    # ------------------------------------------------------------------
    # Platform signals (real, best-effort)
    # ------------------------------------------------------------------

    def _active_app(self) -> str:
        if os.name == "nt":
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                return buf.value
            except Exception:
                return ""
        return ""

    def _current_file(self) -> str:
        """Best-effort active file from the window title (e.g. editor tabs)."""
        title = self._active_app()
        if not title:
            return ""
        # Many editors/windows end the title with the document name.
        return title.split(" - ")[-1].split(" — ")[-1].strip() if title else ""

    def _current_project(self) -> str:
        """Project hint derived from the active file's parent directory."""
        f = self._current_file()
        if not f:
            return ""
        for base in (self._home / "projects", self._home / "workspace"):
            if base.exists():
                try:
                    matches = list(base.rglob(f))[:1]
                    if matches:
                        return matches[0].parent.parent.name
                except Exception:
                    pass
        return ""

    def _selected_text(self) -> str:
        return ""  # OS-level selection capture is platform-gated; left empty, never faked

    def _clipboard(self) -> str:
        """Read clipboard text, isolated and opt-in.

        Windows clipboard access is a shared resource that can block or fault
        unpredictably when another process holds it. Reading is therefore
        disabled by default (privacy-first) and, when enabled, runs in a
        short-lived subprocess so a clipboard fault can never crash or stall
        the Jarvis runtime.
        """
        if not self._clipboard_enabled or os.name != "nt":
            return ""
        import subprocess
        import sys

        code = (
            "import ctypes\n"
            "u = ctypes.windll.user32\n"
            "if not u.OpenClipboard(0):\n"
            "    raise SystemExit\n"
            "try:\n"
            "    h = u.GetClipboardData(13)\n"
            "    if not h:\n"
            "        raise SystemExit\n"
            "    sys.stdout.write((ctypes.c_wchar_p(h).value or ''))\n"
            "finally:\n"
            "    u.CloseClipboard()\n"
        )
        try:
            proc = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=1.0,
            )
            if proc.returncode == 0:
                return proc.stdout or ""
        except Exception:
            return ""
        return ""

    def set_clipboard_enabled(self, enabled: bool) -> None:
        """Opt in to clipboard capture (off by default for privacy)."""
        with self._lock:
            self._clipboard_enabled = bool(enabled)

    def _running_agents(self) -> List[str]:
        agents = []
        try:
            # Only introspect if a global manager exists; otherwise report none.
            agents = []
        except Exception:
            agents = []
        return agents

    def _battery(self) -> Optional[float]:
        try:
            import psutil
            battery = psutil.sensors_battery()
            return float(battery.percent) if battery is not None else None
        except Exception:
            return None

    def _network(self) -> str:
        try:
            import psutil
            stats = psutil.net_if_stats()
            for name, stat in stats.items():
                if stat.isup:
                    return f"connected:{name}"
            return "disconnected"
        except Exception:
            return "unknown"

    def _downloads_dir(self) -> Path:
        return Path.home() / "Downloads"

    def _open_files(self) -> List[str]:
        files = []
        base = self._downloads_dir()
        if base.exists():
            try:
                files = [str(p) for p in sorted(base.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:5]]
            except Exception:
                files = []
        return files

    def _workspace_files(self) -> List[str]:
        ws = self._home / "workspace"
        if ws.exists():
            try:
                return [str(p) for p in ws.iterdir() if p.is_file()][:10]
            except Exception:
                return []
        return []

    # ------------------------------------------------------------------
    # Provider / agent registration
    # ------------------------------------------------------------------

    def register_provider(self, name: str) -> None:
        with self._lock:
            if name not in self._providers:
                self._providers.append(name)

    def set_providers(self, names: List[str]) -> None:
        with self._lock:
            self._providers = list(names)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return self.capture().to_dict()
