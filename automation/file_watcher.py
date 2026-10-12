"""
Filesystem watcher for event-triggered automations (Master 13 Phase 14).

Design constraints:

- Stdlib-only polling (os.scandir snapshots) — no new dependency; a watchdog
  backend can replace the poll loop later without changing the emitted
  contract.
- Fail-closed boundaries: only configured ``allowed_roots`` (config.yaml
  ``automation.file_watchers.allowed_roots``) are ever scanned; every path is
  re-validated to resolve inside its root before an event is emitted, so a
  symlink swap mid-scan can never leak events from outside.
- Debounce: changes observed within ``debounce_seconds`` coalesce per path,
  collapsing create/modify storms into one event carrying the final state.
- Dedup + caps: identical (path,event) notifications within the dedup TTL are
  dropped; per-cycle and per-root scan caps keep a huge tree from starving
  the process.

Emitted events (via automation.events.publish_external):

    file.created / file.modified / file.deleted
    payload: {"path": str, "root": str}
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

FileState = Dict[str, Tuple[int, int]]          # path -> (mtime_ns, size)


def watcher_settings(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Resolve automation.file_watchers settings with safe defaults."""
    if cfg is None:
        try:
            from aetheros_cli.config import load_config

            cfg = load_config()
        except Exception:
            cfg = {}
    section = cfg.get("automation", {}) if isinstance(cfg, dict) else {}
    fw = section.get("file_watchers", {}) if isinstance(section.get("file_watchers"), dict) else {}

    def _num(key: str, default: float) -> float:
        try:
            value = float(fw.get(key, default))
        except (TypeError, ValueError):
            return default
        return value if value > 0 else default

    roots = fw.get("allowed_roots")
    if not isinstance(roots, list):
        roots = []
    allowed: List[str] = []
    seen: Set[str] = set()
    for root in roots[:32]:
        text = str(root or "").strip()
        if not text:
            continue
        expanded = str(Path(text).expanduser())
        if expanded and expanded not in seen:
            seen.add(expanded)
            allowed.append(expanded)
    return {
        "allowed_roots": allowed,
        "poll_interval_seconds": min(_num("poll_interval_seconds", 5.0), 300.0),
        "debounce_seconds": max(0.0, _num("debounce_seconds", 2.0)),
        "max_files_per_root": int(max(100, _num("max_files_per_root", 20000))),
        "max_events_per_cycle": int(max(1, _num("max_events_per_cycle", 200))),
    }


