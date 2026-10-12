"""``aetheros providers`` / ``aetheros models`` / ``aetheros usage`` commands.

Additive CLI surface for provider + model management. All data comes from the
existing provider registry, model catalogs, state database, and config — this
module only orchestrates them for display.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Optional

ROUTING_MODES = ("manual", "fastest", "cheapest", "quality", "offline", "enterprise")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _jprint(obj: Any) -> None:
    print(json.dumps(obj, indent=2, default=str))


def _mask(key: str) -> str:
    if not key:
        return "(not set)"
    if len(key) <= 8:
        return key[:2] + "…" * 4
    return key[:4] + "…" + key[-4:]


def _require_value(flag: str) -> str:
    """Read a secret from stdin (non-interactive-safe getpass)."""
    import getpass

    try:
        return getpass.getpass(f"{flag}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise SystemExit(1) from None


# ---------------------------------------------------------------------------
# providers command
# ---------------------------------------------------------------------------

def cmd_providers_list(args) -> None:  # noqa: ARG001
    """List every known provider with capability metadata."""
    from providers import list_providers

    from aetheros_cli.provider_health import provider_capabilities

    json_out = getattr(args, "json", False)
    providers = sorted(list_providers(), key=lambda p: (p.category, p.name))
    rows = []
    for p in providers:
        rows.append(provider_capabilities(p.name))

    if json_out:
        _jprint({"providers": rows})
        return

    print()
    print(f"  {len(rows)} providers:")
    print()
    for r in rows:
        flags = []
        if r.get("supports_vision"):
            flags.append("vision")
        if r.get("supports_streaming"):
            flags.append("streaming")
        if r.get("supports_health_check"):
            flags.append("health-check")
        flag_str = (", ".join(flags)) if flags else ""
        auth = r.get("auth_type") or "?"
        print(f"  {r['name']:<24} {r['category']:<10} auth={auth:<12} {flag_str}")
    print()


def cmd_providers_health(args) -> None:  # noqa: ARG001
    """Probe health of configured providers."""
    from aetheros_cli.provider_health import probe_configured_providers

    only_configured = getattr(args, "only_configured", True)
    include_all = not only_configured or getattr(args, "all", False)
    results = probe_configured_providers(only_configured=not include_all)

    if getattr(args, "json", False):
        _jprint({"providers": results})
        return

    print()
    if not results:
        print("  No providers configured. Set an API key with `aetheros providers key set`")
        print("  or `aetheros setup` first.")
        print()
        return
    print(f"  {len(results)} provider(s):")
    print()
    for r in results:
        status = "UP" if r.get("online") else "DOWN"
        latency = f"{r.get('latency_ms'):.0f}ms" if r.get("latency_ms") is not None else "-"
        authed = "auth-ok" if r.get("authenticated") else ("no-key" if r.get("error") == "no_api_key" else "-")
        err = r.get("error") or ""
        err_suffix = f"  ({err})" if err and err != "no_api_key" else ""
        print(f"  {r['provider']:<22} {status:<4} {latency:<7} {authed:<8}{err_suffix}")
    print()


def cmd_providers_models(args) -> None:
    """List models for a provider."""
    from aetheros_cli.models import provider_model_ids

    provider = (getattr(args, "provider", "") or "").strip()
    if not provider:
        print("Usage: aetheros providers models <provider>")
        raise SystemExit(2)
    try:
        ids = provider_model_ids(provider)
    except Exception as exc:
        print(f"Error resolving models for '{provider}': {exc}")
        raise SystemExit(1) from exc
    if getattr(args, "json", False):
        _jprint({"provider": provider, "models": ids})
        return
    print()
    if not ids:
        print(f"  No models known for '{provider}'.")
    else:
        print(f"  {len(ids)} models for '{provider}':")
        for mid in ids:
            print(f"    {mid}")
    print()


def cmd_providers_capabilities(args) -> None:
    """Show a single provider's capability metadata."""
    from providers import get_provider_profile

    from aetheros_cli.provider_health import provider_capabilities

    provider = (getattr(args, "provider", "") or "").strip()
    if not provider:
        print("Usage: aetheros providers capabilities <provider>")
        raise SystemExit(2)
    p = get_provider_profile(provider)
    if p is None:
        print(f"Unknown provider: {provider}")
        raise SystemExit(1)
    r = provider_capabilities(p.name)
    if getattr(args, "json", False):
        _jprint(r)
        return
    print()
    for k, v in r.items():
        if isinstance(v, (list, tuple)):
            v = ", ".join(str(x) for x in v)
        print(f"  {k:<20} {v}")
    print()


