"""Core data model for the AetherOS Computer-Use action pipeline.

Implements the cross-cutting contracts used by every component:

* :class:`ActionType` — the closed vocabulary of computer-use action kinds
  (CLICK, TYPE, NAVIGATE, UPLOAD, ...).
* :class:`RiskLevel` — LOW..CRITICAL classification attached to every action.
* :class:`TrustSource` — provenance of an instruction/message (Step 45 trust
  boundary). External content (web pages, documents, model output) is never
  treated as authorized instructions.
* :class:`Action` — the full per-action record required by Step 11
  (actionId / agentId / sessionId / actionType / target / parameters /
  riskLevel / permission / reason / timestamp / expectedResult /
  verificationStrategy).
* :class:`Element` — a semantic UI target (accessibility-first).
* :class:`Observation` — structured environment snapshot fed to the model.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


def _new_id() -> str:
    return uuid.uuid4().hex


class ActionType(str, Enum):
    """Closed vocabulary of computer-use action kinds (Step 12)."""

    CLICK = "CLICK"
    DOUBLE_CLICK = "DOUBLE_CLICK"
    TYPE = "TYPE"
    KEY_PRESS = "KEY_PRESS"
    SCROLL = "SCROLL"
    MOVE = "MOVE"
    DRAG = "DRAG"
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    NAVIGATE = "NAVIGATE"
    UPLOAD = "UPLOAD"
    DOWNLOAD = "DOWNLOAD"
    COPY = "COPY"
    PASTE = "PASTE"
    SCREENSHOT = "SCREENSHOT"
    WAIT = "WAIT"
    WINDOW_FOCUS = "WINDOW_FOCUS"
    TAB_SWITCH = "TAB_SWITCH"
    APP_LAUNCH = "APP_LAUNCH"
    APP_CLOSE = "APP_CLOSE"
    FILE_OPEN = "FILE_OPEN"
    FILE_SAVE = "FILE_SAVE"


class RiskLevel(str, Enum):
    """Risk classification attached to every action (Step 13)."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def rank(self) -> int:
        order = (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL)
        return order.index(self)

    def __le__(self, other: "RiskLevel") -> bool:
        return self.rank <= other.rank

    def __lt__(self, other: "RiskLevel") -> bool:
        return self.rank < other.rank

    def __ge__(self, other: "RiskLevel") -> bool:
        return self.rank >= other.rank

    def __gt__(self, other: "RiskLevel") -> bool:
        return self.rank > other.rank


class ActionStatus(str, Enum):
    """Lifecycle of a single action."""

    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    DENIED = "DENIED"
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RECOVERING = "RECOVERING"
    CANCELLED = "CANCELLED"


class TrustSource(str, Enum):
    """Provenance of an instruction or payload (Step 45 trust boundary).

    Order matters: lower rank == higher trust. Security policy and direct
    user instructions outrank external content; web content, document
    content and model output are all treated as untrusted data.
    """

    USER_INSTRUCTION = "USER_INSTRUCTION"
    SECURITY_POLICY = "SECURITY_POLICY"
    SYSTEM_INSTRUCTION = "SYSTEM_INSTRUCTION"
    AGENT_PLAN = "AGENT_PLAN"
    TOOL_OUTPUT = "TOOL_OUTPUT"
    WEB_CONTENT = "WEB_CONTENT"
    DOCUMENT_CONTENT = "DOCUMENT_CONTENT"
    MODEL_OUTPUT = "MODEL_OUTPUT"

    @classmethod
    def lowest_trust(cls) -> "TrustSource":
        return cls.MODEL_OUTPUT

    @classmethod
    def is_external(cls, source: "TrustSource") -> bool:
        """True for sources that may embed hostile instructions."""
        return source in (cls.WEB_CONTENT, cls.DOCUMENT_CONTENT, cls.MODEL_OUTPUT)

    def trust_rank(self) -> int:
        return _TRUST_RANK[self.value]

    def outranks(self, other: "TrustSource") -> bool:
        """True when *this* source is more trusted than *other*."""
        return self.trust_rank() < other.trust_rank()


# Module-level mapping (kept out of the class body so the Enum machinery
# cannot absorb it as a member). Higher trust => lower rank.
_TRUST_RANK = {
    TrustSource.USER_INSTRUCTION.value: 0,
    TrustSource.SECURITY_POLICY.value: 1,
    TrustSource.SYSTEM_INSTRUCTION.value: 2,
    TrustSource.AGENT_PLAN.value: 3,
    TrustSource.TOOL_OUTPUT.value: 4,
    TrustSource.WEB_CONTENT.value: 5,
    TrustSource.DOCUMENT_CONTENT.value: 5,
    TrustSource.MODEL_OUTPUT.value: 6,
}


class VerificationVerdict(str, Enum):
    """Result of checking expected state after an action."""

    PASS = "PASS"
    FAIL = "FAIL"
    TIMEOUT = "TIMEOUT"
    NOT_REQUIRED = "NOT_REQUIRED"
    UNKNOWN = "UNKNOWN"


