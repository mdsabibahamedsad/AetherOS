"""
Licensing
=========

License management and enforcement for enterprise features.
Supports feature-based licensing, seat counts, and expiration.
"""

from __future__ import annotations

import enum
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class LicenseError(Exception):
    """Raised when a license operation fails."""


@dataclass
class LicenseFeature:
    """A named, tracked feature within a license."""
    name: str
    description: str = ""
    enabled: bool = True
    max_seats: int = 0  # 0 = unlimited
    limits: Dict[str, Any] = field(default_factory=dict)


@dataclass
class License:
    """An enterprise license granting access to features."""
    key: str = ""
    organization_id: str = ""
    features: Dict[str, LicenseFeature] = field(default_factory=dict)
    max_users: int = 0
    max_workspaces: int = 0
    issued_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    is_trial: bool = False
    tier: str = "free"  # free, pro, enterprise
    valid: bool = True

    def is_expired(self) -> bool:
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False

    def has_feature(self, feature_name: str) -> bool:
        """Check if the license includes a specific feature."""
        feature = self.features.get(feature_name)
        if not feature:
            return False
        return feature.enabled and not self.is_expired()

    def validate(self) -> bool:
        """Validate license integrity and expiration."""
        if not self.valid:
            return False
        if self.is_expired():
            self.valid = False
            return False
        return True


class LicenseManager:
    """Manage licenses and check feature access."""

    def __init__(self) -> None:
        self._licenses: Dict[str, License] = {}

    def register_license(self, license_data: License) -> License:
        """Register a new license."""
        self._licenses[license_data.key] = license_data
        logger.info("License registered: %s (tier: %s)", license_data.key[:16], license_data.tier)
        return license_data

    def get_license(self, key: str) -> Optional[License]:
        return self._licenses.get(key)

    def get_org_license(self, org_id: str) -> Optional[License]:
        for lic in self._licenses.values():
            if lic.organization_id == org_id:
                return lic
        return None

    def revoke_license(self, key: str) -> bool:
        license_data = self._licenses.get(key)
        if license_data:
            license_data.valid = False
            return True
        return False

    def check_feature(
        self,
        org_id: str,
        feature_name: str,
    ) -> bool:
        """Check if an organization has access to a feature."""
        license_data = self.get_org_license(org_id)
        if not license_data:
            return False
        if not license_data.validate():
            return False
        return license_data.has_feature(feature_name)
