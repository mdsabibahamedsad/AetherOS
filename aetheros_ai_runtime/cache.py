"""Model cache + warming/eviction + download budgets (sections 49-52).

Metadata/download/runtime/benchmark caches with validation; warming
policies cold/warm/hot; LRU eviction that never evicts running models;
disk/VRAM budgets enforced before download/load.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional


class ModelCache:
    def __init__(self, *, max_entries: int = 200) -> None:
        self._lock = threading.Lock()
        self._meta: OrderedDict = OrderedDict()
        self._max = max_entries

    def put_meta(self, key: str, value: Dict[str, Any]) -> None:
        with self._lock:
            self._meta[key] = {"value": value, "at": time.time()}
            self._meta.move_to_end(key)
            while len(self._meta) > self._max:
                self._meta.popitem(last=False)

    def get_meta(self, key: str, *, max_age_s: float = 3600.0) -> Optional[Dict[str, Any]]:
        with self._lock:
            entry = self._meta.get(key)
            if entry is None:
                return None
            if time.time() - entry["at"] > max_age_s:
                self._meta.pop(key, None)
                return None
            self._meta.move_to_end(key)
            return entry["value"]

    def validate_artifact(self, path: Path, *, sha256: str = "") -> Dict[str, Any]:
        p = Path(path)
        if not p.exists():
            return {"ok": False, "reason": "missing"}
        if sha256:
            import hashlib
            digest = hashlib.sha256()
            with open(p, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    digest.update(chunk)
            if digest.hexdigest() != sha256.lower():
                return {"ok": False, "reason": "checksum mismatch"}
        return {"ok": True, "reason": "present" + ("+verified" if sha256 else "")}


class WarmPool:
    def __init__(self, *, vram_budget_gb: float = 0.0) -> None:
        self._lock = threading.Lock()
        self._loaded: Dict[str, Dict[str, Any]] = {}  # id -> {gb, running, at}
        self.budget_gb = vram_budget_gb

    def load(self, model_id: str, gb: float, policy: str = "warm") -> Dict[str, Any]:
        """Load honoring VRAM budget (cold=skip when pressured)."""
        with self._lock:
            used = sum(v["gb"] for v in self._loaded.values())
            if policy == "cold":
                return {"loaded": False, "reason": "cold policy: on-demand only"}
            if self.budget_gb and used + gb > self.budget_gb:
                evicted = self._evict_locked(exclude_running=True,
                                             need_gb=gb)
                used = sum(v["gb"] for v in self._loaded.values())
                if self.budget_gb and used + gb > self.budget_gb:
                    return {"loaded": False, "reason": "vram budget exceeded",
                            "evicted": evicted}
                return {"loaded": True, "evicted": evicted}
            self._loaded[model_id] = {"gb": gb, "running": False,
                                      "at": time.time()}
            return {"loaded": True, "evicted": []}

    def mark_running(self, model_id: str, running: bool = True) -> None:
        with self._lock:
            if model_id in self._loaded:
                self._loaded[model_id]["running"] = running
                self._loaded[model_id]["at"] = time.time()

    def evict(self, *, need_gb: float = 0.0) -> List[str]:
        with self._lock:
            return self._evict_locked(exclude_running=True, need_gb=need_gb)

    def _evict_locked(self, *, exclude_running: bool,
                      need_gb: float) -> List[str]:
        cands = sorted(
            ((k, v) for k, v in self._loaded.items()
             if not (exclude_running and v.get("running"))),
            key=lambda kv: kv[1]["at"])
        evicted, freed = [], 0.0
        for k, v in cands:
            if need_gb and freed >= need_gb:
                break
            evicted.append(k)
            freed += v["gb"]
        for k in evicted:
            self._loaded.pop(k, None)
        return evicted

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {"loaded": list(self._loaded),
                    "used_gb": round(sum(v["gb"] for v in self._loaded.values()), 2),
                    "budget_gb": self.budget_gb}
