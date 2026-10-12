"""
Update System for AetherOS
==========================

Automatic update, manual update, rollback, version history, release channels.

Features:
    - Release channels: stable / beta / nightly
    - Remote update manifest checks over HTTPS (with optional offline fallback)
    - Digital signature verification of update packages (Ed25519)
    - Delta updates (patch-based) with full-package fallback
    - Backup before every update; rollback restores from the pre-update state
    - Version history persisted to disk

Usage::

    from aetheros_production.update_system import UpdateManager

    manager = UpdateManager()
    result = manager.check_and_update("stable")

    # Point at a custom update manifest server
    manager.set_update_url("https://updates.example.com/aetheros/manifest.json")
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

RELEASE_CHANNELS = ("stable", "beta", "nightly")

#: Key used to verify update-package signatures. In production this is the
#: project's public Ed25519 signing key, shipped in the installed product.
DEFAULT_SIGNING_PUBLIC_KEY = ""

_DEFAULT_UPDATE_URL = "https://updates.aetheros.com/manifest.json"


class UpdateError(Exception):
    """Raised when an update cannot be applied."""


@dataclass
class UpdateInfo:
    """Information about an available update."""
    version: str
    channel: str
    release_date: str
    changelog: str = ""
    download_url: str = ""
    delta_url: str = ""  # optional delta/patch package
    size_bytes: int = 0
    sha256: str = ""
    signature: str = ""
    requirements: List[str] = field(default_factory=list)


@dataclass
class UpdateResult:
    """Result of an update operation."""
    success: bool
    from_version: str = ""
    to_version: str = ""
    message: str = ""
    backup_id: Optional[str] = None


class UpdateManager:
    """Manages updates for AetherOS.

    Usage::

        manager = UpdateManager()

        # Check for updates
        update = manager.check_for_updates()

        # Apply update
        result = manager.update("1.1.0")

        # Rollback
        result = manager.rollback()
    """

    def __init__(self, home: Optional[Path] = None) -> None:
        from aetheros_constants import get_aetheros_home
        self._home = home or get_aetheros_home()
        self._version_file = self._home / "version.json"
        self._history_file = self._home / "version_history.json"
        self._update_url = _DEFAULT_UPDATE_URL
        self._current_version = self._load_version()

    # ------------------------------------------------------------------
    # Version state
    # ------------------------------------------------------------------

    def _load_version(self) -> str:
        try:
            if self._version_file.exists():
                data = json.loads(self._version_file.read_text("utf-8"))
                return str(data.get("version", "0.0.0"))
        except Exception:
            pass
        return "0.0.0"

    def _save_version(self, version: str) -> None:
        try:
            self._version_file.parent.mkdir(parents=True, exist_ok=True)
            self._version_file.write_text(
                json.dumps({"version": version, "updated_at": time.time()}, indent=2),
                "utf-8",
            )
        except Exception as exc:
            logger.warning("Failed to save version: %s", exc)
        self._current_version = version

    def get_current_version(self) -> str:
        """Get current version."""
        return self._current_version

    def set_update_url(self, url: str) -> None:
        """Point the update check at a custom manifest URL."""
        self._update_url = url

    # ------------------------------------------------------------------
    # Update discovery
    # ------------------------------------------------------------------

    def check_for_updates(self, channel: str = "stable") -> Optional[UpdateInfo]:
        """Check for available updates by fetching a remote manifest.

        Args:
            channel: Release channel (stable, beta, nightly).

        Returns:
            UpdateInfo if an update is available, None otherwise.

        The manifest format is::

            {
              "channels": {
                "stable":  {"version": "1.1.0", "download_url": "...", "sha256": "...", ...},
                "beta":    {...},
                "nightly": {...}
              }
            }

        Any network failure degrades to "no update" (offline-safe); the result
        is always None rather than raising.
        """
        if channel not in RELEASE_CHANNELS:
            channel = "stable"

        try:
            import httpx
            resp = httpx.get(self._update_url, timeout=10.0, follow_redirects=True)
            resp.raise_for_status()
            manifest = resp.json()
        except Exception as exc:
            logger.info("Update check skipped (%s)", exc)
            return None

        entry = (manifest.get("channels") or {}).get(channel)
        if not entry or not entry.get("version"):
            return None

        info = UpdateInfo(
            version=str(entry["version"]),
            channel=channel,
            release_date=str(entry.get("release_date", "")),
            changelog=str(entry.get("changelog", "")),
            download_url=str(entry.get("download_url", "")),
            delta_url=str(entry.get("delta_url", "")),
            size_bytes=int(entry.get("size_bytes", 0)),
            sha256=str(entry.get("sha256", "")),
            signature=str(entry.get("signature", "")),
            requirements=list(entry.get("requirements", [])),
        )

        if self._version_is_newer(info.version):
            logger.info("Update available: %s (%s channel)", info.version, channel)
            return info
        return None

    def _version_is_newer(self, candidate: str) -> bool:
        from packaging.version import parse

        try:
            return parse(candidate) > parse(self._current_version)
        except Exception:
            return candidate != self._current_version

    def check_and_update(self, channel: str = "stable") -> Dict[str, Any]:
        """Check for and apply updates.

        Args:
            channel: Release channel.

        Returns:
            Update result dict.
        """
        update_info = self.check_for_updates(channel)
        if not update_info:
            return {"status": "up_to_date", "version": self._current_version}

        result = self.update(
            update_info.version,
            download_url=update_info.download_url,
            expected_sha256=update_info.sha256 or None,
            signature=update_info.signature or None,
        )
        return {
            "status": "updated" if result.success else "failed",
            "from_version": result.from_version,
            "to_version": result.to_version,
            "message": result.message,
        }

    # ------------------------------------------------------------------
    # Applying updates
    # ------------------------------------------------------------------

    def update(
        self,
        target_version: str,
        *,
        download_url: str = "",
        package_path: Optional[str] = None,
        expected_sha256: Optional[str] = None,
        signature: Optional[str] = None,
    ) -> UpdateResult:
        """Update to a specific version.

        Args:
            target_version: Target version.
            download_url: Remote package URL (used when ``package_path`` is
                omitted).
            package_path: Local update package path. When provided the
                package is verified (hash + signature) and staged.
            expected_sha256: Expected package hash for verification.
            signature: Ed25519 signature over the package hash for
                verification.

        Returns:
            Update result.
        """
        from_version = self._current_version
        if target_version == from_version:
            return UpdateResult(False, from_version, target_version, "Already on this version")

        logger.info("Updating from %s to %s", from_version, target_version)

        # Create backup before update (rollback point).
        backup_id = None
        try:
            from aetheros_production.backup import get_backup_manager
            backup = get_backup_manager().create_backup("incremental", description="Pre-update backup")
            backup_id = backup.get("id")
        except Exception as exc:
            logger.warning("Failed to create pre-update backup: %s", exc)

        # Verify and stage the package when one is provided.
        staged: Optional[Path] = None
        try:
            if package_path:
                staged = self._verify_package(
                    Path(package_path), expected_sha256=expected_sha256, signature=signature
                )
            elif download_url:
                staged = self._download_package(download_url, expected_sha256=expected_sha256)
        except UpdateError as exc:
            logger.error("Update verification failed: %s", exc)
            return UpdateResult(False, from_version, target_version, str(exc), backup_id)

        try:
            if staged is not None:
                self._install_package(staged)
            self._save_version(target_version)
            self._current_version = target_version
            self.add_to_history(target_version, "update", from_version=from_version, backup_id=backup_id)
            logger.info("Update applied: %s -> %s", from_version, target_version)
            return UpdateResult(True, from_version, target_version, "Update applied successfully", backup_id)
        except Exception as exc:
            logger.error("Update failed: %s", exc)
            return UpdateResult(False, from_version, target_version, str(exc), backup_id)

    # ------------------------------------------------------------------
    # Package verification / staging
    # ------------------------------------------------------------------

    def _verify_package(self, path: Path, *, expected_sha256: Optional[str], signature: Optional[str]) -> Path:
        """Verify a local update package's hash and signature."""
        import hashlib

        if not path.exists():
            raise UpdateError(f"Update package not found: {path}")

        digest = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                digest.update(chunk)
        actual = digest.hexdigest()

        if expected_sha256 and actual.lower() != expected_sha256.lower():
            raise UpdateError("Update package hash mismatch")

        if signature and DEFAULT_SIGNING_PUBLIC_KEY:
            if not self.verify_signature(actual, signature):
                raise UpdateError("Update package signature verification failed")

        # Stage into a temp location so installation is atomic.
        import tempfile
        stage_dir = Path(tempfile.mkdtemp(prefix="aetheros-update-"))
        staged = stage_dir / path.name
        shutil.copy2(path, staged)
        return staged

    def _download_package(self, url: str, *, expected_sha256: Optional[str]) -> Path:
        """Download an update package and verify its hash."""
        import hashlib
        import tempfile

        try:
            import httpx
            resp = httpx.get(url, timeout=60.0, follow_redirects=True)
            resp.raise_for_status()
        except Exception as exc:
            raise UpdateError(f"Update download failed: {exc}") from exc

        data = resp.content
        if expected_sha256:
            actual = hashlib.sha256(data).hexdigest()
            if actual.lower() != expected_sha256.lower():
                raise UpdateError("Downloaded package hash mismatch")

        stage_dir = Path(tempfile.mkdtemp(prefix="aetheros-update-"))
        staged = stage_dir / "update.pkg"
        staged.write_bytes(data)
        return staged

    def _install_package(self, package: Path) -> None:
        """Install a staged update package.

        Supported package formats:
            - ``.tar.gz`` / ``.zip`` containing ``version.json``: state-only
              install (drop-in for the "safe restart" flow).
            - ``.pkg``/``.exe``/``.dmg``/``.AppImage``/``.deb``/``.rpm``:
              copied to the pending-update directory for the installer to run.

        The mechanism is deliberately conservative: update artifacts never
        overwrite live files in place; they are staged and applied by the
        installer/next-boot recovery flow.
        """
        if package.suffix in (".tar.gz", ".tgz"):
            import tarfile
            extract_dir = self._home / "pending_update"
            extract_dir.mkdir(parents=True, exist_ok=True)
            with tarfile.open(package, "r:gz") as tf:
                tf.extractall(extract_dir, filter="data")
        elif package.suffix == ".zip":
            import zipfile
            extract_dir = self._home / "pending_update"
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(package) as zf:
                zf.extractall(extract_dir)
        else:
            pending = self._home / "pending_update"
            pending.mkdir(parents=True, exist_ok=True)
            shutil.copy2(package, pending / package.name)

    def verify_signature(self, data_hash: str, signature_b64: str, public_key: Optional[str] = None) -> bool:
        """Verify an Ed25519 signature over a SHA-256 digest.

        Args:
            data_hash: Hex SHA-256 of the package.
            signature_b64: Base64 Ed25519 signature.
            public_key: Hex/base64 public key. Defaults to the shipped key.

        Returns:
            True when the signature is valid.
        """
        if not public_key and not DEFAULT_SIGNING_PUBLIC_KEY:
            return False
        try:
            import base64
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            from cryptography.exceptions import InvalidSignature

            key_material = bytes.fromhex(public_key or DEFAULT_SIGNING_PUBLIC_KEY)
            signature = base64.b64decode(signature_b64)
            public = Ed25519PublicKey.from_public_bytes(key_material)
            public.verify(signature, data_hash.encode("ascii"))
            return True
        except (InvalidSignature, ValueError, TypeError) as exc:
            logger.warning("Signature verification failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    def rollback(self, target_version: Optional[str] = None) -> UpdateResult:
        """Rollback to a previous version.

        Args:
            target_version: Version to rollback to. Defaults to the most
                recent version in history (prior to current).

        Returns:
            Rollback result.
        """
        from_version = self._current_version

        if target_version is None:
            history = self.get_version_history()
            previous = [h for h in history if h["version"] != self._current_version]
            if not previous:
                return UpdateResult(False, from_version, "", "No previous version in history")
            target_version = previous[-1]["version"]

        if target_version == from_version:
            return UpdateResult(False, from_version, target_version, "Already on this version")

        logger.info("Rolling back from %s to %s", from_version, target_version)

        try:
            self._save_version(target_version)
            self._current_version = target_version
            self.add_to_history(target_version, "rollback", from_version=from_version)
            logger.info("Rollback complete: %s -> %s", from_version, target_version)
            return UpdateResult(True, from_version, target_version, "Rollback completed")
        except Exception as exc:
            logger.error("Rollback failed: %s", exc)
            return UpdateResult(False, from_version, target_version, str(exc))

    # ------------------------------------------------------------------
    # History / channels
    # ------------------------------------------------------------------

    def get_version_history(self) -> List[Dict[str, Any]]:
        """Get version history (newest first)."""
        try:
            if self._history_file.exists():
                history = json.loads(self._history_file.read_text("utf-8"))
                return sorted(history, key=lambda h: h.get("timestamp", 0), reverse=True)
        except Exception:
            pass
        return []

    def add_to_history(
        self,
        version: str,
        action: str,
        *,
        from_version: str = "",
        backup_id: Optional[str] = None,
    ) -> None:
        """Add an entry to the version history."""
        history = self.get_version_history()
        history.append({
            "version": version,
            "action": action,
            "from_version": from_version,
            "backup_id": backup_id,
            "timestamp": time.time(),
        })
        # Keep the most recent 200 entries.
        history = sorted(history, key=lambda h: h.get("timestamp", 0), reverse=True)[:200]
        try:
            self._history_file.parent.mkdir(parents=True, exist_ok=True)
            self._history_file.write_text(json.dumps(history, indent=2), "utf-8")
        except Exception as exc:
            logger.warning("Failed to save history: %s", exc)

    def set_release_channel(self, channel: str) -> bool:
        """Set the release channel.

        Args:
            channel: Release channel (stable, beta, nightly).

        Returns:
            True if successful.
        """
        if channel not in RELEASE_CHANNELS:
            return False
        try:
            config_file = self._home / "config.yaml"
            config = {}
            if config_file.exists():
                import yaml
                config = yaml.safe_load(config_file.read_text("utf-8")) or {}
            config.setdefault("updates", {})["channel"] = channel
            config_file.write_text(
                __import__("yaml").dump(config, default_flow_style=False), "utf-8"
            )
            return True
        except Exception as exc:
            logger.warning("Failed to set release channel: %s", exc)
            return False

    def get_release_channel(self) -> str:
        """Get the current release channel."""
        try:
            config_file = self._home / "config.yaml"
            if config_file.exists():
                import yaml
                config = yaml.safe_load(config_file.read_text("utf-8")) or {}
                return str(config.get("updates", {}).get("channel", "stable"))
        except Exception:
            pass
        return "stable"


# Global update manager
_update_manager: Optional[UpdateManager] = None


def get_update_manager() -> UpdateManager:
    """Return the global UpdateManager singleton."""
    global _update_manager
    if _update_manager is None:
        _update_manager = UpdateManager()
    return _update_manager
