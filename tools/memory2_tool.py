"""Memory 2.0 agent tools (Master 41 section 33).

Exposes scoped memory operations to the agent via the existing tool
registry.  All handlers go through the singleton ``MemoryService``; raw
storage is never exposed.  Secret-shaped writes are refused by the writer.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict

from tools.registry import registry

_lock = threading.Lock()
_service = None


def _svc():
    global _service
    with _lock:
        if _service is None:
            from aetheros_memory_intelligence.service import MemoryService
            _service = MemoryService()
            _service.initialize()
        return _service


def _ok(**kw: Any) -> str:
    return json.dumps(kw, ensure_ascii=False)


def memory2_search(args: Dict[str, Any], **kw: Any) -> str:
    svc = _svc()
    out = svc.retrieve(
        args.get("query", ""),
        project_id=args.get("project_id", ""),
        task_id=args.get("task_id", ""),
        top_k=int(args.get("top_k", 8)),
        budget=int(args.get("budget", 0)),
        mode=args.get("mode", "hybrid"))
    return _ok(success=True, **out)


def memory2_get(args: Dict[str, Any], **kw: Any) -> str:
    rec = _svc().get(args.get("id", ""))
    if rec is None:
        return _ok(success=False, error="not-found")
    return _ok(success=True, record=rec)


def memory2_create(args: Dict[str, Any], **kw: Any) -> str:
    from aetheros_memory_intelligence.record import ProvenanceKind, RecordScope, RecordType
    svc = _svc()
    rtype = args.get("type", "")
    out = svc.remember(
        args.get("content", ""),
        record_type=RecordType(rtype) if rtype else None,
        scope=RecordScope(args.get("scope", "user")),
        provenance=ProvenanceKind(args.get("provenance", "model_inferred")),
        project_id=args.get("project_id", ""),
        task_id=args.get("task_id", ""),
        session_id=args.get("session_id", ""),
        user_confirmed=bool(args.get("user_confirmed", False)),
        explicit=bool(args.get("explicit", False)),
        metadata=args.get("metadata") or {})
    return _ok(success=out.get("action") == "stored", **out)


def memory2_explain(args: Dict[str, Any], **kw: Any) -> str:
    exp = _svc().explain(args.get("id", ""))
    if exp is None:
        return _ok(success=False, error="not-found")
    return _ok(success=True, explanation=exp)


def memory2_forget(args: Dict[str, Any], **kw: Any) -> str:
    out = _svc().forget(record_id=args.get("id", ""),
                        topic=args.get("topic", ""),
                        project_id=args.get("project_id", ""),
                        all_memories=bool(args.get("all", False)))
    return _ok(success=True, **out)


def memory2_project(args: Dict[str, Any], **kw: Any) -> str:
    view = _svc().get_project_memory(args.get("project_id", ""))
    return _ok(success=True, project=view)


def memory2_graph(args: Dict[str, Any], **kw: Any) -> str:
    g = _svc().get_entity_graph(args.get("entity_id", ""),
                                depth=int(args.get("depth", 1)),
                                project_id=args.get("project_id", ""))
    return _ok(success=True, graph=g)


def memory2_conflicts(args: Dict[str, Any], **kw: Any) -> str:
    out = _svc().resolve_conflicts()
    quality = _svc().quality()
    return _ok(success=True, resolved=out, quality=quality)


def _check() -> bool:
    return True


_BASE = {"type": "object", "properties": {}, "additionalProperties": True}

registry.register(
    name="memory2_search",
    toolset="memory",
    schema={"name": "memory2_search",
            "description": "Search long-term memory (hybrid retrieval with scope isolation and budget).",
            "parameters": {"type": "object",
                           "properties": {"query": {"type": "string"},
                                          "project_id": {"type": "string"},
                                          "task_id": {"type": "string"},
                                          "top_k": {"type": "integer"},
                                          "budget": {"type": "integer"},
                                          "mode": {"type": "string"}},
                           "required": ["query"]}},
    handler=lambda args, **k: memory2_search(args, **k),
    check_fn=_check)

registry.register(
    name="memory2_get",
    toolset="memory",
    schema={"name": "memory2_get",
            "description": "Get a single memory record by id.",
            "parameters": {"type": "object",
                           "properties": {"id": {"type": "string"}},
                           "required": ["id"]}},
    handler=lambda args, **k: memory2_get(args, **k),
    check_fn=_check)

registry.register(
    name="memory2_create",
    toolset="memory",
    schema={"name": "memory2_create",
            "description": "Store a long-term memory (gated: secrets/trivial refused, untrusted preferences suggested).",
            "parameters": {"type": "object",
                           "properties": {"content": {"type": "string"},
                                          "type": {"type": "string"},
                                          "scope": {"type": "string"},
                                          "provenance": {"type": "string"},
                                          "project_id": {"type": "string"},
                                          "task_id": {"type": "string"},
                                          "session_id": {"type": "string"},
                                          "user_confirmed": {"type": "boolean"},
                                          "explicit": {"type": "boolean"}},
                           "required": ["content"]}},
    handler=lambda args, **k: memory2_create(args, **k),
    check_fn=_check)

registry.register(
    name="memory2_explain",
    toolset="memory",
    schema={"name": "memory2_explain",
            "description": "Explain why a memory exists (provenance, confidence, evidence).",
            "parameters": {"type": "object",
                           "properties": {"id": {"type": "string"}},
                           "required": ["id"]}},
    handler=lambda args, **k: memory2_explain(args, **k),
    check_fn=_check)

registry.register(
    name="memory2_forget",
    toolset="memory",
    schema={"name": "memory2_forget",
            "description": "Forget a memory, topic, project, or all memories (tombstone + invalidate).",
            "parameters": {"type": "object",
                           "properties": {"id": {"type": "string"},
                                          "topic": {"type": "string"},
                                          "project_id": {"type": "string"},
                                          "all": {"type": "boolean"}}}},
    handler=lambda args, **k: memory2_forget(args, **k),
    check_fn=_check)

registry.register(
    name="memory2_project",
    toolset="memory",
    schema={"name": "memory2_project",
            "description": "Get the live project memory view (decisions, tasks, research, files).",
            "parameters": {"type": "object",
                           "properties": {"project_id": {"type": "string"}},
                           "required": ["project_id"]}},
    handler=lambda args, **k: memory2_project(args, **k),
    check_fn=_check)

registry.register(
    name="memory2_graph",
    toolset="memory",
    schema={"name": "memory2_graph",
            "description": "Query the personal knowledge graph (entities/relationships).",
            "parameters": {"type": "object",
                           "properties": {"entity_id": {"type": "string"},
                                          "depth": {"type": "integer"},
                                          "project_id": {"type": "string"}}}},
    handler=lambda args, **k: memory2_graph(args, **k),
    check_fn=_check)

registry.register(
    name="memory2_conflicts",
    toolset="memory",
    schema={"name": "memory2_conflicts",
            "description": "Resolve memory conflicts and report quality issues.",
            "parameters": _BASE},
    handler=lambda args, **k: memory2_conflicts(args, **k),
    check_fn=_check)
