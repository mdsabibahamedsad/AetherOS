"""AetherOS Integrations — security primitives.

Encrypted credential vault (Fernet), secret rotation, audit log, secret
redaction, and least-privilege permission checks. No credentials are ever
stored in plaintext; the vault key comes from the environment or a locked
key file.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import stat
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet, InvalidToken

from aetheros_integrations.config import get_aetheros_dir, load_integrations_settings
from aetheros_integrations.models import AuditEntry, CredentialEnvelope

logger = logging.getLogger(__name__)


class VaultUnavailableError(RuntimeError):
    """Raised when the vault key cannot be resolved."""


def _derive_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


class CredentialVault:
    """Fernet-encrypted credential store on disk.

    The key is resolved from (in order): ``AETHEROS_INTEGRATIONS_VAULT_KEY``
    env var, a local ``vault.key`` file created on first use (mode 0600), or
    a master secret derived from the machine. Never exposes plaintext except
    through ``decrypt()`` calls the caller explicitly makes.
    """

    def __init__(self, settings=None, dirpath: Optional[Path] = None):
        self._settings = settings or load_integrations_settings()
        self._dir = dirpath or get_aetheros_dir(self._settings.data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._key_file = self._dir / "vault.key"
        self._store_path = self._dir / "credentials.json"
        self._fernet: Optional[Fernet] = None
        self._records: Dict[str, Dict[str, Any]] = {}
        self._init_vault()

    def _init_vault(self) -> None:
        env_key = os.environ.get(self._settings.auth.vault_key_env, "")
        if env_key:
            self._fernet = Fernet(_derive_key(env_key))
        elif self._key_file.exists():
            try:
                raw = self._key_file.read_bytes().strip()
                self._fernet = Fernet(raw)
            except Exception as exc:  # noqa: BLE001
                raise VaultUnavailableError(f"Vault key file unreadable: {exc}") from exc
        else:
            key = Fernet.generate_key()
            self._key_file.write_bytes(key)
            try:
                self._key_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
            except OSError:
                pass
            self._fernet = Fernet(key)
        self._load()

    def _load(self) -> None:
        if not self._store_path.exists():
            return
        try:
            data = json.loads(self._store_path.read_text(encoding="utf-8"))
            for item in data:
                env = CredentialEnvelope(**item)
                self._records[env.id] = env
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load credential vault: %s", exc)

    def _save(self) -> None:
        payload = [e.to_dict() for e in self._records.values()]
        self._store_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # ---- public API -----------------------------------------------------

    def store(
        self,
        provider_key: str,
        secrets: Dict[str, Any],
        *,
        kind: str = "oauth2",
        scopes: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
        credential_id: Optional[str] = None,
    ) -> CredentialEnvelope:
        with self._lock:
            ciphertext = self._fernet.encrypt(json.dumps(secrets).encode("utf-8"))
            env = CredentialEnvelope(
                id=credential_id or str(uuid.uuid4()),
                provider_key=provider_key,
                kind=kind,
                ciphertext=ciphertext,
                scopes=scopes or [],
                meta=meta or {},
            )
            self._records[env.id] = env
            self._save()
            return env

    def decrypt(self, credential_id: str) -> Dict[str, Any]:
        with self._lock:
            env = self._records.get(credential_id)
            if env is None:
                raise KeyError(f"No credential {credential_id}")
            try:
                plaintext = self._fernet.decrypt(env.ciphertext)
                return json.loads(plaintext.decode("utf-8"))
            except InvalidToken as exc:  # pragma: no cover - key mismatch
                raise VaultUnavailableError("Vault key mismatch; cannot decrypt credential") from exc

    def get(self, credential_id: str) -> Optional[CredentialEnvelope]:
        with self._lock:
            return self._records.get(credential_id)

    def list(self) -> List[CredentialEnvelope]:
        with self._lock:
            return list(self._records.values())

    def delete(self, credential_id: str) -> bool:
        with self._lock:
            if credential_id in self._records:
                del self._records[credential_id]
                self._save()
                return True
            return False

    def rotate(self, credential_id: str, new_secrets: Dict[str, Any]) -> CredentialEnvelope:
        """Rotate a credential: re-encrypt with a fresh ciphertext and bump version."""
        with self._lock:
            env = self._records.get(credential_id)
            if env is None:
                raise KeyError(f"No credential {credential_id}")
            ciphertext = self._fernet.encrypt(json.dumps(new_secrets).encode("utf-8"))
            env.ciphertext = ciphertext
            env.version += 1
            env.updated_at = time.time()
            self._save()
            return env

    def rotate_all_for(self, provider_key: str, new_secrets: Dict[str, Any]) -> int:
        count = 0
        for env in self.list():
            if env.provider_key == provider_key:
                self.rotate(env.id, new_secrets)
                count += 1
        return count

    def export_redacted(self) -> List[Dict[str, Any]]:
        """Export vault inventory with secrets masked — never expose tokens."""
        out = []
        for env in self.list():
            d = env.to_dict()
            d["ciphertext"] = "<encrypted>"
            out.append(d)
        return out


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

class AuditLog:
    """Append-only audit log stored under the integrations data dir."""

    def __init__(self, dirpath: Optional[Path] = None, settings=None):
        self._settings = settings or load_integrations_settings()
        self._dir = dirpath or get_aetheros_dir(self._settings.data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "audit.jsonl"
        self._lock = threading.RLock()

    def record(self, action: str, actor: str = "system", target: str = "", detail: Optional[Dict[str, Any]] = None) -> AuditEntry:
        entry = AuditEntry(actor=actor, action=action, target=target, detail=detail or {})
        with self._lock:
            try:
                with open(self._path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(entry.to_dict()) + "\n")
            except OSError as exc:  # pragma: no cover - fs error
                logger.warning("Audit write failed: %s", exc)
        return entry

    def query(self, action: Optional[str] = None, actor: Optional[str] = None, limit: int = 100) -> List[AuditEntry]:
        entries: List[AuditEntry] = []
        if not self._path.exists():
            return entries
        with self._lock:
            for line in self._path.read_text(encoding="utf-8").splitlines():
                try:
                    d = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if action and d.get("action") != action:
                    continue
                if actor and d.get("actor") != actor:
                    continue
                entries.append(AuditEntry(**d))
        return entries[-limit:]


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------

_SECRET_PATTERNS: List[re.Pattern] = [
    re.compile(r"(?i)\b(sk|pk|xoxb|xoxp|xoxa|ghp|gho|ghu|glpat|AKIA|Bearer)\s*[-_A-Za-z0-9]{8,}\b"),
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password|passwd|client[_-]?secret|access[_-]?token|refresh[_-]?token)\b\s*[:=]\s*\S+"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
]


def redact_sensitive_text(text: Optional[str]) -> Optional[str]:
    """Mask common secret shapes. Returns None for None input."""
    if text is None:
        return None
    out = text
    for pat in _SECRET_PATTERNS:
        out = pat.sub("<redacted>", out)
    return out


def redact_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    if not data:
        return dict(data)
    out: Dict[str, Any] = {}
    sensitive_keys = {"token", "access_token", "refresh_token", "client_secret", "secret", "password", "api_key", "apikey", "authorization"}
    for k, v in data.items():
        if isinstance(k, str) and k.lower() in sensitive_keys:
            out[k] = "<redacted>"
        elif isinstance(v, dict):
            out[k] = redact_dict(v)
        elif isinstance(v, list):
            out[k] = [redact_dict(x) if isinstance(x, dict) else x for x in v]
        elif isinstance(v, str):
            out[k] = redact_sensitive_text(v)
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------------------
# Permissions (least privilege)
# ---------------------------------------------------------------------------

class PermissionManager:
    """Scoped permission checks per integration. Deny by default."""

    def __init__(self):
        self._grants: Dict[str, Dict[str, Any]] = {}

    def set_permissions(self, integration_id: str, permissions: Dict[str, Any]) -> None:
        self._grants[integration_id] = permissions

    def get_permissions(self, integration_id: str) -> Dict[str, Any]:
        return self._grants.get(integration_id, {})

    def remove(self, integration_id: str) -> None:
        self._grants.pop(integration_id, None)

    def can(self, integration_id: str, action: str, resource: str = "") -> bool:
        perms = self._grants.get(integration_id, {})
        if not perms:
            return False
        allowed = perms.get("allow", [])
        deny = perms.get("deny", [])
        candidate = f"{resource}:{action}" if resource else action
        if candidate in deny or action in deny:
            return False
        if candidate in allowed or action in allowed:
            return True
        if perms.get("allow_all", False):
            return True
        return False
