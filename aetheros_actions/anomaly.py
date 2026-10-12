"""Anomaly detection + agent quarantine (Steps 71-72).

Detects behavioural anomalies in a stream of actions — mass modification,
repeated destructive actions, unexpected app launches, rapid repeated
clicks, screenshot bursts — and, when a run exceeds a threshold, quarantines
the responsible agent (revokes its computer-use capabilities and preserves
evidence). Pure heuristics over the recorded action stream; no execution.

The manager wires the detector behind anomaly detection defaults so an agent
that starts thrashing a machine is stopped and isolated rather than allowed
to continue.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_actions.model import Action, ActionType

# Destructive action kinds that matter for "repeated destructive" detection.
_DESTRUCTIVE_KINDS = frozenset({
    ActionType.CLOSE, ActionType.APP_CLOSE, ActionType.UPLOAD,
    ActionType.DOWNLOAD, ActionType.FILE_SAVE,
})


@dataclass
class AnomalyInfo:
    """One detected anomaly."""

    kind: str                  # mass_modification | repeated_destructive | ...
    agent_id: str = ""
    detail: str = ""
    threshold: int = 0
    observed: int = 0
    window: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "agent_id": self.agent_id,
            "detail": self.detail,
            "threshold": self.threshold,
            "observed": self.observed,
            "window": self.window,
        }


# Revoked capability groups when an agent is quarantined.
QUARANTINE_REVOKES = (
    "computer_control",   # the whole computer-use surface
    "mouse",              # pointer control
    "keyboard",           # keyboard control
    "clipboard_write",    # writing the clipboard
    "app_launch",         # launching/closing apps
)


class AnomalyDetector:
    """Sliding-window heuristics over a per-run action stream."""

    def __init__(
        self,
        *,
        mass_modification_threshold: int = 5,
        repeated_destructive_threshold: int = 3,
        unexpected_launch_window: float = 5.0,
        unexpected_launch_threshold: int = 2,
        rapid_click_window: float = 3.0,
        rapid_click_threshold: int = 8,
        screenshot_burst_window: float = 5.0,
        screenshot_burst_threshold: int = 6,
        now: Optional[float] = None,
    ) -> None:
        self.mass_modification_threshold = mass_modification_threshold
        self.repeated_destructive_threshold = repeated_destructive_threshold
        self.unexpected_launch_window = unexpected_launch_window
        self.unexpected_launch_threshold = unexpected_launch_threshold
        self.rapid_click_window = rapid_click_window
        self.rapid_click_threshold = rapid_click_threshold
        self.screenshot_burst_window = screenshot_burst_window
        self.screenshot_burst_threshold = screenshot_burst_threshold
        self._now = now or time.time
        self._mutating: List[float] = []
        self._destructive: List[Action] = []
        self._launches: List[float] = []
        self._clicks: List[float] = []
        self._screenshots: List[float] = []

    # ── recording ────────────────────────────────────────────────────

    def record(self, action: Action, timestamp: Optional[float] = None) -> None:
        """Record an action; returns nothing (call ``detect()`` after)."""
        ts = timestamp if timestamp is not None else self._now()
        if action.risk_level.rank > 0 or action.action_type in _DESTRUCTIVE_KINDS:
            self._mutating.append(ts)
        if action.action_type in _DESTRUCTIVE_KINDS:
            self._destructive.append(action)
        if action.action_type is ActionType.APP_LAUNCH:
            self._launches.append(ts)
        if action.action_type is ActionType.CLICK:
            self._clicks.append(ts)
        if action.action_type is ActionType.SCREENSHOT:
            self._screenshots.append(ts)

    # ── detection ────────────────────────────────────────────────────

    def detect(self, agent_id: str = "") -> Optional[AnomalyInfo]:
        """Return the first anomaly that exceeds a threshold, else None."""
        now = self._now()
        self._prune(now)

        if len(self._destructive) >= self.repeated_destructive_threshold:
            last = self._destructive[-1]
            return AnomalyInfo(
                kind="repeated_destructive", agent_id=agent_id,
                detail=(f"{last.action_type.value} repeated "
                        f"{len(self._destructive)} times"),
                threshold=self.repeated_destructive_threshold,
                observed=len(self._destructive),
            )

        if len(self._mutating) >= self.mass_modification_threshold:
            return AnomalyInfo(
                kind="mass_modification", agent_id=agent_id,
                detail=f"{len(self._mutating)} mutating actions in the run",
                threshold=self.mass_modification_threshold,
                observed=len(self._mutating),
            )

        if len(self._launches) >= self.unexpected_launch_threshold:
            return AnomalyInfo(
                kind="unexpected_app_launch", agent_id=agent_id,
                detail=(f"{len(self._launches)} app launches within "
                        f"{self.unexpected_launch_window:.0f}s"),
                threshold=self.unexpected_launch_threshold,
                observed=len(self._launches),
                window=self.unexpected_launch_window,
            )

        if len(self._clicks) >= self.rapid_click_threshold:
            return AnomalyInfo(
                kind="rapid_clicks", agent_id=agent_id,
                detail=f"{len(self._clicks)} clicks within {self.rapid_click_window:.0f}s",
                threshold=self.rapid_click_threshold,
                observed=len(self._clicks),
                window=self.rapid_click_window,
            )

        if len(self._screenshots) >= self.screenshot_burst_threshold:
            return AnomalyInfo(
                kind="screenshot_burst", agent_id=agent_id,
                detail=f"{len(self._screenshots)} screenshots within {self.screenshot_burst_window:.0f}s",
                threshold=self.screenshot_burst_threshold,
                observed=len(self._screenshots),
                window=self.screenshot_burst_window,
            )

        return None

    def _prune(self, now: float) -> None:
        self._launches = [t for t in self._launches if now - t <= self.unexpected_launch_window]
        self._clicks = [t for t in self._clicks if now - t <= self.rapid_click_window]
        self._screenshots = [t for t in self._screenshots
                             if now - t <= self.screenshot_burst_window]

    def reset(self) -> None:
        self._mutating.clear()
        self._destructive.clear()
        self._launches.clear()
        self._clicks.clear()
        self._screenshots.clear()


class AgentQuarantine:
    """Tracks quarantined agents and the capabilities revoked from them.

    Quarantine is revocable: ``unquarantine`` restores the agent. Evidence
    (the anomaly that triggered it) is preserved on the record.
    """

    def __init__(self) -> None:
        self._quarantined: Dict[str, Dict[str, Any]] = {}

    def quarantine_agent(
        self,
        agent_id: str,
        reason: str,
        *,
        evidence: Optional[List[Dict[str, Any]]] = None,
        revokes: tuple = QUARANTINE_REVOKES,
    ) -> None:
        self._quarantined[agent_id] = {
            "reason": reason,
            "revokes": list(revokes),
            "evidence": list(evidence or []),
        }

    def is_quarantined(self, agent_id: str) -> bool:
        return agent_id in self._quarantined

    def revocations(self, agent_id: str) -> List[str]:
        rec = self._quarantined.get(agent_id)
        return list(rec["revokes"]) if rec else []

    def evidence(self, agent_id: str) -> List[Dict[str, Any]]:
        rec = self._quarantined.get(agent_id)
        return list(rec.get("evidence", [])) if rec else []

    def unquarantine(self, agent_id: str) -> bool:
        return self._quarantined.pop(agent_id, None) is not None

    def reset(self) -> None:
        self._quarantined.clear()