def cmd_providers_key_set(args) -> None:
    """Store an API key (env or OS keychain per security.api_key_storage)."""
    from aetheros_cli.api_key_store import save_provider_key

    provider = (getattr(args, "provider", "") or "").strip()
    if not provider:
        print("Usage: aetheros providers key set <provider> [--value KEY]")
        raise SystemExit(2)
    value = getattr(args, "value", None)
    if value is None:
        value = _require_value(f"API key for {provider}")
    if not value:
        print("No key provided — aborting.")
        raise SystemExit(1)
    ok = save_provider_key(provider, value, keychain_only=getattr(args, "keychain_only", False))
    if not ok:
        print(f"Failed to store key for '{provider}'.")
        raise SystemExit(1)
    storage = "OS keychain" if getattr(args, "keychain_only", False) else "key store"
    print(f"Stored API key for '{provider}' in {storage}.")


def cmd_providers_key_show(args) -> None:
    """Show (masked) whether a key exists and where it lives."""
    from aetheros_cli.api_key_store import get_provider_key, key_status_line

    provider = (getattr(args, "provider", "") or "").strip()
    if not provider:
        print("Usage: aetheros providers key show <provider>")
        raise SystemExit(2)
    key = get_provider_key(provider)
    if not key:
        print(f"  {provider:<22} (not configured)")
        return
    print(f"  {provider:<22} {key_status_line(provider)}")


def cmd_providers_key_remove(args) -> None:
    """Remove a stored key."""
    from aetheros_cli.api_key_store import remove_provider_key

    provider = (getattr(args, "provider", "") or "").strip()
    if not provider:
        print("Usage: aetheros providers key remove <provider>")
        raise SystemExit(2)
    removed = remove_provider_key(provider)
    print(f"Removed key for '{provider}' ({removed}).")


def cmd_providers_key_rotate(args) -> None:
    """Replace an existing key with a new value."""
    from aetheros_cli.api_key_store import rotate_provider_key

    provider = (getattr(args, "provider", "") or "").strip()
    if not provider:
        print("Usage: aetheros providers key rotate <provider> [--value KEY]")
        raise SystemExit(2)
    value = getattr(args, "value", None)
    if value is None:
        value = _require_value(f"New API key for {provider}")
    if not value:
        print("No key provided — aborting.")
        raise SystemExit(1)
    result = rotate_provider_key(provider, value)
    if not result.get("success"):
        print(f"Failed to rotate key for '{provider}': {result.get('error', 'unknown error')}")
        raise SystemExit(1)
    print(f"Rotated key for '{provider}'.")


def cmd_providers_key_list(args) -> None:
    """List which providers have keys (values masked)."""
    from aetheros_cli.api_key_store import list_provider_keys

    json_out = getattr(args, "json", False)
    entries = list_provider_keys()
    if json_out:
        _jprint({"keys": entries})
        return
    print()
    if not entries:
        print("  No provider API keys stored.")
        print()
        return
    for e in entries:
        if e.get("in_env") and e.get("in_keychain"):
            status = "env + keychain"
        elif e.get("in_keychain"):
            status = "keychain"
        else:
            status = "env"
        print(f"  {e['provider']:<22} {status}")
    print()


def cmd_providers_key_backend(args) -> None:  # noqa: ARG001
    """Show the active key-storage backend."""
    from aetheros_cli.api_key_store import storage_backend

    backend = storage_backend()
    print(f"Active key-storage backend: {backend}")
    if backend == "env":
        print("  Keys are stored in the .env file (default, unchanged).")
        print("  Switch to the OS keychain with: aetheros config security.api_key_storage keychain")


