"""
Retention Engine — configurable policies for memory lifecycle management.

Supports multiple retention policies:
  - Keep forever (pinned/important memories)
  - Expire after N days (TTL-based)
  - Project lifetime (expire with project)
  - Workspace lifetime (expire with workspace)
  - Manual pinning (user/agent marked)
  - Automatic promotion (STM → LTM based on importance)
  - Automatic archival (old/low-importance → archive)

Integrates with the garbage collector for periodic cleanup.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from memory.memory_store import MemoryStore, MemoryEntry, MemoryScope

logger = logging.getLogger(__name__)


class RetentionAction(enum.Enum):
    """Actions the retention engine can take on an entry."""
    KEEP = "keep"
    ARCHIVE = "archive"
    DELETE = "delete"
    PROMOTE = "promote"
    COMPRESS = "compress"


@dataclass
class RetentionPolicy:
    """A configurable retention policy for memory entries.

    Attributes:
        name: Policy name
        description: Description of what this policy does
        memory_types: Memory types this applies to (empty = all)
        max_age_days: Maximum age in days before action
        min_importance: Minimum importance to keep
        action: What action to take when conditions are met
        promote_to_ltm: Whether to promote to LTM first
        max_entries: Maximum entries before cleanup
        active: Whether this policy is enabled
    """
    name: str = "default"
    description: str = "Default retention policy"
    memory_types: List[str] = field(default_factory=list)
    max_age_days: Optional[float] = None
    min_importance: float = 0.0
    action: RetentionAction = RetentionAction.KEEP
    promote_to_ltm: bool = False
    max_entries: Optional[int] = None
    active: bool = True


# Built-in policies
BUILTIN_POLICIES = [
    RetentionPolicy(
        name="short_term_expiry",
        description="Short-term memories expire after 7 days",
        memory_types=["short_term"],
        max_age_days=7.0,
        min_importance=0.3,
        action=RetentionAction.PROMOTE,
        promote_to_ltm=True,
    ),
    RetentionPolicy(
        name="long_term_keep",
        description="Important long-term memories are kept forever",
        memory_types=["long_term"],
        min_importance=0.7,
        action=RetentionAction.KEEP,
    ),
    RetentionPolicy(
        name="long_term_archive",
        description="Low-importance long-term memories archived after 90 days",
        memory_types=["long_term"],
        max_age_days=90.0,
        min_importance=0.3,
        action=RetentionAction.ARCHIVE,
    ),
    RetentionPolicy(
        name="episodic_compress",
        description="Old episodes are compressed after 30 days",
        memory_types=["episodic"],
        max_age_days=30.0,
        action=RetentionAction.COMPRESS,
    ),
    RetentionPolicy(
        name="workspace_cleanup",
        description="Workspace memories cleaned up on workspace end",
        memory_types=["workspace"],
        action=RetentionAction.DELETE,
        active=False,  # Activated when workspace ends
    ),
    RetentionPolicy(
        name="conversation_expiry",
        description="Conversation memories expire after 24 hours",
        memory_types=["short_term", "episodic"],
        max_age_days=1.0,
        min_importance=0.2,
        action=RetentionAction.DELETE,
    ),
]


class RetentionEngine:
    """Manages retention policies and memory lifecycle.

    Evaluates policies against all entries and returns actions
    for the garbage collector to execute.

    Usage:
        engine = RetentionEngine()
        engine.add_policy(RetentionPolicy(name="my_policy", ...))
        actions = engine.evaluate(entries)
        # actions is a list of (entry, action) tuples
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._policies: List[RetentionPolicy] = []
        self._custom_promote_fn: Optional[Callable] = None

        # Load built-in policies
        for policy in BUILTIN_POLICIES:
            self.add_policy(policy)

    # ------------------------------------------------------------------
    # Policy management
    # ------------------------------------------------------------------

    def add_policy(self, policy: RetentionPolicy) -> None:
        """Add a retention policy."""
        with self._lock:
            self._policies.append(policy)
        logger.debug("Retention: added policy '%s'", policy.name)

    def remove_policy(self, name: str) -> bool:
        """Remove a retention policy by name."""
        with self._lock:
            before = len(self._policies)
            self._policies = [p for p in self._policies if p.name != name]
            return len(self._policies) < before

    def activate_policy(self, name: str) -> bool:
        """Activate a policy."""
        with self._lock:
            for p in self._policies:
                if p.name == name:
                    p.active = True
                    return True
        return False

    def deactivate_policy(self, name: str) -> bool:
        """Deactivate a policy."""
        with self._lock:
            for p in self._policies:
                if p.name == name:
                    p.active = False
                    return True
        return False

    def list_policies(self, active_only: bool = False) -> List[RetentionPolicy]:
        """List all retention policies."""
        with self._lock:
            policies = list(self._policies)
        if active_only:
            policies = [p for p in policies if p.active]
        return policies

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, entries: List[MemoryEntry],
                 store: MemoryStore = None) -> List[tuple]:
        """Evaluate retention policies against entries.

        Returns list of (entry, action, policy_name) tuples.
        """
        now = time.time()
        actions: List[tuple] = []

        with self._lock:
            policies = list(self._policies)

        for entry in entries:
            for policy in policies:
                if not policy.active:
                    continue

                # Check memory type filter
                if policy.memory_types:
                    if entry.memory_type not in policy.memory_types:
                        continue

                # Check age
                if policy.max_age_days is not None:
                    age_days = (now - entry.created_at) / 86400
                    if age_days < policy.max_age_days:
                        continue

                # Check importance
                if entry.importance < policy.min_importance:
                    continue

                # Check max entries
                if policy.max_entries is not None and store:
                    count = store.count(namespace=entry.namespace)
                    if count <= policy.max_entries:
                        continue

                # Policy matched
                action = policy.action

                # Should promote to LTM first?
                if policy.promote_to_ltm and action != RetentionAction.KEEP:
                    actions.append((entry, RetentionAction.PROMOTE, policy.name))

                if action == RetentionAction.KEEP:
                    continue

                actions.append((entry, action, policy.name))
                break  # First matching policy wins

        return actions

    def should_pin(self, entry: MemoryEntry) -> bool:
        """Check if an entry should be pinned (never deleted)."""
        return (
            entry.importance >= 0.9
            or entry.metadata.get("pinned", False)
            or "pinned" in entry.tags
        )

    def should_promote_to_ltm(self, entry: MemoryEntry,
                              threshold: float = 0.7) -> bool:
        """Check if a short-term entry should be promoted to LTM."""
        return (
            entry.memory_type == "short_term"
            and entry.importance >= threshold
            and not entry.metadata.get("promoted", False)
        )

    def set_promote_function(self, fn: Callable) -> None:
        """Set a custom promotion function.

        The function receives a MemoryEntry and returns True if
        the entry should be promoted to long-term memory.
        """
        self._custom_promote_fn = fn

    @staticmethod
    def get_default_policies() -> List[RetentionPolicy]:
        """Get the list of default built-in policies."""
        return list(BUILTIN_POLICIES)
