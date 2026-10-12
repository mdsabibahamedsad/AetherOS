"""
Event-trigger specifications and safe structured filters (Master 13 Phases
9, 11, 17).

An automation may declare:

    "trigger": {
        "kind": "event",
        "event_types": ["file.created", "task.failed"],
        "filters": [{"path": "payload.path", "op": "prefix", "value": "/data"}],
        "cooldown_seconds": 120,
        "allow_untrusted": false
    }

Filter evaluation is a fixed operator set over dotted paths — no expression
language, no eval, no code execution. Unknown operators fail closed.
External (untrusted) events only match triggers that explicitly opt in via
``allow_untrusted: true``; even then payloads are used solely for matching,
never interpolated into prompts or permissions.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

FILTER_OPS = ("eq", "ne", "in", "prefix", "exists")

MAX_FILTERS = 16
MAX_EVENT_TYPES = 32


def normalize_trigger(value: Any) -> Optional[Dict[str, Any]]:
    """Validate + canonicalize a trigger spec. None/empty → None (schedule-driven)."""
    if value is None:
        return None
    if value == "" or value == {}:
        return None
    if not isinstance(value, dict):
        raise ValueError("trigger must be a mapping")
    kind = str(value.get("kind") or "").strip().lower()
    if kind in ("", "manual"):
        return None
    if kind != "event":
        raise ValueError(f"Unsupported trigger kind {kind!r}; supported: event")

    raw_types = value.get("event_types")
    if isinstance(raw_types, str):
        raw_types = [t for t in (s.strip() for s in raw_types.split(",")) if t]
    if not isinstance(raw_types, (list, tuple)) or not raw_types:
        raise ValueError("event trigger requires event_types (list or comma string)")
    types: List[str] = []
    for item in raw_types[:MAX_EVENT_TYPES]:
        text = str(item).strip()
        if not text:
            continue
        if any(ch.isspace() for ch in text) or len(text) > 120:
            raise ValueError(f"Invalid event_type {item!r}")
        if text not in types:
            types.append(text)
    if not types:
        raise ValueError("event trigger requires at least one event type")

    filters = _normalize_filters(value.get("filters"))
    cooldown_raw = value.get("cooldown_seconds")
    cooldown: Optional[int] = None
    if cooldown_raw not in (None, ""):
        try:
            cooldown = int(cooldown_raw)
        except (TypeError, ValueError):
            raise ValueError("trigger.cooldown_seconds must be an integer") from None
        if cooldown < 0:
            raise ValueError("trigger.cooldown_seconds must be >= 0")

    return {
        "kind": "event",
        "event_types": types,
        "filters": filters,
        "cooldown_seconds": cooldown,
        "allow_untrusted": bool(value.get("allow_untrusted", False)),
    }


def _normalize_filters(raw: Any) -> List[Dict[str, Any]]:
    """Canonicalize filter entries into {path, op, value} dicts."""
    if raw in (None, "", []):
        return []
    if isinstance(raw, dict):
        # Shorthand {"payload.status": "failed"} → eq matches.
        entries: Sequence[Any] = [
            {"path": k, "op": "eq", "value": v} for k, v in raw.items()
        ]
    elif isinstance(raw, (list, tuple)):
        entries = list(raw)
    else:
        raise ValueError("trigger.filters must be a mapping or a list")

    normalized: List[Dict[str, Any]] = []
    for entry in entries[:MAX_FILTERS]:
        if not isinstance(entry, dict):
            raise ValueError("each filter must be a mapping with path/op/value")
        path = str(entry.get("path") or "").strip().strip(".")
        op = str(entry.get("op") or "eq").strip().lower()
        if not path:
            raise ValueError("filter.path is required")
        if op not in FILTER_OPS:
            raise ValueError(
                f"filter.op {op!r} unsupported; allowed: {', '.join(FILTER_OPS)}"
            )
        normalized.append({"path": path, "op": op, "value": entry.get("value")})
    return normalized


def resolve_path(obj: Any, dotted: str) -> tuple:
    """Walk a dotted path through dicts/lists. Returns (found, value)."""
    current = obj
    for part in dotted.split("."):
        part = part.strip()
        if not part:
            continue
        if isinstance(current, dict):
            if part in current:
                current = current[part]
                continue
            return False, None
        if isinstance(current, (list, tuple)):
            try:
                index = int(part)
            except ValueError:
                return False, None
            if -len(current) <= index < len(current):
                current = current[index]
                continue
            return False, None
        return False, None
    return True, current


def _match_one(event_dict: Dict[str, Any], flt: Dict[str, Any]) -> bool:
    scope: Any = event_dict
    path = flt["path"]
    if path.startswith("event."):
        scope = event_dict
        path = path[len("event."):]
    elif not path.startswith("payload."):
        scope = {"value": event_dict.get("payload")}
        path = f"value.{path}" if path else "value"
    found, value = resolve_path(scope, path)
    op = flt["op"]
    expected = flt.get("value")

    if op == "exists":
        return found
    if not found:
        return False
    try:
        if op == "eq":
            return value == expected
        if op == "ne":
            return value != expected
        if op == "in":
            candidates = expected if isinstance(expected, (list, tuple, set)) else [expected]
            return value in candidates
        if op == "prefix":
            return (
                isinstance(value, str)
                and isinstance(expected, str)
                and value.startswith(expected)
            )
    except TypeError:
        return False
    return False


def event_matches(trigger: Optional[Dict[str, Any]], event_dict: Dict[str, Any]) -> bool:
    """Whether one normalized event satisfies one automation's trigger."""
    if not isinstance(trigger, dict) or trigger.get("kind") != "event":
        return False
    event_type = str(event_dict.get("event_type") or "")
    if event_type not in (trigger.get("event_types") or []):
        return False
    trust = str(event_dict.get("trust") or "internal")
    if trust == "external" and not trigger.get("allow_untrusted", False):
        logger.debug(
            "Trigger skipped external event %s (allow_untrusted=false)",
            event_type,
        )
        return False
    filters = trigger.get("filters") or []
    for flt in filters:
        try:
            if not _match_one(event_dict, flt):
                return False
        except Exception:
            logger.exception("Filter evaluation failed; failing closed")
            return False
    return True


def describe_trigger(trigger: Optional[Dict[str, Any]]) -> str:
    if not isinstance(trigger, dict) or trigger.get("kind") != "event":
        return "(schedule only)"
    parts = [", ".join(trigger.get("event_types") or [])]
    if trigger.get("filters"):
        parts.append(
            "%d filter(s)" % len(trigger["filters"])
        )
    if trigger.get("allow_untrusted"):
        parts.append("allows external events")
    return "on " + "; ".join(parts)
