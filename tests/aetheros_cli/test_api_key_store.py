"""Tests for the provider API-key store (``aetheros_cli/api_key_store.py``).

The store reads ``security.api_key_storage`` from config to pick a backend
(env | keychain | auto). Tests force the ``env`` backend (the hermetic test
environment has no keychain) and use an isolated AETHEROS_HOME, so writes go
to a temp ``.env``.
"""

import pytest

from aetheros_cli import api_key_store


@pytest.fixture
def env_backend(monkeypatch):
    monkeypatch.setattr(api_key_store, "_config_backend", lambda: "env")
    return api_key_store


def test_storage_backend_resolves_auto(monkeypatch):
    monkeypatch.setattr(api_key_store, "_config_backend", lambda: "auto")
    monkeypatch.setattr(api_key_store, "_keychain_available", lambda: True)
    assert api_key_store.storage_backend() == "keychain"
    monkeypatch.setattr(api_key_store, "_keychain_available", lambda: False)
    assert api_key_store.storage_backend() == "env"


def test_env_backend_default(env_backend):
    assert env_backend.storage_backend() == "env"


def test_save_and_get_roundtrip(env_backend):
    assert env_backend.save_provider_key("groq", "sk-test-123")["success"] is True
    key = env_backend.get_provider_key("groq")
    assert key == "sk-test-123"


def test_get_missing_returns_none(env_backend):
    assert env_backend.get_provider_key("definitely-not-a-provider") is None


def test_remove_deletes(env_backend):
    env_backend.save_provider_key("groq", "sk-test-123")
    assert env_backend.remove_provider_key("groq") is True
    assert env_backend.get_provider_key("groq") is None


def test_rotate_replaces(env_backend):
    env_backend.save_provider_key("groq", "sk-old")
    result = env_backend.rotate_provider_key("groq", "sk-new")
    assert result["success"] is True
    assert env_backend.get_provider_key("groq") == "sk-new"


def test_empty_key_rejected(env_backend):
    result = env_backend.save_provider_key("groq", "   ")
    assert result["success"] is False
    assert result["error"] == "empty_key"


def test_list_includes_stored_provider(env_backend):
    env_backend.save_provider_key("groq", "sk-test-123")
    entries = env_backend.list_provider_keys()
    assert any(e["provider"] == "groq" and e["in_env"] for e in entries)


def test_export_import_roundtrip(env_backend, tmp_path):
    env_backend.save_provider_key("groq", "sk-export-1")
    exported = env_backend.export_keys()
    assert exported.get("groq") == "sk-export-1"

    path = tmp_path / "keys.json"
    env_backend.save_keys_to_file(str(path), {"mistral": "sk-export-2"})
    loaded = env_backend.load_keys_from_file(str(path))
    assert loaded["mistral"] == "sk-export-2"
    results = env_backend.import_keys(loaded)
    assert results["mistral"]["success"] is True
    assert env_backend.get_provider_key("mistral") == "sk-export-2"


def test_key_status_line_masks(env_backend):
    env_backend.save_provider_key("groq", "sk-abcdef123456")
    line = env_backend.key_status_line("groq")
    assert "3456" in line
    assert "sk-abcdef123456" not in line


def test_key_status_line_unconfigured(env_backend):
    assert env_backend.key_status_line("groq") == "(not configured)"
