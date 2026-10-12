"""Digital signatures, publisher verification, and integrity checks for hub items."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class SecurityManager:
    def __init__(self):
        self._trusted_keys: dict[str, dict] = {}
        self._load_trusted_keys()

    def _load_trusted_keys(self):
        from hub.store import HubStore
        store = HubStore()
        stored = store.get_setting("trusted_publisher_keys", "{}")
        try:
            self._trusted_keys = json.loads(stored)
        except (json.JSONDecodeError, TypeError):
            self._trusted_keys = {}

    def _save_trusted_keys(self):
        from hub.store import HubStore
        store = HubStore()
        store.set_setting("trusted_publisher_keys", json.dumps(self._trusted_keys))

    def compute_checksum(self, file_path: str, algorithm: str = "sha256") -> str:
        h = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def verify_checksum(self, file_path: str, expected: str,
                        algorithm: str = "sha256") -> bool:
        actual = self.compute_checksum(file_path, algorithm)
        return actual == expected

    def sign_manifest(self, manifest: dict, private_key_pem: str) -> str:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
        import base64
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(), password=None)
        payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        signature = private_key.sign(payload, padding.PKCS1v15(), hashes.SHA256())
        return base64.b64encode(signature).decode()

    def verify_signature(self, manifest: dict, signature_b64: str,
                         public_key_pem: str) -> bool:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
        import base64
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode())
            payload = json.dumps(manifest, sort_keys=True,
                                 separators=(",", ":")).encode()
            signature = base64.b64decode(signature_b64)
            public_key.verify(signature, payload, padding.PKCS1v15(), hashes.SHA256())
            return True
        except Exception as e:
            logger.error("Signature verification failed: %s", e)
            return False

    def register_publisher_key(self, publisher: str, public_key_pem: str,
                               verified: bool = False) -> None:
        self._trusted_keys[publisher] = {
            "public_key": public_key_pem,
            "verified": verified,
            "registered_at": datetime.utcnow().isoformat() + "Z",
        }
        self._save_trusted_keys()

    def is_publisher_verified(self, publisher: str) -> bool:
        info = self._trusted_keys.get(publisher)
        return info.get("verified", False) if info else False

    def get_publisher_info(self, publisher: str) -> Optional[dict]:
        return self._trusted_keys.get(publisher)

    def verify_package_integrity(self, package_dir: str) -> dict:
        manifest_path = os.path.join(package_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            return {"valid": False, "error": "manifest.json not found"}
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
        checksums = {}
        for root, dirs, files in os.walk(package_dir):
            for fn in files:
                fp = os.path.join(root, fn)
                rel = os.path.relpath(fp, package_dir)
                checksums[rel] = self.compute_checksum(fp)
        manifest_checksums = manifest.get("checksums", {})
        for rel_path, expected in manifest_checksums.items():
            actual = checksums.get(rel_path)
            if not actual:
                return {"valid": False, "error": f"Missing file: {rel_path}"}
            if actual != expected:
                return {"valid": False, "error": f"Checksum mismatch: {rel_path}"}
        return {"valid": True, "checksums": checksums}

    def safe_uninstall(self, install_path: str, backup_path: str = None) -> bool:
        import shutil
        if backup_path and os.path.exists(install_path):
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            shutil.copytree(install_path, backup_path, dirs_exist_ok=True)
        if os.path.exists(install_path):
            shutil.rmtree(install_path, ignore_errors=True)
            return True
        return False

    def get_integrity_report(self, item_id: str, install_path: str) -> dict:
        report = {
            "item_id": item_id,
            "install_path": install_path,
            "exists": os.path.exists(install_path),
            "checksum_valid": False,
            "signature_valid": False,
            "publisher_verified": False,
            "file_count": 0,
            "total_size": 0,
        }
        if not os.path.exists(install_path):
            return report
        file_count = 0
        total_size = 0
        for root, dirs, files in os.walk(install_path):
            file_count += len(files)
            for fn in files:
                total_size += os.path.getsize(os.path.join(root, fn))
        report["file_count"] = file_count
        report["total_size"] = total_size
        manifest_path = os.path.join(install_path, "manifest.json")
        if os.path.exists(manifest_path):
            result = self.verify_package_integrity(install_path)
            report["checksum_valid"] = result.get("valid", False)
        signature_path = os.path.join(install_path, "signature.sig")
        if os.path.exists(signature_path) and os.path.exists(
                os.path.join(install_path, "public_key.pem")):
            try:
                with open(os.path.join(install_path, "manifest.json"), encoding="utf-8") as f:
                    manifest = json.load(f)
                with open(signature_path, encoding="utf-8") as f:
                    sig = f.read()
                with open(os.path.join(install_path, "public_key.pem"), encoding="utf-8") as f:
                    pub_key = f.read()
                report["signature_valid"] = self.verify_signature(
                    manifest, sig, pub_key)
            except Exception:
                pass
        return report
