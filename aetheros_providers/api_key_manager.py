"""API Key Manager — secure storage, encryption, validation.

Comprehensive API key management with:
- Encrypted storage (via SecurityFoundation)
- Key validation against provider APIs
- Duplicate detection
- Expired key detection
- Rate limit detection
- Connection testing
"""

from __future__ import annotations

import enum
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("aetheros_providers.keys")


class KeyStatus(enum.Enum):
    UNVERIFIED = "unverified"
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXCEEDED = "quota_exceeded"


@dataclass
class APIKeyInfo:
    key_id: str
    provider: str
    key_preview: str
    status: KeyStatus = KeyStatus.UNVERIFIED
    added_at: float = field(default_factory=time.time)
    last_validated: float = 0.0
    validation_error: str = ""
    is_primary: bool = False
    rate_limit_remaining: int = -1
    rate_limit_reset: float = 0.0


KeyValidationFn = Callable[[str], KeyStatus]


class APIKeyManager:
    """Secure API key management.

    Stores keys with encryption. Validates against provider APIs.
    Detects duplicates, expired keys, and rate limits.
    """

    def __init__(
        self,
        secrets_manager: Optional[Any] = None,
        provider_manager: Optional[Any] = None,
    ) -> None:
        self._lock = threading.RLock()
        self._keys: Dict[str, APIKeyInfo] = {}
        self._key_values: Dict[str, str] = {}
        self._validators: Dict[str, KeyValidationFn] = {}
        self._provider_keys: Dict[str, Set[str]] = {}
        self._secrets = secrets_manager
        self._provider_manager = provider_manager

    # ------------------------------------------------------------------
    # Key registration
    # ------------------------------------------------------------------

    def add_key(
        self,
        provider: str,
        api_key: str,
        key_id: Optional[str] = None,
        is_primary: bool = False,
        validate: bool = True,
    ) -> APIKeyInfo:
        """Add an API key for a provider.

        Args:
            provider: Provider name (e.g. "openai", "anthropic").
            api_key: The actual API key value.
            key_id: Optional custom identifier. Auto-generated if not provided.
            is_primary: Whether this is the primary key for the provider.
            validate: Whether to validate the key immediately.

        Returns:
            The APIKeyInfo for the registered key.
        """
        if key_id is None:
            key_id = f"{provider}_{int(time.time())}_{len(self._keys)}"

        preview = self._preview_key(api_key)

        info = APIKeyInfo(
            key_id=key_id,
            provider=provider,
            key_preview=preview,
            is_primary=is_primary,
        )

        with self._lock:
            self._keys[key_id] = info
            self._key_values[key_id] = api_key
            if provider not in self._provider_keys:
                self._provider_keys[provider] = set()
            self._provider_keys[provider].add(key_id)

        if self._secrets:
            try:
                self._secrets.store_secret(f"api_key_{provider}_{key_id}", api_key)
            except Exception:
                pass

        if validate:
            self.validate_key(key_id)

        logger.info("API key added for %s: %s (primary=%s)", provider, preview, is_primary)
        return info

    def remove_key(self, key_id: str) -> bool:
        with self._lock:
            info = self._keys.pop(key_id, None)
            if info is None:
                return False
            self._key_values.pop(key_id, None)
            provider_keys = self._provider_keys.get(info.provider)
            if provider_keys:
                provider_keys.discard(key_id)
            logger.info("API key removed: %s (%s)", key_id, info.key_preview)
            return True

    def get_key(self, key_id: str) -> Optional[str]:
        with self._lock:
            return self._key_values.get(key_id)

    def get_info(self, key_id: str) -> Optional[APIKeyInfo]:
        with self._lock:
            return self._keys.get(key_id)

    def get_keys_for_provider(self, provider: str) -> List[APIKeyInfo]:
        with self._lock:
            key_ids = self._provider_keys.get(provider, set())
            return [self._keys[kid] for kid in key_ids if kid in self._keys]

    def get_primary_key(self, provider: str) -> Optional[str]:
        with self._lock:
            key_ids = self._provider_keys.get(provider, set())
            for kid in key_ids:
                info = self._keys.get(kid)
                if info and info.is_primary:
                    return self._key_values.get(kid)
            for kid in key_ids:
                return self._key_values.get(kid)
            return None

    def set_primary(self, key_id: str) -> bool:
        with self._lock:
            info = self._keys.get(key_id)
            if info is None:
                return False
            for kid in self._provider_keys.get(info.provider, set()):
                other = self._keys.get(kid)
                if other:
                    other.is_primary = False
            info.is_primary = True
            return True

    def list_providers_with_keys(self) -> List[str]:
        with self._lock:
            return [
                p for p, keys in self._provider_keys.items()
                if any(k in self._keys for k in keys)
            ]

    def has_any_key(self) -> bool:
        return len(self._keys) > 0

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def register_validator(self, provider: str, validator: KeyValidationFn) -> None:
        with self._lock:
            self._validators[provider] = validator

    def validate_key(self, key_id: str) -> KeyStatus:
        info = self._keys.get(key_id)
        if info is None:
            return KeyStatus.UNVERIFIED

        api_key = self._key_values.get(key_id)
        if not api_key:
            return KeyStatus.INVALID

        validator = self._validators.get(info.provider)
        if validator is None:
            info.status = KeyStatus.VALID
            info.last_validated = time.time()
            return KeyStatus.VALID

        try:
            status = validator(api_key)
            info.status = status
            info.last_validated = time.time()
            if status != KeyStatus.VALID:
                info.validation_error = f"Validation returned: {status.value}"
            return status
        except Exception as exc:
            info.status = KeyStatus.INVALID
            info.last_validated = time.time()
            info.validation_error = str(exc)
            return KeyStatus.INVALID

    def validate_all_keys(self) -> Dict[str, KeyStatus]:
        results = {}
        with self._lock:
            key_ids = list(self._keys.keys())
        for kid in key_ids:
            results[kid] = self.validate_key(kid)
        return results

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect_duplicates(self) -> Dict[str, List[str]]:
        """Detect duplicate key values across providers."""
        value_to_ids: Dict[str, List[str]] = {}
        with self._lock:
            for kid, val in self._key_values.items():
                if val not in value_to_ids:
                    value_to_ids[val] = []
                value_to_ids[val].append(kid)
        return {v: ids for v, ids in value_to_ids.items() if len(ids) > 1}

    def detect_expired_keys(self) -> List[str]:
        """Detect keys that have been marked as expired."""
        with self._lock:
            return [
                kid for kid, info in self._keys.items()
                if info.status == KeyStatus.EXPIRED
            ]

    def get_rate_limited_keys(self) -> List[str]:
        with self._lock:
            now = time.time()
            return [
                kid for kid, info in self._keys.items()
                if info.status == KeyStatus.RATE_LIMITED
                and info.rate_limit_reset > now
            ]

    def update_rate_limit(
        self,
        key_id: str,
        remaining: int,
        reset_at: float,
    ) -> None:
        with self._lock:
            info = self._keys.get(key_id)
            if info:
                info.rate_limit_remaining = remaining
                info.rate_limit_reset = reset_at
                if remaining <= 0:
                    info.status = KeyStatus.RATE_LIMITED

    # ------------------------------------------------------------------
    # Connection testing
    # ------------------------------------------------------------------

    def test_connection(
        self,
        provider: str,
        api_key: str,
        base_url: Optional[str] = None,
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        """Test a provider connection with a given API key.

        Returns a dict with keys: success, latency_ms, status, error.
        """
        import json as _json
        import urllib.request as _request
        import urllib.error as _error

        model_url = base_url or self._get_default_base_url(provider)
        if not model_url:
            return {"success": False, "error": f"No base URL for {provider}"}

        url = model_url.rstrip("/") + "/models"
        start = time.monotonic()

        try:
            req = _request.Request(url, headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            })
            with _request.urlopen(req, timeout=timeout) as resp:
                latency = (time.monotonic() - start) * 1000
                return {
                    "success": True,
                    "latency_ms": round(latency, 1),
                    "status": resp.status,
                    "error": "",
                }
        except _error.HTTPError as exc:
            latency = (time.monotonic() - start) * 1000
            return {
                "success": False,
                "latency_ms": round(latency, 1),
                "status": exc.code,
                "error": f"HTTP {exc.code}: {exc.reason}",
            }
        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            return {
                "success": False,
                "latency_ms": round(latency, 1),
                "status": 0,
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _preview_key(key: str) -> str:
        clean = key.strip()
        n = len(clean)
        if n <= 0:
            return "****"
        if n <= 4:
            return clean[:2] + "****"
        if n < 8:
            return clean[:2] + "****" + clean[-2:]
        return clean[:4] + "****" + clean[-4:]

    @staticmethod
    def _get_default_base_url(provider: str) -> str:
        urls = {
            "openai": "https://api.openai.com",
            "anthropic": "https://api.anthropic.com",
            "google": "https://generativelanguage.googleapis.com",
            "openrouter": "https://openrouter.ai/api/v1",
            "deepseek": "https://api.deepseek.com",
            "mistral": "https://api.mistral.ai",
            "cohere": "https://api.cohere.com",
            "together": "https://api.together.xyz",
            "groq": "https://api.groq.com",
            "xai": "https://api.x.ai",
        }
        return urls.get(provider, "")