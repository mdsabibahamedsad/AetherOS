"""Memory boundaries & isolation enforcement.

The fabric enforces that an actor (identified by user/workspace/session/agent)
may only write and read entries whose boundary scope it is authorized for.
Default policy: an entry written by user A is visible only to user A unless
the boundary is loosened to workspace/session.  Cross-user access is denied.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from aetheros_memory_intelligence.schema import MemoryEntry
from aetheros_memory_intelligence.types import MemoryBoundary, MemoryType


@dataclass
class AccessContext:
    """The identity/scope of the actor requesting access to memory."""

    user_id: str = ""
    workspace_id: str = ""
    session_id: str = ""
    agent_id: str = ""
    is_admin: bool = False

    def scoped(self) -> bool:
        return bool(self.user_id or self.workspace_id or self.session_id or self.agent_id)


class BoundaryPolicy:
    """Configuration for boundary enforcement (defaults are strict)."""

    def __init__(
        self,
        *,
        cross_workspace_allowed: bool = False,
        session_overlaps_workspace: bool = True,
        admin_bypasses: bool = True,
    ) -> None:
        self.cross_workspace_allowed = cross_workspace_allowed
        self.session_overlaps_workspace = session_overlaps_workspace
        self.admin_bypasses = admin_bypasses


class MemoryBoundaries:
    """Enforces boundary isolation on writes and reads."""

    def __init__(self, policy: Optional[BoundaryPolicy] = None) -> None:
        self._policy = policy or BoundaryPolicy()

    # ------------------------------------------------------------------
    # Write authorization
    # ------------------------------------------------------------------

    def can_write(self, entry: MemoryEntry, actor: AccessContext) -> bool:
        """True if ``actor`` is allowed to persist ``entry``.

        Rules:
        - SYSTEM entries require an admin actor.
        - AGENT entries require the same agent_id (or admin).
        - USER entries require matching user_id (or admin).
        - WORKSPACE entries require matching workspace_id and (unless admin)
          when cross-workspace writes are not allowed, the actor must belong to the
          workspace.
        - SESSION entries require matching session_id, or (when the policy
          allows) the same workspace.
        """
        if self._policy.admin_bypasses and actor.is_admin:
            return True
        if entry.memory_type == MemoryType.SYSTEM:
            return False  # never user-writable
        if entry.boundary == MemoryBoundary.SYSTEM:
            return actor.is_admin
        if entry.boundary == MemoryBoundary.AGENT:
            if not actor.agent_id:
                return False
            return actor.agent_id == entry.agent_id or actor.is_admin
        if entry.boundary == MemoryBoundary.USER:
            if not actor.user_id:
                return False
            return actor.user_id == entry.user_id or actor.is_admin
        if entry.boundary == MemoryBoundary.WORKSPACE:
            if not actor.workspace_id or not entry.workspace_id:
                return False
            if not self._policy.cross_workspace_allowed:
                # Cross-workspace writes not allowed - must be in same workspace
                return actor.workspace_id == entry.workspace_id
            # Cross-workspace writes allowed - actor can write to any workspace
            return True
        if entry.boundary == MemoryBoundary.SESSION:
            if actor.session_id and entry.session_id and actor.session_id == entry.session_id:
                return True
            if self._policy.session_overlaps_workspace:
                if actor.workspace_id and entry.workspace_id:
                    return actor.workspace_id == entry.workspace_id
            return actor.is_admin
        return False

    def enforce_write(self, entry: MemoryEntry, actor: AccessContext) -> MemoryEntry:
        """Raise PermissionError if the actor may not write the entry."""
        if not self.can_write(entry, actor):
            raise PermissionError(
                f"memory boundary denied: actor "
                f"(user={actor.user_id or '-'}, ws={actor.workspace_id or '-'}, "
                f"session={actor.session_id or '-'}, agent={actor.agent_id or '-'}) "
                f"cannot write entry boundary={entry.boundary.value}"
            )
        return entry

    # ------------------------------------------------------------------
    # Read authorization
    # ------------------------------------------------------------------

    def can_read(self, entry: MemoryEntry, actor: AccessContext) -> bool:
        """True if ``actor`` may see ``entry``.

        A session/agent actor may read entries within its own boundary even if
        written by another user, but a user actor may NOT read another user's
        private entries.
        """
        if self._policy.admin_bypasses and actor.is_admin:
            return True
        if entry.boundary == MemoryBoundary.SYSTEM:
            return actor.is_admin
        if entry.boundary == MemoryBoundary.AGENT:
            if not actor.agent_id:
                return False
            return actor.agent_id == entry.agent_id or actor.is_admin
        if entry.boundary == MemoryBoundary.USER:
            return bool(actor.user_id and actor.user_id == entry.user_id)
        if entry.boundary == MemoryBoundary.WORKSPACE:
            if actor.workspace_id:
                return actor.workspace_id == entry.workspace_id
            return bool(actor.user_id and actor.user_id == entry.user_id)
        if entry.boundary == MemoryBoundary.SESSION:
            if actor.session_id and entry.session_id:
                return actor.session_id == entry.session_id
            if actor.workspace_id and entry.workspace_id:
                return actor.workspace_id == entry.workspace_id
            if actor.agent_id and entry.agent_id:
                return actor.agent_id == entry.agent_id
            return False
        return False

    def filter_readable(self, entries: List[MemoryEntry], actor: AccessContext) -> List[MemoryEntry]:
        return [e for e in entries if self.can_read(e, actor)]