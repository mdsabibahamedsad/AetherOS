"""Provider health & capability introspection.

Thin, dependency-free layer over the ``providers/`` registry that answers the
two questions the CLI surfaces care about:

* **Is this provider reachable / authenticated right now?** —
  :func:`probe_provider_health` reuses ``ProviderProfile.check_health`` so
  per-provider auth quirks (``x-api-key`` for Anthropic, public catalogs for
  OpenRouter, custom headers) are honored automatically.
* **What can this provider do?** — :func:`provider_capabilities` exposes the
  declarative profile metadata (logo, category, api_mode, auth type, vision /
  streaming support, endpoints).

Nothing here mutates config, credentials, or runtime state — it is a
read-only introspection surface used by ``aetheros providers``.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Provider categories that never carry an API key but are still valid
# configured providers (OAuth / SDK / subprocess auth).
_NON_KEY_AUTH_TYPES = {
    "oauth_device_code",
    "oauth_external",
    "copilot",
    "aws_sdk",
    "external_process",
}


def _resolve_credentials(name: str) -> dict:
    """Best-effort credential resolution for a provider.

    Returns a dict with ``api_key`` / ``base_url`` keys (possibly empty).
    Never raises — resolution failures degrade to empty creds so callers can
    still report "unreachable/unconfigured" instead of crashing.
    """
    result: dict = {"api_key": "", "base_url": ""}
    try:
        from aetheros_cli.auth import resolve_api_key_provider_credentials

        creds = resolve_api_key_provider_credentials(name)
        if isinstance(creds, dict):
            result["api_key"] = str(creds.get("api_key") or "").strip()
            result["base_url"] = str(creds.get("base_url") or "").strip()
    except Exception:
        pass
    return result


def provider_capabilities(name: str) -> dict | None:
    """Return a declarative capability summary for a provider, or None."""
    from providers import get_provider_profile

    p = get_provider_profile(name)
    if p is None:
        return None
    return {
        "name": p.name,
        "display_name": p.display_name or p.name,
        "description": p.description,
        "logo": p.logo,
        "version": p.version,
        "category": p.category,
        "api_mode": p.api_mode,
        "auth_type": p.auth_type,
        "supports_vision": p.supports_vision,
        "supports_streaming": p.supports_streaming,
        "supports_health_check": p.supports_health_check,
        "base_url": p.base_url,
        "models_url": p.models_url,
        "hostname": p.get_hostname(),
        "signup_url": p.signup_url,
        "env_vars": tuple(p.env_vars),
        "fallback_models": tuple(p.fallback_models),
    }


def probe_provider_health(name: str, *, timeout: float = 8.0) -> dict:
    """Probe a single provider's reachability + auth.

    Returns the ``ProviderProfile.check_health`` dict, augmented with the
    provider's display name and a ``configured`` flag (whether a credential is
    present). Never raises.
    """
    from providers import get_provider_profile

    p = get_provider_profile(name)
    if p is None:
        return {
            "provider": name,
            "online": False,
            "latency_ms": None,
            "http_status": None,
            "authenticated": False,
            "configured": False,
            "error": "unknown_provider",
            "checked_at": time.time(),
        }

    creds = _resolve_credentials(name) if p.auth_type in _NON_KEY_AUTH_TYPES else {}
    if p.auth_type not in _NON_KEY_AUTH_TYPES:
        creds = _resolve_credentials(name)

    configured = bool(creds.get("api_key")) or p.auth_type in _NON_KEY_AUTH_TYPES
    health = p.check_health(
        api_key=creds.get("api_key") or None,
        base_url=creds.get("base_url") or None,
        timeout=timeout,
    )
    health.setdefault("provider", name)
    health["configured"] = configured
    health["auth_type"] = p.auth_type
    health["display_name"] = p.display_name or p.name
    return health


def list_configured_providers() -> list[dict]:
    """Return every registered provider with a ``configured`` flag.

    A provider counts as configured when it has a resolvable credential:
    an api-key env var, an entry in the credential pool, or a non-api-key
    auth flow (OAuth / SDK / subprocess).
    """
    from providers import list_providers

    providers: list[dict] = []
    for p in list_providers():
        configured = False
        if p.auth_type in _NON_KEY_AUTH_TYPES:
            configured = True
        else:
            try:
                from aetheros_cli.auth import (
                    get_api_key_provider_status as _status,
                )

                st = _status(p.name)
                if isinstance(st, dict):
                    configured = bool(
                        st.get("configured")
                        or st.get("has_key")
                        or st.get("has_credentials")
                    )
                else:
                    configured = bool(st)
            except Exception:
                # Fallback: any of the profile's api-key env vars present.
                import os

                configured = any(
                    (os.getenv(v) or "").strip() and not v.endswith(("_BASE_URL", "_URL"))
                    for v in p.env_vars
                )
        providers.append(
            {
                "name": p.name,
                "display_name": p.display_name or p.name,
                "logo": p.logo,
                "category": p.category,
                "configured": configured,
            }
        )
    return providers


def probe_configured_providers(*, timeout: float = 8.0, only_configured: bool = False) -> list[dict]:
    """Probe all providers, returning health dicts.

    ``only_configured=True`` restricts to providers with a resolvable
    credential (used by ``aetheros providers health`` without args).
    """
    results: list[dict] = []
    for row in list_configured_providers():
        if only_configured and not row["configured"]:
            continue
        try:
            results.append(probe_provider_health(row["name"], timeout=timeout))
        except Exception as exc:  # defensive — never let one provider break the report
            logger.debug("health probe failed for %s: %s", row["name"], exc)
            results.append(
                {
                    "provider": row["name"],
                    "online": False,
                    "latency_ms": None,
                    "http_status": None,
                    "authenticated": False,
                    "configured": row["configured"],
                    "error": str(exc)[:300],
                    "checked_at": time.time(),
                }
            )
    return results


def format_health_row(health: dict) -> str:
    """Render a single health dict as a one-line status string."""
    status = "●" if health.get("online") else "○"
    name = health.get("display_name") or health.get("provider")
    latency = health.get("latency_ms")
    latency_s = f"{latency}ms" if isinstance(latency, int) else "—"
    configured = "key" if health.get("configured") else "no-key"
    error = health.get("error")
    err_s = f" ({error})" if error and error not in {"no_listable_catalog", "health_check_disabled", "no_base_url"} else ""
    return f"{status} {name:<24} {latency_s:<8} {configured:<7}{err_s}"
