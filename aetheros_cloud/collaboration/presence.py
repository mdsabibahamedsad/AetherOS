"""Presence manager — live cursors, online indicators, collaboration sessions."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set

from aetheros_cloud.models import CollaborationSession, generate_id, now

logger = logging.getLogger(__name__)


class PresenceManager:
    """Real-time presence and collaboration session management.

    Tracks who is viewing/editing what, with shared cursor positions.
    """

    def __init__(self):
        self._sessions: Dict[str, CollaborationSession] = {}
        self._online_users: Dict[str, float] = {}  # user_id -> last_seen
        self._on_presence: List[Callable] = []
        self._cleanup_task: Optional[asyncio.Task] = None

    def join_session(self, workspace_id: str, user_id: str,
                     entity_type: str = "", entity_id: str = "") -> CollaborationSession:
        session_id = f"{workspace_id}:{entity_type}:{entity_id}"
        session = self._sessions.get(session_id)
        if session is None:
            session = CollaborationSession(
                id=session_id,
                workspace_id=workspace_id,
                entity_type=entity_type,
                entity_id=entity_id,
                created_at=now(),
            )
            self._sessions[session_id] = session
        if user_id not in session.participants:
            session.participants.append(user_id)
        session.is_live = True
        self._online_users[user_id] = now()
        self._broadcast("presence.join", {"session_id": session_id, "user_id": user_id})
        return session

    def leave_session(self, session_id: str, user_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        session.participants = [p for p in session.participants if p != user_id]
        session.cursors.pop(user_id, None)
        if not session.participants:
            session.is_live = False
        self._broadcast("presence.leave", {"session_id": session_id, "user_id": user_id})
        return True

    def update_cursor(self, session_id: str, user_id: str,
                      position: Dict[str, Any]) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        session.cursors[user_id] = {**position, "updated_at": now()}
        self._online_users[user_id] = now()
        self._broadcast("cursor.move", {
            "session_id": session_id, "user_id": user_id, "position": position,
        })
        return True

    def get_session(self, session_id: str) -> Optional[CollaborationSession]:
        return self._sessions.get(session_id)

    def get_active_sessions(self, workspace_id: Optional[str] = None) -> List[CollaborationSession]:
        if workspace_id:
            return [s for s in self._sessions.values()
                    if s.workspace_id == workspace_id and s.is_live]
        return [s for s in self._sessions.values() if s.is_live]

    def get_online_users(self, workspace_id: Optional[str] = None) -> List[str]:
        cutoff = now() - 60
        if workspace_id:
            users: Set[str] = set()
            for s in self._sessions.values():
                if s.workspace_id == workspace_id and s.is_live:
                    users.update(s.participants)
            return [u for u in users if self._online_users.get(u, 0) > cutoff]
        return [u for u, t in self._online_users.items() if t > cutoff]

    def is_user_online(self, user_id: str) -> bool:
        return self._online_users.get(user_id, 0) > now() - 60

    def on_presence(self, callback: Callable):
        self._on_presence.append(callback)

    def _broadcast(self, event: str, data: dict):
        for cb in self._on_presence:
            try:
                cb(event, data)
            except Exception as e:
                logger.debug("Presence callback error: %s", e)

    def start_cleanup(self, interval: int = 30):
        if self._cleanup_task:
            return
        async def _cleanup():
            while True:
                await asyncio.sleep(interval)
                cutoff = now() - 120
                stale = [sid for sid, s in self._sessions.items()
                         if not s.participants and s.created_at < cutoff]
                for sid in stale:
                    del self._sessions[sid]
        self._cleanup_task = asyncio.create_task(_cleanup())

    def stop_cleanup(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
