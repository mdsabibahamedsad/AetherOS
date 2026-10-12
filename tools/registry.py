"""Central registry for all aetheros tools.

Each tool file calls ``registry.register()`` at module level to declare its
schema, handler, toolset membership, and availability check.  ``model_tools.py``
queries the registry instead of maintaining its own parallel data structures.

Import chain (circular-import safe):
    tools/registry.py  (no imports from model_tools or tool files)
           ^
    tools/*.py  (import from tools.registry at module level)
           ^
    model_tools.py  (imports tools.registry + all tool modules)
           ^
    run_agent.py, cli.py, batch_runner.py, etc.
"""

import ast
import importlib
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


def _is_registry_register_call(node: ast.AST) -> bool:
    """Return True when *node* is a ``registry.register(...)`` call expression."""
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return False
    func = node.value.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "register"
        and isinstance(func.value, ast.Name)
        and func.value.id == "registry"
    )


def _module_registers_tools(module_path: Path) -> bool:
    """Return True when the module contains a top-level ``registry.register(...)`` call.

    Only inspects module-body statements so that helper modules which happen
    to call ``registry.register()`` inside a function are not picked up.
    """
    try:
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(module_path))
    except (OSError, SyntaxError):
        return False

    return any(_is_registry_register_call(stmt) for stmt in tree.body)


def discover_builtin_tools(tools_dir: Optional[Path] = None) -> List[str]:
    """Import built-in self-registering tool modules and return their module names."""
    tools_path = Path(tools_dir) if tools_dir is not None else Path(__file__).resolve().parent
    module_names = [
        f"tools.{path.stem}"
        for path in sorted(tools_path.glob("*.py"))
        if path.name not in {"__init__.py", "registry.py", "mcp_tool.py"}
        and _module_registers_tools(path)
    ]

    imported: List[str] = []
    for mod_name in module_names:
        try:
            importlib.import_module(mod_name)
            imported.append(mod_name)
        except Exception as e:
            logger.warning("Could not import tool module %s: %s", mod_name, e)
    return imported


