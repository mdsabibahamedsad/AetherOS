"""Extension sources: local/bundled/remote/git/private/org/offline.

Every source has a trust policy; arbitrary git repos are never auto-
trusted. Remote fetch via injected fetchers (offline-first: installed +
cached metadata keep working when registries are unreachable).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

FetchFn = Callable[[str], bytes]


@dataclass
class SourcePolicy:
    kind: str  # local|bundled|remote|git|private|org|builtin
    ref: str = ""
    trust: str = "untrusted"  # trusted|untrusted
    allow_unsigned: bool = False
    offline_ok: bool = True


BUILTIN_POLICY = SourcePolicy(kind="builtin", trust="trusted", allow_unsigned=True)
LOCAL_POLICY = SourcePolicy(kind="local", trust="untrusted", allow_unsigned=False)


class SourceManager:
    def __init__(self, *, fetch: Optional[FetchFn] = None,
                 cache_dir: Optional[Path] = None) -> None:
        self._fetch = fetch
        self._cache = Path(cache_dir) if cache_dir else None
        self._policies: Dict[str, SourcePolicy] = {}
        if self._cache:
            self._cache.mkdir(parents=True, exist_ok=True)

    def set_policy(self, name: str, policy: SourcePolicy) -> None:
        self._policies[name] = policy

    def policy_for(self, kind: str, ref: str = "") -> SourcePolicy:
        if kind == "builtin":
            return BUILTIN_POLICY
        if kind in ("local", "local_package"):
            return LOCAL_POLICY
        for name, pol in self._policies.items():
            if pol.kind == kind and (not pol.ref or pol.ref == ref):
                return pol
        # Fail closed: unknown remote kinds are untrusted, unsigned blocked.
        return SourcePolicy(kind=kind, ref=ref, trust="untrusted",
                            allow_unsigned=False)

    def fetch_index(self, url: str) -> Dict[str, Any]:
        """Fetch a registry index with disk cache fallback (offline mode)."""
        cached = self._cached(url)
        if self._fetch is None:
            if cached is not None:
                return {"index": cached, "online": False, "source": "cache"}
            return {"index": {}, "online": False, "source": "none"}
        try:
            raw = self._fetch(url)
            index = json.loads(raw.decode("utf-8"))
            self._store_cache(url, index)
            return {"index": index, "online": True, "source": url}
        except Exception as exc:
            if cached is not None:
                return {"index": cached, "online": False,
                        "source": "cache", "error": str(exc)[:200]}
            return {"index": {}, "online": False, "source": "none",
                    "error": str(exc)[:200]}

    def _key(self, url: str) -> str:
        import hashlib
        return hashlib.sha256(url.encode()).hexdigest() + ".json"

    def _cached(self, url: str) -> Optional[Dict[str, Any]]:
        if self._cache is None:
            return None
        path = self._cache / self._key(url)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def _store_cache(self, url: str, index: Dict[str, Any]) -> None:
        if self._cache is None:
            return
        try:
            (self._cache / self._key(url)).write_text(
                json.dumps(index, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