def _dispatch_providers_key(args) -> None:
    sub = getattr(args, "providers_key_command", None)
    handlers = {
        "set": cmd_providers_key_set,
        "show": cmd_providers_key_show,
        "remove": cmd_providers_key_remove,
        "rotate": cmd_providers_key_rotate,
        "list": cmd_providers_key_list,
        "backend": cmd_providers_key_backend,
    }
    handler = handlers.get(sub)
    if handler is None:
        print("Usage: aetheros providers key {set|show|remove|rotate|list|backend}")
        raise SystemExit(2)
    handler(args)


def cmd_providers(args) -> None:
    """Top-level dispatcher for ``aetheros providers [subcommand]``."""
    sub = getattr(args, "providers_command", None)
    handlers = {
        "list": cmd_providers_list,
        "health": cmd_providers_health,
        "models": cmd_providers_models,
        "capabilities": cmd_providers_capabilities,
        "key": _dispatch_providers_key,
    }
    handler = handlers.get(sub) or cmd_providers_list
    handler(args)


def build_providers_parser(subparsers) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "providers",
        help="List providers, check health, and manage provider API keys",
    )
    sub = parser.add_subparsers(dest="providers_command")

    p_list = sub.add_parser("list", help="List all known providers with capabilities")
    p_list.add_argument("--json", action="store_true", help="Emit JSON")
    p_list.set_defaults(func=cmd_providers_list)

    p_health = sub.add_parser("health", help="Probe health of configured providers")
    p_health.add_argument("--all", action="store_true", help="Probe all known providers, not just configured ones")
    p_health.add_argument("--json", action="store_true", help="Emit JSON")
    p_health.set_defaults(func=cmd_providers_health)

    p_models = sub.add_parser("models", help="List models for a provider")
    p_models.add_argument("provider", help="Provider name (e.g. groq, mistral)")
    p_models.add_argument("--json", action="store_true", help="Emit JSON")
    p_models.set_defaults(func=cmd_providers_models)

    p_caps = sub.add_parser("capabilities", help="Show a provider's capabilities")
    p_caps.add_argument("provider", help="Provider name")
    p_caps.add_argument("--json", action="store_true", help="Emit JSON")
    p_caps.set_defaults(func=cmd_providers_capabilities)

    p_key = sub.add_parser("key", help="Manage provider API keys")
    key_sub = p_key.add_subparsers(dest="providers_key_command")

    def _key_provider(parser):
        parser.add_argument("provider", help="Provider name")
        parser.add_argument("--value", default=None, help="Key value (omit to be prompted securely)")
        parser.add_argument("--keychain-only", action="store_true", help="Do not mirror the key into .env")

    k_set = key_sub.add_parser("set", help="Store an API key")
    _key_provider(k_set)
    k_set.set_defaults(func=cmd_providers_key_set)

    k_show = key_sub.add_parser("show", help="Show key status (masked)")
    _key_provider(k_show)
    k_show.set_defaults(func=cmd_providers_key_show)

    k_rm = key_sub.add_parser("remove", help="Remove a stored key")
    _key_provider(k_rm)
    k_rm.set_defaults(func=cmd_providers_key_remove)

    k_rot = key_sub.add_parser("rotate", help="Replace an existing key")
    _key_provider(k_rot)
    k_rot.set_defaults(func=cmd_providers_key_rotate)

    k_list = key_sub.add_parser("list", help="List providers with keys (masked)")
    k_list.add_argument("--json", action="store_true", help="Emit JSON")
    k_list.set_defaults(func=cmd_providers_key_list)

    k_backend = key_sub.add_parser("backend", help="Show active key-storage backend")
    k_backend.set_defaults(func=cmd_providers_key_backend)

    parser.set_defaults(func=cmd_providers)
    return parser


# ---------------------------------------------------------------------------
# models command
# ---------------------------------------------------------------------------

