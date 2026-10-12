"""Provider API-key store.

Manages provider API keys through one interface with two backends:

* ``env`` (default) — the existing behavior: keys live in ``~/.aetheros/.env``
  via ``save_env_value`` / ``get_env_value``. Nothing changes for existing
  users.
* ``keychain`` (opt-in) — keys are stored in the operating system secure
  credential store (Windows Credential Manager / macOS Keychain / Linux
  Secret Service) through ``aetheros_security.secrets.SecretsManager``. The
  runtime still reads ``.env``/process env, so saving also materializes a
  mirror into ``.env`` by default; ``--keychain-only`` keeps the value out of
  plaintext (the management surface reads from the keychain).

The backend is selected via ``security.api_key_storage`` in ``config.yaml``
(``env`` | ``keychain`` | ``auto``). ``auto`` uses the OS store when
available and falls back to ``.env`` otherwise.

Support: multiple keys per provider are handled by the credential pool
(``agent/credential_pool.py``); this module manages the *primary* key per
provider plus import/export/rotation helpers.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Namespace prefix for keychain entries so provider keys never collide with
# other Aetheros secrets.
_KEYCHAIN_PREFIX = "aetheros:provider:api_key:"


def _config_backend() -> str:
    """Resolve the configured API-key storage backend (env|keychain|auto)."""
    try:
        from aetheros_cli.config import load_config

        cfg = load_config()
        return str((cfg.get("security") or {}).get("api_key_storage") or "env").strip().lower()
    except Exception:
        return "env"


def storage_backend() -> str:
    """Return the effective backend after resolving ``auto``."""
    backend = _config_backend()
    if backend == "auto":
        return "keychain" if _keychain_available() else "env"
    return backend if backend in {"env", "keychain"} else "env"


def _keychain_available() -> bool:
    try:
        from aetheros_security.secrets import get_secrets_manager

        mgr = get_secrets_manager()
        return mgr is not None and mgr.backend is not None
    except Exception:
        return False


def _keychain_name(provider: str) -> str:
    return f"{_KEYCHAIN_PREFIX}{provider}"


def _env_var_for_provider(provider: str) -> str:
    """Return the canonical API-key env var for a provider.

    Uses the profile's first non-base-url env var when available, otherwise
    derives ``<NAME>_API_KEY`` from the provider slug.
    """
    try:
        from providers import get_provider_profile

        p = get_provider_profile(provider)
        if p is not None:
            for var in p.env_vars:
                if not var.endswith(("_BASE_URL", "_URL")):
                    return var
    except Exception:
        pass
    from aetheros_cli.auth import PROVIDER_REGISTRY

    pconfig = PROVIDER_REGISTRY.get(provider)
    if pconfig and getattr(pconfig, "api_key_env_vars", None):
        for var in pconfig.api_key_env_vars:
            if not var.endswith(("_BASE_URL", "_URL")):
                return var
    return f"{provider.replace('-', '_').upper()}_API_KEY"


def _read_env_key(env_var: str) -> str | None:
    from aetheros_cli.config import get_env_value

    val = get_env_value(env_var)
    return str(val).strip() if val else None


def get_provider_key(provider: str, *, include_env: bool = True) -> str | None:
    """Return the primary API key for *provider* (keychain first when active).

    ``include_env`` falls back to the env var when the keychain has no entry.
    """
    if storage_backend() == "keychain":
        try:
            from aetheros_security.secrets import SecretCategory, get_secrets_manager

            mgr = get_secrets_manager()
            val = mgr.retrieve(_keychain_name(provider))
            if val:
                return str(val).strip()
        except Exception as exc:
            logger.debug("keychain read failed for %s: %s", provider, exc)
        if not include_env:
            return None
    env_var = _env_var_for_provider(provider)
    return _read_env_key(env_var)


def save_provider_key(
    provider: str,
    key: str,
    *,
    keychain_only: bool = False,
) -> dict:
    """Save a provider's API key, returning a result dict.

    ``keychain_only=True`` stores only in the OS store (no plaintext mirror).
    Otherwise the key is written through the active backend and, when the
    backend is ``keychain``, a mirror is also written to ``.env`` so the
    existing runtime path (which reads ``.env``/process env) keeps working.
    """
    key = (key or "").strip()
    if not key:
        return {"success": False, "error": "empty_key", "stored_as": "", "backend": storage_backend()}

    backend = storage_backend()
    env_var = _env_var_for_provider(provider)
    results: dict[str, Any] = {"provider": provider, "env_var": env_var, "backend": backend}

    if backend == "keychain":
        from aetheros_security.secrets import SecretCategory, get_secrets_manager

        try:
            mgr = get_secrets_manager()
            ok = mgr.store(
                _keychain_name(provider),
                key,
                category=SecretCategory.API_KEY,
                description=f"Aetheros provider API key: {provider}",
                metadata={"provider": provider, "kind": "provider-api-key"},
            )
            results["keychain"] = ok
        except Exception as exc:
            results["keychain"] = False
            results["keychain_error"] = str(exc)[:300]
        if keychain_only:
            results["success"] = bool(results.get("keychain"))
            results["stored_as"] = _keychain_name(provider)
            results["mirrored_to_env"] = False
            return results
        # Mirror into .env so the runtime (which reads env) keeps working.
        try:
            from aetheros_cli.config import save_env_value

            save_env_value(env_var, key)
            results["mirrored_to_env"] = True
        except Exception as exc:
            results["mirrored_to_env"] = False
            results["env_error"] = str(exc)[:300]
        results["success"] = bool(results.get("keychain") or results.get("mirrored_to_env"))
        results["stored_as"] = f"{_keychain_name(provider)} (+ {env_var})"
        return results

    # env backend (default) — current behavior.
    from aetheros_cli.config import save_env_value

    try:
        save_env_value(env_var, key)
        results["success"] = True
        results["stored_as"] = env_var
    except Exception as exc:
        results["success"] = False
        results["error"] = str(exc)[:300]
        results["stored_as"] = ""
    return results


def remove_provider_key(provider: str) -> bool:
    """Remove a provider's API key from every active store."""
    removed = False
    if storage_backend() == "keychain":
        try:
            from aetheros_security.secrets import get_secrets_manager

            mgr = get_secrets_manager()
            removed = mgr.delete(_keychain_name(provider)) or removed
        except Exception:
            pass
    env_var = _env_var_for_provider(provider)
    try:
        from aetheros_cli.config import remove_env_value

        removed = remove_env_value(env_var) or removed
    except Exception:
        pass
    return removed


