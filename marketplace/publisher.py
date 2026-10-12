"""
Publisher Management
====================

Manages extension publishers and their verification status.
Supports publisher registration, key management, and verification.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Publisher:
    """A registered extension publisher."""
    name: str
    display_name: str = ""
    email: str = ""
    website: str = ""
    description: str = ""
    public_key: str = ""
    key_fingerprint: str = ""
    verified: bool = False
    joined_at: str = ""
    extension_count: int = 0
    total_downloads: int = 0

    @property
    def fingerprint_short(self) -> str:
        return self.key_fingerprint[:16] if self.key_fingerprint else ""


class PublisherRegistry:
    """Manages publisher identities and verification."""

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        self._storage_path = storage_path or Path.home() / ".aetheros" / "publishers.json"
        self._publishers: Dict[str, Publisher] = {}
        self._load()

    def register(self, publisher: Publisher) -> None:
        """Register or update a publisher."""
        self._publishers[publisher.name] = publisher
        self._save()

    def get(self, name: str) -> Optional[Publisher]:
        """Get a publisher by name."""
        return self._publishers.get(name)

    def list(self) -> List[Publisher]:
        """List all registered publishers."""
        return list(self._publishers.values())

    def remove(self, name: str) -> bool:
        """Remove a publisher by name."""
        if name in self._publishers:
            del self._publishers[name]
            self._save()
            return True
        return False

    def verify(self, name: str) -> bool:
        """Mark a publisher as verified."""
        pub = self._publishers.get(name)
        if pub:
            pub.verified = True
            self._save()
            return True
        return False

    def unverify(self, name: str) -> bool:
        """Remove verified status from a publisher."""
        pub = self._publishers.get(name)
        if pub:
            pub.verified = False
            self._save()
            return True
        return False

    def _load(self) -> None:
        try:
            if self._storage_path.exists():
                data = json.loads(self._storage_path.read_text(encoding="utf-8"))
                for item in data if isinstance(data, list) else data.get("publishers", []):
                    pub = Publisher(**{k: v for k, v in item.items() if k != "_storage_path"})
                    self._publishers[pub.name] = pub
        except Exception as exc:
            logger.debug("Failed to load publishers: %s", exc)

    def _save(self) -> None:
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = [
                {
                    "name": p.name,
                    "display_name": p.display_name,
                    "email": p.email,
                    "website": p.website,
                    "description": p.description,
                    "public_key": p.public_key,
                    "key_fingerprint": p.key_fingerprint,
                    "verified": p.verified,
                    "joined_at": p.joined_at,
                    "extension_count": p.extension_count,
                    "total_downloads": p.total_downloads,
                }
                for p in self._publishers.values()
            ]
            self._storage_path.write_text(
                json.dumps({"publishers": data}, indent=2), encoding="utf-8"
            )
        except Exception as exc:
            logger.warning("Failed to save publishers: %s", exc)


def verify_publisher(public_key: str) -> str:
    """Compute the fingerprint for a publisher's public key.

    Returns the SHA-256 fingerprint hex digest.
    """
    return hashlib.sha256(public_key.encode("utf-8")).hexdigest()
