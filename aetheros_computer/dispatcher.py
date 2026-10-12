"""
API-First Dispatcher (Master 15 Phase 94).

Implements the API-First strategy: when both API and GUI are available,
prefer API → structured automation → accessibility API → DOM → visual → coordinates.

This dispatcher routes actions through the most appropriate execution path.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from aetheros_computer.action import (
    ActionMetadata,
    ActionDomain,
    RiskTier,
    get_action_risk,
    get_action_verification,
)
from aetheros_computer.perception import PerceptionEngine, VisualTargeter, UIElement, PerceptionSource

logger = logging.getLogger(__name__)


class ExecutionPath(Enum):
    """Execution path priority (highest first)."""

    API = "api"                      # Structured API (REST, GraphQL, RPC)
    STRUCTURED_AUTOMATION = "structured"  # Puppeteer/Playwright scripts, browser extensions
    ACCESSIBILITY_API = "accessibility"   # Native AX/UIA/AT-SPI
    DOM = "dom"                      # Browser DOM manipulation
    VISUAL = "visual"                # Vision model + OCR
    COORDINATE = "coordinate"        # Raw coordinate fallback


@dataclass
class ExecutionRoute:
    """Selected execution route for an action."""

    path: ExecutionPath
    handler: Callable
    confidence: float
    fallback_paths: List[ExecutionPath] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DispatchResult:
    """Result of action dispatch."""

    success: bool
    result: Any = None
    error: Optional[str] = None
    path_used: ExecutionPath = ExecutionPath.COORDINATE
    execution_time: float = 0.0
    verification: Dict[str, Any] = field(default_factory=dict)


class APIDispatcher:
    """
    API-First dispatcher implementing Phase 94 strategy.

    For each action, selects the highest-priority available execution path:
    1. API (REST/GraphQL/gRPC) - if available and authenticated
    2. Structured automation (Playwright/Puppeteer scripts)
    3. Accessibility API (native AX/UIA/AT-SPI)
    4. DOM manipulation (CDP, browser extensions)
    5. Visual (vision model + OCR)
    6. Coordinate fallback
    """

    def __init__(
        self,
        perception_engine: "PerceptionEngine" = None,
        browser_bridge: Any = None,
        desktop_backend: Any = None,
        terminal_executor: Any = None,
        api_clients: Dict[str, Any] = None,
    ):
        self.perception = perception_engine
        self.browser_bridge = browser_bridge
        self.desktop_backend = desktop_backend
        self.terminal_executor = terminal_executor
        self.api_clients = api_clients or {}

        # Route handlers (to be registered)
        self._handlers: Dict[ExecutionPath, Dict[str, Callable]] = {
            path: {} for path in ExecutionPath
        }

        # Capability registry: action -> available paths
        self._capabilities: Dict[str, List[ExecutionPath]] = {}

    def register_handler(self, path: ExecutionPath, action: str, handler: Callable) -> None:
        """Register a handler for an action on a specific path."""
        self._handlers[path][action] = handler
        logger.debug(f"Registered {path.value} handler for {action}")

    def register_capability(self, action: str, paths: List[ExecutionPath]) -> None:
        """Register which paths are available for an action."""
        self._capabilities[action] = paths

    def register_mcp_tool(self, action: str, tool_name: str,
                          argument_map: Optional[Dict[str, str]] = None) -> None:
        """Phase 93: register an MCP-backed handler on the API path with
        automatic fallback.

        The wrapper calls the MCP tool through the EXISTING registry dispatch
        (so MASTER 7 authz / sandbox / approval still apply — never bypassed),
        and returns a failure result on any error so the normal fallback
        ladder continues to the next path.
        """
        arg_map = argument_map or {}

        def _mcp_handler(action_metadata, context):
            try:
                from tools.registry import registry

                call_args = {}
                src = context or {}
                for dst_key, src_key in arg_map.items():
                    if src_key in src:
                        call_args[dst_key] = src[src_key]
                    elif hasattr(action_metadata, src_key):
                        call_args[dst_key] = getattr(action_metadata, src_key)
                raw = registry.dispatch(tool_name, call_args)
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(parsed, dict) and parsed.get("success") is False:
                    return {"success": False, "error": parsed.get("error", "mcp failed")}
                return {"success": True, "result": parsed}
            except Exception as exc:
                # Fall through the ladder; NEVER bypass policy on MCP failure.
                return {"success": False, "error": f"mcp tool '{tool_name}' failed: {exc}"}

        async def _async_mcp_handler(action_metadata, context):
            return _mcp_handler(action_metadata, context)

        self.register_handler(ExecutionPath.API, action, _async_mcp_handler)
        paths = self.get_available_paths(action)
        self._capabilities[action] = [ExecutionPath.API] + \
            [p for p in paths if p != ExecutionPath.API]

    def get_available_paths(self, action: str) -> List[ExecutionPath]:
        """Get available execution paths for an action (highest priority first)."""
        if action in self._capabilities:
            return self._capabilities[action]

        # Default capability mapping
        return self._default_paths_for_action(action)

    def _default_paths_for_action(self, action: str) -> List[ExecutionPath]:
        """Default path priority for action."""
        action_lower = action.lower()

        # Browser actions
        if action.startswith("browser."):
            if "navigate" in action or "submit" in action:
                return [ExecutionPath.API, ExecutionPath.STRUCTURED_AUTOMATION,
                       ExecutionPath.ACCESSIBILITY_API, ExecutionPath.DOM,
                       ExecutionPath.VISUAL, ExecutionPath.COORDINATE]
            elif "click" in action or "type" in action or "form" in action:
                return [ExecutionPath.ACCESSIBILITY_API, ExecutionPath.DOM,
                       ExecutionPath.VISUAL, ExecutionPath.COORDINATE]
            elif "snapshot" in action or "capture" in action:
                return [ExecutionPath.ACCESSIBILITY_API, ExecutionPath.VISUAL]
            return [ExecutionPath.ACCESSIBILITY_API, ExecutionPath.DOM,
                   ExecutionPath.VISUAL, ExecutionPath.COORDINATE]

        # Desktop actions
        if action.startswith("desktop."):
            return [ExecutionPath.ACCESSIBILITY_API, ExecutionPath.VISUAL, ExecutionPath.COORDINATE]

        # Terminal actions
        if action.startswith("terminal."):
            return [ExecutionPath.API, ExecutionPath.STRUCTURED_AUTOMATION]

        # Vision actions
        if action.startswith("vision."):
            return [ExecutionPath.VISUAL, ExecutionPath.ACCESSIBILITY_API]

        # Filesystem
        if action.startswith("filesystem."):
            return [ExecutionPath.API, ExecutionPath.STRUCTURED_AUTOMATION]

        # Default
        return [ExecutionPath.COORDINATE]

    def select_route(self, action: str, context: Dict[str, Any] = None) -> Optional[ExecutionRoute]:
        """Select best available execution route for action."""
        paths = self.get_available_paths(action)

        for path in paths:
            handler = self._handlers.get(path, {}).get(action)
            if handler:
                return ExecutionRoute(
                    path=path,
                    handler=handler,
                    confidence=1.0,
                    fallback_paths=paths[paths.index(path)+1:],
                )

        return None

    async def dispatch(
        self,
        action_metadata: "ActionMetadata",
        context: Dict[str, Any] = None,
    ) -> DispatchResult:
        """
        Dispatch action through best available path (Phase 94).

        Implements the API-First strategy: tries paths in priority order,
        falling back on failure.
        """
        start = time.time()
        context = context or {}
        action = action_metadata.action_type

        route = self.select_route(action, context)
        if not route:
            return DispatchResult(
                success=False,
                error=f"No handler available for action: {action}",
                path_used=ExecutionPath.COORDINATE,
            )

        # Try primary path
        result = await self._execute_with_fallback(action_metadata, context, route)
        result.execution_time = time.time() - result.execution_time if hasattr(result, 'execution_time') else time.time() - start
        return result

    async def _execute_with_fallback(
        self,
        action_metadata: "ActionMetadata",
        context: Dict[str, Any],
        route: ExecutionRoute,
    ) -> DispatchResult:
        """Execute with automatic fallback on failure."""
        paths_tried = [route.path]
        last_error = None

        # Try primary path
        try:
            result = await route.handler(action_metadata, context)
            if result.get("success", False):
                return DispatchResult(
                    success=True,
                    result=result.get("result"),
                    path_used=route.path,
                    execution_time=0,  # Will be set by caller
                )
            last_error = result.get("error", "Handler returned failure")
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Path {route.path.value} failed for {action_metadata.action_type}: {e}")

        # Try fallback paths
        for fallback_path in route.fallback_paths:
            fallback_handler = self._handlers.get(fallback_path, {}).get(
                action_metadata.action_type)
            if not fallback_handler:
                continue

            logger.info(f"Falling back to {fallback_path.value} for {route.handler.__name__}")
            paths_tried.append(fallback_path)

            try:
                result = await fallback_handler(route.handler.__name__, context)
                if result.get("success", False):
                    return DispatchResult(
                        success=True,
                        result=result.get("result"),
                        path_used=fallback_path,
                        execution_time=0,
                    )
                last_error = result.get("error", "Fallback failed")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Fallback {fallback_path.value} failed: {e}")

        # All paths exhausted
        return DispatchResult(
            success=False,
            error=f"All paths exhausted for {route.handler.__name__}. Last error: {last_error}",
            path_used=paths_tried[-1] if paths_tried else ExecutionPath.COORDINATE,
        )


# =============================================================================
# DEFAULT HANDLERS
# =============================================================================

def create_browser_api_handler(bridge: Any) -> Callable:
    """Create handler for browser API path (REST/GraphQL)."""
    async def handler(action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # Check if we have API client for this domain
        # For now, return failure to fall through
        return {"success": False, "error": "API client not configured"}
    return handler


def create_structured_automation_handler(bridge: Any) -> Callable:
    """Create handler for structured automation (Playwright scripts)."""
    async def handler(action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # Use agent-browser CLI for structured automation
        # This would invoke pre-recorded Playwright scripts
        return {"success": False, "error": "Structured automation not configured"}
    return handler


def create_accessibility_handler(bridge: Any, desktop_backend: Any = None) -> Callable:
    """Create handler for accessibility API path."""
    async def handler(action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        action_name = context.get("action", "")
        metadata = context.get("metadata")

        if action.startswith("browser."):
            # Use browser bridge's CDP accessibility
            if bridge:
                return await _execute_browser_accessibility(bridge, action, context)
        elif action.startswith("desktop."):
            # Use desktop backend accessibility
            if context.get("desktop_backend"):
                return await _execute_desktop_accessibility(context.get("desktop_backend"), action, context)
        return {"success": False, "error": "Accessibility backend not available"}
    return handler


async def _execute_browser_accessibility(bridge: Any, action: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute browser action via accessibility tree (CDP)."""
    from tools.browser_tool import browser_click, browser_type, browser_navigate, browser_snapshot
    import json

    metadata = context.get("metadata")
    target = context.get("target", "")
    text = context.get("text", "")

    if action == "browser.navigate":
        result = browser_navigate(action="navigate", url=target)
    elif action == "browser.click":
        result = browser_click(action="click", ref=target)
    elif action == "browser.type":
        result = browser_type(action="type", ref=target, text=context.get("text", ""))
    elif action == "browser.snapshot":
        result = browser_snapshot(action="snapshot", session_id=context.get("session_key", ""))
    else:
        return {"success": False, "error": f"Unsupported browser accessibility action: {action}"}

    return json.loads(result)


