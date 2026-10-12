"""Blast-radius estimation for computer-use actions (Step 73).

Estimates the reach of an action in terms of what could be affected:
a single window, a whole app, the workspace, the system, or external
(outbound) state. Pure — reads only the action record. Used by the dry-run
preview and the anomaly/approval surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_actions.model import Action, ActionType

# Scopes, coarsest reach last (used for ordering).
SINGLE_WINDOW = "single_window"
SINGLE_APP = "single_app"
WORKSPACE = "workspace"
SYSTEM = "system"
EXTERNAL = "external"


@dataclass
class BlastRadiusEstimate:
    """How far an action's effects reach."""

    scope: str = SINGLE_WINDOW
    affected_count: int = 1
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scope": self.scope,
            "affected_count": self.affected_count,
            "description": self.description,
        }


# action type → (scope, affected_count, description).
_RADIUS_TABLE: Dict[ActionType, tuple] = {
    ActionType.CLICK: (SINGLE_WINDOW, 1, "one element in the focused window"),
    ActionType.DOUBLE_CLICK: (SINGLE_WINDOW, 1, "one element in the focused window"),
    ActionType.TYPE: (SINGLE_WINDOW, 1, "one focused input"),
    ActionType.KEY_PRESS: (SINGLE_WINDOW, 1, "one focused input"),
    ActionType.SCROLL: (SINGLE_WINDOW, 1, "the focused viewport"),
    ActionType.MOVE: (SINGLE_WINDOW, 1, "the pointer (no click)"),
    ActionType.DRAG: (SINGLE_WINDOW, 1, "dragged content"),
    ActionType.OPEN: (SINGLE_APP, 1, "the opened document/URL"),
    ActionType.FILE_OPEN: (SINGLE_APP, 1, "the opened file"),
    ActionType.NAVIGATE: (SINGLE_APP, 1, "the focused browser tab"),
    ActionType.TAB_SWITCH: (SINGLE_APP, 1, "the focused browser window"),
    ActionType.WINDOW_FOCUS: (SINGLE_APP, 1, "one window"),
    ActionType.COPY: (SINGLE_WINDOW, 1, "the clipboard (write)"),
    ActionType.PASTE: (SINGLE_WINDOW, 1, "the focused input"),
    ActionType.SCREENSHOT: (SINGLE_WINDOW, 1, "captured pixels (no state change)"),
    ActionType.WAIT: (SINGLE_WINDOW, 0, "no state change"),
    ActionType.APP_LAUNCH: (SINGLE_APP, 1, "a new app process"),
    ActionType.CLOSE: (SINGLE_WINDOW, 1, "one window/tab"),
    ActionType.APP_CLOSE: (SINGLE_APP, 1, "an app and its windows"),
    ActionType.DOWNLOAD: (WORKSPACE, 1, "a file on the local filesystem"),
    ActionType.FILE_SAVE: (WORKSPACE, 1, "a file on the local filesystem"),
    ActionType.UPLOAD: (EXTERNAL, 1, "bytes transmitted outside the machine"),
}


def estimate_blast_radius(action: Action) -> BlastRadiusEstimate:
    """Estimate the reach of a single action."""
    entry = _RADIUS_TABLE.get(action.action_type)
    if entry is None:
        return BlastRadiusEstimate(scope=SYSTEM, affected_count=1,
                                   description="unknown action kind — assume worst reach")
    scope, count, description = entry
    return BlastRadiusEstimate(scope=scope, affected_count=count,
                               description=description)


def plan_blast_radius(actions: List[Action]) -> BlastRadiusEstimate:
    """Aggregate the reach of a whole plan (worst scope wins)."""
    order = [SINGLE_WINDOW, SINGLE_APP, WORKSPACE, SYSTEM, EXTERNAL]
    if not actions:
        return BlastRadiusEstimate(scope=SINGLE_WINDOW, affected_count=0,
                                   description="empty plan — no state touched")
    worst = max((estimate_blast_radius(a) for a in actions),
                key=lambda r: order.index(r.scope))
    affected = sum(estimate_blast_radius(a).affected_count for a in actions)
    return BlastRadiusEstimate(
        scope=worst.scope,
        affected_count=affected,
        description=(
            f"{len(actions)} step(s); worst reach: {worst.scope} "
            f"({worst.description})"
        ),
    )