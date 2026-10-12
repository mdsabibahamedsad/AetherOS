"""AetherOS portal upstream adapter.

Reads the user's AetherOS OAuth state from ``~/.aetheros/auth.json`` through
the shared runtime resolver, validates or refreshes the inference JWT, then
exposes the upstream base URL plus bearer for the proxy server to forward to.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, FrozenSet, Optional

from aetheros_cli.auth import (
    AuthError,
    DEFAULT_AETHEROS_INFERENCE_URL,
    _load_auth_store,
    _auth_store_lock,
    _is_terminal_nous_refresh_error,
    _quarantine_nous_oauth_state,
    _quarantine_nous_pool_entries,
    _save_auth_store,
    _validate_nous_inference_url_from_network,
    _write_shared_nous_state,
    resolve_aetheros_runtime_credentials,
)
from aetheros_cli.proxy.adapters.base import UpstreamAdapter, UpstreamCredential

logger = logging.getLogger(__name__)

# Endpoints inference-api.aetheros.com actually serves. Anything else
# the proxy will reject with 404 â€” keeps stray clients from leaking weird
# requests to the upstream.
_ALLOWED_PATHS: FrozenSet[str] = frozenset(
    {
        "/chat/completions",
        "/completions",
        "/embeddings",
        "/models",
    }
)


class AetherOSPortalAdapter(UpstreamAdapter):
    """Proxy upstream for the AetherOS portal inference API."""

    def __init__(self) -> None:
        # Serialize proxy requests in this process; cross-process token refresh
        # and persistence are handled by resolve_nous_runtime_credentials().
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return "nous"

    @property
    def display_name(self) -> str:
        return "AetherOS"

    @property
    def allowed_paths(self) -> FrozenSet[str]:
        return _ALLOWED_PATHS

    def is_authenticated(self) -> bool:
        state = self._read_state()
        if state is None:
            return False
        # We need either a usable inference JWT OR (refresh_token + access_token)
        # to recover. The refresh helper validates and refreshes as needed.
        return bool(
            state.get("agent_key")
            or (state.get("refresh_token") and state.get("access_token"))
        )

    def get_credential(self) -> UpstreamCredential:
        return self._get_credential()

    def get_retry_credential(
        self,
        *,
        failed_credential: UpstreamCredential,
        status_code: int,
    ) -> Optional[UpstreamCredential]:
        _ = failed_credential
        if status_code != 401:
            return None
        logger.info("proxy: AetherOS upstream rejected bearer; force-refreshing invoke JWT")
        return self._get_credential(
            force_refresh=True,
        )

    def _get_credential(
        self,
        *,
        force_refresh: bool = False,
    ) -> UpstreamCredential:
        with self._lock:
            state = self._read_state()
            if state is None:
                raise RuntimeError(
                    "Not logged into AetherOS. Run `aetheros auth add aetheros` first."
                )

            try:
                refreshed = resolve_aetheros_runtime_credentials(
                    force_refresh=force_refresh,
                )
            except AuthError as exc:
                if _is_terminal_nous_refresh_error(exc):
                    _quarantine_nous_oauth_state(
                        state,
                        exc,
                        reason="proxy_refresh_failure",
                    )
                    self._save_state(
                        state,
                        quarantine_error=exc,
                        quarantine_reason="proxy_refresh_failure",
                    )
                raise RuntimeError(
                    f"Failed to refresh AetherOS credentials: {exc}"
                ) from exc
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to refresh AetherOS credentials: {exc}"
                ) from exc

            runtime_key = refreshed.get("api_key")
            if not runtime_key:
                raise RuntimeError(
                    "AetherOS login refresh did not return a usable inference JWT. "
                    "Try `aetheros auth add aetheros` to re-authenticate."
                )

            base_url = (
                _validate_nous_inference_url_from_network(refreshed.get("base_url"))
                or DEFAULT_AETHEROS_INFERENCE_URL
            )
            base_url = base_url.rstrip("/")

            return UpstreamCredential(
                bearer=runtime_key,
                base_url=base_url,
                expires_at=refreshed.get("expires_at"),
            )

    # ------------------------------------------------------------------
    # Internal helpers â€” auth.json access. Kept local rather than added
    # to aetheros_cli.auth to avoid expanding that module's public surface.
    # ------------------------------------------------------------------

    def _read_state(self) -> Optional[Dict[str, Any]]:
        try:
            with _auth_store_lock():
                store = _load_auth_store()
        except Exception as exc:
            logger.warning("proxy: failed to load auth store: %s", exc)
            return None
        providers = store.get("providers") or {}
        # Read the canonical key first, then the legacy "nous" key.
        state = providers.get("aetheros") or providers.get("nous")
        if not isinstance(state, dict):
            return None
        return dict(state)  # copy so the refresh helper can mutate freely

    def _save_state(
        self,
        state: Dict[str, Any],
        *,
        quarantine_error: Optional[AuthError] = None,
        quarantine_reason: Optional[str] = None,
    ) -> None:
        try:
            with _auth_store_lock():
                store = _load_auth_store()
                if quarantine_error is not None and quarantine_reason:
                    _quarantine_nous_pool_entries(
                        store,
                        quarantine_error,
                        reason=quarantine_reason,
                    )
                providers = store.setdefault("providers", {})
                providers["aetheros"] = state
                _save_auth_store(store)
            _write_shared_nous_state(state)
        except Exception as exc:
            logger.warning("proxy: failed to persist AetherOS quarantine state: %s", exc)


# Backward-compat alias for the legacy class name.
NousPortalAdapter = AetherOSPortalAdapter

__all__ = ["AetherOSPortalAdapter", "NousPortalAdapter"]
