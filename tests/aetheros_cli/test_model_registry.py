"""Tests for the model registry (``aetheros_cli/model_registry.py``).

The registry is a pure per-model annotation store persisted as JSON under
``$AETHEROS_HOME/state/model_registry.json``. These tests use an isolated
path so no user state is touched.
"""

import pytest

from aetheros_cli.model_registry import ModelRegistry, search_models


@pytest.fixture
def registry(tmp_path):
    return ModelRegistry(path=tmp_path / "model_registry.json")


def test_empty_registry_has_no_flags(registry):
    assert registry.get("some-model") == {}
    assert registry.favorites == []
    assert registry.pinned == []
    assert registry.hidden == []
    assert registry.deprecated == []


def test_set_flag_and_persist(registry):
    assert registry.set_flag("model-a", "favorite", True) is True
    assert registry.flag("model-a", "favorite") is True
    assert registry.favorites == ["model-a"]
    # Reload from disk proves persistence.
    reloaded = ModelRegistry(path=registry.path)
    assert reloaded.flag("model-a", "favorite") is True


def test_toggle_flag(registry):
    assert registry.toggle("model-b", "pinned") is True
    assert registry.toggle("model-b", "pinned") is False
    assert registry.pinned == []


def test_unknown_flag_ignored(registry):
    assert registry.set_flag("m", "nonsense", True) is False
    assert registry.flag("m", "nonsense") is False


def test_empty_entry_pruned(registry):
    registry.set_flag("m", "favorite", True)
    registry.set_flag("m", "favorite", False)
    assert registry._data == {}
    assert registry.favorites == []


def test_sort_pinned_and_favorites_first(monkeypatch, registry):
    rows = [("p", "z-model"), ("p", "a-model"), ("p", "pinned-model"), ("p", "fav-model")]
    registry.set_flag("pinned-model", "pinned", True)
    registry.set_flag("fav-model", "favorite", True)
    monkeypatch.setattr("aetheros_cli.model_registry.get_registry", lambda: registry)
    ordered = ModelRegistry.sort_models(rows)
    assert ordered[0] == ("p", "pinned-model")
    assert ordered[1] == ("p", "fav-model")


def test_sort_by_name(monkeypatch, registry):
    rows = [("p", "z-model"), ("p", "a-model")]
    monkeypatch.setattr("aetheros_cli.model_registry.get_registry", lambda: registry)
    assert ModelRegistry.sort_models(rows, key="name") == [("p", "a-model"), ("p", "z-model")]


def test_filter_visible_drops_hidden(registry):
    registry.set_flag("secret", "hidden", True)
    rows = [("p", "visible"), ("p", "secret")]
    assert [r[1] for r in registry.filter_visible(rows)] == ["visible"]
    assert [r[1] for r in registry.filter_visible(rows, include_hidden=True)] == ["visible", "secret"]


def test_annotate(registry):
    registry.set_flag("m1", "favorite", True)
    rows = registry.annotate([("p", "m1"), ("p", "m2")])
    assert rows[0]["favorite"] is True
    assert rows[1]["favorite"] is False
    assert rows[0]["hidden"] is False


def _fake_providers():
    """Well-formed fake profiles — must carry the attrs models.py's auto-extend
    reads (name/auth_type/display_name/description) so triggering the first
    import of ``aetheros_cli.models`` under this patch doesn't AttributeError
    or truncate CANONICAL_PROVIDERS to just one provider."""
    class _P:
        def __init__(self, name):
            self.name = name
            self.auth_type = "api_key"
            self.display_name = name.title()
            self.description = "fake"
            self.fallback_models = ("m",)

    return [_P(n) for n in ("groq", "perplexity", "cloudflare", "mistral", "together", "fireworks", "cohere", "google-vertex-ai")]


def _patch_catalog(monkeypatch, model_ids):
    monkeypatch.setattr("providers.list_providers", _fake_providers)
    monkeypatch.setattr("aetheros_cli.models.provider_model_ids", lambda provider: list(model_ids))


def test_search_models_matches_substring(monkeypatch):
    """Substring search across the (provider, model) universe."""
    _patch_catalog(monkeypatch, ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"])
    results = search_models("70b", max_results=10)
    assert results and all(r["provider"] == "groq" for r in results)
    assert any("70b" in r["model"] for r in results)


def test_search_models_flag_filter(monkeypatch, registry):
    monkeypatch.setattr(
        "aetheros_cli.model_registry.get_registry",
        lambda: registry,
    )
    _patch_catalog(monkeypatch, ["favorite-model", "plain-model"])
    registry.set_flag("favorite-model", "favorite", True)
    results = search_models(flag="favorite")
    assert [r["model"] for r in results] == ["favorite-model"]


def test_search_models_excludes_hidden(monkeypatch, registry):
    monkeypatch.setattr(
        "aetheros_cli.model_registry.get_registry",
        lambda: registry,
    )
    _patch_catalog(monkeypatch, ["visible", "ghost"])
    registry.set_flag("ghost", "hidden", True)
    assert [r["model"] for r in search_models()] == ["visible"]
    # Default sort is provider/name, so ghost sorts before visible.
    assert set(r["model"] for r in search_models(include_hidden=True)) == {"visible", "ghost"}
