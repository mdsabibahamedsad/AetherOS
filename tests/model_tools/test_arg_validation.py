"""Behavior contracts for the Phase 8 runtime argument-validation stage.

Registry handlers receive one positional ``args`` dict (the dispatch
contract), so every fake handler below mirrors that signature.
"""

import json

import pytest

import model_tools
from tools.registry import registry


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    registry.deregister("_m12_argval")
    model_tools.reset_tool_authorization_gate_cache()


def _register_args_tool(handler):
    registry.register(
        name="_m12_argval",
        toolset="debugging",
        schema={
            "name": "_m12_argval",
            "description": "arg validation contract tool",
            "parameters": {
                "type": "object",
                "required": ["path"],
                "properties": {
                    "path": {"type": "string"},
                    "retries": {"type": "integer"},
                    "ratio": {"type": "number"},
                    "flags": {"type": "boolean"},
                    "opts": {"type": "object"},
                    "tags": {"type": "array"},
                },
            },
        },
        handler=handler,
    )


def _call(args):
    return json.loads(
        model_tools.handle_function_call("_m12_argval", args, task_id="t")
    )


def _gate_on(monkeypatch):
    monkeypatch.setattr(
        model_tools,
        "_control_plane_flag",
        lambda flag, default=False: flag == "arg_validation",
    )


def _gate_off(monkeypatch):
    monkeypatch.setattr(
        model_tools, "_control_plane_flag", lambda flag, default=False: False
    )


def test_gate_off_invalid_args_still_dispatch(monkeypatch):
    """Legacy semantics: gate off → no argument rejection at all."""
    seen = {}

    def handler(args=None, **kw):
        seen.update(args or kw)
        return '{"ok": true}'

    _register_args_tool(handler)
    _gate_off(monkeypatch)

    payload = _call({"retries": "not-an-int"})  # wrong type AND missing path
    assert payload.get("ok") is True


def test_gate_on_missing_required_rejected_before_dispatch(monkeypatch):
    called = {"n": 0}

    def handler(args=None, **kw):
        called["n"] += 1
        return "{}"

    _register_args_tool(handler)
    _gate_on(monkeypatch)

    payload = _call({})
    assert payload["error_type"] == "invalid_arguments"
    assert "path" in payload["error"]
    assert called["n"] == 0


def test_gate_on_wrong_type_rejected(monkeypatch):
    def handler(args=None, **kw):
        return "{}"

    _register_args_tool(handler)
    _gate_on(monkeypatch)

    for bad in (
        {"path": 5},
        {"path": "ok", "retries": "three"},
        {"path": "ok", "flags": "yes"},
        {"path": "ok", "opts": [1]},
    ):
        payload = _call(bad)
        assert payload.get("error_type") == "invalid_arguments", f"case {bad}"


def test_gate_on_valid_args_pass_through(monkeypatch):
    def handler(args=None, **kw):
        return json.dumps({"got": (args or {}).get("path")})

    _register_args_tool(handler)
    _gate_on(monkeypatch)

    payload = _call({"path": "x.txt", "retries": 2.0})
    assert payload.get("got") == "x.txt"


def test_unknown_fields_not_rejected(monkeypatch):
    """additionalProperties defaults to allowed (JSON-Schema semantics)."""
    def handler(args=None, **kw):
        return '{"ok": true}'

    _register_args_tool(handler)
    _gate_on(monkeypatch)

    payload = _call({"path": "p", "extra_unknown": [1]})
    assert payload.get("ok") is True


def test_validator_unit_paths():
    def handler(args=None, **kw):
        return "{}"

    _register_args_tool(handler)
    v = model_tools.validate_tool_arguments
    assert v("_m12_argval", {"path": "p"}) is None
    assert "missing required" in v("_m12_argval", {})
    assert "integer" in v("_m12_argval", {"path": "p", "retries": 1.5})
    assert v("nonexistent_tool_xyz", {}) is None