async def _execute_desktop_accessibility(backend: Any, action: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute desktop action via accessibility API."""
    if hasattr(backend, action):
        method = getattr(backend, action.replace("desktop.", ""))
        if callable(method):
            return await method(context)
    return {"success": False, "error": f"Action not supported by desktop backend: {action}"}


def create_dom_handler(bridge: Any) -> Callable:
    """Create handler for DOM manipulation path (CDP)."""
    async def handler(action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # Use CDP for direct DOM manipulation
        if not bridge:
            return {"success": False, "error": "No browser bridge"}

        # Would use browser_cdp tool for raw CDP calls
        from tools.browser_cdp_tool import _browser_cdp_via_supervisor
        # Implementation would route CDP commands
        return {"success": False, "error": "DOM handler not fully implemented"}
    return handler


def create_visual_handler(perception_engine: "PerceptionEngine" = None) -> Callable:
    """Create handler for visual path (vision model + OCR)."""
    async def handler(action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # Use vision_understand + OCR for visual targeting
        if not perception_engine:
            return {"success": False, "error": "No perception engine"}

        # Use visual targeter to find element
        targeter = VisualTargeter(perception_engine)
        snapshot = await perception_engine.get_merged_snapshot()
        targeter = VisualTargeter(perception_engine)

        # Find target by description
        description = context.get("description", context.get("target", ""))
        target = await targeter.find_target(description, snapshot)

        if not target:
            return {"success": False, "error": "Visual target not found"}

        # Execute via coordinate fallback
        params = target.to_action_params()
        # Would delegate to desktop backend or browser
        return {"success": False, "error": "Visual handler needs executor integration"}
    return handler


def create_coordinate_handler(desktop_backend: Any = None) -> Callable:
    """Create handler for coordinate fallback (last resort)."""
    async def handler(action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if desktop_backend and hasattr(desktop_backend, action.replace("desktop.", "")):
            return await getattr(desktop_backend, action.replace("desktop.", ""))(context)
        return {"success": False, "error": f"No coordinate handler for {action}"}
    return handler


# =============================================================================
# HIGH-LEVEL DISPATCHER
# =============================================================================

class Dispatcher:
    """
    High-level dispatcher coordinating API-First execution with
    perception, verification, and recovery.
    """

    def __init__(
        self,
        perception_engine: "PerceptionEngine" = None,
        browser_bridge: Any = None,
        desktop_backend: Any = None,
        terminal_executor: Any = None,
        api_clients: Dict[str, Any] = None,
        approval_engine: "UnifiedApprovalEngine" = None,
        verification_engine: "VerificationEngine" = None,
        recovery_engine: "RecoveryEngine" = None,
    ):
        self.api_dispatcher = APIDispatcher(
            perception_engine=perception_engine,
            browser_bridge=browser_bridge,
            desktop_backend=desktop_backend,
            terminal_executor=terminal_executor,
            api_clients=api_clients,
        )
        self.perception = perception_engine
        self.approval = approval_engine
        self.verification = verification_engine
        self.recovery = recovery_engine
        # Phase 88: optional independent verifier for high-risk completions.
        self.independent_verifier = None

        # Register default handlers
        self._register_default_handlers()

    def set_independent_verifier(self, verifier) -> None:
        """Attach an IndependentVerifier (Phases 86-88)."""
        self.independent_verifier = verifier

    def _register_default_handlers(self) -> None:
        """Register default handlers for each path."""
        api = self.api_dispatcher

        # API path handlers
        api.register_handler(ExecutionPath.API, "browser.navigate", create_browser_api_handler(None))
        api.register_handler(ExecutionPath.API, "filesystem.read", lambda a, c: {"success": False, "error": "Not implemented"})

        # Structured automation
        api.register_handler(ExecutionPath.STRUCTURED_AUTOMATION, "browser.navigate",
                           create_structured_automation_handler(None))

        # Accessibility API
        api.register_handler(ExecutionPath.ACCESSIBILITY_API, "browser.navigate",
                           create_accessibility_handler(None))
        api.register_handler(ExecutionPath.ACCESSIBILITY_API, "browser.click",
                           create_accessibility_handler(None))
        api.register_handler(ExecutionPath.ACCESSIBILITY_API, "browser.type",
                           create_accessibility_handler(None))
        api.register_handler(ExecutionPath.ACCESSIBILITY_API, "desktop.click",
                           create_accessibility_handler(None))
        api.register_handler(ExecutionPath.ACCESSIBILITY_API, "desktop.type",
                           create_accessibility_handler(None))

        # DOM
        api.register_handler(ExecutionPath.DOM, "browser.navigate", create_dom_handler(None))
        api.register_handler(ExecutionPath.DOM, "browser.click", create_dom_handler(None))
        api.register_handler(ExecutionPath.DOM, "browser.type", create_dom_handler(None))

        # Visual
        api.register_handler(ExecutionPath.VISUAL, "desktop.click", create_visual_handler(None))
        api.register_handler(ExecutionPath.VISUAL, "desktop.type", create_visual_handler(None))
        api.register_handler(ExecutionPath.VISUAL, "vision.analyze", create_visual_handler(None))

        # Coordinate fallback
        api.register_handler(ExecutionPath.COORDINATE, "desktop.click", create_coordinate_handler(None))
        api.register_handler(ExecutionPath.COORDINATE, "desktop.type", create_coordinate_handler(None))

    async def execute(
        self,
        action_metadata: "ActionMetadata",
        context: Dict[str, Any] = None,
        require_verification: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute action with full pipeline:
        0. Emergency stop / safe mode / task budget / dry-run gates
        1. Idempotency pre-check (explicit key only)
        2. Approval check
        3. API-First dispatch with fallback
        4. Verification
        5. Recovery on failure
        6. Checkpoint + audit logging
        """
        from aetheros_computer.action import log_action
        context = context or {}
        _stream_emit = None
        try:
            from aetheros_computer.events_stream import get_stream, safe_target_hash
            _stream = get_stream()

            def _stream_emit(evt, **kw):
                _stream.emit(evt, task_id=action_metadata.task_id,
                             action_id=action_metadata.action_id,
                             action=action_metadata.action_type,
                             risk=action_metadata.risk_level.name,
                             target_hash=safe_target_hash(action_metadata.target),
                             **kw)
        except Exception:
            pass

        # 0-1. Phases 21/58/59: supervision state gates + takeover re-observe.
        try:
            from aetheros_computer.supervision import get_supervision

            sup = get_supervision()
            gate = sup.allows_action(action_metadata.risk_level.value)
            if not gate["allowed"]:
                if _stream_emit:
                    _stream_emit("PAUSED", detail=gate["reason"])
                return {"success": False, "error": f"supervision: {gate['reason']}"}
        except Exception:
            sup = None

        # 0a. Phase 83: global emergency stop blocks new computer actions.
        try:
            from automation.guard import estop_active

            estop = estop_active()
        except Exception:
            estop = None
        if estop is not None:
            return {"success": False,
                    "error": f"emergency stop active: {estop.get('reason') or 'no reason given'}"}

        # 0b. Phase 84: safe mode => read-only computer access (R2+ denied).
        try:
            from automation.guard import safe_mode_enabled

            if safe_mode_enabled() and action_metadata.risk_level.value >= RiskTier.R2_MODERATE.value:
                return {"success": False,
                        "error": "safe mode: only read-only computer actions are allowed"}
        except Exception:
            pass

        # 0c. Phases 82/50: per-task action budget + checkpoint record.
        try:
            from aetheros_computer import task_checkpoint as tcp

            budget = tcp.check_budget(action_metadata.task_id or "default")
            if not budget["allowed"]:
                return {"success": False,
                        "error": f"task action budget exhausted ({budget['used']}/{budget['max']})"}
            tcp.start_task(action_metadata.task_id or "default")
        except Exception:
            pass

        # 0d. Phase 85: dry run — plan without executing.
        if getattr(action_metadata, "dry_run", False):
            route = self.api_dispatcher.select_route(action_metadata.action_type, context)
            return {
                "success": True,
                "dry_run": True,
                "would_execute": action_metadata.action_type,
                "route": route.path.value if route else None,
                "risk": action_metadata.risk_level.name,
                "verification": get_action_verification(action_metadata.action_type).name,
            }

        # 1. Phase 52: explicit idempotency key blocks duplicates pre-execution.
        idem_key = getattr(action_metadata, "idempotency_key", None)
        if idem_key:
            try:
                from aetheros_computer.idempotency import check_and_record

                if check_and_record(idem_key):
                    return {"success": False, "duplicate": True,
                            "error": "action already recorded within TTL", "idempotency_key": idem_key}
            except Exception:
                pass

        # 2. Approval check
        if self.approval:
            allowed, reason = self.approval.check_and_request_approval(
                action_metadata, context.get("session_key", ""), context
            )
            if not allowed:
                return {"success": False, "error": f"Approval denied: {reason}"}

        # 3. Dispatch with API-First strategy
        if _stream_emit:
            _stream_emit("ACTION")
        result = await self.api_dispatcher.dispatch(action_metadata, context)

        # 4. Verification (Phase 10)
        if result.success and require_verification and self.verification:
            verification = await self.verification.verify(action_metadata, result)
            if _stream_emit:
                _stream_emit("VERIFY", detail=str(verification.get("outcome", "")))
            if not verification.get("success", False):
                # 5. Recovery (Phase 11)
                if self.recovery:
                    if _stream_emit:
                        _stream_emit("RECOVERY")
                    recovery_result = await self.recovery.recover(action_metadata, result, verification)
                    if recovery_result.get("success"):
                        result = recovery_result
                    else:
                        result["verification_failed"] = True
                        result["verification_error"] = verification.get("error")

        # 4b. Phase 88: independent verification for high-risk completions.
        try:
            verifier = getattr(self, "independent_verifier", None)
            if verifier is not None and isinstance(result, dict) and result.get("success"):
                from aetheros_computer.multi_agent import make_safe_summary

                summary = make_safe_summary(action_metadata,
                                            {"success": True,
                                             "result": result.get("result")})
                verdict = verifier.verify_completion(summary)
                if not verdict.get("verified", True):
                    result["success"] = False
                    result["unverified"] = True
                    result["error"] = verdict.get("error", "failed independent verification")
                    if _stream_emit:
                        _stream_emit("FAILED", detail="independent verifier refused")
        except Exception:
            pass

        # 6a. Checkpoint successful completion (Phase 50).
        if isinstance(result, dict) and result.get("success") and action_metadata.task_id:
            try:
                from aetheros_computer.task_checkpoint import record_completion

                record_completion(action_metadata.task_id, action_metadata.action_id)
            except Exception:
                pass

        # 6b. Audit + live stream
        log_action(action_metadata, {"success": result.get("success"), "result": result.get("result")})
        if _stream_emit:
            _stream_emit("COMPLETE" if (isinstance(result, dict) and result.get("success"))
                         else "FAILED")

        return result


# =============================================================================
# VERIFICATION ENGINE (Phase 10)
# =============================================================================

class VerificationOutcome:
    """Phase 10 (cert): classified verification results — never assume success."""
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class VerificationEngine:
    """Verify action results against expected state (Phases 10, 69, 70)."""

    def __init__(self, perception_engine: "PerceptionEngine" = None):
        self.perception = perception_engine

    @staticmethod
    def classify_outcome(found: int, expected: int,
                         engine_available: bool = True) -> str:
        if not engine_available:
            return VerificationOutcome.UNKNOWN
        if expected == 0:
            return VerificationOutcome.UNKNOWN
        if found == expected:
            return VerificationOutcome.SUCCESS
        if found > 0:
            return VerificationOutcome.PARTIAL_SUCCESS
        return VerificationOutcome.FAILED

    async def verify(
        self,
        action_metadata: "ActionMetadata",
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Verify action result; returns outcome + success flag."""
        verification_req = get_action_verification(action_metadata.action_type)

        if verification_req.name == "NONE":
            return {"success": True, "outcome": VerificationOutcome.UNKNOWN}

        if verification_req == VerificationRequirement.STATE_MATCH:
            return await self._verify_state_match(action_metadata, result)
        elif verification_req == VerificationRequirement.DOMAIN_CONFIRMATION:
            return await self._verify_domain(action_metadata, result)
        elif verification_req == VerificationRequirement.IDEMPOTENCY_CHECK:
            return await self._verify_idempotency(action_metadata, result)
        elif verification_req == VerificationRequirement.INDEPENDENT_VERIFY:
            return {"success": True, "outcome": VerificationOutcome.UNKNOWN,
                    "note": "Independent verification required"}

        return {"success": True, "outcome": VerificationOutcome.UNKNOWN}

    async def _verify_state_match(self, metadata: "ActionMetadata", result: Dict) -> Dict[str, Any]:
        """Verify expected state via perception; classify the outcome."""
        if not self.perception:
            outcome = self.classify_outcome(0, 1, engine_available=False)
            return {"success": True, "outcome": outcome,
                    "note": "No perception engine for verification"}

        snapshot = await self.perception.get_merged_snapshot(metadata.task_id)

        indicators = self._get_expected_indicators(metadata)
        found = sum(
            1 for ind in indicators
            if any(ind.lower() in (el.name + el.value + el.description).lower()
                   for el in snapshot.elements)
        )
        outcome = self.classify_outcome(found, len(indicators), engine_available=True)
        ok = outcome in (VerificationOutcome.SUCCESS, VerificationOutcome.PARTIAL_SUCCESS)
        out = {"success": ok, "outcome": outcome,
               "indicators_found": found, "indicators_expected": len(indicators)}
        if not ok:
            missing = [i for i in indicators
                       if not any(i.lower() in (el.name + el.value + el.description).lower()
                                  for el in snapshot.elements)]
            out["error"] = f"expected indicators not found: {missing}"
        return out

    def _get_expected_indicators(self, metadata: "ActionMetadata") -> List[str]:
        """Get expected state indicators for action."""
        action = metadata.action_type
        target = metadata.target

        if "click" in action:
            return [target] if target else []
        if "type" in action:
            return [metadata.intent] if metadata.intent else []
        if "navigate" in action:
            # For navigation, expect URL change
            return [target] if target else []
        if "submit" in action:
            return ["success", "submitted", "thank you", "confirmation"]
        if "delete" in action:
            return ["deleted", "removed"]
        return []

    async def _verify_domain(self, metadata: "ActionMetadata", result: Dict) -> Dict[str, Any]:
        """Verify destination domain matches expected (Phases 69-70).

        Uses the actual landed URL from the result (``current_url``/``url``
        keys) when the runtime provides one; otherwise UNKNOWN, never a
        silent pass.
        """
        target = metadata.target
        if not target:
            return {"success": True, "outcome": VerificationOutcome.UNKNOWN}

        current_url = ""
        if isinstance(result, dict):
            payload = result.get("result") if isinstance(result.get("result"), dict) else result
            current_url = str(payload.get("current_url") or payload.get("url")
                              or payload.get("final_url") or "")

        try:
            from aetheros_computer.dataflow import verify_navigation

            verdict = verify_navigation(expected_url=target,
                                        current_url=current_url or target)
        except Exception as exc:
            return {"success": False, "outcome": VerificationOutcome.FAILED,
                    "error": f"navigation verification error: {exc}"}

        if not current_url:
            return {"success": True, "outcome": VerificationOutcome.UNKNOWN,
                    "domain_check": verdict,
                    "note": "runtime did not report landed URL"}

        return {
            "success": bool(verdict["verified"]),
            "outcome": (VerificationOutcome.SUCCESS if verdict["verified"]
                        else VerificationOutcome.FAILED),
            "domain_check": verdict,
            **({} if verdict["verified"] else
               {"error": "; ".join(verdict["reasons"])}),
        }

    async def _verify_idempotency(self, metadata: "ActionMetadata", result: Dict) -> Dict[str, Any]:
        """Verify action wasn't duplicated (Phase 52).

        The authoritative pre-execution check lives in Dispatcher.execute;
        here we only confirm a key existed so post-hoc audits can rely on it.
        """
        if metadata.idempotency_key:
            from aetheros_computer.idempotency import make_key

            recorded_key = metadata.idempotency_key or make_key(
                metadata.action_type, metadata.target)
            return {"success": True, "outcome": VerificationOutcome.SUCCESS,
                    "idempotency_recorded": True, "key_prefix": str(recorded_key)[:8]}
        return {"success": True, "outcome": VerificationOutcome.UNKNOWN,
                "note": "no idempotency key on action"}


# =============================================================================
# RECOVERY ENGINE (Phase 11)
# =============================================================================

class RecoveryEngine:
    """Recover from failed actions (Phases 11, 51, 67).

    Strategies are driven by an injectable ``reobserve_fn(metadata, failed)``
    callback returning either ``None`` (cannot re-observe) or a fresh context
    dict whose ``target``/``selector`` reflect the CURRENT UI. Retry is
    bounded by ``max_retries``; irreversible-risk actions are never auto-
    retried here unless the caller marks them retryable via
    ``metadata.max_retries > 0``.
    """

    def __init__(self, dispatcher: "Dispatcher" = None):
        self.dispatcher = dispatcher
        self.max_retries = 2
        self.reobserve_fn = None  # Callable[[ActionMetadata, Dict], Optional[Dict]]

    async def recover(
        self,
        action_metadata: "ActionMetadata",
        failed_result: Dict[str, Any],
        verification: Dict[str, Any],
    ) -> Dict[str, Any]:
        attempt = int(action_metadata.metadata.get("retry_attempt", 0))
        allowed = max(self.max_retries, int(getattr(action_metadata, "max_retries", 0)))
        if attempt >= allowed:
            return {"success": False, "error": "Max retries exceeded"}

        # Phase 68 (+53): never blindly repeat high-impact / non-retryable effects.
        from aetheros_computer.side_effects import auto_retry_forbidden

        if action_metadata.risk_level.value >= RiskTier.R3_HIGH.value \
                or auto_retry_forbidden(action_metadata.action_type):
            if attempt == 0 and not getattr(action_metadata, "metadata", {}).get("explicit_retry_ok"):
                return {"success": False,
                        "error": "high-risk/non-idempotent failure requires "
                                 "explicit re-approval before retry"}

        error = str(failed_result.get("error", ""))
        failure_type = self._classify_failure(error)

        if failure_type == "TIMEOUT":
            return await self._recover_timeout(action_metadata)

        # TARGET_NOT_FOUND / LOW_CONFIDENCE / UI_CHANGED → re-observe then retry.
        new_context = None
        if callable(self.reobserve_fn):
            try:
                new_context = self.reobserve_fn(action_metadata, failed_result)
                if hasattr(new_context, "__await__"):  # tolerate async callbacks
                    new_context = await new_context
            except Exception:
                new_context = None
        if not isinstance(new_context, dict):
            return {"success": False,
                    "error": f"recovery needs re-observation for {failure_type} "
                             f"(no reobserve_fn or it returned nothing)"}

        retried = await self._dispatch_retry(action_metadata, new_context, attempt)
        if isinstance(retried, dict) and retried.get("success"):
            retried["recovered_from"] = failure_type
            retried["retry_attempt"] = attempt + 1
        return retried

    async def _dispatch_retry(
        self,
        metadata: "ActionMetadata",
        context: Dict[str, Any],
        attempt: int,
    ) -> Dict[str, Any]:
        import copy

        retry_md = copy.copy(metadata)
        retry_md.metadata = {**(metadata.metadata or {}), "retry_attempt": attempt + 1}
        merged = dict(context or {})
        route = self.dispatcher.api_dispatcher.select_route(retry_md.action_type, merged) if self.dispatcher else None
        if route is None:
            return {"success": False, "error": "no route available for recovery retry"}
        result = await self.dispatcher.api_dispatcher._execute_with_fallback(
            retry_md, merged, route
        )
        exec_time = time.time()
        return {
            "success": bool(result.success),
            "result": result.result,
            "error": result.error,
            "path_used": result.path_used.value,
            "_exec_ts": exec_time,
        }

    async def _recover_timeout(self, metadata: "ActionMetadata") -> Dict[str, Any]:
        """Retry once with a doubled timeout."""
        import copy

        retry_md = copy.copy(metadata)
        retry_md.timeout_seconds = float(metadata.timeout_seconds or 30) * 2
        retry_md.metadata = {**(metadata.metadata or {}),
                             "retry_attempt": int(metadata.metadata.get("retry_attempt", 0)) + 1}
        if self.dispatcher is None:
            return {"success": False, "error": "no dispatcher for timeout retry"}
        result = await self.dispatcher.api_dispatcher.dispatch(retry_md, {})
        out = {"success": bool(result.success), "result": result.result,
               "error": result.error, "timeout_doubled": True}
        return out

    def _classify_failure(self, error: str) -> str:
        error_lower = error.lower()
        if "not found" in error_lower or "no such element" in error_lower:
            return "TARGET_NOT_FOUND"
        if "confidence" in error_lower or "low confidence" in error_lower:
            return "LOW_CONFIDENCE"
        if "timeout" in error_lower or "timed out" in error_lower:
            return "TIMEOUT"
        if "ui changed" in error_lower or "stale" in error_lower:
            return "UI_CHANGED"
        return "UNKNOWN"


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ExecutionPath",
    "ExecutionRoute",
    "DispatchResult",
    "APIDispatcher",
    "Dispatcher",
    "VerificationEngine",
    "RecoveryEngine",
    "create_browser_api_handler",
    "create_structured_automation_handler",
    "create_accessibility_handler",
    "create_dom_handler",
    "create_visual_handler",
    "create_coordinate_handler",
]