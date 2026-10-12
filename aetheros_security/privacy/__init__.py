"""
Privacy Controls for AetherOS
=============================

User-facing privacy controls with consent-first defaults:

    - Offline mode (no network egress)
    - Telemetry opt-in (default OFF)
    - Diagnostics opt-in (default OFF)
    - Anonymous crash reporting opt-in (default OFF)
    - Data export (portable JSON bundle of user data)
    - Data deletion (purge user data with optional secure overwrite)
    - Sensitive data masking (PII redaction helpers)

Consent state is persisted to ``<AETHEROS_HOME>/privacy.json`` with restrictive
file permissions. Nothing leaves the machine unless the corresponding consent
flag is explicitly enabled.

Usage::

    from aetheros_security.privacy import PrivacyManager

    manager = PrivacyManager()
    manager.set_telemetry_consent(True)      # explicit opt-in
    allowed = manager.telemetry_allowed()    # False unless opted in
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

#: Network destinations that must never be contacted in offline mode.
LOCALHOST_HOSTS = {"localhost", "127.0.0.1", "::1"}


class PrivacyManager:
    """Manages privacy and consent settings for AetherOS.

    All telemetry/diagnostics/crash-reporting features are gated behind
    explicit opt-in. Consent flags are persisted locally and never reset
    silently.
    """

    def __init__(self, settings_file: Optional[str] = None) -> None:
        self._settings_file = Path(settings_file) if settings_file else self._default_file()
        self._settings: Dict[str, Any] = {
            "offline_mode": False,
            "telemetry_opt_in": False,
            "diagnostics_opt_in": False,
            "crash_report_opt_in": False,
            "mask_pii": False,
            "export_dir": "",
            "consent_history": [],
        }
        self._load()

    @staticmethod
    def _default_file() -> Path:
        from aetheros_constants import get_aetheros_home
        return get_aetheros_home() / "privacy.json"

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._settings_file.exists():
            return
        try:
            data = json.loads(self._settings_file.read_text("utf-8"))
            self._settings.update({k: v for k, v in data.items() if k in self._settings})
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not load privacy settings: %s", exc)

    def _save(self, changed_key: str) -> None:
        try:
            self._settings_file.parent.mkdir(parents=True, exist_ok=True)
            self._settings["consent_history"].append(
                {"key": changed_key, "value": self._settings.get(changed_key), "at": time.time()}
            )
            # Keep only the last 200 consent events.
            self._settings["consent_history"] = self._settings["consent_history"][-200:]
            self._settings_file.write_text(json.dumps(self._settings, indent=2), "utf-8")
            try:
                os.chmod(self._settings_file, 0o600)
            except OSError:
                pass
        except OSError as exc:
            logger.warning("Could not save privacy settings: %s", exc)

    # ------------------------------------------------------------------
    # Getters / setters
    # ------------------------------------------------------------------

    def get_settings(self) -> Dict[str, Any]:
        """Return a copy of the current privacy settings."""
        return json.loads(json.dumps(self._settings))

    def is_offline_mode(self) -> bool:
        return bool(self._settings.get("offline_mode", False))

    def set_offline_mode(self, enabled: bool) -> None:
        self._settings["offline_mode"] = bool(enabled)
        self._save("offline_mode")

    def telemetry_allowed(self) -> bool:
        """Whether telemetry may be collected (requires opt-in + online)."""
        return bool(self._settings.get("telemetry_opt_in", False)) and not self.is_offline_mode()

    def set_telemetry_consent(self, enabled: bool) -> None:
        self._settings["telemetry_opt_in"] = bool(enabled)
        self._save("telemetry_opt_in")

    def diagnostics_allowed(self) -> bool:
        return bool(self._settings.get("diagnostics_opt_in", False)) and not self.is_offline_mode()

    def set_diagnostics_consent(self, enabled: bool) -> None:
        self._settings["diagnostics_opt_in"] = bool(enabled)
        self._save("diagnostics_opt_in")

    def crash_report_allowed(self) -> bool:
        return bool(self._settings.get("crash_report_opt_in", False)) and not self.is_offline_mode()

    def set_crash_report_consent(self, enabled: bool) -> None:
        self._settings["crash_report_opt_in"] = bool(enabled)
        self._save("crash_report_opt_in")

    def mask_pii_enabled(self) -> bool:
        return bool(self._settings.get("mask_pii", False))

    def set_mask_pii(self, enabled: bool) -> None:
        self._settings["mask_pii"] = bool(enabled)
        self._save("mask_pii")

    # ------------------------------------------------------------------
    # Sensitive data masking
    # ------------------------------------------------------------------

    _EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
    _PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)")
    _API_KEY_RE = re.compile(r"(?i)\b(sk-[a-zA-Z0-9]{20,}|[a-zA-Z0-9_]{16,}\.[a-zA-Z0-9_]{16,}\.[a-zA-Z0-9_]{16,})\b")

    def mask_text(self, text: str) -> str:
        """Mask PII and secrets in free text.

        Each masked token is replaced with a stable placeholder so repeated
        values stay consistent within a document.
        """
        replacements: Dict[str, str] = {}

        def _mask(kind: str, match: re.Match) -> str:
            token = match.group(0)
            if token not in replacements:
                replacements[token] = f"[{kind}-{len(replacements) + 1}]"
            return replacements[token]

        masked = self._EMAIL_RE.sub(lambda m: _mask("email", m), text)
        masked = self._PHONE_RE.sub(lambda m: _mask("phone", m), masked)
        masked = self._API_KEY_RE.sub(lambda m: _mask("secret", m), masked)
        return masked

    def mask_value(self, key: str, value: str) -> str:
        """Mask a single value, keyed by a field name hint."""
        key_lower = key.lower()
        if any(tok in key_lower for tok in ("email", "phone", "password", "token", "key", "secret", "cookie")):
            if "email" in key_lower:
                return self.mask_text(value)
            return "*" * min(len(value), 12)
        return value

    # ------------------------------------------------------------------
    # Data export / deletion
    # ------------------------------------------------------------------

    def export_data(self, output_dir: Optional[str] = None) -> Path:
        """Export user data to a JSON bundle.

        Args:
            output_dir: Destination directory (defaults to the configured
                export dir or a temp dir).

        Returns:
            Path to the exported bundle.
        """
        from aetheros_constants import get_aetheros_home

        home = get_aetheros_home()
        target = Path(output_dir) if output_dir else Path(self._settings.get("export_dir") or tempfile.gettempdir())
        target.mkdir(parents=True, exist_ok=True)

        bundle: Dict[str, Any] = {
            "exported_at": time.time(),
            "privacy_settings": self.get_settings(),
            "config": self._read_if_exists(home / "config.yaml", max_bytes=2 * 1024 * 1024),
        }
        # Export non-secret workspace metadata only. Secrets stay behind.
        for sub in ("skills", "cron"):
            path = home / sub
            if path.is_dir():
                bundle[sub] = self._collect_dir_metadata(path)

        out_path = target / f"aetheros-export-{int(time.time())}.json"
        out_path.write_text(json.dumps(bundle, indent=2, default=str), "utf-8")
        logger.info("Data exported to %s", out_path)
        return out_path

    @staticmethod
    def _read_if_exists(path: Path, max_bytes: int) -> Optional[str]:
        try:
            if path.exists() and path.stat().st_size <= max_bytes:
                return path.read_text("utf-8", errors="replace")
        except OSError:
            pass
        return None

    @staticmethod
    def _collect_dir_metadata(path: Path) -> List[str]:
        out = []
        try:
            for entry in sorted(path.iterdir()):
                if entry.is_file():
                    out.append(entry.name)
        except OSError:
            pass
        return out

    def delete_user_data(
        self,
        *,
        secure: bool = False,
        include_secrets: bool = False,
    ) -> Dict[str, Any]:
        """Delete user data under AetherOS home.

        Args:
            secure: Overwrite files with random bytes before deletion.
            include_secrets: Also remove the secrets vault / keychain-backed
                metadata and auth accounts.

        Returns:
            A report of what was deleted.
        """
        from aetheros_constants import get_aetheros_home

        home = get_aetheros_home()
        removed: List[str] = []
        targets = ["sessions", "memory", "skills", "logs", "cron"]
        for sub in targets:
            path = home / sub
            if path.exists():
                self._rmtree(path, secure)
                removed.append(sub)

        for fname in ["config.yaml", "state.db", "audit.jsonl", "privacy.json"]:
            path = home / fname
            if path.exists():
                self._secure_delete(path, secure)
                removed.append(fname)

        if include_secrets:
            for fname in ["secrets.vault", "secrets_index.json", "auth_accounts.json", ".encryption_key"]:
                path = home / fname
                if path.exists():
                    self._secure_delete(path, secure)
                    removed.append(fname)
            try:
                from aetheros_security.secrets import SecretsManager, SecretBackend
                mgr = SecretsManager(backend=SecretBackend.ENCRYPTED_VAULT, home=home)
                for meta in mgr.list_secrets():
                    mgr.delete(meta["name"])
                removed.append("secrets (vault)")
            except Exception as exc:  # pragma: no cover
                logger.warning("Could not purge secrets vault: %s", exc)

        self._settings = {k: v for k, v in self._settings.items() if k != "consent_history"}
        self._settings["consent_history"] = []
        try:
            self._settings_file.write_text(json.dumps(self._settings, indent=2), "utf-8")
            removed.append("privacy settings reset")
        except OSError:
            pass

        return {"deleted": removed, "secure": secure, "at": time.time()}

    def _secure_delete(self, path: Path, secure: bool) -> None:
        if secure:
            try:
                size = path.stat().st_size
                with open(path, "r+b") as f:
                    f.write(os.urandom(size))
                    f.flush()
                    os.fsync(f.fileno())
            except OSError:
                pass
        try:
            path.unlink()
        except OSError as exc:
            logger.warning("Could not delete %s: %s", path, exc)

    def _rmtree(self, path: Path, secure: bool) -> None:
        if secure:
            for file in path.rglob("*"):
                if file.is_file():
                    self._secure_delete(file, secure)
        try:
            shutil.rmtree(path)
        except OSError as exc:
            logger.warning("Could not remove %s: %s", path, exc)

    # ------------------------------------------------------------------
    # Network egress guard
    # ------------------------------------------------------------------

    def check_egress_allowed(self, host: str) -> bool:
        """Check whether a network egress is permitted under current settings.

        In offline mode only loopback and metadata-free local connections are
        allowed. This is the enforcement hook used by outbound clients.
        """
        host = (host or "").lower().rstrip(".")
        if not self.is_offline_mode():
            return True
        return host in LOCALHOST_HOSTS


# Global privacy manager
_privacy_manager: PrivacyManager | None = None


def get_privacy_manager() -> PrivacyManager:
    """Return the global PrivacyManager singleton."""
    global _privacy_manager
    if _privacy_manager is None:
        _privacy_manager = PrivacyManager()
    return _privacy_manager
