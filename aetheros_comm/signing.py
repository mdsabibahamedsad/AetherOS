"""
Agent Communication Fabric — message signing, integrity, and replay
protection (master spec steps 15, 16, 17).

Sensitive messages are signed with an HMAC-SHA256 key derived from a
profile-scoped fabric secret. The receiver can verify:

    - who sent the message (the key is bound to the fabric instance, and the
      envelope carries ``senderAgentId`` inside the signed canonical bytes),
    - whether the message changed (any mutation invalidates the signature),
    - whether the message is valid for this protocol version.

Replay protection records every accepted ``(senderAgentId, messageId)`` for a
retention window; a previously accepted message is rejected if replayed.
Expired messages are rejected by :mod:`aetheros_comm.envelope` (step 17).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

from .envelope import AgentMessageEnvelope, EnvelopeError

logger = logging.getLogger(__name__)

try:
    from aetheros_constants import get_aetheros_home
except Exception:  # pragma: no cover - fall back to a local path
    def get_aetheros_home() -> Path:  # type: ignore[misc]
        return Path.home() / ".aetheros"


class SignatureError(Exception):
    """Raised when signature verification fails."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _load_or_create_key(key_path: Path) -> bytes:
    if key_path.exists():
        try:
            return key_path.read_bytes()
        except OSError:  # pragma: no cover
            pass
    key = secrets.token_bytes(32)
    try:
        key_path.parent.mkdir(parents=True, exist_ok=True)
        # Best-effort restrictive permissions (POSIX); on Windows the
        # ACL is left to the user's home-directory permissions.
        fd = os.open(str(key_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                     mode=0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(key)
    except OSError:  # pragma: no cover
        logger.warning("Could not persist fabric signing key at %s", key_path)
    return key


class MessageSigner:
    """Signs and verifies envelope integrity with HMAC-SHA256."""

    def __init__(self, key: Optional[bytes] = None,
                 key_path: Optional[Path] = None) -> None:
        if key is None:
            key_path = key_path or (get_aetheros_home() / "comms" / "signing.key")
            key = _load_or_create_key(key_path)
        self._key = key
        self._algorithm = "hmac-sha256"

    @property
    def algorithm(self) -> str:
        return self._algorithm

    def sign(self, envelope: AgentMessageEnvelope) -> str:
        """Return the base64 signature for ``envelope`` and attach it."""
        digest = hmac.new(self._key, envelope.canonical_bytes(),
                          hashlib.sha256).digest()
        envelope.signature = base64.b64encode(digest).decode("ascii")
        return envelope.signature

    def verify(self, envelope: AgentMessageEnvelope) -> bool:
        """Verify the attached signature without mutating the envelope."""
        if not envelope.signature:
            return False
        try:
            provided = base64.b64decode(envelope.signature.encode("ascii"))
        except Exception:
            return False
        expected = hmac.new(self._key, envelope.canonical_bytes(),
                            hashlib.sha256).digest()
        return hmac.compare_digest(provided, expected)

    def require_valid(self, envelope: AgentMessageEnvelope) -> None:
        """Verify and raise :class:`SignatureError` on failure."""
        if not self.verify(envelope):
            raise SignatureError(
                "signature missing or invalid for "
                f"message {envelope.messageId} from {envelope.senderAgentId}")


class ReplayStore:
    """Tracks accepted ``(sender, messageId)`` pairs to block replays.

    Thread-safe. Entries older than ``retention_seconds`` are pruned so
    long-running fabrics do not grow without bound.
    """

    def __init__(self, retention_seconds: float = 3600.0) -> None:
        self._retention = retention_seconds
        self._seen: Dict[Tuple[str, str], float] = {}
        self._lock = threading.RLock()

    def is_replay(self, sender: str, message_id: str) -> bool:
        with self._lock:
            return (sender, message_id) in self._seen

    def record(self, sender: str, message_id: str) -> None:
        now = time.time()
        with self._lock:
            self._prune(now)
            self._seen[(sender, message_id)] = now

    def check_and_record(self, sender: str, message_id: str) -> bool:
        """Return True if accepted (not a replay); False if replay."""
        with self._lock:
            if self.is_replay(sender, message_id):
                return False
            self.record(sender, message_id)
            return True

    def _prune(self, now: float) -> None:
        cutoff = now - self._retention
        stale = [k for k, t in self._seen.items() if t < cutoff]
        for key in stale:
            del self._seen[key]

    def clear(self) -> None:
        with self._lock:
            self._seen.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._seen)


def verify_message(envelope: AgentMessageEnvelope, signer: MessageSigner) -> None:
    """Convenience: verify an envelope, mapping failures to EnvelopeError.

    Used by the inbound pipeline so a bad signature surfaces as a *schema /
    security* rejection rather than a crash.
    """
    try:
        signer.require_valid(envelope)
    except SignatureError as exc:
        raise EnvelopeError(str(exc.reason), "BAD_SIGNATURE") from exc