class ToolEntry:
    """Metadata for a single registered tool."""

    __slots__ = (
        "name", "toolset", "schema", "handler", "check_fn",
        "requires_env", "is_async", "description", "emoji",
        "max_result_size_chars", "dynamic_schema_overrides",
        # Tool execution pipeline fields
        "risk_level", "permissions", "confirmation_required",
        "sandbox_config", "retry_config", "circuit_breaker_config",
        "timeout_config", "output_security_level", "version",
        # Unified tool interface fields
        "provider", "platform", "supports_streaming", "supports_cancellation", 
        "supports_background_execution", "output_schema",
        # Health tracking fields
        "_health_status", "_last_health_check", "_consecutive_failures",
        "_total_calls", "_failed_calls", "_total_execution_time",
        # Contract check (Master 12 Phase 7)
        "_schema_valid",
        # Observability fields
        "_observability_enabled", "_last_used_by", "_last_used_at", 
        "_use_count", "_error_count", "_total_resource_usage"
    )

    def __init__(self, name, toolset, schema, handler, check_fn,
                 requires_env, is_async, description, emoji,
                 max_result_size_chars=None, dynamic_schema_overrides=None,
                 # Tool execution pipeline fields with sensible defaults
                 risk_level="LOW_RISK", permissions=None, confirmation_required=False,
                 sandbox_config=None, retry_config=None, circuit_breaker_config=None,
                 timeout_config=None, output_security_level="NONE", version="1.0.0",
                 # Unified tool interface fields - extracted from schema or defaults
                 provider="aetheros", platform=None, supports_streaming=False,
                 supports_cancellation=False, supports_background_execution=False,
                 output_schema=None):
        self.name = name
        self.toolset = toolset
        self.schema = schema
        self.handler = handler
        self.check_fn = check_fn
        self.requires_env = requires_env or []
        self.is_async = is_async
        self.description = description or schema.get("description", "")
        self.emoji = emoji
        self.max_result_size_chars = max_result_size_chars
        # Optional zero-arg callable returning a dict of schema overrides
        # applied at get_definitions() time. Use for fields that depend on
        # runtime config (e.g. delegate_task's description must reflect the
        # user's current delegation.max_concurrent_children / max_spawn_depth
        # so the model isn't told the wrong limits). The callable is invoked
        # on every get_definitions() call; results are merged shallow on top
        # of the base schema before the {"type": "function", ...} wrap.
        self.dynamic_schema_overrides = dynamic_schema_overrides
        # Tool execution pipeline fields
        self.risk_level = risk_level
        self.permissions = permissions or []
        self.confirmation_required = confirmation_required
        self.sandbox_config = sandbox_config or {}
        self.retry_config = retry_config or {}
        self.circuit_breaker_config = circuit_breaker_config or {}
        self.timeout_config = timeout_config or {}
        self.output_security_level = output_security_level
        self.version = version
        # Unified tool interface fields - extract from schema or use defaults
        self.provider = provider
        self.platform = platform
        self.supports_streaming = supports_streaming
        self.supports_cancellation = supports_cancellation
        self.supports_background_execution = supports_background_execution
        # Extract output schema from schema if not provided, otherwise use default
        if output_schema is not None:
            self.output_schema = output_schema
        else:
            # Try to extract from schema, otherwise use default
            schema_output = schema.get("outputSchema") if isinstance(schema, dict) else None
            self.output_schema = schema_output or {"type": "object", "properties": {"result": {"type": "string"}}}
        # Health tracking fields - initialize with default values
        self._health_status = "unknown"  # unknown, healthy, degraded, unhealthy
        self._last_health_check = 0.0
        self._schema_valid = False  # set by register() contract check
        self._consecutive_failures = 0
        self._total_calls = 0
        self._failed_calls = 0
        self._total_execution_time = 0.0
        # Observability fields - initialize with default values
        self._observability_enabled = False
        self._last_used_by = None  # Could be agent ID, task ID, etc.
        self._last_used_at = 0.0
        self._use_count = 0
        self._error_count = 0
        self._total_resource_usage = 0.0  # Could track CPU time, memory, etc.


# ---------------------------------------------------------------------------
# check_fn TTL cache
#
# check_fn callables like tools/terminal_tool.check_terminal_requirements
# probe external state (Docker daemon, Modal SDK install, playwright binary
# availability). For a long-lived CLI or gateway process, calling them on
# every get_definitions() is pure waste — external state changes on human
# timescales. Cache results for ~30 s so env-var flips via ``aetheros tools``
# or live credential file changes propagate within a turn or two without
# requiring any explicit invalidation.
# ---------------------------------------------------------------------------

_CHECK_FN_TTL_SECONDS = 30.0
_check_fn_cache: Dict[Callable, tuple[float, bool]] = {}
_check_fn_cache_lock = threading.Lock()


def _check_fn_cached(fn: Callable) -> bool:
    """Return bool(fn()), TTL-cached across calls. Swallows exceptions as False."""
    now = time.monotonic()
    with _check_fn_cache_lock:
        cached = _check_fn_cache.get(fn)
        if cached is not None:
            ts, value = cached
            if now - ts < _CHECK_FN_TTL_SECONDS:
                return value
    try:
        value = bool(fn())
    except Exception:
        value = False
    with _check_fn_cache_lock:
        _check_fn_cache[fn] = (now, value)
    return value


def invalidate_check_fn_cache() -> None:
    """Drop all cached ``check_fn`` results. Call after config changes that
    affect tool availability (e.g. ``aetheros tools enable``)."""
    with _check_fn_cache_lock:
        _check_fn_cache.clear()