def cmd_models_search(args) -> None:
    """Search the known model universe."""
    from aetheros_cli.model_registry import search_models

    query = (getattr(args, "query", "") or "").strip()
    providers = getattr(args, "providers", None)
    flag = getattr(args, "flag", None)
    include_hidden = bool(getattr(args, "include_hidden", False))
    limit = int(getattr(args, "limit", 50) or 50)

    rows = search_models(
        query,
        providers=providers,
        flag=flag,
        include_hidden=include_hidden,
        max_results=limit,
    )

    if getattr(args, "json", False):
        _jprint({"results": rows})
        return

    print()
    if not rows:
        print("  No models matched.")
        print()
        return
    print(f"  {len(rows)} result(s):")
    for r in rows:
        marks = ""
        if r["pinned"]:
            marks += " 📌"
        if r["favorite"]:
            marks += " ⭐"
        if r["deprecated"]:
            marks += " (deprecated)"
        print(f"    {r['provider']:<22} {r['model']}{marks}")
    print()


def _flag_arg(args) -> Optional[str]:
    for f in ("favorite", "pinned", "hidden", "deprecated"):
        if getattr(args, f"flag_{f}", False):
            return f
    return None


def cmd_models_flag(args) -> None:
    """Set/clear a flag on a model (favorite, pinned, hidden, deprecated)."""
    from aetheros_cli.model_registry import get_registry

    model_id = (getattr(args, "model", "") or "").strip()
    if not model_id:
        print("Usage: aetheros models flag <model> --favorite|--pinned|--hidden|--deprecated [--clear]")
        raise SystemExit(2)
    flag = _flag_arg(args)
    if flag is None:
        print("Specify one of --favorite, --pinned, --hidden, --deprecated.")
        raise SystemExit(2)
    clear = bool(getattr(args, "clear", False))
    reg = get_registry()
    value = reg.set_flag(model_id, flag, not clear)
    print(f"{'Cleared' if clear else 'Set'} flag '{flag}' on '{model_id}' (now {'on' if value else 'off'}).")


def cmd_models_show_flags(args) -> None:
    """Show all flagged models."""
    from aetheros_cli.model_registry import get_registry

    reg = get_registry()
    json_out = getattr(args, "json", False)
    data = {
        "favorites": reg.favorites,
        "pinned": reg.pinned,
        "hidden": reg.hidden,
        "deprecated": reg.deprecated,
    }
    if json_out:
        _jprint(data)
        return
    print()
    for flag in ("pinned", "favorites", "hidden", "deprecated"):
        ids = data[flag]
        print(f"  {flag.capitalize()}: {', '.join(ids) if ids else '(none)'}")
    print()


def cmd_models_route(args) -> None:
    """Resolve a routing policy."""
    from aetheros_cli.model_router import persist_route, resolve_route

    mode = (getattr(args, "mode", None) or "manual").lower()
    if mode not in ROUTING_MODES:
        print(f"Unknown routing mode: {mode}. Choose from: {', '.join(ROUTING_MODES)}")
        raise SystemExit(2)
    route = resolve_route(mode)
    if getattr(args, "json", False):
        _jprint(route)
        return
    print()
    print(f"  Route ({route['mode']}):")
    print(f"    provider : {route['provider'] or '(unset)'}")
    print(f"    model    : {route['model'] or '(unset)'}")
    print(f"    rationale: {route['rationale']}")
    if route.get("configured"):
        print("    (matches current config)")
    print()
    if getattr(args, "persist", False):
        ok = persist_route(route)
        if ok:
            print("  Persisted to config.yaml (model.provider / model.default).")
        else:
            print("  Persist skipped (nothing to change).")


def cmd_models_list_flags(args) -> None:
    """Alias of ``models flags``."""
    cmd_models_show_flags(args)


def cmd_models(args) -> None:
    """Top-level dispatcher for ``aetheros models [subcommand]``."""
    sub = getattr(args, "models_command", None)
    handlers = {
        "search": cmd_models_search,
        "flag": cmd_models_flag,
        "flags": cmd_models_show_flags,
        "list": cmd_models_show_flags,
        "route": cmd_models_route,
    }
    handler = handlers.get(sub)
    if handler is None:
        print("Usage: aetheros models {search|flag|flags|list|route}")
        raise SystemExit(2)
    handler(args)


