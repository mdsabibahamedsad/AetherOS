"""Model registry — user-managed per-model state.

Tracks persistent per-model annotations across all providers:

* **favorite** — quick-access flag (surfaces first in pickers)
* **pinned** — pinned to the top of the registry / pickers
* **hidden** — hidden from interactive pickers (but still selectable by id)
* **deprecated** — marked deprecated by the user or the catalog

State lives in ``$AETHEROS_HOME/state/model_registry.json`` — one JSON file,
no schema migrations needed (additive keys with defaults).

The registry is a *pure data* layer: it never talks to the network and never
mutates provider/model catalogs. It only annotates model IDs. Search/filter/
sort helpers operate on (provider, model_id) pairs supplied by the caller.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

_FLAGS = ("favorite", "pinned", "hidden", "deprecated")


class ModelRegistry:
    """Persistent per-model annotation store."""

    def __init__(self, path: str | os.PathLike | None = None):
        self._path = path
        self._data: dict[str, dict[str, Any]] = {}
        self._loaded = False

    @property
    def path(self):
        if self._path is not None:
            return self._path
        from aetheros_constants import get_aetheros_home

        home = get_aetheros_home()
        return home / "state" / "model_registry.json"

    # ── persistence ──────────────────────────────────────────
    def load(self) -> "ModelRegistry":
        if self._loaded:
            return self
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as fh:
                    raw = json.load(fh)
                if isinstance(raw, dict):
                    self._data = {
                        str(k): dict(v) for k, v in raw.items() if isinstance(v, dict)
                    }
        except Exception as exc:
            logger.debug("model registry load failed: %s", exc)
        self._loaded = True
        return self

    def save(self) -> bool:
        try:
            parent = os.path.dirname(os.path.abspath(self.path))
            os.makedirs(parent, exist_ok=True)
            tmp = f"{self.path}.tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, sort_keys=True)
            os.replace(tmp, self.path)
            return True
        except Exception as exc:
            logger.warning("model registry save failed: %s", exc)
            return False

    # ── accessors ───────────────────────────────────────────
    def get(self, model_id: str) -> dict[str, Any]:
        self.load()
        return dict(self._data.get(model_id, {}))

    def _entry(self, model_id: str) -> dict[str, Any]:
        self.load()
        entry = self._data.setdefault(model_id, {})
        entry.setdefault("favorite", False)
        entry.setdefault("pinned", False)
        entry.setdefault("hidden", False)
        entry.setdefault("deprecated", False)
        return entry

    def flag(self, model_id: str, flag: str) -> bool:
        """Return the value of a flag (default False)."""
        if flag not in _FLAGS:
            return False
        return bool(self.get(model_id).get(flag, False))

    def set_flag(self, model_id: str, flag: str, value: bool) -> bool:
        """Set a flag and persist. Returns the new value."""
        if flag not in _FLAGS:
            return False
        entry = self._entry(model_id)
        entry[flag] = bool(value)
        if not any(entry.get(f) for f in _FLAGS):
            # Drop empty entries to keep the file tidy.
            self._data.pop(model_id, None)
        self.save()
        return entry[flag]

    def toggle(self, model_id: str, flag: str) -> bool:
        """Toggle a flag and persist. Returns the new value."""
        if flag not in _FLAGS:
            return False
        current = self.flag(model_id, flag)
        return self.set_flag(model_id, flag, not current)

    def mark_deprecated(self, model_id: str, deprecated: bool = True) -> bool:
        return self.set_flag(model_id, "deprecated", deprecated)

    # ── collections ─────────────────────────────────────────
    def models_with_flag(self, flag: str) -> list[str]:
        if flag not in _FLAGS:
            return []
        self.load()
        return [mid for mid, entry in self._data.items() if entry.get(flag)]

    @property
    def favorites(self) -> list[str]:
        return self.models_with_flag("favorite")

    @property
    def pinned(self) -> list[str]:
        return self.models_with_flag("pinned")

    @property
    def hidden(self) -> list[str]:
        return self.models_with_flag("hidden")

    @property
    def deprecated(self) -> list[str]:
        return self.models_with_flag("deprecated")

    # ── filtering / sorting ─────────────────────────────────
    @staticmethod
    def sort_models(rows: list[tuple[str, str]], *, key: str = "default") -> list[tuple[str, str]]:
        """Sort ``(provider, model_id)`` rows by a display strategy.

        ``default`` — pinned first (registry order), then favorites, then
        provider name, then model id. ``name`` — alphabetical by model id.
        """
        if key == "name":
            return sorted(rows, key=lambda r: (r[0].lower(), r[1].lower()))
        registry = get_registry()

        def _rank(row):
            pinned = registry.flag(row[1], "pinned")
            favorite = registry.flag(row[1], "favorite")
            return (0 if pinned else 1 if favorite else 2, row[0].lower(), row[1].lower())

        return sorted(rows, key=_rank)

    def filter_visible(self, rows: list[tuple[str, str]], *, include_hidden: bool = False) -> list[tuple[str, str]]:
        """Drop hidden models unless ``include_hidden``."""
        if include_hidden:
            return list(rows)
        hidden = set(self.hidden)
        return [r for r in rows if r[1] not in hidden]

    def annotate(self, rows: list[tuple[str, str]]) -> list[dict]:
        """Attach flag annotations to ``(provider, model_id)`` rows."""
        out = []
        for provider, model_id in rows:
            entry = self.get(model_id)
            out.append(
                {
                    "provider": provider,
                    "model": model_id,
                    "favorite": entry.get("favorite", False),
                    "pinned": entry.get("pinned", False),
                    "hidden": entry.get("hidden", False),
                    "deprecated": entry.get("deprecated", False),
                }
            )
        return out


_default_registry: ModelRegistry | None = None


def get_registry() -> ModelRegistry:
    """Return the process-wide default registry (lazy)."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ModelRegistry()
    return _default_registry


