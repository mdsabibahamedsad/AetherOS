"""Tool SDK runtime (Master 62 §12-13): definitions, safety metadata, execution.

Supports sync tools, async tools, long-running (deadline-bounded) tools,
approval-gated tools, artifact-producing tools. Streaming tools surface as
generators through the events feed. Every invocation: schema validation ->
policy -> rate/concurrency limits -> idempotency -> execution -> audit.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from aetheros_platform.errors import err
from aetheros_platform.policy import PolicyBridge
from aetheros_platform.ratelimit import LIMITER
from aetheros_platform.schemas import validate


class ToolRegistry:
    def __init__(self, audit: Optional[Callable] = None) -> None:
        self._manifests: Dict[str, Dict[str, Any]] = {}
        self._impls: Dict[str, Callable] = {}
        self._seen_idem: Dict[str, Any] = {}
        self.policy = PolicyBridge(audit=audit)
        self._audit = audit

    # -- definition ---------------------------------------------------------
    def register(self, manifest: Dict[str, Any], impl: Callable) -> Dict[str, Any]:
        errors = validate("Tool", manifest)
        if errors:
            raise err("INVALID_SCHEMA", f"tool manifest invalid: {errors[0]}")
        name, version = manifest["name"], manifest["version"]
        key = f"{name}@{version}"
        if key in self._manifests:
            raise err("CONFLICT", f"tool {key} already registered")
        self._manifests[key] = manifest
        self._impls[key] = impl
        if self._audit:
            self._audit("tool.registered", "", key, "ok", {})
        return manifest

    def get(self, name: str, version: Optional[str] = None) -> Dict[str, Any]:
        if version:
            key = f"{name}@{version}"
            if key not in self._manifests:
                raise err("TOOL_UNAVAILABLE", f"unknown tool {key}")
            return self._manifests[key]
        cands = sorted(k for k in self._manifests if k.startswith(name + "@"))
        if not cands:
            raise err("TOOL_UNAVAILABLE", f"unknown tool {name}")
        return self._manifests[cands[-1]]

    def list(self) -> List[Dict[str, Any]]:
        return list(self._manifests.values())

    # -- invocation -----------------------------------------------------------
    def invoke(self, name: str, args: Dict[str, Any], actor: str = "",
               grants: Optional[List[str]] = None,
               idempotency_key: Optional[str] = None,
               version: Optional[str] = None,
               timeout_s: Optional[float] = None) -> Any:
        manifest = self.get(name, version)
        key = f"{manifest['name']}@{manifest['version']}"
        if idempotency_key and idempotency_key in self._seen_idem:
            return self._seen_idem[idempotency_key]
        schema_errors = self._validate_args(manifest.get("inputSchema") or {}, args)
        if schema_errors:
            raise err("INVALID_SCHEMA", f"tool args invalid: {schema_errors[0]}")
        # Least-privilege: caller grants must not exceed the tool's declared
        # capabilities. A caller asserting authority the tool never declared
        # (e.g. smuggling "email.send" through a memory.read tool) is denied —
        # tool output is untrusted data, never a source of authority.
        declared = set(manifest.get("capabilities", []))
        excess = sorted({g for g in (grants or []) if g not in declared})
        if excess:
            raise err("CAPABILITY_NOT_GRANTED",
                      f"grants exceed tool '{manifest['name']}' declared "
                      f"capabilities: {excess[:5]}",
                      capability=excess[0],
                      remediation="invoke with only the capabilities this tool "
                                  "declares")
        for cap in manifest.get("capabilities", []):
            self.policy.require_allowed({"capability": cap, "actor": actor,
                                         "side_effects_irreversible":
                                             bool(manifest.get("sideEffects")) and
                                             "irreversible" in manifest.get("sideEffects", [])},
                                        grants or [])
        ident = actor or "anonymous"
        LIMITER.check("tool-invoke", ident, key)
        LIMITER.acquire_inflight(ident)
        t0 = time.time()
        try:
            impl = self._impls[key]
            deadline = timeout_s or float(manifest.get("timeoutSeconds", 60))
            if inspect.iscoroutinefunction(impl):
                result = self._run_coro(impl(args), deadline)
            else:
                result = self._run_sync(impl, args, deadline)
            if idempotency_key:
                self._seen_idem[idempotency_key] = result
            if self._audit:
                self._audit("tool.invoked", actor, key, "ok",
                            {"elapsed_s": round(time.time() - t0, 3)})
            return result
        except TimeoutError:
            raise err("TIMEOUT", f"tool {key} exceeded {deadline}s",
                      remediation="raise timeoutSeconds or split the work")
        finally:
            LIMITER.release_inflight(ident)

    def _validate_args(self, schema: Dict[str, Any], args: Dict[str, Any]) -> List[str]:
        if not schema:
            return []
        import jsonschema
        try:
            jsonschema.validate(args, schema)
        except Exception as exc:  # ValidationError
            return [str(exc).split("\n")[0][:200]]
        return []

    def _run_sync(self, impl: Callable, args: Dict[str, Any], deadline: float) -> Any:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(impl, args)
            try:
                return fut.result(timeout=deadline)
            except concurrent.futures.TimeoutError:
                raise TimeoutError()

    def _run_coro(self, coro, deadline: float) -> Any:
        return asyncio.run(asyncio.wait_for(coro, timeout=deadline))
