"""Multi-provider fan-out and provider fallback chains (P6, P7, P93).

FanOutSearch queries every available search provider (or an explicit
subset), normalizes to a single envelope, and tags each result with its
provider. FallbackChain walks ordered candidates so native → MCP → browser
→ document fallbacks are explicit and policy-checked, never implicit.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


class FanOutSearch:
    """Query multiple independent providers; merge with provenance."""

    def __init__(self, providers: List[Any], per_provider_limit: int = 5):
        self.providers = [p for p in providers if getattr(p, "supports_search", lambda: True)()]
        self.per_provider_limit = per_provider_limit

    @classmethod
    def from_registry(cls, limit: int = 5,
                      preferred: Optional[List[str]] = None) -> "FanOutSearch":
        from agent.web_search_registry import list_providers

        providers = []
        wanted = preferred or None
        for name in sorted(list_providers()):
            if wanted is not None and name not in wanted:
                continue
            try:
                provider = list_providers()[name]
            except Exception:
                continue
            try:
                available = provider.is_available()
            except Exception:
                available = False
            if available and provider.supports_search():
                providers.append(provider)
        return cls(providers, per_provider_limit=limit)

    def __bool__(self) -> bool:
        return bool(self.providers)

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Merged envelope in the canonical shape: data.web entries carry
        an extra 'providers' list when the same URL appears in multiple
        independent indexes."""
        merged: Dict[str, Dict[str, Any]] = {}
        errors: List[str] = []
        for provider in self.providers:
            try:
                response = provider.search(query=query,
                                           limit=max(3, self.per_provider_limit))
            except Exception as exc:
                errors.append(f"{getattr(provider, 'name', '?')}:{exc}"[:120])
                continue
            if not isinstance(response, dict) or not response.get("success"):
                errors.append(f"{getattr(provider, 'name', '?')}:failed")
                continue
            for raw in ((response.get("data") or {}).get("web")) or []:
                url = str(raw.get("url") or "").strip()
                if not url:
                    continue
                key = url.rstrip("/")
                entry = merged.setdefault(key, {
                    "title": str(raw.get("title") or ""),
                    "url": url,
                    "description": str(raw.get("description") or ""),
                    "position": len(merged) + 1,
                    "providers": [],
                })
                pname = getattr(provider, "name", "unknown")
                if pname not in entry["providers"]:
                    entry["providers"].append(pname)
        web = sorted(merged.values(), key=lambda e: -len(e["providers"]))
        return {
            "success": bool(web),
            "data": {"web": web[:limit]},
            "fanout": {"providers_queried": len(self.providers),
                       "errors": errors[:5]},
        }


class FallbackChain:
    """P93: ordered fallback execution with typed failure recording."""

    def __init__(self, steps: List[Tuple[str, Callable[[], Any]]]):
        self.steps = steps

    def run(self) -> Dict[str, Any]:
        attempts = []
        for name, fn in self.steps:
            try:
                result = fn()
                ok = bool(result) and result is not None
                attempts.append({"step": name, "ok": ok})
                if ok:
                    return {"success": True, "via": name, "result": result,
                            "attempts": attempts}
            except Exception as exc:
                from agent.research.engine import classify_tool_failure

                attempts.append({
                    "step": name, "ok": False,
                    "failure": classify_tool_failure(exc).value,
                    "detail": str(exc)[:120],
                })
        return {"success": False, "via": None, "attempts": attempts}
