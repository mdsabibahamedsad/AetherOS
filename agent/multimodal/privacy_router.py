"""Privacy Classification and Provider Privacy Routing (Phases 71-74).

- Classifies media into PUBLIC / PRIVATE / SENSITIVE / RESTRICTED.
- Decides whether media may be sent to an external provider, or must be
  processed locally, or must be refused — using user/workspace/provider policy
  (MASTER 7).
- Enables local/offline multimodal processing where local models exist.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from agent.multimodal.media_abstraction import MediaObject, SensitivityLevel

logger = logging.getLogger(__name__)


class ProcessingTarget(Enum):
    """Where media may be processed."""

    LOCAL = "local"          # never leaves the machine
    EXTERNAL = "external"    # may go to a configured provider
    REFUSE = "refuse"        # no permitted processor


@dataclass
class PrivacyDecision:
    target: ProcessingTarget
    sensitivity: SensitivityLevel
    reason: str = ""
    external_provider_allowed: bool = False


# Content hints that upgrade sensitivity classification.
_SENSITIVE_HINTS = [
    "password", "passwd", "secret", "api_key", "api-key", "apikey", "token",
    "authorization", "bearer", "private_key", "private key", "ssh-rsa",
    "pan ", "card number", "ssn", "social security",
]
_RESTRICTED_HINTS = [
    "classified", "top secret", "confidential", "nda", "legal hold",
]


class PrivacyClassifier:
    """Classify media sensitivity from content hints and explicit labels."""

    def __init__(self, default: SensitivityLevel = SensitivityLevel.PRIVATE) -> None:
        self._default = default

    def classify(
        self,
        media: MediaObject,
        content_hint: str = "",
        explicit: Optional[SensitivityLevel] = None,
    ) -> SensitivityLevel:
        if explicit is not None:
            return explicit
        if media.sensitivity != SensitivityLevel.PRIVATE:
            return media.sensitivity
        hint = (content_hint or "").lower()
        if any(marker in hint for marker in _RESTRICTED_HINTS):
            return SensitivityLevel.RESTRICTED
        if any(marker in hint for marker in _SENSITIVE_HINTS):
            return SensitivityLevel.SENSITIVE
        return self._default


class ProviderPrivacyRouter:
    """Route media to LOCAL / EXTERNAL / REFUSE per policy (Phase 72)."""

    def __init__(
        self,
        classifier: Optional[PrivacyClassifier] = None,
        local_processors: Optional[List[str]] = None,
    ) -> None:
        self.classifier = classifier or PrivacyClassifier()
        self.local_processors = local_processors or ["ocr", "stt", "vision", "documents"]
        # policy: external sensitivity levels that are allowed to leave
        self._allow_external: set = {SensitivityLevel.PUBLIC}

    def configure_policy(
        self,
        allow_external_sensitivity: Optional[List[SensitivityLevel]] = None,
        force_local: bool = False,
    ) -> None:
        if allow_external_sensitivity is not None:
            self._allow_external = set(allow_external_sensitivity)
        self._force_local = force_local

    def decide(
        self,
        media: MediaObject,
        content_hint: str = "",
        explicit_sensitivity: Optional[SensitivityLevel] = None,
        external_processors: Optional[List[str]] = None,
    ) -> PrivacyDecision:
        """Decide where a media object may be processed."""
        sens = self.classifier.classify(media, content_hint, explicit_sensitivity)
        force_local = getattr(self, "_force_local", False)

        if getattr(self, "_force_local", False):
            return PrivacyDecision(
                ProcessingTarget.LOCAL, sens, "force_local policy", False
            )
        if sens in self._allow_external:
            return PrivacyDecision(
                ProcessingTarget.EXTERNAL, sens, "sensitivity allows external", True
            )
        # Check if a local processor could handle this modality type.
        can_local = media.type.value in self.local_processors
        if can_local:
            return PrivacyDecision(
                ProcessingTarget.LOCAL,
                sens,
                "sensitivity blocks external; local processing available",
                False,
            )
        return PrivacyDecision(
            ProcessingTarget.REFUSE,
            sens,
            "no permitted processor for sensitivity level",
            False,
        )


def default_privacy_router() -> ProviderPrivacyRouter:
    """Build a router honoring the multimodal config section (if present)."""
    router = ProviderPrivacyRouter()
    try:
        from aetheros_cli.config import load_config

        cfg = load_config()
        section = cfg.get("multimodal", {}).get("privacy", {})
        force_local = bool(section.get("force_local", False))
        allow = section.get("allow_external_sensitivity", ["public"])
        allowed = [SensitivityLevel(v) for v in allow if v in (
            "public", "private", "sensitive", "restricted"
        )]
        router.configure_policy(allow_external_sensitivity=allowed, force_local=force_local)
    except Exception as e:  # pragma: no cover - config optional
        logger.debug("default_privacy_router fell back to defaults: %s", e)
    return router