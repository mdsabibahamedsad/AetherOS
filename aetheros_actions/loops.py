"""Loop detection for computer-use runs (Step 20).

Detects repeated actions, repeated failed actions, same-coordinate repeats,
and A↔B oscillation. When a loop is detected the run must stop safely
instead of hammering the same target.

The detector is a sliding window over per-action fingerprints. It is
thread-safe and side-effect free.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from aetheros_actions.model import Action


@dataclass
class LoopInfo:
    """Why a run was flagged as a loop."""

    kind: str  # "repeat" | "oscillation" | "repeated_failure"
    signature: str = ""
    count: int = 0
    window_size: int = 0
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "signature": self.signature,
            "count": self.count,
            "window": self.window_size,
            "detail": self.detail,
        }


def action_signature(action: Action) -> str:
    """Stable fingerprint for an action, ignoring indices/ids.

    Includes the action type, target, and the mutation-relevant parameters
    (text, url, key, value, direction, app). Coordinates are included when
    present (repeated same-coordinate clicks are a classic loop symptom).
    """
    params = action.parameters or {}
    keep = {k: params[k] for k in ("text", "url", "key", "value", "direction",
                                   "app", "button", "modifiers") if k in params}
    coord = params.get("coordinate")
    if isinstance(coord, (list, tuple)) and len(coord) >= 2:
        keep["coordinate"] = list(coord)
    return f"{action.action_type.value}:{action.target or ''}:{sorted(keep.items())}"


class LoopDetector:
    """Sliding-window loop detector.

    Parameters:
      window_size — number of recent actions examined (default 8).
      repeat_threshold — minimum repeat count that flags a loop (default 3).
      failure_threshold — min consecutive failures that flag a loop.
    """

    def __init__(
        self,
        window_size: int = 8,
        repeat_threshold: int = 3,
        failure_threshold: int = 3,
    ) -> None:
        self.window_size = max(2, int(window_size))
        self.repeat_threshold = max(2, int(repeat_threshold))
        self.failure_threshold = max(2, int(failure_threshold))
        self._lock = threading.RLock()
        self._window: List[Action] = []
        self._failures: List[Action] = []

    # ── recording ────────────────────────────────────────────────────

    def record(self, action: Action, *, failed: bool = False) -> None:
        with self._lock:
            sig = action_signature(action)
            self._window.append(action)
            if len(self._window) > self.window_size:
                self._window = self._window[-self.window_size:]
            if failed:
                self._failures.append(action)
                if len(self._failures) > self.window_size:
                    self._failures = self._failures[-self.window_size:]

    # ── detection ────────────────────────────────────────────────────

    def detect(self) -> Optional[LoopInfo]:
        with self._lock:
            return self._detect_locked()

    def _detect_locked(self) -> Optional[LoopInfo]:
        # Repeated failures.
        if len(self._failures) >= self.failure_threshold:
            return LoopInfo(
                kind="repeated_failure",
                count=len(self._failures),
                window_size=len(self._failures),
                detail=f"{len(self._failures)} consecutive failed actions",
            )
        if not self._window:
            return None
        window = self._window
        sigs = [action_signature(a) for a in window]
        # Oscillation takes precedence over plain repeats: A→B→A→B alternation
        # must be reported as "oscillation", not as a repeat of the last step.
        if len(sigs) >= 4:
            tail = sigs[-(self.window_size):]
            a, b = tail[-2:] if len(tail) >= 2 else ("", "")
            if a and b and a != b:
                alternating = all(tail[i] == (a if i % 2 == 0 else b) for i in range(len(tail)))
                if alternating and tail.count(a) >= 3:
                    return LoopInfo(
                        kind="oscillation",
                        signature=f"{a} <-> {b}",
                        count=len(tail),
                        window_size=len(tail),
                        detail="A/B alternation detected (agent oscillation)",
                    )
        # Same signature repeated within window.
        counts: Dict[str, int] = {}
        last_sig = sigs[-1]
        for sig in sigs:
            counts[sig] = counts.get(sig, 0) + 1
        if counts.get(last_sig, 0) >= self.repeat_threshold:
            return LoopInfo(
                kind="repeat",
                signature=last_sig,
                count=counts[last_sig],
                window_size=len(window),
                detail=f"same action performed {counts[last_sig]}x in last {len(window)} steps",
            )
        return None

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            return {
                "window_size": len(self._window),
                "failures": len(self._failures),
            }