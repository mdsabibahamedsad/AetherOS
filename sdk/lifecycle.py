"""
Plugin Lifecycle State Machine
===============================

Manages the lifecycle of plugins through well-defined states:

    INSTALLED → DISABLED → ENABLED → RUNNING
                  ↓           ↓
               UNINSTALLED  ERROR

Transitions are validated, audited, and reversible where possible
(ENABLED → DISABLED, DISABLED → INSTALLED for rollback).
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class LifecycleState(enum.Enum):
    """Valid states in the plugin lifecycle."""

    # Initial state after install — plugin is on disk but not active
    INSTALLED = "installed"
    # Disabled by user or policy — not loaded at startup
    DISABLED = "disabled"
    # Enabled and loaded — plugin is active
    ENABLED = "enabled"
    # Plugin is actively executing (tools, hooks, etc.)
    RUNNING = "running"
    # Plugin encountered a fatal error
    ERROR = "error"
    # Plugin has been removed from disk
    UNINSTALLED = "uninstalled"


# Valid transitions: source state -> allowed target states
_ALLOWED_TRANSITIONS: Dict[LifecycleState, Set[LifecycleState]] = {
    LifecycleState.INSTALLED: {LifecycleState.DISABLED, LifecycleState.ENABLED, LifecycleState.UNINSTALLED},
    LifecycleState.DISABLED: {LifecycleState.ENABLED, LifecycleState.INSTALLED, LifecycleState.UNINSTALLED},
    LifecycleState.ENABLED: {LifecycleState.DISABLED, LifecycleState.RUNNING, LifecycleState.ERROR},
    LifecycleState.RUNNING: {LifecycleState.ENABLED, LifecycleState.ERROR},
    LifecycleState.ERROR: {LifecycleState.DISABLED, LifecycleState.ENABLED},
    LifecycleState.UNINSTALLED: set(),
}


@dataclass
class StateTransition:
    """Record of a single state transition."""
    from_state: LifecycleState
    to_state: LifecycleState
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reason: str = ""
    actor: str = ""


class PluginLifecycle:
    """Lifecycle manager for a single plugin.

    Tracks state, validates transitions, fires callbacks, and maintains
    an audit trail.

    Usage::

        lifecycle = PluginLifecycle("my-plugin")
        lifecycle.on_transition(LifecycleState.INSTALLED, LifecycleState.ENABLED, my_enable_cb)
        lifecycle.transition_to(LifecycleState.ENABLED, reason="user requested")
    """

    def __init__(self, plugin_name: str) -> None:
        self._plugin_name = plugin_name
        self._state: LifecycleState = LifecycleState.INSTALLED
        self._transitions: List[StateTransition] = []
        self._callbacks: Dict[tuple, List[Callable]] = {}
        self._health_status: Dict[str, Any] = {}

    # -- State queries -------------------------------------------------------

    @property
    def state(self) -> LifecycleState:
        """Current lifecycle state."""
        return self._state

    @property
    def is_installed(self) -> bool:
        return self._state == LifecycleState.INSTALLED

    @property
    def is_enabled(self) -> bool:
        return self._state == LifecycleState.ENABLED

    @property
    def is_running(self) -> bool:
        return self._state == LifecycleState.RUNNING

    @property
    def is_disabled(self) -> bool:
        return self._state == LifecycleState.DISABLED

    @property
    def is_error(self) -> bool:
        return self._state == LifecycleState.ERROR

    # -- State transitions ---------------------------------------------------

    def transition_to(
        self,
        target: LifecycleState,
        reason: str = "",
        actor: str = "system",
    ) -> None:
        """Attempt a state transition.

        Raises ``ValueError`` if the transition is not allowed.

        Fires registered callbacks for ``(from_state, to_state)``.
        """
        if target == self._state:
            return  # idempotent — already at the target state

        allowed = _ALLOWED_TRANSITIONS.get(self._state, set())
        if target not in allowed:
            raise ValueError(
                f"Plugin '{self._plugin_name}': invalid transition "
                f"{self._state.value} → {target.value}. "
                f"Allowed from {self._state.value}: "
                f"{', '.join(s.value for s in allowed) or '(none)'}"
            )

        transition = StateTransition(
            from_state=self._state,
            to_state=target,
            reason=reason,
            actor=actor,
        )
        self._transitions.append(transition)
        old_state = self._state
        self._state = target

        # Fire callbacks
        callbacks = self._callbacks.get((old_state, target), [])
        for cb in callbacks:
            try:
                cb(old_state, target, reason, actor)
            except Exception as exc:
                logger.warning(
                    "Lifecycle callback for %s → %s on plugin '%s' raised: %s",
                    old_state.value, target.value, self._plugin_name, exc,
                )

        logger.info(
            "Plugin '%s': %s → %s (by %s: %s)",
            self._plugin_name, old_state.value, target.value, actor, reason,
        )

    def can_transition_to(self, target: LifecycleState) -> bool:
        """Check whether a transition to *target* is allowed."""
        return target in _ALLOWED_TRANSITIONS.get(self._state, set())

    # -- Callbacks ------------------------------------------------------------

    def on_transition(
        self,
        from_state: LifecycleState,
        to_state: LifecycleState,
        callback: Callable,
    ) -> None:
        """Register a callback for a specific transition.

        The callback receives ``(from_state, to_state, reason, actor)``.
        """
        self._callbacks.setdefault((from_state, to_state), []).append(callback)

    # -- Audit trail ----------------------------------------------------------

    def get_transition_history(self) -> List[StateTransition]:
        """Return the full audit trail of state transitions."""
        return list(self._transitions)

    def get_last_transition(self) -> Optional[StateTransition]:
        """Return the most recent transition, or None."""
        return self._transitions[-1] if self._transitions else None

    # -- Health ---------------------------------------------------------------

    def report_health(self, status: str, **details) -> None:
        """Report a health check result.

        *status* should be ``"ok"``, ``"degraded"``, or ``"down"``.
        """
        self._health_status = {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            **details,
        }

    def get_health(self) -> Dict[str, Any]:
        """Return the last health report."""
        return dict(self._health_status)

    # -- Convenience helpers --------------------------------------------------

    def enable(self, reason: str = "user requested", actor: str = "user") -> None:
        """Convenience: transition to ENABLED from INSTALLED or DISABLED."""
        self.transition_to(LifecycleState.ENABLED, reason=reason, actor=actor)

    def disable(self, reason: str = "user requested", actor: str = "user") -> None:
        """Convenience: transition to DISABLED from ENABLED or ERROR."""
        self.transition_to(LifecycleState.DISABLED, reason=reason, actor=actor)

    def mark_error(self, reason: str = "", actor: str = "system") -> None:
        """Convenience: transition to ERROR from any running state."""
        self.transition_to(LifecycleState.ERROR, reason=reason, actor=actor)

    def uninstall(self, reason: str = "", actor: str = "user") -> None:
        """Convenience: transition to UNINSTALLED."""
        self.transition_to(LifecycleState.UNINSTALLED, reason=reason, actor=actor)

    def rollback(self) -> bool:
        """Attempt to roll back to the previous state.

        Returns True if rollback succeeded, False if there's no prior state
        or no legal path back to it exists.

        The direct reverse edge may not be in ``_ALLOWED_TRANSITIONS``
        (e.g. ``ENABLED → INSTALLED`` is not a legal one-hop transition;
        rollback must route ``ENABLED → DISABLED → INSTALLED``).  We BFS
        through the allowed-transition graph to find a legal path back to
        the previous state and walk it.

        Note: rollback steps are themselves recorded in the audit trail, so
        a second consecutive ``rollback()`` targets the *last rollback hop*
        (e.g. ``DISABLED``) rather than the state before the original
        transition.
        """
        if len(self._transitions) < 1:
            return False
        last = self._transitions[-1]
        target = last.from_state
        path = _find_transition_path(self._state, target)
        if path is None:
            return False
        # Every step in *path* is a legal edge by construction (BFS over
        # _ALLOWED_TRANSITIONS), so transition_to() cannot raise ValueError.
        for step in path:
            self.transition_to(
                step,
                reason=f"rollback to {target.value}",
                actor="system",
            )
        return True


def _find_transition_path(
    start: LifecycleState, goal: LifecycleState
) -> Optional[List[LifecycleState]]:
    """Return a legal transition path from *start* to *goal*, or None.

    BFS over ``_ALLOWED_TRANSITIONS``.  The returned list is the sequence
    of intermediate states to pass through, excluding *start* itself and
    including *goal*.  ``[]`` is returned when ``start == goal``.
    """
    if start == goal:
        return []
    from collections import deque

    queue: deque = deque([(start, [])])
    seen = {start}
    while queue:
        current, path = queue.popleft()
        for nxt in sorted(
            _ALLOWED_TRANSITIONS.get(current, set()),
            key=lambda s: s.value,  # plain Enum members have no __lt__
        ):
            if nxt in seen:
                continue
            next_path = path + [nxt]
            if nxt == goal:
                return next_path
            seen.add(nxt)
            queue.append((nxt, next_path))
    return None


# ---------------------------------------------------------------------------
# Global lifecycle registry
# ---------------------------------------------------------------------------

_lifecycle_registry: Dict[str, PluginLifecycle] = {}


def get_lifecycle(plugin_name: str) -> PluginLifecycle:
    """Return (or create) the lifecycle manager for a plugin."""
    if plugin_name not in _lifecycle_registry:
        _lifecycle_registry[plugin_name] = PluginLifecycle(plugin_name)
    return _lifecycle_registry[plugin_name]


def list_lifecycles() -> Dict[str, PluginLifecycle]:
    """Return all registered lifecycle managers."""
    return dict(_lifecycle_registry)
