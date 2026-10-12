"""
Deployment Profiles
===================

Configurable deployment profiles for different environments
(development, staging, production) with environment-specific
settings, resource limits, and feature toggles.
"""

from __future__ import annotations

import enum
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ProfileEnvironment(enum.Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    DR = "disaster_recovery"
    CUSTOM = "custom"


@dataclass
class ProfileConfig:
    """Configuration values within a deployment profile."""
    features: Dict[str, bool] = field(default_factory=dict)
    limits: Dict[str, int] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)
    log_level: str = "INFO"
    enable_metrics: bool = True
    enable_tracing: bool = False


@dataclass
class DeploymentProfile:
    """A named deployment profile for a specific environment."""
    name: str
    environment: ProfileEnvironment = ProfileEnvironment.DEVELOPMENT
    id: str = field(default_factory=lambda: f"dp_{uuid.uuid4().hex[:12]}")
    description: str = ""
    config: ProfileConfig = field(default_factory=ProfileConfig)
    parent_profile: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    version: str = "1.0.0"

    def merge(self, other: "DeploymentProfile") -> "DeploymentProfile":
        """Merge another profile into this one (inherited overrides)."""
        merged = DeploymentProfile(
            name=f"{self.name}+{other.name}",
            environment=self.environment,
            config=ProfileConfig(
                features={**other.config.features, **self.config.features},
                limits={**other.config.limits, **self.config.limits},
                settings={**other.config.settings, **self.config.settings},
                log_level=self.config.log_level,
                enable_metrics=self.config.enable_metrics,
                enable_tracing=self.config.enable_tracing,
            ),
        )
        return merged


class ProfileManager:
    """Manage deployment profiles."""

    def __init__(self) -> None:
        self._profiles: Dict[str, DeploymentProfile] = {}

    def register(self, profile: DeploymentProfile) -> None:
        self._profiles[profile.name] = profile

    def get(self, name: str) -> Optional[DeploymentProfile]:
        return self._profiles.get(name)

    def list(self, environment: Optional[ProfileEnvironment] = None) -> List[DeploymentProfile]:
        if environment:
            return [p for p in self._profiles.values() if p.environment == environment]
        return list(self._profiles.values())

    def remove(self, name: str) -> bool:
        if name in self._profiles:
            del self._profiles[name]
            return True
        return False

    def get_default(self, environment: ProfileEnvironment) -> Optional[DeploymentProfile]:
        """Get the default profile for an environment."""
        for p in self._profiles.values():
            if p.environment == environment and "default" in p.name.lower():
                return p
        return None
