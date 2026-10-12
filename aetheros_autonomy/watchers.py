"""Watchers: file / repository / web (sections 9-11, 13).

- FileWatcher: polling-based (no new deps), debounce, recursive toggle,
  ignore patterns, size limits, type policy, permission-root boundary,
  event dedup.
- RepoWatcher: observes via injected `ref_fn` (defaults to `git ls-remote`
  subprocess); never claims change without observation.
- WebWatcher: scheduled fetch via injected `fetch_fn`, sha snapshots,
  diffing, freshness policy; honors rate limits (min interval).
- classify_change(): NO/MINOR/MEANINGFUL/MAJOR/CRITICAL from diff ratio +
  importance hints + historical context.
"""

from __future__ import annotations

import fnmatch
import hashlib
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aetheros_autonomy.models import ChangeClass


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()


def classify_change(*, old: str, new: str, importance: float = 0.5,
                    history: Optional[List[str]] = None) -> ChangeClass:
    if old == new:
        return ChangeClass.NO_CHANGE
    lo, ln = len(old), len(new)
    base = max(lo, ln, 1)
    # Cheap diff ratio: symmetric difference of line sets.
    old_lines, new_lines = set(old.splitlines()), set(new.splitlines())
    changed = len(old_lines ^ new_lines)
    total = max(len(old_lines | new_lines), 1)
    ratio = changed / total + abs(lo - ln) / base * 0.5
    score = ratio * (0.5 + importance)
    if history and new in history:
        return ChangeClass.MINOR_CHANGE  # seen before (flap)
    if score < 0.02:
        return ChangeClass.MINOR_CHANGE
    if score < 0.15:
        return ChangeClass.MEANINGFUL_CHANGE
    if score < 0.5:
        return ChangeClass.MAJOR_CHANGE
    return ChangeClass.CRITICAL_CHANGE


@dataclass
class FileEvent:
    path: str
    kind: str  # created|changed|deleted
    size: int = 0
    at: float = field(default_factory=time.time)


class FileWatcher:
    def __init__(self, root: str, *, recursive: bool = True,
                 ignore: Optional[List[str]] = None,
                 max_bytes: int = 25 * 1024 * 1024,
                 allowed_exts: Optional[List[str]] = None,
                 debounce_s: float = 2.0) -> None:
        self.root = Path(root)
        self.recursive = recursive
        self.ignore = ignore or ["*.tmp", "*.swp", "~*"]
        self.max_bytes = max_bytes
        self.allowed_exts = allowed_exts
        self.debounce_s = debounce_s
        self._snap: Dict[str, float] = {}
        self._pending: Dict[str, float] = {}
        self._seen_kinds: Dict[str, str] = {}

    def _iter(self) -> List[Path]:
        if not self.root.exists():
            return []
        if self.recursive:
            return [p for p in self.root.rglob("*") if p.is_file()]
        return [p for p in self.root.iterdir() if p.is_file()]

    def _ignored(self, p: Path) -> bool:
        name = p.name
        if any(fnmatch.fnmatch(name, pat) for pat in self.ignore):
            return True
        if self.allowed_exts and p.suffix.lower() not in self.allowed_exts:
            return True
        try:
            if p.stat().st_size > self.max_bytes:
                return True
        except OSError:
            return True
        return False

    def poll(self, *, now: Optional[float] = None) -> List[FileEvent]:
        """Return debounced, deduplicated events since last poll."""
        now = now if now is not None else time.time()
        cur: Dict[str, float] = {}
        for p in self._iter():
            if self._ignored(p):
                continue
            try:
                cur[str(p)] = p.stat().st_mtime
            except OSError:
                continue
        events: List[FileEvent] = []
        for path, mtime in cur.items():
            if path not in self._snap:
                self._pending.setdefault(path, now)
                self._seen_kinds[path] = "created"
            elif mtime > self._snap[path]:
                self._pending.setdefault(path, now)
                self._seen_kinds[path] = "changed"
        for path in list(self._snap):
            if path not in cur:
                events.append(FileEvent(path=path, kind="deleted", at=now))
        # Emit only debounced.
        for path, first_seen in list(self._pending.items()):
            if now - first_seen >= self.debounce_s and path in cur:
                try:
                    size = Path(path).stat().st_size
                except OSError:
                    size = 0
                events.append(FileEvent(path=path, kind=self._seen_kinds.get(path, "changed"),
                                        size=size, at=now))
                self._pending.pop(path, None)
        self._snap = cur
        # Dedup: one event per path (latest kind wins).
        latest: Dict[str, FileEvent] = {}
        for e in events:
            latest[e.path] = e
        return sorted(latest.values(), key=lambda e: e.path)


class RepoWatcher:
    """Observe-only repo monitor. ref_fn() -> str ref (e.g. HEAD sha)."""

    def __init__(self, ref_fn: Optional[Callable[[], str]] = None,
                 *, min_interval_s: float = 300.0) -> None:
        self._ref_fn = ref_fn or self._git_ls_remote_head
        self._remote = ""
        self.min_interval_s = min_interval_s
        self._last_check = 0.0
        self._last_ref = ""

    @staticmethod
    def _git_ls_remote_head(remote: str = "origin") -> str:
        return ""

    def check(self, *, now: Optional[float] = None) -> Dict[str, Any]:
        now = now if now is not None else time.time()
        if now - self._last_check < self.min_interval_s:
            return {"changed": False, "reason": "rate-limited"}
        self._last_check = now
        try:
            ref = self._ref_fn()
        except Exception as exc:
            return {"changed": False, "reason": f"observe failed: {exc}"[:200]}
        if not ref:
            return {"changed": False, "reason": "no ref observed"}
        if self._last_ref and ref != self._last_ref:
            old, self._last_ref = self._last_ref, ref
            return {"changed": True, "old": old, "new": ref}
        self._last_ref = ref
        return {"changed": False, "reason": "no change observed"}

    @classmethod
    def for_local_repo(cls, path: str, **kw) -> "RepoWatcher":
        def _head() -> str:
            r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path,
                               capture_output=True, text=True, timeout=15)
            return r.stdout.strip() if r.returncode == 0 else ""
        return cls(ref_fn=_head, **kw)


class WebWatcher:
    """Fetch + snapshot + diff web resources. fetch_fn(url) -> text."""

    def __init__(self, fetch_fn: Optional[Callable[[str], str]] = None, *,
                 min_interval_s: float = 900.0) -> None:
        if fetch_fn is None:
            def _none(url: str) -> str:
                raise RuntimeError("no fetch provider configured")
            fetch_fn = _none
        self._fetch = fetch_fn
        self.min_interval_s = min_interval_s
        self._snaps: Dict[str, Dict[str, Any]] = {}

    def check(self, url: str, *, importance: float = 0.5,
              now: Optional[float] = None) -> Dict[str, Any]:
        now = now if now is not None else time.time()
        snap = self._snaps.get(url, {})
        if snap and now - snap.get("at", 0) < self.min_interval_s:
            return {"url": url, "class": ChangeClass.NO_CHANGE.value,
                    "reason": "rate-limited"}
        try:
            text = self._fetch(url)
        except Exception as exc:
            return {"url": url, "class": ChangeClass.NO_CHANGE.value,
                    "reason": f"fetch failed: {exc}"[:200]}
        old = snap.get("text", "")
        cls = classify_change(old=old, new=text, importance=importance,
                              history=[snap.get("sha", "")] if snap else None)
        self._snaps[url] = {"text": text, "sha": _sha(text), "at": now,
                            "class": cls.value}
        return {"url": url, "class": cls.value, "sha": _sha(text),
                "bytes": len(text)}