def rotate_provider_key(provider: str, new_key: str) -> dict:
    """Rotate a provider's API key (store new value, keep entry alive)."""
    return save_provider_key(provider, new_key)


def list_provider_keys() -> list[dict]:
    """List providers with a stored key and its backend. Never leaks values."""
    backend = storage_backend()
    rows: list[dict] = []
    try:
        from providers import list_providers

        names = sorted({p.name for p in list_providers()})
    except Exception:
        names = []
    for name in names:
        has_env = bool(_read_env_key(_env_var_for_provider(name)))
        has_keychain = False
        if backend == "keychain":
            try:
                from aetheros_security.secrets import get_secrets_manager

                mgr = get_secrets_manager()
                has_keychain = mgr.exists(_keychain_name(name))
            except Exception:
                has_keychain = False
        if has_env or has_keychain:
            rows.append(
                {
                    "provider": name,
                    "in_env": has_env,
                    "in_keychain": has_keychain,
                }
            )
    return rows


def export_keys() -> dict:
    """Export all stored provider keys as ``{provider: key}`` (values included).

    Use with care — the caller is responsible for redaction/encryption of the
    exported artifact.
    """
    out: dict[str, str] = {}
    try:
        from providers import list_providers

        names = sorted({p.name for p in list_providers()})
    except Exception:
        return out
    for name in names:
        key = get_provider_key(name)
        if key:
            out[name] = key
    return out


def import_keys(mapping: dict, *, keychain_only: bool = False) -> dict:
    """Import ``{provider: key}`` mapping, returning per-provider results."""
    results: dict[str, dict] = {}
    if not isinstance(mapping, dict):
        return {"_error": "expected a dict of {provider: key}"}
    for provider, key in mapping.items():
        if not isinstance(key, str) or not key.strip():
            results[str(provider)] = {"success": False, "error": "empty_key"}
            continue
        results[str(provider)] = save_provider_key(str(provider), key, keychain_only=keychain_only)
    return results


def load_keys_from_file(path: str) -> dict:
    """Load a provider→key JSON file written by ``export_keys``."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_keys_to_file(path: str, mapping: dict) -> None:
    """Serialize ``{provider: key}`` to a JSON file."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(mapping, fh, indent=2, sort_keys=True)


def key_status_line(provider: str) -> str:
    """One-line status: configured / missing / masked tail."""
    key = get_provider_key(provider)
    if not key:
        return "(not configured)"
    if len(key) > 8:
        return f"••••{key[-4:]} ({storage_backend()})"
    return "(configured)"
