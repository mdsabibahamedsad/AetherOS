"""AetherOS Computer-Use — unified orchestration layer.

This package coordinates the existing production engines (browser, desktop /
computer-use, vision/OCR, permissions, approval, audit) into a single safe
action pipeline:

    OBSERVE → PLAN → AUTHORIZE → EXECUTE → VERIFY → RECOVER → REPORT

It does NOT re-implement browser or desktop control. Browser actions delegate
to :mod:`tools.browser_tool`; desktop actions delegate to
:mod:`tools.computer_use`; observation delegates to :mod:`aetheros_vision`.

Security model
--------------
* Every action carries an :class:`~aetheros_actions.model.Action` record
  (actionId / agentId / sessionId / actionType / target / parameters /
  riskLevel / permission / reason / timestamp / expectedResult /
  verificationStrategy).
* Every action is classified by risk (LOW..CRITICAL) and evaluated against
  the session's autonomy level before execution (ALLOW / DENY /
  REQUIRE_CONFIRMATION).
* Web and document content is treated as untrusted data; it can never
  escalate its own permissions (see :mod:`aetheros_actions.trust`).
* A strict state machine (IDLE..CANCELLED) bounds every run; loop detection
  and bounded recovery stop runaway sequences.
"""

from __future__ import annotations

from aetheros_actions.model import (
    Action,
    ActionStatus,
    ActionType,
    Element,
    FailureKind,
    Observation,
    Reversibility,
    RiskLevel,
    TrustSource,
    VerificationVerdict,
)
from aetheros_actions.state import ComputerUseState, StateMachine
from aetheros_actions.elements import UIElementDetector
from aetheros_actions.observer import ScreenObserver
from aetheros_actions.planner import ActionPlanner, PlanVerdict
from aetheros_actions.executor import ActionResult, ActionExecutor
from aetheros_actions.verifier import ActionVerifier
from aetheros_actions.recovery import RecoveryManager
from aetheros_actions.loops import LoopDetector, LoopInfo
from aetheros_actions.permissions import PermissionManager, PermissionDecision
from aetheros_actions.session import ComputerUseSession, SessionManager
from aetheros_actions.audit import AuditLogger
from aetheros_actions.manager import ComputerUseManager, get_computer_use_manager
from aetheros_actions.anomaly import AgentQuarantine, AnomalyDetector, AnomalyInfo
from aetheros_actions.blast_radius import BlastRadiusEstimate
from aetheros_actions.dryrun import DryRunImpact, PlanPreview
from aetheros_actions.failure import classify_failure
from aetheros_actions.idempotency import IdempotencyRegistry
from aetheros_actions.intent import IntentCheck, IntentVerifier
from aetheros_actions.lock import ResourceLockManager
from aetheros_actions.receipts import ActionReceipt
from aetheros_actions.reversibility import classify_reversibility

__all__ = [
    "Action",
    "ActionReceipt",
    "ActionStatus",
    "ActionType",
    "ActionResult",
    "ActionExecutor",
    "ActionPlanner",
    "ActionVerifier",
    "AgentQuarantine",
    "AnomalyDetector",
    "AnomalyInfo",
    "AuditLogger",
    "BlastRadiusEstimate",
    "ComputerUseManager",
    "ComputerUseSession",
    "ComputerUseState",
    "DryRunImpact",
    "Element",
    "FailureKind",
    "IdempotencyRegistry",
    "IntentCheck",
    "IntentVerifier",
    "LoopDetector",
    "LoopInfo",
    "Observation",
    "PermissionDecision",
    "PermissionManager",
    "PlanPreview",
    "PlanVerdict",
    "RecoveryManager",
    "ResourceLockManager",
    "Reversibility",
    "RiskLevel",
    "ScreenObserver",
    "SessionManager",
    "StateMachine",
    "TrustSource",
    "UIElementDetector",
    "VerificationVerdict",
    "classify_failure",
    "classify_reversibility",
    "get_computer_use_manager",
]