class Reversibility(str, Enum):
    """How recoverable an action is (Step 59). Used by the dry-run preview.

    ``REVERSIBLE`` actions leave no lasting change; ``PARTIALLY_REVERSIBLE``
    change state that can be restored with effort (close/reopen, back-nav);
    ``IRREVERSIBLE`` destroy or push state that cannot be recovered (upload,
    overwrite-save, app exit with unsaved work).
    """

    REVERSIBLE = "REVERSIBLE"
    PARTIALLY_REVERSIBLE = "PARTIALLY_REVERSIBLE"
    IRREVERSIBLE = "IRREVERSIBLE"
    UNKNOWN = "UNKNOWN"

    @property
    def is_irreversible(self) -> bool:
        return self is self.IRREVERSIBLE


class FailureKind(str, Enum):
    """Classification of why an action failed (Step 82)."""

    TRANSIENT = "TRANSIENT"          # retryable: timeout, resource contention
    PERMANENT = "PERMANENT"          # deterministic: bad target, logic error
    VALIDATION = "VALIDATION"        # input/reference rejected before execution
    PERMISSION = "PERMISSION"        # denied by policy / authorization
    UNAVAILABLE = "UNAVAILABLE"      # prerequisite missing (backend, tool, element)
    UNKNOWN = "UNKNOWN"


@dataclass
class Element:
    """A semantic UI target (accessibility-first when possible).

    Prefer ``role`` / ``label`` / ``selector`` / ``index`` targeting over raw
    coordinates. ``bounds`` is used only as a fallback, and is always paired
    with ``confidence`` and bound checks before any click.
    """

    role: str = ""
    label: str = ""
    selector: str = ""  # DOM selector / a11y role+name for browser+desktop
    index: Optional[int] = None  # SOM/AX 1-based index from a prior capture
    bounds: Tuple[int, int, int, int] = (0, 0, 0, 0)  # x, y, w, h
    center: Optional[Tuple[int, int]] = None
    confidence: float = 0.0
    app: str = ""
    source: TrustSource = TrustSource.TOOL_OUTPUT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "label": self.label,
            "selector": self.selector,
            "index": self.index,
            "bounds": list(self.bounds),
            "center": list(self.center) if self.center else None,
            "confidence": self.confidence,
            "app": self.app,
        }


@dataclass
class Observation:
    """Structured snapshot of the environment (Step 3).

    Populated as far as the active adapters support: screen size, active
    window, focused browser tab URL, and a limited set of semantic elements
    / visible text. Never contains cookies, session tokens, or raw secrets.
    """

    timestamp: float = field(default_factory=time.time)
    screen_size: Tuple[int, int] = (0, 0)
    active_window_title: str = ""
    active_app: str = ""
    browser_url: str = ""  # focused tab URL only (never credentials)
    elements: List[Element] = field(default_factory=list)
    visible_text: str = ""  # bounded text preview
    mode: str = "desktop"  # desktop | browser
    source: TrustSource = TrustSource.TOOL_OUTPUT

    def summarize(self) -> Dict[str, Any]:
        return {
            "screen_size": list(self.screen_size),
            "active_window": self.active_window_title,
            "active_app": self.active_app,
            "browser_url": self.browser_url,
            "mode": self.mode,
            "element_count": len(self.elements),
            "visible_text_snippet": self.visible_text[:500],
        }


@dataclass
class Action:
    """Full per-action record (Step 11). Every field is required at dispatch."""

    action_type: ActionType
    target: str = ""  # semantic target: element label/ref, URL, path, app name
    parameters: Dict[str, Any] = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW
    permission: str = ""  # named permission governing this action
    reason: str = ""
    expected_result: Dict[str, Any] = field(default_factory=dict)
    verification_strategy: str = ""  # "" | "element" | "url" | "text" | "file" | "none"
    action_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    session_id: str = ""
    source: TrustSource = TrustSource.AGENT_PLAN
    timestamp: float = field(default_factory=time.time)
    status: ActionStatus = ActionStatus.PENDING
    # Step 59/60/61/63: reversibility, dry-run preview, idempotency, trace.
    reversibility: Reversibility = Reversibility.UNKNOWN
    dry_run: bool = False            # plan/preview only — never execute
    idempotency_key: str = ""        # dedup key for retry-safe pipelines
    trace_id: str = ""               # correlation id across plan/run/receipts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actionId": self.action_id,
            "agentId": self.agent_id,
            "sessionId": self.session_id,
            "actionType": self.action_type.value,
            "target": self.target,
            "parameters": self.parameters,
            "riskLevel": self.risk_level.value,
            "permission": self.permission,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "expectedResult": self.expected_result,
            "verificationStrategy": self.verification_strategy,
            "source": self.source.value,
            "status": self.status.value,
            "reversibility": self.reversibility.value,
            "dryRun": self.dry_run,
            "idempotencyKey": self.idempotency_key,
            "traceId": self.trace_id,
        }