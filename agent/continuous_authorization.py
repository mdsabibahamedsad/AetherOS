"""Continuous Authorization Checks for Zero-Trust Security.

Implements continuous authorization checks that verify permissions at tool
execution boundaries, including:
- Pre-execution authorization checks
- Execution-time monitoring
- Post-execution validation
- Dynamic policy re-evaluation based on context changes
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from unittest.mock import patch

from .security_principal import Principal, Agent, Tool
from .authorization_engine import (
    AuthorizationEngine, AuthorizationRequest, AuthorizationDecision,
    Decision, RiskLevel, PermissionAction, AuthorizationContext
)
from .tool_security import ToolSecurityManager, ToolPermissionManifest
from tools.registry import registry
from aetheros_cli import auth as auth_mod
from agent.credential_pool import CredentialPool
import logging

logger = logging.getLogger(__name__)


class AuthorizationCheckTiming(Enum):
    """Timing for authorization checks."""
    PRE_EXECUTION = "pre_execution"
    EXECUTION = "execution"
    POST_EXECUTION = "post_execution"
    CONTINUOUS = "continuous"


@dataclass
class AuthorizationEvent:
    """Record of an authorization check event."""
    timestamp: float = field(default_factory=time.time)
    request_id: str = field(default_factory=lambda: str(__import__("uuid").uuid4()))
    principal_id: str = ""
    action: str = ""
    resource: str = ""
    permission_action: str = ""
    decision: str = ""  # allow, deny, require_approval, challenge
    reason: str = ""
    risk_level: str = ""  # none, low, medium, high, critical
    context_id: Optional[str] = None
    execution_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContinuousAuthorizationError(Exception):
    """Exception raised when continuous authorization fails."""
    pass


class ToolExecutionBlockedError(ContinuousAuthorizationError):
    """Exception raised when tool execution is blocked by authorization."""
    pass


class AuthorizationMonitor:
    """Monitors and enforces continuous authorization for tool executions."""
    
    def __init__(self):
        self._authorization_engine = AuthorizationEngine()
        self._tool_security_manager = ToolSecurityManager()
        self._active_executions: Dict[str, Dict[str, Any]] = {}
        self._event_history: List[AuthorizationEvent] = []
        self._lock = threading.Lock()
        self._max_history_size = 1000
        # Integration with existing tool execution systems
        self._original_dispatch = None
        self._is_patched = False
    
    def start_monitoring(self):
        """Start monitoring tool executions for continuous authorization."""
        if self._is_patched:
            return  # Already monitoring
        
        try:
            # Patch the tool registry's dispatch method
            self._original_dispatch = registry.dispatch
            registry.dispatch = self._dispatch_with_authorization
            self._is_patched = True
            logger.info("Started continuous authorization monitoring")
        except Exception as e:
            logger.error(f"Failed to start authorization monitoring: {e}")
            raise
    
    def stop_monitoring(self):
        """Stop monitoring tool executions."""
        if not self._is_patched:
            return  # Not monitoring
        
        try:
            # Restore the original dispatch method
            if self._original_dispatch is not None:
                registry.dispatch = self._original_dispatch
                self._original_dispatch = None
                self._is_patched = False
                logger.info("Stopped continuous authorization monitoring")
        except Exception as e:
            logger.error(f"Failed to stop authorization monitoring: {e}")
    
    def _dispatch_with_authorization(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        task_id: Optional[str] = None,
        user_task: Optional[str] = None,
        **kwargs
    ) -> Any:
        """Dispatch a tool call with continuous authorization checks.
        
        This wraps the original registry.dispatch method to add:
        1. Pre-execution authorization check
        2. Execution monitoring
        3. Post-execution validation
        """
        start_time = time.time()
        execution_id = f"{tool_name}_{int(time.time() * 1000)}"
        
        try:
            # 1. Pre-execution authorization check
            pre_auth_decision = self._check_pre_execution_authorization(
                tool_name, tool_args, task_id, user_task, **kwargs
            )
            
            if not pre_auth_decision["allowed"]:
                # Block execution if not authorized
                raise ToolExecutionBlockedError(
                    f"Tool execution blocked: {pre_auth_decision['reason']}"
                )
            
            # 2. Track the execution for continuous monitoring
            execution_context = {
                "start_time": start_time,
                "tool_name": tool_name,
                "tool_args": tool_args.copy(),
                "task_id": task_id,
                "user_task": user_task,
                "authorization_decision": pre_auth_decision,
                "checkpoints": [],
                "metadata": kwargs.copy()
            }
            
            with self._lock:
                self._active_executions[execution_id] = execution_context
            
            try:
                # 3. Execute the tool with execution-time monitoring
                result = self._execute_with_monitoring(
                    tool_name, tool_args, execution_id, **kwargs
                )
                
                # 4. Post-execution validation
                post_auth_decision = self._check_post_execution_authorization(
                    tool_name, tool_args, result, execution_context
                )
                
                # 5. Record the authorization event
                self._record_authorization_event(
                    tool_name, tool_args, pre_auth_decision, post_auth_decision,
                    execution_id, start_time, result
                )
                
                return result
                
            except Exception as e:
                # If execution fails, still record the event
                self._record_authorization_event(
                    tool_name, tool_args, pre_auth_decision, 
                    {"allowed": False, "reason": f"Execution failed: {str(e)}"},
                    execution_id, start_time, None, str(e)
                )
                raise  # Re-raise the original exception
            finally:
                # Clean up execution tracking
                with self._lock:
                    self._active_executions.pop(execution_id, None)
                    
        except ToolExecutionBlockedError:
            # Re-raise blocking errors as-is
            raise
        except Exception as e:
            # Handle any other unexpected errors
            logger.error(f"Unexpected error in authorization monitoring: {e}")
            raise ContinuousAuthorizationError(f"Authorization monitoring failed: {str(e)}")
    
    def _check_pre_execution_authorization(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        task_id: Optional[str] = None,
        user_task: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Check authorization before tool execution."""
        # Get current agent and context information
        # In a real implementation, this would come from the current execution context
        # For now, we'll create a basic context
        
        # Try to get current agent from various sources
        agent_principal = self._get_current_agent()
        
        # Build authorization context
        auth_context = AuthorizationContext(
            task_id=task_id,
            metadata={
                "user_task": user_task,
                "tool_name": tool_name,
                "tool_args_summary": self._summarize_tool_args(tool_args),
                **kwargs
            }
        )
        
        # Use the tool security manager for detailed authorization
        auth_decision = self._tool_security_manager.authorize_tool_execution(
            agent_principal, tool_name, tool_args, auth_context
        )
        
        # Also check with the general authorization engine
        engine_auth_request = AuthorizationRequest(
            principal=agent_principal,
            action="tool.call",
            resource=f"tool:{tool_name}",
            permission_action=PermissionAction.EXECUTE,
            context=auth_context,
            risk_assessment={"tool_name": tool_name}
        )
        
        engine_auth_decision = self._authorization_engine.is_authorized(engine_auth_request)
        
        # Combine decisions - if either says deny, block execution
        if (auth_decision.decision.value == "deny" or 
            engine_auth_decision.decision.value == "deny"):
            return {
                "allowed": False,
                "reason": f"Authorization denied: {auth_decision.reason if auth_decision.decision.value == 'deny' else engine_auth_decision.reason}",
                "decision": auth_decision if auth_decision.decision.value == "deny" else engine_auth_decision,
                "requires_approval": (
                    auth_decision.decision.value == "require_approval" or 
                    engine_auth_decision.decision.value == "require_approval"
                )
            }
        )
        
        # If either requires approval, mark as requiring approval
        requires_approval = (
            auth_decision.decision.value == "require_approval" or 
            engine_auth_decision.decision.value == "require_approval"
        )
        
        return {
            "allowed": True,
            "reason": "Authorization granted",
            "decision": auth_decision,  # Prefer the more detailed tool security decision
            "requires_approval": requires_approval
        }
    
    def _execute_with_monitoring(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        execution_id: str,
        **kwargs
    ) -> Any:
        """Execute the tool with execution-time monitoring."""
        # For now, we'll just call the original dispatch method
        # In a more sophisticated implementation, we might:
        # 1. Monitor resource usage during execution
        # 2. Check for policy violations during execution
        # 3. Implement timeouts based on authorization context
        # 4. Monitor for suspicious behavior patterns
        
        # Add a checkpoint for execution start
        self._add_execution_checkpoint(execution_id, "execution_start", {
            "timestamp": time.time(),
            "tool_name": tool_name
        })
        
        # Call the original dispatch method
        result = self._original_dispatch(
            tool_name, tool_args, task_id=kwargs.get("task_id"),
            user_task=kwargs.get("user_task"), **{k: v for k, v in kwargs.items() 
                                              if k not in ["task_id", "user_task"]}
        )
        
        # Add a checkpoint for execution completion
        self._add_execution_checkpoint(execution_id, "execution_complete", {
            "timestamp": time.time(),
            "result_summary": self._summarize_result(result)
        })
        
        return result
    
    def _check_post_execution_authorization(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        result: Any,
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check authorization after tool execution."""
        # Validate that the result is consistent with the authorization decision
        # For example, if we authorized reading a file, verify that the result
        # doesn't contain sensitive information that shouldn't have been accessed
        
        # In a basic implementation, we'll just return that post-execution check passed
        # A more advanced implementation would:
        # 1. Check for data exfiltration in the result
        # 2. Verify that only authorized resources were accessed
        # 3. Check for privilege escalation attempts
        # 4. Validate that the result size is within expected bounds
        
        return {
            "allowed": True,
            "reason": "Post-execution validation passed",
            "decision": {"allowed": True, "reason": "Post-execution validation passed"}
        }
    
    def _add_execution_checkpoint(
        self,
        execution_id: str,
        checkpoint_type: str,
        data: Dict[str, Any]
    ):
        """Add a checkpoint to an active execution."""
        with self._lock:
            if execution_id in self._active_executions:
                checkpoint = {
                    "timestamp": time.time(),
                    "type": checkpoint_type,
                    "data": data
                }
                self._active_executions[execution_id]["checkpoints"].append(checkpoint)
    
    def _get_current_agent(self) -> Principal:
        """Get the current agent principal from execution context.
        
        In a real implementation, this would extract the agent from
        the current execution context, thread locals, or session storage.
        For now, we'll return a placeholder agent.
        """
        # Try to get from thread-local storage or context
        # This is a simplified implementation - in practice, this would
        # integrate with the actual agent execution context
        
        # Return a default agent for now
        from .security_principal import Agent
        return Agent(
            principal_id="current_agent",
            principal_type=PrincipalType.AGENT,
            agent_type="unknown",
            owner="unknown"
        )
    
    def _summarize_tool_args(self, tool_args: Dict[str, Any]) -> str:
        """Create a summary of tool arguments for logging."""
        # Create a brief summary that doesn't expose sensitive information
        summary_parts = []
        for key, value in tool_args.items():
            if isinstance(value, str) and len(value) > 50:
                summary_parts.append(f"{key}=[{len(value)} chars]")
            elif isinstance(value, str) and ("key" in key.lower() or "token" in key.lower() or "pass" in key.lower()):
                summary_parts.append(f"{key}=[REDACTED]")
            else:
                summary_parts.append(f"{key}={str(value)[:100]}")  # Limit length
        return ", ".join(summary_parts)
    
    def _summarize_result(self, result: Any) -> str:
        """Create a summary of tool result for logging."""
        if result is None:
            return "None"
        if isinstance(result, str):
            if len(result) > 100:
                return f"[{len(result)} chars]"
            return result[:100]
        return str(result)[:100]
    
    def _record_authorization_event(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        pre_decision: Dict[str, Any],
        post_decision: Dict[str, Any],
        execution_id: str,
        start_time: float,
        result: Any = None,
        error: Optional[str] = None
    ):
        """Record an authorization event for auditing and analysis."""
        end_time = time.time()
        execution_time_ms = (end_time - start_time) * 1000 if not error else None
        
        # Determine the overall decision
        overall_decision = "allow"
        overall_reason = "Authorized"
        overall_risk_level = "none"
        
        if not pre_decision["allowed"]:
            overall_decision = "deny"
            overall_reason = pre_decision["reason"]
            overall_risk_level = "high"
        elif error:
            overall_decision = "error"
            overall_reason = f"Execution error: {error}"
            overall_risk_level = "medium"
        elif not post_decision["allowed"]:
            overall_decision = "deny"
            overall_reason = post_decision["reason"]
            overall_risk_level = "medium"
        
        # Create the event
        event = AuthorizationEvent(
            principal_id="current_agent",  # Would be actual agent ID in practice
            action=f"tool.call:{tool_name}",
            resource=f"tool:{tool_name}",
            permission_action="execute",
            decision=overall_decision,
            reason=overall_reason,
            risk_level=overall_risk_level,
            execution_time_ms=execution_time_ms,
            metadata={
                "tool_name": tool_name,
                "tool_args_summary": self._summarize_tool_args(tool_args),
                "result_present": result is not None,
                "error_present": error is not None,
                "pre_decision": pre_decision,
                "post_decision": post_decision,
                "execution_id": execution_id
            }
        )
        
        # Add to history
        with self._lock:
            self._event_history.append(event)
            # Keep history size manageable
            if len(self._event_history) > self._max_history_size:
                self._event_history = self._event_history[-self._max_history_size:]
        
        # Log the event for auditing
        logger.info(
            f"Authorization Event: {event.decision} {event.action} "
            f"- {event.reason} (risk: {event.risk_level})"
        )
    
    def get_event_history(self, limit: Optional[int] = None) -> List[AuthorizationEvent]:
        """Get authorization event history."""
        with self._lock:
            if limit is None:
                return self._event_history.copy()
            return self._event_history[-limit:] if limit > 0 else []
    
    def get_active_executions(self) -> Dict[str, Dict[str, Any]]:
        """Get currently active tool executions."""
        with self._lock:
            return self._active_executions.copy()
    
    def clear_history(self):
        """Clear the authorization event history."""
        with self._lock:
            self._event_history.clear()


# Global authorization monitor instance
_AUTHORIZATION_MONITOR = None
_MONITOR_LOCK = threading.Lock()


def get_authorization_monitor() -> AuthorizationMonitor:
    """Get the global authorization monitor instance."""
    global _AUTHORIZATION_MONITOR
    with _MONITOR_LOCK:
        if _AUTHORIZATION_MONITOR is None:
            _AUTHORIZATION_MONITOR = AuthorizationMonitor()
        return _AUTHORIZATION_MONITOR


def start_continuous_authorization():
    """Start continuous authorization monitoring."""
    monitor = get_authorization_monitor()
    monitor.start_monitoring()


def stop_continuous_authorization():
    """Stop continuous authorization monitoring."""
    monitor = get_authorization_monitor()
    monitor.stop_monitoring()


def check_tool_authorization(
    tool_name: str,
    tool_args: Dict[str, Any],
    context: Optional[AuthorizationContext] = None
) -> Tuple[bool, str]:
    """Check if a tool execution is authorized.
    
    Returns (is_authorized, reason_if_not).
    """
    monitor = get_authorization_monitor()
    
    # Get current agent (simplified)
    from .security_principal import Agent
    agent = Agent(
        principal_id="check_agent",
        principal_type=PrincipalType.AGENT,
        agent_type="unknown",
        owner="unknown"
    )
    
    auth_context = context or AuthorizationContext()
    auth_decision = monitor._tool_security_manager.authorize_tool_execution(
        agent, tool_name, tool_args, auth_context
    )
    
    return (
        auth_decision.decision.value == "allow",
        auth_decision.reason
    )


# Decorator for adding continuous authorization to functions
def requires_authorization(
    tool_name: Optional[str] = None,
    check_args: bool = True
):
    """Decorator to add continuous authorization checks to functions.
    
    Usage:
        @requires_authorization(tool_name="write_file")
        def write_file(path, content):
            # Function implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Determine tool name from decorator or function name
            actual_tool_name = tool_name or func.__name__.replace("_", "-")
            
            # Prepare tool args from function arguments
            # This is simplified - real implementation would need to map
            # function arguments to tool arguments based on signature
            tool_args = {}
            if check_args and args:
                # Simple mapping for common cases
                if len(args) >= 1 and actual_tool_name in ["write_file", "read_file"]:
                    tool_args["path"] = str(args[0]) if args[0] else ""
                if len(args) >= 2 and actual_tool_name == "write_file":
                    tool_args["content"] = str(args[1]) if args[1] else ""
            
            # Add keyword arguments
            tool_args.update(kwargs)
            
            # Check authorization
            is_authorized, reason = check_tool_authorization(actual_tool_name, tool_args)
            if not is_authorized:
                raise ContinuousAuthorizationError(
                    f"Authorization failed for {actual_tool_name}: {reason}"
                )
            
            # Execute the function
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Initialize continuous authorization when module is imported
def _initialize_continuous_authorization():
    """Initialize continuous authorization monitoring."""
    try:
        start_continuous_authorization()
        logger.info("Continuous authorization monitoring initialized")
    except Exception as e:
        logger.error(f"Failed to initialize continuous authorization: {e}")


# Auto-initialize when imported
_initialize_continuous_authorization()