def search_models(
    query: str = "",
    *,
    providers: list[str] | None = None,
    flag: str | None = None,
    include_hidden: bool = False,
    max_results: int = 50,
) -> list[dict]:
    """Search the known model universe.

    Builds ``(provider, model_id)`` pairs from the provider registry and the
    cached model catalogs, then applies the registry's hidden/flag filters and
    a substring match on the query.

    ``providers`` limits the scan (default: all providers). Returns annotated
    dicts from :meth:`ModelRegistry.annotate`.
    """
    from aetheros_cli.models import provider_model_ids

    from providers import list_providers

    registry = get_registry()
    selected_providers = [p for p in list_providers() if providers is None or p.name in providers]
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for p in selected_providers:
        try:
            ids = provider_model_ids(p.name)
        except Exception:
            ids = list(p.fallback_models or [])
        for mid in ids:
            mid = str(mid).strip()
            if not mid or mid in seen:
                continue
            seen.add(mid)
            rows.append((p.name, mid))

    if flag in _FLAGS:
        flagged = set(registry.models_with_flag(flag))
        rows = [r for r in rows if r[1] in flagged]

    rows = registry.filter_visible(rows, include_hidden=include_hidden)

    if query:
        q = query.strip().lower()
        rows = [r for r in rows if q in r[1].lower() or q in r[0].lower()]

    rows = ModelRegistry.sort_models(rows)
    annotated = registry.annotate(rows)
    return annotated[: max_results]


def resolve_model_identity(model_id: str) -> tuple[str, str] | None:
    """Resolve a ``provider:model`` or bare model id to ``(provider, model)``.

    Returns None when the model cannot be attributed to any known provider.
    """
    model_id = (model_id or "").strip()
    if not model_id:
        return None
    if ":" in model_id:
        provider, _, model = model_id.partition(":")
        from providers import get_provider_profile

        if get_provider_profile(provider.strip()) is not None and model.strip():
            return provider.strip(), model.strip()
    # Bare id — search the catalog universe.
    for row in search_models(model_id, max_results=200):
        if row["model"] == model_id:
            return row["provider"], row["model"]
    return None