class FileWatcher:
    """Polling differ over a fixed set of validated roots."""

    def __init__(self, roots: List[str], settings: Optional[Dict[str, Any]] = None):
        self.settings = settings or watcher_settings({})
        self.roots = self._validate_roots(roots)
        self._snapshots: Dict[str, FileState] = {root: {} for root in self.roots}
        self._primed = {root: False for root in self.roots}
        # debounce buffer: path -> {"event": str, "root": str, "first_seen": ts}
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._last_emitted: Dict[str, float] = {}
        self._dedup_ttl = max(
            float(self.settings.get("debounce_seconds", 2.0)) * 2.0, 1.0
        )

    def _validate_roots(self, roots: List[str]) -> List[str]:
        allowed = [str(Path(r)) for r in self.settings.get("allowed_roots") or []]
        valid: List[str] = []
        for root in roots or []:
            candidate = str(Path(str(root)).expanduser())
            resolved = self._safe_resolve(candidate)
            if resolved is None:
                logger.warning(
                    "File watcher root %r rejected: does not exist or escapes "
                    "automation.file_watchers.allowed_roots",
                    candidate,
                )
                continue
            inside = any(
                resolved == allowed_root
                or resolved.startswith(allowed_root + os.sep)
                for allowed_root in allowed
            )
            if not inside:
                logger.warning(
                    "File watcher root %r is outside allowed_roots — denied "
                    "(fail closed)",
                    candidate,
                )
                continue
            if resolved not in valid:
                valid.append(resolved)
        return valid

    @staticmethod
    def _safe_resolve(path: str) -> Optional[str]:
        try:
            p = Path(path).expanduser()
            if not p.exists():
                return None
            return str(p.resolve())
        except OSError:
            return None

    def _snapshot(self, root: str) -> FileState:
        state: FileState = {}
        cap = int(self.settings["max_files_per_root"])
        base = Path(root)
        try:
            for current, dirs, files in os.walk(base, followlinks=False):
                dirs[:] = [
                    d for d in dirs
                    if not d.startswith(".") and len(os.path.join(current, d)) < 500
                ]
                for name in files:
                    if len(state) >= cap:
                        logger.warning(
                            "File watcher hit max_files_per_root=%d under %s; "
                            "further entries ignored this cycle",
                            cap, root,
                        )
                        return state
                    full = os.path.join(current, name)
                    try:
                        st = os.stat(full, follow_symlinks=False)
                        if not os.path.isfile(full):
                            continue
                        state[full] = (st.st_mtime_ns, st.st_size)
                    except OSError:
                        continue
        except OSError as exc:
            logger.debug("Watcher scan failed for %s: %s", root, exc)
        return state

    def _emit_ready(self, now: float) -> List[dict]:
        ready: List[dict] = []
        keep: Dict[str, Dict[str, Any]] = {}
        cap = int(self.settings["max_events_per_cycle"])
        for path, entry in self._pending.items():
            if len(ready) < cap and now - entry["first_seen"] >= float(
                self.settings["debounce_seconds"]
            ):
                last = self._last_emitted.get(path)
                if last is not None and now - last < self._dedup_ttl:
                    continue
                self._last_emitted[path] = now
                ready.append(entry)
            else:
                keep[path] = entry
        # Bound the dedup map.
        if len(self._last_emitted) > 8192:
            cutoff = now - self._dedup_ttl * 4
            self._last_emitted = {
                p: t for p, t in self._last_emitted.items() if t > cutoff
            }
        self._pending = keep
        return ready

    def poll(self) -> List[dict]:
        """One scan cycle. Returns debounced change descriptors (not yet Events)."""
        now = time.time()
        changes: List[dict] = []
        for root in self.roots:
            previous = self._snapshots.get(root, {})
            current = self._snapshot(root)
            self._snapshots[root] = current
            if not self._primed[root]:
                # First pass establishes the baseline without emitting a flood.
                self._primed[root] = True
                continue
            for path in current.keys() - previous.keys():
                changes.append({"event": "created", "path": path, "root": root})
            for path in current.keys() & previous.keys():
                if current[path] != previous[path]:
                    changes.append({"event": "modified", "path": path, "root": root})
            for path in previous.keys() - current.keys():
                changes.append({"event": "deleted", "path": path, "root": root})

        for change in changes[: int(self.settings["max_events_per_cycle"])]:
            path = change["path"]
            existing = self._pending.get(path)
            if existing is None:
                self._pending[path] = {
                    "event": change["event"],
                    "path": path,
                    "root": change["root"],
                    "first_seen": now,
                }
            elif change["event"] == "deleted":
                existing["event"] = "deleted"
        return changes

    def flush_ready(self) -> List[dict]:
        """Emit debounced entries whose quiet period elapsed."""
        return self._emit_ready(time.time())


def emit_changes(changes: List[dict], bus_publish: Optional[Callable] = None) -> int:
    """Publish watcher change descriptors as external events. Returns count."""
    publish = bus_publish
    if publish is None:
        from automation.events import publish_external as publish
    count = 0
    for entry in changes:
        path = entry.get("path") or ""
        root = entry.get("root") or ""
        resolved = FileWatcher._safe_resolve(path) if entry.get("event") != "deleted" else None
        if entry.get("event") != "deleted":
            if resolved is None:
                continue
            normalized_root = FileWatcher._safe_resolve(root)
            if normalized_root is None or not (
                resolved == normalized_root
                or resolved.startswith(normalized_root + os.sep)
            ):
                logger.warning(
                    "Suppressed %s event: %r escaped root %r",
                    entry.get("event"), path, root,
                )
                continue
            payload_path = resolved
        else:
            payload_path = str(Path(path))
        publish(
            f"file.{entry.get('event', 'modified')}",
            {"path": payload_path, "root": root},
            source=f"file_watcher:{root}",
        )
        count += 1
    return count
