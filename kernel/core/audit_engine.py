"""
Audit Engine — immutable audit logging for all consequential actions.

Provides tamper-evident audit trails with cryptographic integrity.
"""

from __future__ import annotations

import logging
import threading
import time
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path

from kernel.core.types import (
    ProvenanceType,
    new_id,
    _now,
)
from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    """An immutable audit log entry."""
    entry_id: str
    timestamp: float
    event_type: str
    actor_id: str
    action: str
    target: str
    outcome: str  # success, failure, denied
    details: Dict[str, Any] = field(default_factory=dict)
    provenance: ProvenanceType = ProvenanceType.SYSTEM_DERIVED
    previous_hash: str = ""
    entry_hash: str = ""
    sequence_number: int = 0


class AuditEngine:
    """
    Immutable audit logging engine.
    
    Provides tamper-evident audit trails with cryptographic chaining.
    Every consequential action is logged with full context.
    """

    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self._lock = threading.RLock()
        
        # Storage
        self.audit_dir = Path(config.state_dir or "~/.aetheros/audit").expanduser() if hasattr(config, 'state_dir') else Path("~/.aetheros/audit").expanduser()
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory buffer (flushed periodically)
        self._buffer: List[AuditEntry] = []
        self._buffer_size = 100
        
        # Chain state
        self._last_hash = "0" * 64
        self._sequence_number = 0
        
        # Load existing chain
        self._load_chain()

    def _load_chain(self) -> None:
        """Load existing audit chain from disk."""
        try:
            # Find latest audit file
            audit_files = sorted(self.audit_dir.glob("audit_*.jsonl"))
            if not audit_files:
                return

            latest = audit_files[-1]
            with open(latest, 'r') as f:
                for line in f:
                    if line.strip():
                        entry_data = json.loads(line)
                        # Verify chain integrity
                        if entry_data.get("previous_hash") != self._last_hash:
                            logger.warning("Audit chain integrity broken at sequence %d",
                                         entry_data.get("sequence_number", 0))
                            break
                        
                        self._last_hash = entry_data.get("entry_hash", self._last_hash)
                        self._sequence_number = entry_data.get("sequence_number", self._sequence_number)
            
            logger.info("AuditEngine: loaded chain up to sequence %d", self._sequence_number)
        except Exception as exc:
            logger.error("Failed to load audit chain: %s", exc)

    def log(
        self,
        event_type: str,
        actor_id: str,
        action: str,
        target: str,
        outcome: str,
        details: Dict[str, Any] = None,
        provenance: ProvenanceType = ProvenanceType.SYSTEM_DERIVED,
    ) -> AuditEntry:
        """Log an audit entry."""
        self._sequence_number += 1
        
        entry = AuditEntry(
            entry_id=new_id("audit"),
            timestamp=_now(),
            event_type=event_type,
            actor_id=actor_id,
            action=action,
            target=target,
            outcome=outcome,
            details=details or {},
            provenance=provenance,
            previous_hash=self._last_hash,
            sequence_number=self._sequence_number,
        )
        
        # Compute entry hash
        entry.entry_hash = self._compute_entry_hash(entry)
        self._last_hash = entry.entry_hash

        with self._lock:
            self._buffer.append(entry)
            
            # Flush if buffer full
            if len(self._buffer) >= self._buffer_size:
                self._flush_buffer()

        if self.event_bus:
            self.event_bus.emit("audit.logged", {
                "entry_id": entry.entry_id,
                "event_type": event_type,
                "actor_id": actor_id,
                "action": action,
                "outcome": outcome,
                "sequence": self._sequence_number,
            })

        return entry

    def _compute_entry_hash(self, entry: AuditEntry) -> str:
        """Compute cryptographic hash of an audit entry."""
        # Create deterministic representation
        data = {
            "entry_id": entry.entry_id,
            "timestamp": entry.timestamp,
            "event_type": entry.event_type,
            "actor_id": entry.actor_id,
            "action": entry.action,
            "target": entry.target,
            "outcome": entry.outcome,
            "details": entry.details,
            "provenance": entry.provenance.value,
            "previous_hash": entry.previous_hash,
            "sequence_number": entry.sequence_number,
        }
        
        # Sort keys for determinism
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def _flush_buffer(self) -> None:
        """Flush buffer to disk."""
        if not self._buffer:
            return

        try:
            # Write to daily rotating file
            date_str = time.strftime("%Y%m%d")
            audit_file = self.audit_dir / f"audit_{date_str}.jsonl"
            
            with open(audit_file, 'a') as f:
                for entry in self._buffer:
                    data = {
                        "entry_id": entry.entry_id,
                        "timestamp": entry.timestamp,
                        "event_type": entry.event_type,
                        "actor_id": entry.actor_id,
                        "action": entry.action,
                        "target": entry.target,
                        "outcome": entry.outcome,
                        "details": entry.details,
                        "provenance": entry.provenance.value,
                        "previous_hash": entry.previous_hash,
                        "entry_hash": entry.entry_hash,
                        "sequence_number": entry.sequence_number,
                    }
                    f.write(json.dumps(data, default=str) + "\n")
            
            self._buffer.clear()
        except Exception as exc:
            logger.error("Failed to flush audit buffer: %s", exc)

    def verify_chain(self, start_sequence: int = 1, end_sequence: int = None) -> tuple:
        """Verify audit chain integrity."""
        try:
            audit_files = sorted(self.audit_dir.glob("audit_*.jsonl"))
            if not audit_files:
                return True, "No audit files found"

            expected_hash = "0" * 64
            expected_seq = start_sequence
            checked = 0

            for audit_file in audit_files:
                with open(audit_file, 'r') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        entry_data = json.loads(line)
                        seq = entry_data.get("sequence_number", 0)
                        
                        if seq < start_sequence:
                            continue
                        if end_sequence and seq > end_sequence:
                            break

                        if seq != expected_seq:
                            return False, f"Sequence gap: expected {expected_seq}, got {seq}"

                        if entry_data.get("previous_hash") != expected_hash:
                            return False, f"Hash mismatch at sequence {seq}"

                        # Verify entry hash
                        computed_hash = self._compute_entry_hash_from_data(entry_data)
                        if computed_hash != entry_data.get("entry_hash"):
                            return False, f"Entry hash mismatch at sequence {seq}"

                        expected_hash = entry_data.get("entry_hash", "")
                        expected_seq = seq + 1
                        checked += 1

            return True, f"Verified {checked} entries"
        except Exception as exc:
            return False, f"Verification error: {exc}"

    def _compute_entry_hash_from_data(self, data: Dict[str, Any]) -> str:
        """Compute hash from stored entry data."""
        import hashlib
        # Reconstruct without the hash fields
        hash_data = {k: v for k, v in data.items() if k not in ("entry_hash", "previous_hash")}
        json_str = json.dumps(hash_data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def query(
        self,
        event_type: str = "",
        actor_id: str = "",
        action: str = "",
        target: str = "",
        outcome: str = "",
        since: float = 0,
        until: float = 0,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """Query audit entries."""
        # For simplicity, search recent files
        results = []
        
        audit_files = sorted(self.audit_dir.glob("audit_*.jsonl"), reverse=True)
        
        for audit_file in audit_files:
            if len(results) >= limit:
                break
            try:
                with open(audit_file, 'r') as f:
                    for line in f:
                        if len(results) >= limit:
                            break
                        if not line.strip():
                            continue
                        entry_data = json.loads(line)
                        
                        # Apply filters
                        if event_type and entry_data.get("event_type") != event_type:
                            continue
                        if actor_id and entry_data.get("actor_id") != actor_id:
                            continue
                        if action and entry_data.get("action") != action:
                            continue
                        if target and entry_data.get("target") != target:
                            continue
                        if outcome and entry_data.get("outcome") != outcome:
                            continue
                        if since and entry_data.get("timestamp", 0) < since:
                            continue
                        if until and entry_data.get("timestamp", 0) > until:
                            continue

                        # Convert to AuditEntry
                        entry = AuditEntry(**entry_data)
                        results.append(entry)
            except Exception as exc:
                logger.error("Audit query error reading %s: %s", audit_file, exc)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get audit engine statistics."""
        with self._lock:
            buffer_count = len(self._buffer)
        
        # Count files
        audit_files = list(self.audit_dir.glob("audit_*.jsonl"))
        total_entries = 0
        for f in audit_files:
            try:
                with open(f, 'r') as fp:
                    total_entries += sum(1 for _ in fp)
            except Exception:
                pass

        return {
            "buffered_entries": buffer_count,
            "total_entries_on_disk": total_entries,
            "sequence_number": self._sequence_number,
            "audit_files": len(audit_files),
            "last_hash": self._last_hash[:16],
        }

    def shutdown(self) -> None:
        """Shutdown the audit engine."""
        logger.info("AuditEngine: shutting down")
        self._flush_buffer()