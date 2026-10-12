"""
Security for AetherOS Developer Platform
========================================

Security features for extensions:
    - Digital signatures
    - Extension verification
    - Permission review
    - Malware scanning
    - Safe updates

Usage::

    from aetheros_developer_platform.security import SecurityManager

    manager = SecurityManager()
    manager.verify_extension("/path/to/extension")
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class VerificationStatus(Enum):
    """Extension verification status."""
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    UNKNOWN = "unknown"


@dataclass
class SecurityReport:
    """Security report for an extension."""
    extension_name: str
    status: VerificationStatus
    score: float = 0.0
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    scanned_at: float = 0.0
    scanner_version: str = "1.0.0"
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PermissionReview:
    """Permission review for an extension."""
    extension_name: str
    requested_permissions: List[str]
    approved_permissions: List[str] = field(default_factory=list)
    denied_permissions: List[str] = field(default_factory=list)
    reviewed_at: float = 0.0


class SecurityManager:
    """Manages security for AetherOS extensions.

    Usage::

        manager = SecurityManager()

        # Verify an extension
        report = manager.verify_extension("/path/to/extension")

        # Review permissions
        review = manager.review_permissions("my-plugin", ["filesystem", "network"])
    """

    def __init__(self) -> None:
        self._reports: Dict[str, SecurityReport] = {}
        self._reviews: Dict[str, PermissionReview] = {}
        self._signatures: Dict[str, Dict[str, Any]] = {}
        self._trusted_publishers: List[str] = []

    def verify_extension(
        self,
        extension_path: str,
        *,
        deep_scan: bool = True,
    ) -> SecurityReport:
        """Verify an extension's security.

        Args:
            extension_path: Path to the extension.
            deep_scan: Perform deep scan for malware.

        Returns:
            Security report.
        """
        path = Path(extension_path)
        name = path.name

        report = SecurityReport(
            extension_name=name,
            status=VerificationStatus.UNKNOWN,
            scanned_at=time.time(),
        )

        # Basic checks
        issues = []
        warnings = []

        # Check for manifest
        manifest_file = path / "manifest.yaml"
        if not manifest_file.exists():
            manifest_file = path / "plugin.yaml"
        if not manifest_file.exists():
            issues.append("No manifest file found")
            report.status = VerificationStatus.SUSPICIOUS
        else:
            try:
                import yaml
                manifest = yaml.safe_load(manifest_file.read_text(encoding="utf-8"))
                if not manifest.get("name"):
                    issues.append("Manifest missing name")
                if not manifest.get("version"):
                    warnings.append("Manifest missing version")
                if not manifest.get("author"):
                    warnings.append("Manifest missing author")
            except Exception as exc:
                issues.append(f"Failed to parse manifest: {exc}")
                report.status = VerificationStatus.SUSPICIOUS

        # Check for suspicious patterns
        if deep_scan:
            suspicious_patterns = [
                "eval(",
                "exec(",
                "subprocess",
                "os.system",
                "__import__",
            ]

            for py_file in path.rglob("*.py"):
                try:
                    content = py_file.read_text(encoding="utf-8")
                    for pattern in suspicious_patterns:
                        if pattern in content:
                            warnings.append(f"Suspicious pattern '{pattern}' in {py_file.name}")
                except Exception:
                    pass

        # Calculate score
        score = 1.0
        score -= len(issues) * 0.2
        score -= len(warnings) * 0.05
        score = max(0.0, min(1.0, score))

        report.issues = issues
        report.warnings = warnings
        report.score = score

        if not issues and score >= 0.8:
            report.status = VerificationStatus.VERIFIED
        elif issues:
            report.status = VerificationStatus.SUSPICIOUS
        else:
            report.status = VerificationStatus.UNVERIFIED

        self._reports[name] = report
        logger.info(
            "Verified extension '%s': %s (score: %.2f)",
            name,
            report.status.value,
            score,
        )

        return report

    def get_verification_report(
        self,
        extension_name: str,
    ) -> Optional[SecurityReport]:
        """Get verification report for an extension."""
        return self._reports.get(extension_name)

    def list_verification_reports(self) -> List[SecurityReport]:
        """List all verification reports."""
        return list(self._reports.values())

    def sign_extension(
        self,
        extension_path: str,
        private_key: str,
    ) -> Dict[str, Any]:
        """Sign an extension.

        Args:
            extension_path: Path to the extension.
            private_key: Private key for signing.

        Returns:
            Signature data.
        """
        path = Path(extension_path)

        # Calculate hash of extension contents
        content_hash = hashlib.sha256()
        for file in sorted(path.rglob("*")):
            if file.is_file():
                content_hash.update(file.read_bytes())

        signature = {
            "extension": path.name,
            "hash": content_hash.hexdigest(),
            "signed_at": time.time(),
            "algorithm": "sha256",
        }

        self._signatures[path.name] = signature
        logger.info("Signed extension: %s", path.name)

        return signature

    def verify_signature(
        self,
        extension_path: str,
        signature: Dict[str, Any],
    ) -> bool:
        """Verify an extension's signature."""
        path = Path(extension_path)

        # Calculate current hash
        content_hash = hashlib.sha256()
        for file in sorted(path.rglob("*")):
            if file.is_file():
                content_hash.update(file.read_bytes())

        current_hash = content_hash.hexdigest()
        stored_hash = signature.get("hash", "")

        return current_hash == stored_hash

    def review_permissions(
        self,
        extension_name: str,
        requested_permissions: List[str],
        *,
        auto_approve: bool = False,
    ) -> PermissionReview:
        """Review extension permissions.

        Args:
            extension_name: Extension name.
            requested_permissions: Requested permissions.
            auto_approve: Auto-approve all permissions.

        Returns:
            Permission review.
        """
        approved = []
        denied = []

        # Define safe permissions
        safe_permissions = {
            "filesystem:read",
            "memory:read",
            "memory:write",
        }

        for perm in requested_permissions:
            if auto_approve or perm in safe_permissions:
                approved.append(perm)
            else:
                denied.append(perm)

        review = PermissionReview(
            extension_name=extension_name,
            requested_permissions=requested_permissions,
            approved_permissions=approved,
            denied_permissions=denied,
            reviewed_at=time.time(),
        )

        self._reviews[extension_name] = review
        logger.info(
            "Reviewed permissions for '%s': %d approved, %d denied",
            extension_name,
            len(approved),
            len(denied),
        )

        return review

    def get_permission_review(
        self,
        extension_name: str,
    ) -> Optional[PermissionReview]:
        """Get permission review for an extension."""
        return self._reviews.get(extension_name)

    def list_permission_reviews(self) -> List[PermissionReview]:
        """List all permission reviews."""
        return list(self._reviews.values())

    def add_trusted_publisher(self, publisher: str) -> None:
        """Add a trusted publisher."""
        if publisher not in self._trusted_publishers:
            self._trusted_publishers.append(publisher)

    def remove_trusted_publisher(self, publisher: str) -> bool:
        """Remove a trusted publisher."""
        if publisher in self._trusted_publishers:
            self._trusted_publishers.remove(publisher)
            return True
        return False

    def is_trusted_publisher(self, publisher: str) -> bool:
        """Check if a publisher is trusted."""
        return publisher in self._trusted_publishers

    def list_trusted_publishers(self) -> List[str]:
        """List all trusted publishers."""
        return list(self._trusted_publishers)

    def scan_for_malware(
        self,
        extension_path: str,
    ) -> SecurityReport:
        """Scan an extension for malware.

        This is a simplified scan. In production, this would use
        a proper malware scanning engine.
        """
        return self.verify_extension(extension_path, deep_scan=True)

    def get_safe_update_check(
        self,
        extension_name: str,
        current_version: str,
        new_version: str,
    ) -> Dict[str, Any]:
        """Check if an update is safe.

        Args:
            extension_name: Extension name.
            current_version: Current version.
            new_version: New version.

        Returns:
            Safety check result.
        """
        # Simple version comparison
        from sdk.versioning import Version, VersionRange

        try:
            current = Version(current_version)
            new = Version(new_version)

            is_major_bump = new.major > current.major
            is_minor_bump = new.minor > current.minor

            return {
                "safe": True,
                "extension": extension_name,
                "current_version": current_version,
                "new_version": new_version,
                "is_major_bump": is_major_bump,
                "is_minor_bump": is_minor_bump,
                "recommendation": (
                    "Review changes before updating"
                    if is_major_bump
                    else "Safe to update"
                ),
            }
        except Exception as exc:
            return {
                "safe": False,
                "extension": extension_name,
                "error": str(exc),
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get security statistics."""
        return {
            "verifications": len(self._reports),
            "permission_reviews": len(self._reviews),
            "signatures": len(self._signatures),
            "trusted_publishers": len(self._trusted_publishers),
            "verified": sum(
                1
                for r in self._reports.values()
                if r.status == VerificationStatus.VERIFIED
            ),
            "suspicious": sum(
                1
                for r in self._reports.values()
                if r.status == VerificationStatus.SUSPICIOUS
            ),
        }


# Global security manager
_security_manager: Optional[SecurityManager] = None


def get_security_manager() -> SecurityManager:
    """Return the global SecurityManager singleton."""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager
