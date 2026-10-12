"""
Supply Chain Security for AetherOS
==================================

Verify the integrity of dependencies and artifacts before they run:

    - Dependency hash verification (expected SHA-256 vs installed files)
    - SBOM (CycloneDX-style) generation from an installed distribution
    - Signature verification for update packages
    - Reproducibility checks (version stamping)

Usage::

    from aetheros_security.supply_chain import SupplyChainManager

    manager = SupplyChainManager()
    report = manager.verify_hashes({"requests": "d8ff6d..."})
    sbom = manager.generate_sbom()
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import logging
import re
import sys
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

#: Well-known artifact signature formats handled by :meth:`verify_signature`.
_SIGNATURE_PATTERNS = {
    "sha256": re.compile(r"^sha256:([0-9a-f]{64})$", re.IGNORECASE),
    "sha512": re.compile(r"^sha512:([0-9a-f]{128})$", re.IGNORECASE),
    "hex": re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE),
}


class SupplyChainError(Exception):
    """Raised when an integrity check fails."""


class SupplyChainManager:
    """Integrity and provenance checks for dependencies and artifacts."""

    def __init__(self) -> None:
        self._expected_hashes: Dict[str, str] = {}
        self._verify_on_import: bool = True

    # ------------------------------------------------------------------
    # Hash verification
    # ------------------------------------------------------------------

    def register_expected_hashes(self, hashes: Dict[str, str]) -> None:
        """Register expected distribution-name -> sha256 hash mappings."""
        self._expected_hashes.update({name.lower(): h for name, h in hashes.items()})

    @staticmethod
    def _sha256_of_file(path) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _dist_files(self, dist_name: str) -> List[str]:
        try:
            dist = importlib.metadata.distribution(dist_name)
        except importlib.metadata.PackageNotFoundError:
            return []
        files = []
        for file in dist.files or []:
            # Convert "path" or "dist-info/path" to absolute
            try:
                base = dist.locate_file(str(file))
            except Exception:
                base = file
            files.append(str(base))
        return files

    def verify_hashes(self, hashes: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Verify installed distributions against expected SHA-256 hashes.

        Args:
            hashes: Optional ``{dist_name: sha256}`` map; defaults to the
                registered expectations.

        Returns:
            Report with per-distribution verification results.
        """
        expected = hashes or self._expected_hashes
        results: Dict[str, Any] = {}
        for name, want in expected.items():
            files = self._dist_files(name)
            if not files:
                results[name] = {"status": "not_installed", "want": want}
                continue
            got = self._sha256_of_file(files[0])
            ok = got.lower() == want.lower()
            results[name] = {"status": "ok" if ok else "mismatch", "want": want, "got": got}
            if not ok:
                logger.warning("Hash mismatch for distribution %s", name)
        return {"verified": len(results), "results": results}

    # ------------------------------------------------------------------
    # SBOM generation
    # ------------------------------------------------------------------

    def generate_sbom(self, include_files: bool = False) -> Dict[str, Any]:
        """Generate a CycloneDX-style SBOM from installed distributions.

        Returns:
            A JSON-compatible SBOM document.
        """
        components = []
        for dist in sorted(
            importlib.metadata.distributions(),
            key=lambda d: (d.metadata.get("Name") or "").lower(),
        ):
            name = dist.metadata.get("Name") or ""
            version = dist.metadata.get("Version") or ""
            if not name:
                continue
            component = {
                "type": "library",
                "name": name,
                "version": version,
                "purl": self._purl(name, version),
            }
            components.append(component)

        return {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "version": 1,
            "metadata": {
                "component": {
                    "type": "application",
                    "name": "aetheros",
                    "version": self._project_version(),
                },
                "timestamp": None,
                "tools": [{"name": "aetheros.supply_chain", "version": "1.0.0"}],
            },
            "components": components,
        }

    @staticmethod
    def _purl(name: str, version: str) -> str:
        purl_name = name.lower().replace("_", "-")
        return f"pkg:pypi/{purl_name}@{version}"

    @staticmethod
    def _project_version() -> str:
        try:
            return importlib.metadata.version("aetheros")
        except importlib.metadata.PackageNotFoundError:
            return "0.0.0-dev"

    # ------------------------------------------------------------------
    # Signature verification
    # ------------------------------------------------------------------

    def verify_signature(self, artifact_path: str, signature: str) -> bool:
        """Verify a detached hash signature over an artifact.

        Supported signature encodings: ``sha256:<hex>``, ``sha512:<hex>``,
        or a bare 64-hex sha256.

        Args:
            artifact_path: Path to the artifact file.
            signature: The expected signature string.

        Returns:
            True if the artifact matches the signature.
        """
        sig = (signature or "").strip()
        hasher: Optional[str] = None
        value: Optional[str] = None
        for kind, pattern in _SIGNATURE_PATTERNS.items():
            match = pattern.match(sig)
            if match:
                hasher, value = kind, match.group(1).lower()
                break
        if hasher is None:
            raise SupplyChainError("Unsupported signature format")

        digest = hashlib.sha256()
        with open(artifact_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                digest.update(chunk)
        actual = digest.hexdigest() if hasher == "sha256" else hashlib.sha512(self._read_all(artifact_path)).hexdigest()
        return actual.lower() == value

    @staticmethod
    def _read_all(path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    # ------------------------------------------------------------------
    # Reproducibility
    # ------------------------------------------------------------------

    def verify_reproducible_build(self, expected_sha: str, artifact_path: str) -> bool:
        """Check an artifact against a reference build hash."""
        actual = self._sha256_of_file(artifact_path)
        return actual.lower() == expected_sha.lower()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "registered_hashes": len(self._expected_hashes),
            "verify_on_import": self._verify_on_import,
            "python": sys.version.split()[0],
        }


# Global supply chain manager
_supply_chain_manager: SupplyChainManager | None = None


def get_supply_chain_manager() -> SupplyChainManager:
    """Return the global SupplyChainManager singleton."""
    global _supply_chain_manager
    if _supply_chain_manager is None:
        _supply_chain_manager = SupplyChainManager()
    return _supply_chain_manager
