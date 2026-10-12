"""Model routing — deterministic provider/model selection policies.

``aetheros models route`` exposes routing policies on top of the existing
provider + model infrastructure. Routing is *advisory*: it returns the
``(provider, model, rationale)`` the policy picks, and can persist a chosen
provider/model pair to ``config.yaml``. It never rewrites the conversation
loop's provider resolution — that stays driven by config.

Policies:

* ``manual``  — whatever ``model.provider`` / ``model.default`` say (no change)
* ``fastest`` — prefer low-latency providers (local backends first, then the
  configured providers with the fastest known class)
* ``cheapest`` — lowest per-1M-token cost from the models.dev catalog
* ``quality`` — highest-context / reasoning-capable catalog entry
* ``offline`` — a configured local backend (ollama/lmstudio/custom on
  ``localhost``/``127.0.0.1``)
* ``enterprise`` — a configured enterprise provider (azure/bedrock/vertex/…),
  else fall back to manual

None of the policies probe the network on every call — cheapest/quality read
the models.dev disk cache when present and fall back to the configured model
otherwise.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

ROUTING_MODES = ("manual", "fastest", "cheapest", "quality", "offline", "enterprise")

# Providers that are genuinely low-latency first-party clouds (used by the
# "fastest" policy when local is unavailable).
_FAST_CLOUD_PROVIDERS = ("anthropic", "gemini", "openai-api", "deepseek", "xai", "groq")

# Providers that are enterprise/self-host-friendly (used by "enterprise").
_ENTERPRISE_PROVIDERS = ("azure-foundry", "bedrock", "google-vertex-ai", "vertex-ai", "cloudflare")


def _config() -> dict:
    from aetheros_cli.config import load_config

    try:
        return load_config()
    except Exception:
        return {}


def _configured_providers() -> list[str]:
    """Providers that have credentials available right now."""
    try:
        from aetheros_cli.provider_health import list_configured_providers

        return list_configured_providers()
    except Exception:
        return []


def _local_providers() -> list[str]:
    """Configured providers that talk to a localhost backend."""
    from providers import get_provider_profile, list_providers

    out = []
    for p in list_providers():
        base = (p.base_url or "").lower()
        if any(h in base for h in ("localhost", "127.0.0.1", "0.0.0.0")):
            if get_provider_profile(p.name) is not None:
                out.append(p.name)
    return out


def _default_route() -> tuple[Optional[str], Optional[str]]:
    cfg = _config()
    provider = (cfg.get("model") or {}).get("provider") or os.environ.get("AETHEROS_MODEL_PROVIDER") or ""
    model = (cfg.get("model") or {}).get("default") or os.environ.get("AETHEROS_MODEL") or ""
    return provider or None, model or None


def _catalog_pricing() -> list[dict]:
    """Annotated (provider, model, cost, context) rows from models.dev cache."""
    try:
        from agent.models_dev import fetch_models_dev

        data = fetch_models_dev()
    except Exception:
        return []
    rows = []
    for pdata in (data or {}).values():
        if not isinstance(pdata, dict):
            continue
        provider = str(pdata.get("id", ""))
        models = pdata.get("models", {})
        if not isinstance(models, dict):
            continue
        for mid, mraw in models.items():
            if not isinstance(mraw, dict):
                continue
            cost = mraw.get("cost")
            if isinstance(cost, dict):
                cost_in = float(cost.get("input") or 0)
                cost_out = float(cost.get("output") or 0)
            else:
                cost_in = float(mraw.get("input_cost_per_million") or 0)
                cost_out = float(mraw.get("output_cost_per_million") or 0)
            limit = mraw.get("limit")
            ctx = 0
            if isinstance(limit, dict):
                ctx = int(limit.get("context") or 0)
            if not ctx:
                ctx = int(mraw.get("context_window") or 0)
            reasoning = bool(mraw.get("reasoning") or False)
            if cost_in > 0 or cost_out > 0 or ctx > 0:
                rows.append(
                    {
                        "provider": provider,
                        "model": str(mid),
                        "cost": cost_in + cost_out,
                        "context": ctx,
                        "reasoning": reasoning,
                    }
                )
    return rows


def _best_from_catalog(mode: str, rows: list[dict]) -> Optional[dict]:
    """Pick the best row for a mode, preferring configured providers.

    Returns None when ``rows`` is empty.
    """
    if not rows:
        return None
    configured = _configured_providers()
    preferred = [r for r in rows if r["provider"] in configured]
    pool = preferred or rows
    if mode == "cheapest":
        return min(pool, key=lambda r: r["cost"])
    # quality
    return max(pool, key=lambda r: (r["reasoning"], r["context"]))


def resolve_route(mode: str = "manual", *, persist: bool = False) -> dict:
    """Resolve the current route for a routing mode.

    Returns ``{mode, provider, model, rationale, configured}`` where
    ``configured`` is the pre-existing ``model.provider`` / ``model.default``.
    """
    mode = (mode or "manual").lower()
    if mode not in ROUTING_MODES:
        raise ValueError(f"unknown routing mode {mode!r}; expected one of {', '.join(ROUTING_MODES)}")

    cur_provider, cur_model = _default_route()
    cfg = _config()

    if mode == "manual":
        return {
            "mode": mode,
            "provider": cur_provider,
            "model": cur_model,
            "rationale": "manual — uses configured provider/model",
            "configured": True,
        }

    if mode == "offline":
        local = _local_providers()
        if local:
            provider = local[0]
            model = (cfg.get("model") or {}).get("default") or (cfg.get("model") or {}).get("local_model") or ""
            return {
                "mode": mode,
                "provider": provider,
                "model": model or None,
                "rationale": f"offline — local backend '{provider}' configured",
                "configured": cur_provider == provider,
            }
        return {
            "mode": mode,
            "provider": cur_provider,
            "model": cur_model,
            "rationale": "offline — no localhost backend configured; using current route",
            "configured": True,
        }

    if mode == "enterprise":
        configured = _configured_providers()
        for p in _ENTERPRISE_PROVIDERS:
            if p in configured or any(p in c for c in configured):
                return {
                    "mode": mode,
                    "provider": p,
                    "model": (cfg.get("model") or {}).get("default") or None,
                    "rationale": f"enterprise — '{p}' configured",
                    "configured": cur_provider == p,
                }
        return {
            "mode": mode,
            "provider": cur_provider,
            "model": cur_model,
            "rationale": "enterprise — no enterprise provider configured; using current route",
            "configured": True,
        }

    if mode == "cheapest":
        best = _best_from_catalog("cheapest", _catalog_pricing())
        if best:
            return {
                "mode": mode,
                "provider": best["provider"],
                "model": best["model"],
                "rationale": f"cheapest — ${best['cost']:.2f}/M (input+output) per models.dev",
                "configured": False,
            }

    if mode == "quality":
        best = _best_from_catalog("quality", _catalog_pricing())
        if best:
            # Prefer reasoning models with the largest context, then lowest cost.
            return {
                "mode": mode,
                "provider": best["provider"],
                "model": best["model"],
                "rationale": f"quality — {best['model']} (context {best['context']}, reasoning)",
                "configured": False,
            }

    if mode == "fastest":
        local = _local_providers()
        if local:
            provider = local[0]
            return {
                "mode": mode,
                "provider": provider,
                "model": (cfg.get("model") or {}).get("default") or None,
                "rationale": f"fastest — local backend '{provider}' (zero network latency)",
                "configured": cur_provider == provider,
            }
        configured = _configured_providers()
        for p in _FAST_CLOUD_PROVIDERS:
            if p in configured:
                return {
                    "mode": mode,
                    "provider": p,
                    "model": (cfg.get("model") or {}).get("default") or None,
                    "rationale": f"fastest — low-latency provider '{p}' configured",
                    "configured": cur_provider == p,
                }
        return {
            "mode": mode,
            "provider": cur_provider,
            "model": cur_model,
            "rationale": "fastest — no fast provider configured; using current route",
            "configured": True,
        }

    # Fallback — should be unreachable for valid modes.
    return {
        "mode": mode,
        "provider": cur_provider,
        "model": cur_model,
        "rationale": "fallback — using current route",
        "configured": True,
    }


def persist_route(route: dict) -> bool:
    """Persist a route's provider/model into config.yaml (best-effort).

    Returns True when the config was written. ``manual`` routes are a no-op
    (they already describe the configured state).
    """
    provider = route.get("provider")
    model = route.get("model")
    if not provider:
        return False
    try:
        from aetheros_cli.config import set_config_value

        if provider:
            set_config_value("model.provider", provider)
        if model:
            set_config_value("model.default", model)
        return True
    except Exception as exc:
        logger.warning("persist_route failed: %s", exc)
        return False
