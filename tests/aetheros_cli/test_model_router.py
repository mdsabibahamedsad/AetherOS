"""Tests for the model router (``aetheros_cli/model_router.py``).

The router resolves deterministic provider/model routes. Catalog-heavy modes
(cheapest/quality) read the models.dev cache; configured-aware modes read the
provider health list. We mock the catalog so tests stay hermetic.
"""

import pytest

from aetheros_cli import model_router
from aetheros_cli.model_router import ROUTING_MODES, resolve_route


def test_routing_modes_defined():
    assert set(ROUTING_MODES) == {"manual", "fastest", "cheapest", "quality", "offline", "enterprise"}


def test_unknown_mode_raises():
    with pytest.raises(ValueError):
        resolve_route("bogus")


def test_manual_returns_configured(monkeypatch):
    monkeypatch.setattr(model_router, "_default_route", lambda: ("openai-api", "gpt-5.4"))
    route = resolve_route("manual")
    assert route["provider"] == "openai-api"
    assert route["model"] == "gpt-5.4"
    assert route["configured"] is True


def test_fastest_prefers_local(monkeypatch):
    monkeypatch.setattr(model_router, "_local_providers", lambda: ["custom"])
    monkeypatch.setattr(model_router, "_configured_providers", lambda: ["custom"])
    monkeypatch.setattr(model_router, "_default_route", lambda: ("anthropic", "claude"))
    route = resolve_route("fastest")
    assert route["provider"] == "custom"
    assert "local" in route["rationale"]


def test_fastest_falls_back_to_configured_when_no_local(monkeypatch):
    monkeypatch.setattr(model_router, "_local_providers", lambda: [])
    monkeypatch.setattr(model_router, "_configured_providers", lambda: ["groq"])
    monkeypatch.setattr(model_router, "_default_route", lambda: ("gemini", "gemini-3"))
    route = resolve_route("fastest")
    assert route["provider"] == "groq"


def test_offline_requires_local_backend(monkeypatch):
    monkeypatch.setattr(model_router, "_local_providers", lambda: ["lmstudio"])
    monkeypatch.setattr(model_router, "_default_route", lambda: (None, None))
    route = resolve_route("offline")
    assert route["provider"] == "lmstudio"


def test_offline_no_local_falls_back(monkeypatch):
    monkeypatch.setattr(model_router, "_local_providers", lambda: [])
    monkeypatch.setattr(model_router, "_default_route", lambda: ("anthropic", "claude-sonnet"))
    route = resolve_route("offline")
    assert route["provider"] == "anthropic"
    assert route["configured"] is True


def test_enterprise_prefers_enterprise_provider(monkeypatch):
    monkeypatch.setattr(model_router, "_configured_providers", lambda: ["azure-foundry"])
    monkeypatch.setattr(model_router, "_default_route", lambda: ("anthropic", "claude"))
    route = resolve_route("enterprise")
    assert route["provider"] == "azure-foundry"


def test_enterprise_no_enterprise_falls_back(monkeypatch):
    monkeypatch.setattr(model_router, "_configured_providers", lambda: ["groq"])
    monkeypatch.setattr(model_router, "_default_route", lambda: ("groq", "llama-3.3"))
    route = resolve_route("enterprise")
    assert route["provider"] == "groq"
    assert route["configured"] is True


def test_cheapest_picks_lowest_cost(monkeypatch):
    rows = [
        {"provider": "p1", "model": "expensive", "cost": 100.0, "context": 1000, "reasoning": False},
        {"provider": "p2", "model": "cheap", "cost": 0.5, "context": 1000, "reasoning": False},
    ]
    monkeypatch.setattr(model_router, "_catalog_pricing", lambda: rows)
    monkeypatch.setattr(model_router, "_configured_providers", lambda: [])
    route = resolve_route("cheapest")
    assert route["provider"] == "p2"
    assert route["model"] == "cheap"


def test_quality_picks_reasoning_largest_context(monkeypatch):
    rows = [
        {"provider": "p1", "model": "big-reasoning", "cost": 50.0, "context": 500000, "reasoning": True},
        {"provider": "p2", "model": "small", "cost": 1.0, "context": 1000, "reasoning": False},
    ]
    monkeypatch.setattr(model_router, "_catalog_pricing", lambda: rows)
    monkeypatch.setattr(model_router, "_configured_providers", lambda: [])
    route = resolve_route("quality")
    assert route["provider"] == "p1"
    assert route["model"] == "big-reasoning"


def test_catalog_modes_prefer_configured_provider(monkeypatch):
    rows = [
        {"provider": "configured-p", "model": "local-best", "cost": 2.0, "context": 100000, "reasoning": True},
        {"provider": "other-p", "model": "global-best", "cost": 0.1, "context": 999999, "reasoning": True},
    ]
    monkeypatch.setattr(model_router, "_catalog_pricing", lambda: rows)
    monkeypatch.setattr(model_router, "_configured_providers", lambda: ["configured-p"])
    cheapest = resolve_route("cheapest")
    assert cheapest["provider"] == "configured-p"
    quality = resolve_route("quality")
    assert quality["provider"] == "configured-p"


def test_catalog_modes_fall_back_when_no_rows(monkeypatch):
    monkeypatch.setattr(model_router, "_catalog_pricing", lambda: [])
    monkeypatch.setattr(model_router, "_configured_providers", lambda: [])
    monkeypatch.setattr(model_router, "_default_route", lambda: ("gemini", "gemini-3"))
    for mode in ("cheapest", "quality"):
        route = resolve_route(mode)
        assert route["provider"] == "gemini"
        assert route["configured"] is True


def test_persist_route_writes_config(monkeypatch):
    written = {}

    def fake_set(key, value):
        written[key] = value

    monkeypatch.setattr("aetheros_cli.config.set_config_value", fake_set)
    assert model_router.persist_route({"provider": "groq", "model": "llama-3.3-70b"}) is True
    assert written["model.provider"] == "groq"
    assert written["model.default"] == "llama-3.3-70b"


def test_persist_route_noop_without_provider(monkeypatch):
    monkeypatch.setattr("aetheros_cli.config.set_config_value", lambda *a, **k: None)
    assert model_router.persist_route({"provider": None, "model": None}) is False