def build_models_parser(subparsers) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "models",
        help="Search models and manage per-model flags (favorite, pinned, hidden, deprecated)",
    )
    sub = parser.add_subparsers(dest="models_command")

    p_search = sub.add_parser("search", help="Search the known model universe")
    p_search.add_argument("query", nargs="?", default="", help="Substring to match against model/provider names")
    p_search.add_argument("--providers", nargs="*", default=None, help="Limit to these providers")
    p_search.add_argument("--flag", default=None, help="Only show models with this flag (favorite/pinned/hidden/deprecated)")
    p_search.add_argument("--include-hidden", action="store_true", help="Include hidden models")
    p_search.add_argument("--limit", type=int, default=50, help="Max results (default 50)")
    p_search.add_argument("--json", action="store_true", help="Emit JSON")
    p_search.set_defaults(func=cmd_models_search)

    p_flag = sub.add_parser("flag", help="Set/clear a flag on a model")
    p_flag.add_argument("model", help="Model id (optionally provider:model)")
    p_flag.add_argument("--favorite", dest="flag_favorite", action="store_true")
    p_flag.add_argument("--pinned", dest="flag_pinned", action="store_true")
    p_flag.add_argument("--hidden", dest="flag_hidden", action="store_true")
    p_flag.add_argument("--deprecated", dest="flag_deprecated", action="store_true")
    p_flag.add_argument("--clear", action="store_true", help="Clear the flag instead of setting it")
    p_flag.set_defaults(func=cmd_models_flag)

    p_flags = sub.add_parser("flags", help="List models with each flag")
    p_flags.add_argument("--json", action="store_true", help="Emit JSON")
    p_flags.set_defaults(func=cmd_models_show_flags)

    sub.add_parser("list", help="Alias of flags").set_defaults(func=cmd_models_list_flags)

    p_route = sub.add_parser("route", help="Resolve a routing policy")
    p_route.add_argument("mode", nargs="?", default="manual", help=f"One of: {', '.join(ROUTING_MODES)}")
    p_route.add_argument("--persist", action="store_true", help="Write the resolved provider/model to config.yaml")
    p_route.add_argument("--json", action="store_true", help="Emit JSON")
    p_route.set_defaults(func=cmd_models_route)

    parser.set_defaults(func=cmd_models)
    return parser


# ---------------------------------------------------------------------------
# usage command
# ---------------------------------------------------------------------------

def cmd_usage(args) -> None:
    """Render the usage dashboard."""
    from aetheros_cli.usage_cmd import json_dumps, print_usage_dashboard

    json_out = getattr(args, "json", False)
    sub = getattr(args, "usage_command", None)
    if sub is None or sub in {"summary", "dashboard"}:
        print(print_usage_dashboard(json_out=json_out))
        return

    from aetheros_cli.usage_cmd import usage_by_model, usage_by_provider, usage_recent_sessions

    if sub == "by-provider":
        rows = usage_by_provider()
    elif sub == "by-model":
        rows = usage_by_model()
    elif sub == "recent":
        rows = usage_recent_sessions()
    else:
        print("Usage: aetheros usage {summary|by-provider|by-model|recent}")
        raise SystemExit(2)

    if json_out:
        print(json_dumps(rows))
        return
    print()
    if not rows:
        print("  No data.")
        return
    for r in rows:
        print("  " + json_dumps(r))
    print()


def build_usage_parser(subparsers) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "usage",
        help="Show usage / cost dashboard from session data",
    )
    sub = parser.add_subparsers(dest="usage_command")
    for name in ("summary", "by-provider", "by-model", "recent"):
        p = sub.add_parser(name, help=f"Show usage {name.replace('-', ' ')}")
        p.set_defaults(func=cmd_usage)
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.set_defaults(func=cmd_usage)
    return parser
