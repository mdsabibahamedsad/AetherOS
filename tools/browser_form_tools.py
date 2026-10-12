"""
Master 15 browser form tools — purely ADDITIVE (Phases 19, 20, 52).

browser_form_fill batches field entry through the existing ``browser_type``
handler with per-field classification; browser_submit is confirmation-gated
(Phase 20), masks credential values in its summary, and blocks duplicate
submissions via idempotency (Phase 52). No working module is modified.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_MAX_FIELDS = 50

_FORM_STATE: Dict[str, Dict[str, Any]] = {}
_STATE_LOCK = threading.Lock()


def _err(msg: str, **extra) -> str:
    return json.dumps({"success": False, "error": msg, **extra}, ensure_ascii=False)


def _ok(payload: Dict[str, Any]) -> str:
    return json.dumps({"success": True, **payload}, ensure_ascii=False)


def _parse(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {"success": False, "error": "unparsable"}
    except Exception:
        return {"success": False, "error": str(raw)[:300]}


def _call_browser_type(ref: str, text: str, task_key: str) -> Dict[str, Any]:
    from tools.browser_tool import browser_type

    try:
        return _parse(browser_type(ref=ref, text=text, task_id=task_key))
    except TypeError:
        return _parse(browser_type(ref=ref, text=text))


def browser_form_fill(
    fields: Optional[Dict[str, str]] = None,
    field_meta: Optional[Dict[str, Dict[str, str]]] = None,
    task_id: str = "default",
    **kw,
) -> str:
    """Fill many fields at once. ``field_meta`` optionally supplies
    {ref: {name, type}} so classification can run on real field names."""
    del kw
    task_key = task_id or "default"
    fields = fields if isinstance(fields, dict) else None
    if not fields:
        return _err("fields mapping {ref: value} is required")
    if len(fields) > _MAX_FIELDS:
        return _err(f"too many fields ({len(fields)} > {_MAX_FIELDS})")

    from aetheros_computer.action import classify_field

    results = []
    classifications: Dict[str, str] = {}
    for i, (ref, value) in enumerate(fields.items()):
        meta = (field_meta or {}).get(ref) or {}
        cls = classify_field(str(meta.get("name", "")), str(meta.get("type", ""))).value
        classifications[ref] = cls
        parsed = _call_browser_type(str(ref), str(value), task_key)
        filled = bool(parsed.get("success"))
        results.append({
            "ref": ref,
            "classification": cls,
            "filled": filled,
            **({} if filled else {"error": parsed.get("error")}),
        })
        if not filled:
            return json.dumps({
                "success": False,
                "error": f"fill failed at field {i + 1}/{len(fields)}",
                "results": results,
            }, ensure_ascii=False)

    with _STATE_LOCK:
        _FORM_STATE[task_key] = {
            "fields": dict(fields),
            "classifications": dict(classifications),
        }
    has_sensitive = any(c in ("credential", "financial", "sensitive")
                        for c in classifications.values())
    return _ok({
        "filled": len(fields),
        "classifications": classifications,
        "sensitive_present": has_sensitive,
        "note": "submit requires explicit confirmation via browser_submit(confirm=true)",
    })


def _summary_lines(task_key: str, ref: str, account: str, destination: str) -> list:
    state = _FORM_STATE.get(task_key, {})
    fields: Dict[str, str] = state.get("fields", {})
    classifications: Dict[str, str] = state.get("classifications", {})
    lines = ["CONFIRM SUBMISSION", "", f"Action: form submit",
             f"Submit button: {ref}"]
    if destination:
        lines.append(f"Destination: {destination}")
    if account:
        lines.append(f"Account: {account}")
    lines.append("")
    lines.append(f"Fields to transmit ({len(fields)}):")
    for r, v in fields.items():
        shown = str(v)
        if classifications.get(r) == "credential":
            shown = "*" * min(len(shown), 12)
        else:
            shown = shown[:60]
        lines.append(f"  [{classifications.get(r, 'unknown'):>9}] {r}: {shown}")
    lines.append("")
    return lines


def browser_submit(
    ref: str = "",
    confirm: bool = False,
    account: str = "",
    destination: str = "",
    task_id: str = "default",
    **kw,
) -> str:
    del kw
    task_key = task_id or "default"
    if not ref:
        return _err("ref of the submit button is required")

    lines = _summary_lines(task_key, ref, account, destination)

    # Phase 20: never submit without explicit confirmation.
    if not confirm:
        return json.dumps({
            "success": False,
            "needs_confirmation": True,
            "summary": "\n".join(lines),
            "message": "Re-run with confirm=true to actually submit.",
        }, ensure_ascii=False)

    # Phase 52: duplicate-submission protection.
    from aetheros_computer.idempotency import check_and_record, make_key, reset_key

    state = _FORM_STATE.get(task_key, {})
    payload_digest = hashlib.sha256(
        json.dumps(sorted((state.get("fields") or {}).items()), sort_keys=True,
                   default=str).encode()
    ).hexdigest()[:16]
    idem = make_key("submit", task_key, ref, payload_digest)
    if check_and_record(idem):
        return _err("duplicate submission blocked (identical payload within TTL)",
                    duplicate=True, idempotency_key=idem)

    from tools.browser_tool import browser_click

    parsed = _parse(browser_click(ref=ref, task_id=task_key))
    if not parsed.get("success"):
        reset_key(idem)  # failed click may be retried later
        return json.dumps({"success": False, "error": parsed.get("error", "click failed")},
                          ensure_ascii=False)

    with _STATE_LOCK:
        _FORM_STATE.pop(task_key, None)  # one-shot: state consumed on success
    return _ok({"submitted": True, "idempotency_key": idem})


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
from tools.registry import registry  # noqa: E402

registry.register(
    name="browser_form_fill",
    toolset="browser",
    schema={
        "name": "browser_form_fill",
        "description": "Fill multiple form fields in one call through browser_type. Optionally pass field_meta ({ref:{name,type}}) to enable classification (public/personal/sensitive/credential/financial); credential values are masked in any later submission summary. Always ends needing explicit confirmation before submit.",
        "parameters": {
            "type": "object",
            "properties": {
                "fields": {
                    "type": "object",
                    "description": "{ref: value} mapping, e.g. {'@e1': 'John'}",
                    "additionalProperties": {"type": "string"},
                },
                "field_meta": {
                    "type": "object",
                    "description": "Optional {ref: {name, type}} metadata for classification",
                },
            },
            "required": ["fields"],
        },
    },
    handler=lambda args, **kw: browser_form_fill(
        fields=args.get("fields"),
        field_meta=args.get("field_meta"),
        task_id=kw.get("task_id") or "default",
    ),
)

registry.register(
    name="browser_submit",
    toolset="browser",
    schema={
        "name": "browser_submit",
        "description": "Confirmation-gated form submit through browser_click. First call WITHOUT confirm=true returns a summary (credential fields masked) and does nothing; re-run with confirm=true to execute. Identical payloads within TTL are blocked as duplicates.",
        "parameters": {
            "type": "object",
            "properties": {
                "ref": {"type": "string", "description": "Ref of the submit button"},
                "confirm": {"type": "boolean", "default": False,
                            "description": "Must be true to actually submit"},
                "account": {"type": "string", "description": "Optional account label for summary"},
                "destination": {"type": "string", "description": "Optional destination URL for summary"},
            },
            "required": ["ref"],
        },
    },
    handler=lambda args, **kw: browser_submit(
        ref=args.get("ref", ""), confirm=bool(args.get("confirm", False)),
        account=args.get("account", ""), destination=args.get("destination", ""),
        task_id=kw.get("task_id") or "default",
    ),
)
