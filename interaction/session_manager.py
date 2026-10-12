"""
Session Manager — Session continuity across devices and time.

Allows users to pause workflows, resume later, resume on another device,
and restore interaction context. Integrates with Memory and State Manager.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """Current state of an interaction session.

    Attributes:
        session_id: Unique session identifier
        user_id: User identifier (optional, for multi-user support)
        device_id: Device identifier
        platform: Platform name (desktop, mobile, web)
        status: Session status
        started_at: When the session started
        last_active: Last activity timestamp
        context: Session context data
        metadata: Additional metadata
    """
    session_id: str
    user_id: str = ""
    device_id: str = ""
    platform: str = ""
    status: str = "active"
    started_at: float = 0.0
    last_active: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionSnapshot:
    """A point-in-time snapshot for session resume.

    Attributes:
        snapshot_id: Unique snapshot identifier
        session_id: Source session ID
        timestamp: When the snapshot was taken
        workflow_state: Current workflow state
        interaction_history: Recent interaction history
        active_tasks: Currently active tasks
        open_files: Files being worked on
        environment: Environment variables and state
        preferences: User preferences at snapshot time
        metadata: Additional metadata
    """
    snapshot_id: str = ""
    session_id: str = ""
    timestamp: float = 0.0
    workflow_state: Dict[str, Any] = field(default_factory=dict)
    interaction_history: List[Dict[str, Any]] = field(default_factory=list)
    active_tasks: List[Dict[str, Any]] = field(default_factory=list)
    open_files: List[str] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionContinuity:
    """Continuity record linking sessions across devices/time.

    Attributes:
        continuity_id: Unique continuity identifier
        original_session_id: Original session ID
        resumed_session_id: Session ID after resume
        user_id: User identifier
        snapshots: List of snapshot IDs in this continuity chain
        created_at: When the continuity was created
        last_resumed_at: When it was last resumed
        resume_count: Number of times resumed
        metadata: Additional metadata
    """
    continuity_id: str = ""
    original_session_id: str = ""
    resumed_session_id: str = ""
    user_id: str = ""
    snapshots: List[str] = field(default_factory=list)
    created_at: float = 0.0
    last_resumed_at: float = 0.0
    resume_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionResumeContext:
    """Context provided when resuming a session.

    Attributes:
        session_id: The resumed session ID
        previous_session_id: The original session ID
        workflow_state: Restored workflow state
        active_tasks: Restored active tasks
        open_files: Restored file list
        interaction_summary: Summary of past interactions
        since: Time elapsed since previous session
        metadata: Additional metadata
    """
    session_id: str = ""
    previous_session_id: str = ""
    workflow_state: Dict[str, Any] = field(default_factory=dict)
    active_tasks: List[Dict[str, Any]] = field(default_factory=list)
    open_files: List[str] = field(default_factory=list)
    interaction_summary: str = ""
    since_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """Manages session continuity, pause, and resume across devices.

    Integrates with the AetherOS Kernel State Manager and Memory system
    to persist and restore session context. Supports pausing workflows,
    resuming later, and resuming on another device.

    Usage:
        sm = SessionManager(event_bus, storage_dir="/path/to/sessions")
        sm.initialize()

        session = sm.create_session(user_id="user-1", device_id="device-1")
        snapshot = sm.create_snapshot(session.session_id)

        # Later, on another device
        resume_ctx = sm.resume_session(snapshot.snapshot_id)
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        storage_dir: Optional[str] = None,
    ):
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._sessions: Dict[str, SessionState] = {}
        self._snapshots: Dict[str, SessionSnapshot] = {}
        self._continuities: Dict[str, SessionContinuity] = {}
        self._storage_dir = Path(storage_dir) if storage_dir else Path.cwd() / ".aetheros" / "interaction" / "sessions"
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the session manager and load persisted state."""
        if self._initialized:
            return

        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._load_persisted_state()
        self._initialized = True
        logger.info("SessionManager: initialized (storage=%s)", self._storage_dir)

    def shutdown(self) -> None:
        """Persist state and shut down."""
        self._persist_state()
        self._initialized = False
        logger.info("SessionManager: shut down")

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(
        self,
        user_id: str = "",
        device_id: str = "",
        platform: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> SessionState:
        """Create a new interaction session.

        Args:
            user_id: Optional user identifier
            device_id: Optional device identifier
            platform: Platform name (desktop, mobile, web)
            context: Initial session context

        Returns:
            The created SessionState
        """
        session = SessionState(
            session_id=uuid.uuid4().hex[:16],
            user_id=user_id,
            device_id=device_id,
            platform=platform,
            status="active",
            started_at=time.time(),
            last_active=time.time(),
            context=context or {},
        )

        with self._lock:
            self._sessions[session.session_id] = session

        logger.info("SessionManager: created session %s (user=%s, device=%s)",
                     session.session_id[:8], user_id, device_id)
        return session

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            SessionState or None
        """
        with self._lock:
            return self._sessions.get(session_id)

    def update_session(self, session_id: str, **updates: Any) -> Optional[SessionState]:
        """Update session properties.

        Args:
            session_id: Session identifier
            **updates: Key-value pairs to update

        Returns:
            Updated SessionState or None
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            for key, value in updates.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            session.last_active = time.time()
            return session

    def end_session(self, session_id: str, reason: str = "user_disconnect") -> Optional[SessionState]:
        """End an active session.

        Args:
            session_id: Session identifier
            reason: Reason for ending

        Returns:
            Final SessionState or None
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            session.status = "ended"
            session.last_active = time.time()
            session.metadata["end_reason"] = reason
            session.metadata["ended_at"] = time.time()
            return session

    def list_active_sessions(self) -> List[SessionState]:
        """List all currently active sessions.

        Returns:
            List of active SessionState objects
        """
        with self._lock:
            return [s for s in self._sessions.values() if s.status == "active"]

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def create_snapshot(
        self,
        session_id: str,
        workflow_state: Optional[Dict[str, Any]] = None,
        interaction_history: Optional[List[Dict[str, Any]]] = None,
        active_tasks: Optional[List[Dict[str, Any]]] = None,
        open_files: Optional[List[str]] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> Optional[SessionSnapshot]:
        """Create a point-in-time snapshot of a session.

        Args:
            session_id: Session to snapshot
            workflow_state: Current workflow state
            interaction_history: Recent interactions
            active_tasks: Active tasks
            open_files: Open files
            preferences: User preferences

        Returns:
            SessionSnapshot or None if session not found
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                logger.warning("SessionManager: cannot snapshot unknown session %s", session_id[:8])
                return None

            snapshot = SessionSnapshot(
                snapshot_id=uuid.uuid4().hex[:16],
                session_id=session_id,
                timestamp=time.time(),
                workflow_state=workflow_state or session.context.get("workflow", {}),
                interaction_history=interaction_history or [],
                active_tasks=active_tasks or [],
                open_files=open_files or [],
                environment={},
                preferences=preferences or {},
            )
            self._snapshots[snapshot.snapshot_id] = snapshot

        logger.info("SessionManager: created snapshot %s for session %s",
                     snapshot.snapshot_id[:8], session_id[:8])
        return snapshot

    def get_snapshot(self, snapshot_id: str) -> Optional[SessionSnapshot]:
        """Get a snapshot by ID.

        Args:
            snapshot_id: Snapshot identifier

        Returns:
            SessionSnapshot or None
        """
        with self._lock:
            return self._snapshots.get(snapshot_id)

    def list_snapshots(self, session_id: Optional[str] = None) -> List[SessionSnapshot]:
        """List snapshots, optionally filtered by session.

        Args:
            session_id: Optional session filter

        Returns:
            List of SessionSnapshot objects
        """
        with self._lock:
            if session_id:
                return [s for s in self._snapshots.values() if s.session_id == session_id]
            return list(self._snapshots.values())

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot.

        Args:
            snapshot_id: Snapshot to delete

        Returns:
            True if deleted
        """
        with self._lock:
            return self._snapshots.pop(snapshot_id, None) is not None

    # ------------------------------------------------------------------
    # Continuity (cross-device resume)
    # ------------------------------------------------------------------

    def create_continuity(
        self,
        original_session_id: str,
        user_id: str = "",
    ) -> SessionContinuity:
        """Create a continuity record linking sessions.

        Args:
            original_session_id: The original session ID
            user_id: User identifier

        Returns:
            The created SessionContinuity
        """
        continuity = SessionContinuity(
            continuity_id=uuid.uuid4().hex[:16],
            original_session_id=original_session_id,
            user_id=user_id,
            created_at=time.time(),
        )

        with self._lock:
            self._continuities[continuity.continuity_id] = continuity

        logger.info("SessionManager: created continuity %s for session %s",
                     continuity.continuity_id[:8], original_session_id[:8])
        return continuity

    def resume_session(
        self,
        snapshot_id: str,
        new_device_id: str = "",
        new_platform: str = "",
    ) -> Optional[SessionResumeContext]:
        """Resume a session from a snapshot.

        Creates a new session and restores context from the snapshot.

        Args:
            snapshot_id: Snapshot to resume from
            new_device_id: New device identifier
            new_platform: New platform name

        Returns:
            SessionResumeContext with restored context, or None
        """
        with self._lock:
            snapshot = self._snapshots.get(snapshot_id)
            if snapshot is None:
                logger.warning("SessionManager: cannot resume unknown snapshot %s", snapshot_id[:8])
                return None

            # Create new session
            new_session = self.create_session(
                device_id=new_device_id,
                platform=new_platform,
                context={"workflow": snapshot.workflow_state},
            )

            # Find or create continuity
            continuity = None
            for c in self._continuities.values():
                if c.original_session_id == snapshot.session_id:
                    continuity = c
                    break

            if continuity is None:
                continuity = self.create_continuity(
                    original_session_id=snapshot.session_id,
                )

            # Update continuity
            continuity.resumed_session_id = new_session.session_id
            if snapshot.snapshot_id not in continuity.snapshots:
                continuity.snapshots.append(snapshot.snapshot_id)
            continuity.last_resumed_at = time.time()
            continuity.resume_count += 1

            # Calculate time since original session
            since_seconds = time.time() - snapshot.timestamp

            resume_ctx = SessionResumeContext(
                session_id=new_session.session_id,
                previous_session_id=snapshot.session_id,
                workflow_state=snapshot.workflow_state,
                active_tasks=snapshot.active_tasks,
                open_files=snapshot.open_files,
                since_seconds=since_seconds,
            )

        logger.info(
            "SessionManager: resumed session %s from snapshot %s "
            "(previous=%s, device=%s, platform=%s)",
            resume_ctx.session_id[:8], snapshot_id[:8],
            snapshot.session_id[:8], new_device_id, new_platform,
        )
        return resume_ctx

    def get_continuity(self, continuity_id: str) -> Optional[SessionContinuity]:
        """Get a continuity record.

        Args:
            continuity_id: Continuity identifier

        Returns:
            SessionContinuity or None
        """
        with self._lock:
            return self._continuities.get(continuity_id)

    def find_continuities_for_user(self, user_id: str) -> List[SessionContinuity]:
        """Find all continuities for a user.

        Args:
            user_id: User identifier

        Returns:
            List of SessionContinuity objects
        """
        with self._lock:
            return [c for c in self._continuities.values() if c.user_id == user_id]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist_state(self) -> None:
        """Persist session state to disk."""
        try:
            data = {
                "sessions": {
                    sid: {
                        "session_id": s.session_id,
                        "user_id": s.user_id,
                        "device_id": s.device_id,
                        "platform": s.platform,
                        "status": s.status,
                        "started_at": s.started_at,
                        "last_active": s.last_active,
                        "context": s.context,
                        "metadata": s.metadata,
                    }
                    for sid, s in self._sessions.items()
                },
                "snapshots": {
                    sid: {
                        "snapshot_id": s.snapshot_id,
                        "session_id": s.session_id,
                        "timestamp": s.timestamp,
                        "workflow_state": s.workflow_state,
                        "active_tasks": s.active_tasks,
                        "open_files": s.open_files,
                        "preferences": s.preferences,
                    }
                    for sid, s in self._snapshots.items()
                },
                "continuities": {
                    cid: {
                        "continuity_id": c.continuity_id,
                        "original_session_id": c.original_session_id,
                        "resumed_session_id": c.resumed_session_id,
                        "user_id": c.user_id,
                        "snapshots": c.snapshots,
                        "created_at": c.created_at,
                        "last_resumed_at": c.last_resumed_at,
                        "resume_count": c.resume_count,
                    }
                    for cid, c in self._continuities.items()
                },
            }
            state_file = self._storage_dir / "session_state.json"
            state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("SessionManager: state persistence failed: %s", exc)

    def _load_persisted_state(self) -> None:
        """Load persisted session state from disk."""
        state_file = self._storage_dir / "session_state.json"
        if not state_file.exists():
            return

        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            for sid, sdata in data.get("sessions", {}).items():
                self._sessions[sid] = SessionState(**sdata)
            for sid, sdata in data.get("snapshots", {}).items():
                self._snapshots[sid] = SessionSnapshot(**sdata)
            for cid, cdata in data.get("continuities", {}).items():
                self._continuities[cid] = SessionContinuity(**cdata)
        except Exception as exc:
            logger.warning("SessionManager: state loading failed: %s", exc)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics."""
        with self._lock:
            return {
                "total_sessions": len(self._sessions),
                "active_sessions": sum(1 for s in self._sessions.values() if s.status == "active"),
                "total_snapshots": len(self._snapshots),
                "total_continuities": len(self._continuities),
                "total_resumes": sum(c.resume_count for c in self._continuities.values()),
            }