class ToolRegistry:
    """Singleton registry that collects tool schemas + handlers from tool files."""

    def __init__(self):
        self._tools: Dict[str, ToolEntry] = {}
        self._toolset_checks: Dict[str, Callable] = {}
        self._toolset_aliases: Dict[str, str] = {}
        # MCP dynamic refresh can mutate the registry while other threads are
        # reading tool metadata, so keep mutations serialized and readers on
        # stable snapshots.
        self._lock = threading.RLock()
        # Monotonically-increasing generation counter. Bumped on every
        # mutation (register / deregister / register_toolset_alias / MCP
        # refresh). External callers (e.g. get_tool_definitions) can memoize
        # against it: a cache entry keyed on the generation is valid for as
        # long as the generation hasn't changed.
        self._generation: int = 0

    def _snapshot_state(self) -> tuple[List[ToolEntry], Dict[str, Callable]]:
        """Return a coherent snapshot of registry entries and toolset checks."""
        with self._lock:
            return list(self._tools.values()), dict(self._toolset_checks)

    def _snapshot_entries(self) -> List[ToolEntry]:
        """Return a stable snapshot of registered tool entries."""
        return self._snapshot_state()[0]

    def _snapshot_toolset_checks(self) -> Dict[str, Callable]:
        """Return a stable snapshot of toolset availability checks."""
        return self._snapshot_state()[1]

    def _evaluate_toolset_check(self, toolset: str, check: Callable | None) -> bool:
        """Run a toolset check, treating missing or failing checks as unavailable/available."""
        if not check:
            return True
        try:
            return bool(check())
        except Exception:
            logger.debug("Toolset %s check raised; marking unavailable", toolset)
            return False

    def get_entry(self, name: str) -> Optional[ToolEntry]:
        """Return a registered tool entry by name, or None."""
        with self._lock:
            return self._tools.get(name)

    def get_registered_toolset_names(self) -> List[str]:
        """Return sorted unique toolset names present in the registry."""
        return sorted({entry.toolset for entry in self._snapshot_entries()})

    def get_tool_names_for_toolset(self, toolset: str) -> List[str]:
        """Return sorted tool names registered under a given toolset."""
        return sorted(
            entry.name for entry in self._snapshot_entries()
            if entry.toolset == toolset
        )

    def register_toolset_alias(self, alias: str, toolset: str) -> None:
        """Register an explicit alias for a canonical toolset name."""
        with self._lock:
            existing = self._toolset_aliases.get(alias)
            if existing and existing != toolset:
                logger.warning(
                    "Toolset alias collision: '%s' (%s) overwritten by %s",
                    alias, existing, toolset,
                )
            self._toolset_aliases[alias] = toolset
            self._generation += 1

    def get_registered_toolset_aliases(self) -> Dict[str, str]:
        """Return a snapshot of ``{alias: canonical_toolset}`` mappings."""
        with self._lock:
            return dict(self._toolset_aliases)

    def get_toolset_alias_target(self, alias: str) -> Optional[str]:
        """Return the canonical toolset name for an alias, or None."""
        with self._lock:
            return self._toolset_aliases.get(alias)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        toolset: str,
        schema: dict,
        handler: Callable,
        check_fn: Callable = None,
        requires_env: list = None,
        is_async: bool = False,
        description: str = "",
        emoji: str = "",
        max_result_size_chars: int | float | None = None,
        dynamic_schema_overrides: Callable = None,
        override: bool = False,
        # Unified tool interface fields
        provider: str = "aetheros",
        platform: Optional[str] = None,
        supports_streaming: bool = False,
        supports_cancellation: bool = False,
        supports_background_execution: bool = False,
        output_schema: Optional[dict] = None,
    ):
        """Register a tool.  Called at module-import time by each tool file.

        ``override=True`` is an explicit opt-in for plugins that intend to
        replace an existing built-in tool implementation (e.g. swap the
        default browser tool for a headed-Chrome CDP backend). Without it,
        registrations that would shadow an existing tool from a different
        toolset are rejected to prevent accidental overwrites.
        """
        with self._lock:
            existing = self._tools.get(name)
            if existing and existing.toolset != toolset:
                # Allow MCP-to-MCP overwrites (legitimate: server refresh,
                # or two MCP servers with overlapping tool names).
                both_mcp = (
                    existing.toolset.startswith("mcp-")
                    and toolset.startswith("mcp-")
                )
                if both_mcp:
                    logger.debug(
                        "Tool '%s': MCP toolset '%s' overwriting MCP toolset '%s'",
                        name, toolset, existing.toolset,
                    )
                elif override:
                    # Explicit plugin opt-in: replace the existing tool.
                    # Logged at INFO so the override is auditable in agent.log.
                    logger.info(
                        "Tool '%s': toolset '%s' overriding existing toolset '%s' "
                        "(override=True opt-in)",
                        name, toolset, existing.toolset,
                    )
                else:
                    # Reject shadowing — prevent plugins/MCP from overwriting
                    # built-in tools or vice versa.
                    logger.error(
                        "Tool registration REJECTED: '%s' (toolset '%s') would "
                        "shadow existing tool from toolset '%s'. Pass "
                        "override=True to register() if the replacement is "
                        "intentional, or deregister the existing tool first.",
                        name, toolset, existing.toolset,
                    )
                    return
            self._tools[name] = ToolEntry(
                name=name,
                toolset=toolset,
                schema=schema,
                handler=handler,
                check_fn=check_fn,
                requires_env=requires_env or [],
                is_async=is_async,
                description=description or schema.get("description", ""),
                emoji=emoji,
                max_result_size_chars=max_result_size_chars,
                dynamic_schema_overrides=dynamic_schema_overrides,
                # Tool execution pipeline fields
                risk_level="LOW_RISK",  # Default, can be overridden by tool
                permissions=None,       # Default, can be overridden by tool
                confirmation_required=False,
                sandbox_config=None,
                retry_config=None,
                circuit_breaker_config=None,
                timeout_config=None,
                output_security_level="NONE",
                version="1.0.0",
                # Unified tool interface fields
                provider=provider,
                platform=platform,
                supports_streaming=supports_streaming,
                supports_cancellation=supports_cancellation,
                supports_background_execution=supports_background_execution,
                output_schema=output_schema,
            )
            if check_fn and toolset not in self._toolset_checks:
                self._toolset_checks[toolset] = check_fn
            self._generation += 1

            # Contract check (Master 12 Phase 7): surface malformed schemas
            # at registration time instead of failing silently at the
            # provider. Warn-only — a sloppy third-party schema must not
            # abort discovery of everything after it.
            try:
                _entry = self._tools[name]
                _ok, _err = self.validate_tool_schema(name)
                _entry._schema_valid = bool(_ok)
                if not _ok:
                    logger.warning(
                        "Tool '%s' schema invalid: %s", name, _err
                    )
            except Exception as e:  # pragma: no cover - defensive
                logger.warning("Tool '%s' schema validation error: %s", name, e)

    def deregister(self, name: str) -> None:
        """Remove a tool from the registry.

        Also cleans up the toolset check if no other tools remain in the
        same toolset.  Used by MCP dynamic tool discovery to nuke-and-repave
        when a server sends ``notifications/tools/list_changed``.
        """
        with self._lock:
            entry = self._tools.pop(name, None)
            if entry is None:
                return
            # Drop the toolset check and aliases if this was the last tool in
            # that toolset.
            toolset_still_exists = any(
                e.toolset == entry.toolset for e in self._tools.values()
            )
            if not toolset_still_exists:
                self._toolset_checks.pop(entry.toolset, None)
                self._toolset_aliases = {
                    alias: target
                    for alias, target in self._toolset_aliases.items()
                    if target != entry.toolset
                }
            self._generation += 1
        logger.debug("Deregistered tool: %s", name)

    # ------------------------------------------------------------------
    # Schema retrieval
    # ------------------------------------------------------------------

    def get_definitions(self, tool_names: Set[str], quiet: bool = False) -> List[dict]:
        """Return OpenAI-format tool schemas for the requested tool names.

        Only tools whose ``check_fn()`` returns True (or have no check_fn)
        are included. ``check_fn()`` results are cached for ~30 s via
        :func:`_check_fn_cached` to amortize repeat probes (check_terminal_
        requirements probes modal/docker, browser checks probe playwright,
        etc.); TTL chosen so env-var changes (``aetheros tools enable foo``)
        still take effect in near-real-time without forcing a full cache
        flush on every call.
        """
        result = []
        # Per-call cache on top of the 30 s TTL — handles repeat probes of the
        # same check_fn within one definitions pass without re-reading the
        # TTL clock.
        check_results: Dict[Callable, bool] = {}
        entries_by_name = {entry.name: entry for entry in self._snapshot_entries()}
        for name in sorted(tool_names):
            entry = entries_by_name.get(name)
            if not entry:
                continue
            if entry.check_fn:
                if entry.check_fn not in check_results:
                    check_results[entry.check_fn] = _check_fn_cached(entry.check_fn)
                if not check_results[entry.check_fn]:
                    if not quiet:
                        logger.debug("Tool %s unavailable (check failed)", name)
                    continue
            # Ensure schema always has a "name" field — use entry.name as fallback
            schema_with_name = {**entry.schema, "name": entry.name}
            # Apply runtime-dynamic overrides (e.g. delegate_task description
            # depends on current delegation.max_concurrent_children /
            # max_spawn_depth). Caller side (model_tools.get_tool_definitions)
            # already keys its memo on config.yaml mtime + size, so changes
            # to delegation.* in config invalidate the cache automatically.
            if entry.dynamic_schema_overrides is not None:
                try:
                    overrides = entry.dynamic_schema_overrides()
                    if isinstance(overrides, dict):
                        schema_with_name.update(overrides)
                except Exception as exc:
                    logger.warning(
                        "dynamic_schema_overrides for tool %s raised %s; "
                        "using static schema",
                        name, exc,
                    )
            # Enhance schema with health and observability information
            enhanced_schema = {**schema_with_name}
            # Add health and observability info to description for model awareness
            health_info = f" [Health: {entry._health_status}]"
            observability_info = f" [Used: {entry._use_count} times, Errors: {entry._error_count}]"
            if entry._last_used_at > 0:
                from datetime import datetime
                last_used = datetime.fromtimestamp(entry._last_used_at).strftime("%H:%M:%S")
                observability_info += f", Last used: {last_used} by {entry._last_used_by}"
            
            enhanced_description = entry.description + health_info + observability_info
            enhanced_schema["description"] = enhanced_description
            result.append({"type": "function", "function": enhanced_schema})
        return result

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(self, name: str, args: dict, **kwargs) -> str:
        """Execute a tool handler by name.

        * Async handlers are bridged automatically via ``_run_async()``.
        * All exceptions are caught and returned as ``{"error": "..."}``
          for consistent error format.
        """
        import time
        start_time = time.time()
        
        entry = self.get_entry(name)
        if not entry:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            if entry.is_async:
                from model_tools import _run_async
                result = _run_async(entry.handler(args, **kwargs))
            else:
                result = entry.handler(args, **kwargs)
            
            # Track successful execution
            execution_time = time.time() - start_time
            with self._lock:
                entry._total_calls += 1
                entry._total_execution_time += execution_time
                entry._use_count += 1
                entry._last_used_at = time.time()
                entry._last_used_by = kwargs.get("task_id", "unknown")
                # Update health status based on success
                if entry._consecutive_failures > 0:
                    entry._consecutive_failures = 0  # Reset consecutive failures on success
                if entry._health_status == "unhealthy":
                    entry._health_status = "degraded"  # Improve from unhealthy to degraded
                elif entry._health_status == "degraded" and entry._total_calls >= 10:
                    # If we've had enough successful calls, consider healthy again
                    success_rate = (entry._total_calls - entry._failed_calls) / entry._total_calls
                    if success_rate >= 0.9:  # 90% success rate
                        entry._health_status = "healthy"
            
            return result
        except Exception as e:
            # Track failed execution
            execution_time = time.time() - start_time
            with self._lock:
                entry._total_calls += 1
                entry._failed_calls += 1
                entry._total_execution_time += execution_time
                entry._consecutive_failures += 1
                entry._error_count += 1
                entry._last_used_at = time.time()
                entry._last_used_by = kwargs.get("task_id", "unknown")
                
                # Update health status
                if entry._consecutive_failures >= 3:
                    entry._health_status = "unhealthy"
                elif entry._consecutive_failures >= 1:
                    entry._health_status = "degraded"
            
            logger.exception("Tool %s dispatch error: %s", name, e)
            # Route through the sanitizer so framing tokens / CDATA / fences
            # in exception strings don't reach the model as structural noise.
            # See model_tools._sanitize_tool_error for rationale.
            raw = f"Tool execution failed: {type(e).__name__}: {e}"
            try:
                from model_tools import _sanitize_tool_error
                sanitized = _sanitize_tool_error(raw)
            except Exception:
                sanitized = raw  # defensive: never let the sanitizer block error propagation
            return json.dumps({"error": sanitized})

    # ------------------------------------------------------------------
    # Query helpers  (replace redundant dicts in model_tools.py)
    # ------------------------------------------------------------------

    def get_max_result_size(self, name: str, default: int | float | None = None) -> int | float:
        """Return per-tool max result size, or *default* (or global default)."""
        entry = self.get_entry(name)
        if entry and entry.max_result_size_chars is not None:
            return entry.max_result_size_chars
        if default is not None:
            return default
        from tools.budget_config import DEFAULT_RESULT_SIZE_CHARS
        return DEFAULT_RESULT_SIZE_CHARS

    def get_all_tool_names(self) -> List[str]:
        """Return sorted list of all registered tool names."""
        return sorted(entry.name for entry in self._snapshot_entries())

    def get_schema(self, name: str) -> Optional[dict]:
        """Return a tool's raw schema dict, bypassing check_fn filtering.

        Useful for token estimation and introspection where availability
        doesn't matter — only the schema content does.
        """
        entry = self.get_entry(name)
        return entry.schema if entry else None

    def get_toolset_for_tool(self, name: str) -> Optional[str]:
        """Return the toolset a tool belongs to, or None."""
        entry = self.get_entry(name)
        return entry.toolset if entry else None

    def get_emoji(self, name: str, default: str = "⚡") -> str:
        """Return the emoji for a tool, or *default* if unset."""
        entry = self.get_entry(name)
        return (entry.emoji if entry and entry.emoji else default)

    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive information about a tool."""
        entry = self.get_entry(name)
        if not entry:
            return None
        
        return {
            "name": entry.name,
            "toolset": entry.toolset,
            "description": entry.description,
            "version": entry.version,
            "provider": entry.provider,
            "platform": entry.platform,
            "is_async": entry.is_async,
            "emoji": entry.emoji,
            "max_result_size_chars": entry.max_result_size_chars,
            # Tool execution pipeline fields
            "risk_level": entry.risk_level,
            "permissions": entry.permissions,
            "confirmation_required": entry.confirmation_required,
            "sandbox_config": entry.sandbox_config,
            "retry_config": entry.retry_config,
            "circuit_breaker_config": entry.circuit_breaker_config,
            "timeout_config": entry.timeout_config,
            "output_security_level": entry.output_security_level,
            # Unified tool interface fields
            "supports_streaming": entry.supports_streaming,
            "supports_cancellation": entry.supports_cancellation,
            "supports_background_execution": entry.supports_background_execution,
            # Schema information
            "input_schema": entry.schema,
            "output_schema": entry.output_schema,
            # Availability
            "available": self._evaluate_toolset_check(entry.toolset, self._toolset_checks.get(entry.toolset)) if entry.toolset in self._toolset_checks else True,
            "requires_env": entry.requires_env,
        }

    def get_tool_to_toolset_map(self) -> Dict[str, str]:
        """Return ``{tool_name: toolset_name}`` for every registered tool."""
        return {entry.name: entry.toolset for entry in self._snapshot_entries()}

    def validate_tool_schema(self, name: str) -> Tuple[bool, Optional[str]]:
        """Validate a tool's schema against JSON Schema specification.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        entry = self.get_entry(name)
        if not entry:
            return False, f"Tool '{name}' not found"
        
        # Basic schema validation
        schema = entry.schema
        if not isinstance(schema, dict):
            return False, f"Tool '{name}' schema is not a dict"
        
        if "name" not in schema:
            return False, f"Tool '{name}' schema missing 'name' field"
        
        if schema["name"] != name:
            return False, f"Tool '{name}' schema name mismatch: expected '{name}', got '{schema['name']}'"
        
        if "parameters" not in schema:
            return False, f"Tool '{name}' schema missing 'parameters' field"
        
        # Validate parameters is an object with properties
        parameters = schema.get("parameters")
        if not isinstance(parameters, dict):
            return False, f"Tool '{name}' parameters is not a dict"
        
        if "type" not in parameters or parameters.get("type") != "object":
            return False, f"Tool '{name}' parameters must be an object"
        
        # Additional validation could be added here using a JSON Schema validator
        
        return True, None

    def get_tool_health(self, name: str) -> Optional[Dict[str, Any]]:
        """Get health information for a tool.
        
        Returns:
            Dict with health information or None if tool not found
        """
        entry = self.get_entry(name)
        if not entry:
            return None
        
        # Calculate success rate
        success_rate = 1.0
        if entry._total_calls > 0:
            success_rate = (entry._total_calls - entry._failed_calls) / entry._total_calls
        
        # Calculate average execution time
        avg_execution_time = 0.0
        if entry._total_calls > 0:
            avg_execution_time = entry._total_execution_time / entry._total_calls
        
        return {
            "name": entry.name,
            "status": entry._health_status,
            "last_health_check": entry._last_health_check,
            "consecutive_failures": entry._consecutive_failures,
            "total_calls": entry._total_calls,
            "failed_calls": entry._failed_calls,
            "success_rate": success_rate,
            "avg_execution_time_ms": avg_execution_time * 1000,
            "is_healthy": entry._health_status == "healthy" and entry._consecutive_failures < 3,
        }

    def health_check_tool(self, name: str) -> Dict[str, Any]:
        """Perform a health check on a tool by attempting to call it with safe parameters.
        
        Returns:
            Dict with health check results
        """
        import time
        start_time = time.time()
        
        entry = self.get_entry(name)
        if not entry:
            return {
                "name": name,
                "status": "unknown",
                "error": "Tool not found",
                "is_healthy": False
            }
        
        # Check if tool has a check_fn and run it
        if entry.check_fn:
            try:
                check_result = _check_fn_cached(entry.check_fn)
                if not check_result:
                    with self._lock:
                        entry._health_status = "unhealthy"
                        entry._last_health_check = time.time()
                    return {
                        "name": name,
                        "status": "unhealthy",
                        "error": "Tool availability check failed",
                        "is_healthy": False,
                        "check_time_ms": (time.time() - start_time) * 1000
                    }
            except Exception as e:
                with self._lock:
                    entry._health_status = "unhealthy"
                    entry._last_health_check = time.time()
                return {
                    "name": name,
                    "status": "unhealthy",
                    "error": f"Health check failed: {str(e)}",
                    "is_healthy": False,
                    "check_time_ms": (time.time() - start_time) * 1000
                }
        
        # For now, just update the last health check time
        # A more sophisticated implementation would attempt to call the tool
        # with safe/test parameters, but that could have side effects
        with self._lock:
            entry._last_health_check = time.time()
            # If we were unhealthy due to check failures, try to improve status
            if entry._health_status == "unhealthy":
                entry._health_status = "degraded"
        
        return {
            "name": name,
            "status": entry._health_status,
            "last_health_check": entry._last_health_check,
            "consecutive_failures": entry._consecutive_failures,
            "is_healthy": entry._health_status == "healthy" and entry._consecutive_failures < 3,
            "check_time_ms": (time.time() - start_time) * 1000
        }

    def get_all_tools_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health information for all tools.
        
        Returns:
            Dict mapping tool names to their health information
        """
        result = {}
        for tool_name in self.get_all_tool_names():
            result[tool_name] = self.get_tool_health(tool_name) or {
                "name": tool_name,
                "status": "unknown",
                "is_healthy": False
            }
        return result

    def is_toolset_available(self, toolset: str) -> bool:
        """Check if a toolset's requirements are met.

        Returns False (rather than crashing) when the check function raises
        an unexpected exception (e.g. network error, missing import, bad config).
        """
        with self._lock:
            check = self._toolset_checks.get(toolset)
        return self._evaluate_toolset_check(toolset, check)

    def check_toolset_requirements(self) -> Dict[str, bool]:
        """Return ``{toolset: available_bool}`` for every toolset."""
        entries, toolset_checks = self._snapshot_state()
        toolsets = sorted({entry.toolset for entry in entries})
        return {
            toolset: self._evaluate_toolset_check(toolset, toolset_checks.get(toolset))
            for toolset in toolsets
        }

    def get_available_toolsets(self) -> Dict[str, dict]:
        """Return toolset metadata for UI display."""
        toolsets: Dict[str, dict] = {}
        entries, toolset_checks = self._snapshot_state()
        for entry in entries:
            ts = entry.toolset
            if ts not in toolsets:
                toolsets[ts] = {
                    "available": self._evaluate_toolset_check(
                        ts, toolset_checks.get(ts)
                    ),
                    "tools": [],
                    "description": "",
                    "requirements": [],
                }
            toolsets[ts]["tools"].append(entry.name)
            if entry.requires_env:
                for env in entry.requires_env:
                    if env not in toolsets[ts]["requirements"]:
                        toolsets[ts]["requirements"].append(env)
        return toolsets

    def get_toolset_requirements(self) -> Dict[str, dict]:
        """Build a TOOLSET_REQUIREMENTS-compatible dict for backward compat."""
        result: Dict[str, dict] = {}
        entries, toolset_checks = self._snapshot_state()
        for entry in entries:
            ts = entry.toolset
            if ts not in result:
                result[ts] = {
                    "name": ts,
                    "env_vars": [],
                    "check_fn": toolset_checks.get(ts),
                    "setup_url": None,
                    "tools": [],
                }
            if entry.name not in result[ts]["tools"]:
                result[ts]["tools"].append(entry.name)
            for env in entry.requires_env:
                if env not in result[ts]["env_vars"]:
                    result[ts]["env_vars"].append(env)
        return result

    def check_tool_availability(self, quiet: bool = False):
        """Return (available_toolsets, unavailable_info) like the old function."""
        available = []
        unavailable = []
        seen = set()
        entries, toolset_checks = self._snapshot_state()
        for entry in entries:
            ts = entry.toolset
            if ts in seen:
                continue
            seen.add(ts)
            if self._evaluate_toolset_check(ts, toolset_checks.get(ts)):
                available.append(ts)
            else:
                unavailable.append({
                    "name": ts,
                    "env_vars": entry.requires_env,
                    "tools": [e.name for e in entries if e.toolset == ts],
                })
        return available, unavailable


# Module-level singleton
registry = ToolRegistry()


# ---------------------------------------------------------------------------
# Helpers for tool response serialization
# ---------------------------------------------------------------------------
# Every tool handler must return a JSON string.  These helpers eliminate the
# boilerplate ``json.dumps({"error": msg}, ensure_ascii=False)`` that appears
# hundreds of times across tool files.
#
# Usage:
#   from tools.registry import registry, tool_error, tool_result
#
#   return tool_error("something went wrong")
#   return tool_error("not found", code=404)
#   return tool_result(success=True, data=payload)
#   return tool_result(items)            # pass a dict directly


def tool_error(message, **extra) -> str:
    """Return a JSON error string for tool handlers.

    >>> tool_error("file not found")
    '{"error": "file not found"}'
    >>> tool_error("bad input", success=False)
    '{"error": "bad input", "success": false}'
    """
    result = {"error": str(message)}
    if extra:
        result.update(extra)
    return json.dumps(result, ensure_ascii=False)


def tool_result(data=None, **kwargs) -> str:
    """Return a JSON result string for tool handlers.

    Accepts a dict positional arg *or* keyword arguments (not both):

    >>> tool_result(success=True, count=42)
    '{"success": true, "count": 42}'
    >>> tool_result({"key": "value"})
    '{"key": "value"}'
    """
    if data is not None:
        return json.dumps(data, ensure_ascii=False)
    return json.dumps(kwargs, ensure_ascii=False)
