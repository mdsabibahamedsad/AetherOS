"""Contract-check behavior: register() validates schemas (Master 12 Phase 7)."""

import logging

import pytest

from tools.registry import registry


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    registry.deregister("_m12_contract_ok")
    registry.deregister("_m12_contract_bad")
    registry.deregister("_m12_contract_noparams")


def _schema(name="x", params=True):
    s = {"name": name, "description": "contract test tool"}
    if params:
        s["parameters"] = {"type": "object", "properties": {}}
    return s


def test_valid_schema_marked_valid(caplog):
    with caplog.at_level(logging.WARNING, logger="tools.registry"):
        registry.register(
            name="_m12_contract_ok",
            toolset="debugging",
            schema=_schema("_m12_contract_ok"),
            handler=lambda **kw: "{}",
        )
    entry = registry.get_entry("_m12_contract_ok")
    assert entry is not None
    assert entry._schema_valid is True
    assert "schema invalid" not in caplog.text


def test_mismatched_schema_name_flagged_with_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="tools.registry"):
        registry.register(
            name="_m12_contract_bad",
            toolset="debugging",
            schema=_schema("some_other_name"),
            handler=lambda **kw: "{}",
        )
    entry = registry.get_entry("_m12_contract_bad")
    assert entry._schema_valid is False
    assert "_m12_contract_bad" in caplog.text
    assert "schema invalid" in caplog.text


def test_missing_parameters_flagged(caplog):
    with caplog.at_level(logging.WARNING, logger="tools.registry"):
        registry.register(
            name="_m12_contract_noparams",
            toolset="debugging",
            schema={"name": "_m12_contract_noparams"},
            handler=lambda **kw: "{}",
        )
    assert registry.get_entry("_m12_contract_noparams")._schema_valid is False
