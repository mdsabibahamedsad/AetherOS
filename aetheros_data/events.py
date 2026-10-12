"""Durable vs ephemeral events + ordering (Master 61 sections 10-11)."""

from __future__ import annotations

DURABLE_EVENT_KINDS = frozenset({
    "task.state_transition",
    "task.created",
    "task.cancelled",
    "approval.decided",
    "policy.decision",
    "agent.lifecycle",
    "artifact.created",
    "audit.recorded",
    "authority.granted",
    "authority.revoked",
    "automation.state",
    "recovery.event",
    "checkpoint.created",
    "sync.conflict_resolved",
    "backup.created",
    "restore.completed",
    "config.changed",
    "memory.confirmed",
    "memory.retracted",
})

EPHEMERAL_EVENT_KINDS = frozenset({
    "token.stream",
    "typing.indicator",
    "ui.animation",
    "model.delta",
    "presence.heartbeat",
})

# Required envelope fields for every durable event (section 11).
EVENT_ENVELOPE_FIELDS = (
    "event_id", "sequence", "timestamp", "aggregate_id", "aggregate_type",
    "actor", "task_id", "agent_id", "correlation_id", "causation_id",
    "schema_version", "payload",
)

ORDERING_SEMANTICS = (
    "Primary order is the per-database AUTOINCREMENT `seq` (single writer, "
    "monotonic). Wall-clock `timestamp` is informational only and MUST NOT be "
    "used as the causal order across devices; cross-device causality uses "
    "`correlation_id`/`causation_id` chains plus per-object `version` vectors "
    "in SyncEnvelope (see aetheros_data/sync.py)."
)


def is_durable(kind: str) -> bool:
    if kind in DURABLE_EVENT_KINDS:
        return True
    if kind in EPHEMERAL_EVENT_KINDS:
        return False
    # Unknown kinds: persist if they look consequential, never silently drop.
    return True
