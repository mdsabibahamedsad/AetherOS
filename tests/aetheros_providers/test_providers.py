"""Tests for AetherOS AI Provider & Model Management System."""

import json
import os
import sys
import time
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from aetheros_providers.provider_manager import ProviderManager, ProviderStatus, ProviderInfo
from aetheros_providers.api_key_manager import APIKeyManager, APIKeyInfo, KeyStatus
from aetheros_providers.model_database import ModelDatabase, ModelInfo, ModelCapability
from aetheros_providers.model_selector import ModelSelector, ModelFilter
from aetheros_providers.model_registry import DefaultModelRegistry, TaskType, ModelAssignment
from aetheros_providers.failover import FailoverManager, FailoverStrategy, FailoverConfig, FailoverResult
from aetheros_providers.local_model_manager import LocalModelManager, LocalProvider, LocalProviderInstance
from aetheros_providers.provider_settings import ProviderSettingsManager, ProviderSettings
from aetheros_providers.model_validator import ModelValidator, ValidationResult
from aetheros_providers.multi_provider import MultiProviderOrchestrator, WorkflowStage


# ---------------------------------------------------------------------------
# ProviderManager tests
# ---------------------------------------------------------------------------

class TestProviderManager:
    def test_register(self):
        pm = ProviderManager()
        info = pm.register("test_provider", "Test Provider", priority=10)
        assert info.name == "test_provider"
        assert info.display_name == "Test Provider"
        assert info.priority == 10
        assert info.status == ProviderStatus.UNKNOWN

    def test_register_duplicate(self):
        pm = ProviderManager()
        pm.register("test", "Test")
        info = pm.register("test", "Test 2")
        assert info.display_name == "Test 2"

    def test_enable_disable(self):
        pm = ProviderManager()
        pm.register("test", "Test")
        assert pm.enable("test")
        assert pm.get_info("test").enabled
        assert pm.disable("test")
        assert not pm.get_info("test").enabled
        assert pm.get_info("test").status == ProviderStatus.DISABLED

    def test_enable_nonexistent(self):
        pm = ProviderManager()
        assert not pm.enable("nonexistent")

    def test_remove(self):
        pm = ProviderManager()
        pm.register("test", "Test")
        assert pm.remove("test")
        assert pm.get_info("test") is None
        assert not pm.remove("test")

    def test_get_status(self):
        pm = ProviderManager()
        pm.register("test", "Test")
        assert pm.get_status("test") == ProviderStatus.UNKNOWN
        assert pm.get_status("nonexistent") is None

    def test_health_check_no_fn(self):
        pm = ProviderManager()
        pm.register("test", "Test")
        assert pm.check_health("test")
        assert pm.get_info("test").status == ProviderStatus.ONLINE

    def test_health_check_passes(self):
        pm = ProviderManager()
        pm.register("test", "Test", health_check_fn=lambda: True)
        assert pm.check_health("test")

    def test_health_check_fails(self):
        pm = ProviderManager()
        pm.register("test", "Test", health_check_fn=lambda: False)
        assert not pm.check_health("test")
        assert pm.get_info("test").status == ProviderStatus.DEGRADED

    def test_health_check_exception(self):
        pm = ProviderManager()
        pm.register("test", "Test", health_check_fn=lambda: (_ for _ in ()).throw(Exception("fail")))
        assert not pm.check_health("test")
        assert pm.get_info("test").status == ProviderStatus.ERROR

    def test_health_check_disabled(self):
        pm = ProviderManager()
        pm.register("test", "Test", health_check_fn=lambda: True)
        pm.disable("test")
        assert not pm.check_health("test")

    def test_check_all_health(self):
        pm = ProviderManager()
        pm.register("a", "A", health_check_fn=lambda: True)
        pm.register("b", "B", health_check_fn=lambda: False)
        results = pm.check_all_health()
        assert results["a"]
        assert not results["b"]

    def test_get_healthy_providers(self):
        pm = ProviderManager()
        pm.register("a", "A", health_check_fn=lambda: True)
        pm.register("b", "B", health_check_fn=lambda: False)
        pm.check_all_health()
        assert len(pm.get_healthy_providers()) == 1

    def test_get_enabled_providers(self):
        pm = ProviderManager()
        pm.register("a", "A")
        pm.register("b", "B")
        pm.disable("b")
        enabled = pm.get_enabled_providers()
        assert len(enabled) == 1
        assert enabled[0].name == "a"

    def test_priority_ordering(self):
        pm = ProviderManager()
        pm.register("low", "Low", priority=1)
        pm.register("high", "High", priority=10)
        ordered = pm.get_providers_by_priority()
        assert ordered[0].name == "high"
        assert ordered[1].name == "low"

    def test_get_providers_by_type(self):
        pm = ProviderManager()
        pm.register("cloud", "Cloud", provider_type="cloud")
        pm.register("local", "Local", provider_type="local")
        cloud = pm.get_providers_by_type("cloud")
        assert len(cloud) == 1

    def test_fallback_chain(self):
        pm = ProviderManager()
        pm.register("primary", "Primary")
        pm.register("backup", "Backup")
        pm.set_fallback_chain("primary", ["backup"])
        assert pm.get_fallback_chain("primary") == ["backup"]
        resolved = pm.resolve_with_fallback("primary")
        assert resolved == ["primary", "backup"]

    def test_fallback_chain_disabled(self):
        pm = ProviderManager()
        pm.register("primary", "Primary")
        pm.register("backup", "Backup")
        pm.disable("backup")
        pm.set_fallback_chain("primary", ["backup"])
        resolved = pm.resolve_with_fallback("primary")
        assert resolved == ["primary"]

    def test_priority_set_and_get_prioritized(self):
        pm = ProviderManager()
        pm.register("a", "A")
        pm.set_priority("a", 50)
        assert pm.get_info("a").priority == 50
        prioritized = pm.get_prioritized(["a"])
        assert len(prioritized) == 1

    def test_on_status_change(self):
        pm = ProviderManager()
        pm.register("test", "Test")
        events = []
        pm.on_status_change(lambda n, o, new: events.append((n, o, new)))
        pm.disable("test")
        assert len(events) == 1
        assert events[0][0] == "test"

    def test_mark_recovered(self):
        pm = ProviderManager()
        pm.register("test", "Test", health_check_fn=lambda: False)
        pm.check_health("test")
        pm.mark_recovered("test")
        assert pm.get_info("test").status == ProviderStatus.ONLINE
        assert pm.get_info("test").consecutive_failures == 0

    def test_properties(self):
        pm = ProviderManager()
        pm.register("a", "A")
        pm.register("b", "B")
        assert len(pm.all_providers) == 2
        assert "a" in pm.provider_names
        assert pm.online_count == 0
        assert pm.enabled_count == 2

    def test_summary(self):
        pm = ProviderManager()
        pm.register("test", "Test")
        s = pm.summary()
        assert "Test" in s
        assert "1 enabled" in s

    def test_register_from_profile(self):
        pm = ProviderManager()
        profile = MagicMock()
        profile.name = "custom"
        profile.display_name = "Custom Provider"
        info = pm.register_from_profile(profile)
        assert info.name == "custom"

    @patch("aetheros_providers.provider_manager.ProviderManager.discover_all")
    def test_discover_all(self, mock_discover):
        mock_discover.return_value = 5
        count = ProviderManager().discover_all()
        assert count == 5


# ---------------------------------------------------------------------------
# APIKeyManager tests
# ---------------------------------------------------------------------------

class TestAPIKeyManager:
    def test_add_key(self):
        km = APIKeyManager()
        info = km.add_key("openai", "sk-test123456789", is_primary=True)
        assert info.provider == "openai"
        assert info.is_primary
        assert info.status == KeyStatus.VALID

    def test_get_key(self):
        km = APIKeyManager()
        km.add_key("openai", "sk-test123456789", key_id="k1", validate=False)
        assert km.get_key("k1") == "sk-test123456789"

    def test_get_info(self):
        km = APIKeyManager()
        km.add_key("openai", "sk-test123456789", key_id="k1", validate=False)
        info = km.get_info("k1")
        assert info.key_preview == "sk-t****6789"

    def test_remove_key(self):
        km = APIKeyManager()
        km.add_key("openai", "sk-test", key_id="k1", validate=False)
        assert km.remove_key("k1")
        assert km.get_key("k1") is None
        assert not km.remove_key("k1")

    def test_get_keys_for_provider(self):
        km = APIKeyManager()
        km.add_key("openai", "key1", key_id="k1", validate=False)
        km.add_key("openai", "key2", key_id="k2", validate=False)
        keys = km.get_keys_for_provider("openai")
        assert len(keys) == 2

    def test_get_primary_key(self):
        km = APIKeyManager()
        km.add_key("openai", "primary", key_id="k1", is_primary=True, validate=False)
        km.add_key("openai", "secondary", key_id="k2", validate=False)
        assert km.get_primary_key("openai") == "primary"

    def test_get_primary_key_fallback(self):
        km = APIKeyManager()
        km.add_key("openai", "only", key_id="k1", validate=False)
        assert km.get_primary_key("openai") == "only"

    def test_set_primary(self):
        km = APIKeyManager()
        km.add_key("openai", "a", key_id="k1", is_primary=True, validate=False)
        km.add_key("openai", "b", key_id="k2", validate=False)
        assert km.set_primary("k2")
        assert km.get_info("k2").is_primary
        assert not km.get_info("k1").is_primary

    def test_set_primary_nonexistent(self):
        km = APIKeyManager()
        assert not km.set_primary("nonexistent")

    def test_list_providers_with_keys(self):
        km = APIKeyManager()
        km.add_key("openai", "sk-test", key_id="k1", validate=False)
        km.add_key("anthropic", "sk-ant", key_id="k2", validate=False)
        providers = km.list_providers_with_keys()
        assert "openai" in providers
        assert "anthropic" in providers

    def test_has_any_key(self):
        km = APIKeyManager()
        assert not km.has_any_key()
        km.add_key("openai", "sk-test", key_id="k1", validate=False)
        assert km.has_any_key()

    def test_register_validator(self):
        km = APIKeyManager()
        km.register_validator("custom", lambda k: KeyStatus.VALID)
        km.add_key("custom", "key", key_id="k1")
        assert km.get_info("k1").status == KeyStatus.VALID

    def test_validate_key_no_validator(self):
        km = APIKeyManager()
        km.add_key("openai", "key", key_id="k1", validate=False)
        assert km.validate_key("k1") == KeyStatus.VALID

    def test_validate_key_nonexistent(self):
        km = APIKeyManager()
        assert km.validate_key("nonexistent") == KeyStatus.UNVERIFIED

    def test_validate_key_no_value(self):
        km = APIKeyManager()
        km._keys["k1"] = APIKeyInfo(key_id="k1", provider="openai", key_preview="****")
        assert km.validate_key("k1") == KeyStatus.INVALID

    def test_validate_key_validator_raises(self):
        km = APIKeyManager()
        km.register_validator("buggy", lambda k: (_ for _ in ()).throw(Exception("fail")))
        km.add_key("buggy", "key", key_id="k1", validate=False)
        assert km.validate_key("k1") == KeyStatus.INVALID

    def test_validate_all_keys(self):
        km = APIKeyManager()
        km.add_key("openai", "key1", key_id="k1", validate=False)
        km.add_key("anthropic", "key2", key_id="k2", validate=False)
        results = km.validate_all_keys()
        assert len(results) == 2

    def test_detect_duplicates(self):
        km = APIKeyManager()
        km.add_key("openai", "samevalue", key_id="k1", validate=False)
        km.add_key("anthropic", "samevalue", key_id="k2", validate=False)
        dups = km.detect_duplicates()
        assert len(dups) == 1

    def test_detect_expired_keys(self):
        km = APIKeyManager()
        km.add_key("openai", "key", key_id="k1", validate=False)
        km._keys["k1"].status = KeyStatus.EXPIRED
        expired = km.detect_expired_keys()
        assert "k1" in expired

    def test_get_rate_limited_keys(self):
        km = APIKeyManager()
        km.add_key("openai", "key", key_id="k1", validate=False)
        km._keys["k1"].status = KeyStatus.RATE_LIMITED
        km._keys["k1"].rate_limit_reset = time.time() + 60
        limited = km.get_rate_limited_keys()
        assert "k1" in limited

    def test_get_rate_limited_keys_expired_reset(self):
        km = APIKeyManager()
        km.add_key("openai", "key", key_id="k1", validate=False)
        km._keys["k1"].status = KeyStatus.RATE_LIMITED
        km._keys["k1"].rate_limit_reset = time.time() - 10
        limited = km.get_rate_limited_keys()
        assert "k1" not in limited

    def test_update_rate_limit(self):
        km = APIKeyManager()
        km.add_key("openai", "key", key_id="k1", validate=False)
        km.update_rate_limit("k1", 0, time.time() + 60)
        assert km.get_info("k1").status == KeyStatus.RATE_LIMITED

    def test_update_rate_limit_positive(self):
        km = APIKeyManager()
        km.add_key("openai", "key", key_id="k1", validate=False)
        km.update_rate_limit("k1", 10, time.time() + 60)
        assert km.get_info("k1").rate_limit_remaining == 10

    def test_preview_key_short(self):
        assert APIKeyManager._preview_key("abc") == "ab****"
        assert APIKeyManager._preview_key("abcdefgh") == "abcd****efgh"

    def test_preview_key_long(self):
        preview = APIKeyManager._preview_key("sk-test123456789")
        assert preview == "sk-t****6789"

    def test_get_default_base_url(self):
        assert "api.openai.com" in APIKeyManager._get_default_base_url("openai")
        assert APIKeyManager._get_default_base_url("unknown") == ""

    def test_test_connection(self):
        km = APIKeyManager()
        result = km.test_connection("unknown", "key")
        assert not result["success"]
        assert "No base URL" in result["error"]


# ---------------------------------------------------------------------------
# ModelDatabase tests
# ---------------------------------------------------------------------------

class TestModelDatabase:
    def _make_model(self, model_id="gpt-4o", provider="openai", **kw):
        defaults = dict(model_id=model_id, provider=provider, display_name=model_id,
                        context_window=128000, capabilities=ModelCapability.CHAT)
        defaults.update(kw)
        return ModelInfo(**defaults)

    def test_add_and_get_model(self):
        db = ModelDatabase()
        model = self._make_model()
        db.add_model(model)
        retrieved = db.get_model("openai", "gpt-4o")
        assert retrieved is not None
        assert retrieved.model_id == "gpt-4o"

    def test_get_model_nonexistent(self):
        db = ModelDatabase()
        assert db.get_model("nonexistent", "model") is None

    def test_add_models(self):
        db = ModelDatabase()
        models = [self._make_model("a"), self._make_model("b")]
        db.add_models("openai", models)
        assert db.get_model_count("openai") == 2
        assert db.get_model_count() == 2

    def test_remove_model(self):
        db = ModelDatabase()
        model = self._make_model()
        db.add_model(model)
        assert db.remove_model("openai", "gpt-4o")
        assert db.get_model("openai", "gpt-4o") is None

    def test_remove_nonexistent(self):
        db = ModelDatabase()
        assert not db.remove_model("x", "y")

    def test_remove_provider(self):
        db = ModelDatabase()
        db.add_models("openai", [self._make_model("a"), self._make_model("b")])
        assert db.remove_provider("openai") == 2
        assert db.get_model_count("openai") == 0

    def test_search(self):
        db = ModelDatabase()
        db.add_model(self._make_model("gpt-4o"))
        db.add_model(self._make_model("claude-sonnet-4", provider="anthropic"))
        results = db.search("gpt")
        assert len(results) >= 1
        assert results[0].model_id == "gpt-4o"

    def test_filter_by_providers(self):
        db = ModelDatabase()
        db.add_model(self._make_model("a", provider="openai"))
        db.add_model(self._make_model("b", provider="anthropic"))
        results = db.filter(providers=["openai"])
        assert len(results) == 1

    def test_filter_by_capabilities(self):
        db = ModelDatabase()
        db.add_model(self._make_model("a", capabilities=ModelCapability.CHAT | ModelCapability.VISION))
        db.add_model(self._make_model("b", capabilities=ModelCapability.CHAT))
        results = db.filter(capabilities=ModelCapability.VISION)
        assert len(results) == 1

    def test_filter_by_min_context(self):
        db = ModelDatabase()
        db.add_model(self._make_model("a", context_window=1000))
        db.add_model(self._make_model("b", context_window=200000))
        results = db.filter(min_context=100000)
        assert len(results) == 1

    def test_filter_local_only(self):
        db = ModelDatabase()
        db.add_model(self._make_model("a", is_local=False))
        db.add_model(self._make_model("b", is_local=True))
        results = db.filter(local_only=True)
        assert len(results) == 1

    def test_filter_cloud_only(self):
        db = ModelDatabase()
        db.add_model(self._make_model("a", is_local=False))
        db.add_model(self._make_model("b", is_local=True))
        results = db.filter(cloud_only=True)
        assert len(results) == 1

    def test_filter_favorites_only(self):
        db = ModelDatabase()
        db.add_model(self._make_model("a", is_favorite=True))
        db.add_model(self._make_model("b"))
        results = db.filter(favorites_only=True)
        assert len(results) == 1

    def test_toggle_favorite(self):
        db = ModelDatabase()
        db.add_model(self._make_model("a"))
        assert db.toggle_favorite("openai", "a")
        assert not db.toggle_favorite("openai", "a")

    def test_toggle_pin(self):
        db = ModelDatabase()
        db.add_model(self._make_model("a"))
        assert db.toggle_pin("openai", "a")
        pinned = db.get_pinned()
        assert len(pinned) == 1

    def test_mark_used(self):
        db = ModelDatabase()
        db.add_model(self._make_model("a"))
        db.mark_used("openai", "a")
        recently = db.get_recently_used()
        assert len(recently) == 1
        assert db.get_model("openai", "a").use_count == 1

    def test_mark_used_max_recent(self):
        db = ModelDatabase()
        db._max_recent = 3
        for i in range(5):
            db.add_model(self._make_model(f"model-{i}"))
            db.mark_used("openai", f"model-{i}")
        assert len(db.get_recently_used()) == 3

    def test_register_provider_fetch(self):
        db = ModelDatabase()
        fn = lambda: [{"id": "fetched-model"}]
        db.register_provider_fetch("custom", fn)
        assert db._fetch_fns["custom"] == fn

    def test_fetch_models_cached(self):
        db = ModelDatabase()
        db.add_model(self._make_model("cached-model"))
        db._last_fetch["openai"] = time.time()
        models = db.fetch_models("openai")
        assert len(models) == 1

    def test_fetch_models_no_fn(self):
        db = ModelDatabase()
        models = db.fetch_models("unknown")
        assert models == []

    def test_fetch_models_uses_fn(self):
        db = ModelDatabase()
        fn = lambda: [{"id": "fresh-model", "supports_streaming": True}]
        db.register_provider_fetch("custom", fn)
        models = db.fetch_models("custom", force=True)
        assert len(models) == 1
        assert models[0].model_id == "fresh-model"

    def test_fetch_models_fn_fails(self):
        db = ModelDatabase()
        fn = lambda: (_ for _ in ()).throw(Exception("fail"))
        db.register_provider_fetch("failing", fn)
        db.add_model(self._make_model("existing", provider="failing"))
        models = db.fetch_models("failing", force=True)
        assert len(models) == 1

    def test_fetch_all(self):
        db = ModelDatabase()
        db.register_provider_fetch("p1", lambda: [{"id": "m1"}])
        db.register_provider_fetch("p2", lambda: [{"id": "m2"}])
        results = db.fetch_all(force=True)
        assert results["p1"] == 1
        assert results["p2"] == 1

    def test_set_cache_ttl(self):
        db = ModelDatabase()
        db.set_cache_ttl(300)
        assert db._cache_ttl == 300

    def test_clear_cache(self):
        db = ModelDatabase()
        db.add_model(self._make_model("a"))
        db.clear_cache()
        assert db.get_model_count() == 0

    def test_cache_persistence(self, tmp_path):
        db = ModelDatabase(cache_dir=tmp_path)
        db.add_model(self._make_model("persisted"))
        db._save_cache()
        assert (tmp_path / "model_cache.json").exists()

    def test_refresh_if_stale(self):
        db = ModelDatabase()
        db.register_provider_fetch("openai", lambda: [{"id": "fresh"}])
        db._last_fetch["openai"] = time.time() - 7200
        count = db.refresh_if_stale()
        assert count == 1

    def test_model_info_properties(self):
        model = self._make_model(capabilities=ModelCapability.CHAT | ModelCapability.VISION | ModelCapability.STREAMING,
                                  context_window=200000, latency_class="fast",
                                  input_price_per_mtok=0.15, output_price_per_mtok=0.60)
        assert model.supports_vision
        assert not model.supports_reasoning
        assert model.supports_streaming
        assert model.is_chat_model
        assert model.is_cheap
        assert model.has_large_context
        assert model.is_fast

    def test_get_all_models(self):
        db = ModelDatabase()
        db.add_model(self._make_model("a"))
        db.add_model(self._make_model("b"))
        assert len(db.get_all_models()) == 2

    def test_get_favorites(self):
        db = ModelDatabase()
        db.add_model(self._make_model("a", is_favorite=True))
        db.add_model(self._make_model("b"))
        assert len(db.get_favorites()) == 1

    def test_get_pinned(self):
        db = ModelDatabase()
        db.add_model(self._make_model("a", is_pinned=True))
        assert len(db.get_pinned()) == 1

    def test_raw_to_model(self):
        raw = {"id": "gpt-4", "display_name": "GPT-4", "context_window": 8192,
               "supports_vision": True, "supports_tools": True, "supports_streaming": True}
        model = ModelDatabase._raw_to_model(raw, "openai")
        assert model.model_id == "gpt-4"
        assert model.supports_vision
        assert model.supports_tools
        assert model.supports_streaming


# ---------------------------------------------------------------------------
# ModelSelector tests
# ---------------------------------------------------------------------------

class TestModelSelector:
    def _setup(self):
        db = ModelDatabase()
        db.add_model(ModelInfo(model_id="gpt-4o", provider="openai", display_name="GPT-4o",
                               context_window=128000, input_price_per_mtok=2.50, output_price_per_mtok=10.00,
                               capabilities=ModelCapability.CHAT | ModelCapability.VISION | ModelCapability.TOOL_CALLING | ModelCapability.STREAMING,
                               latency_class="fast"))
        db.add_model(ModelInfo(model_id="claude-sonnet-4", provider="anthropic", display_name="Claude Sonnet 4",
                               context_window=200000, input_price_per_mtok=3.00, output_price_per_mtok=15.00,
                               capabilities=ModelCapability.CHAT | ModelCapability.TOOL_CALLING | ModelCapability.STREAMING | ModelCapability.REASONING | ModelCapability.CODE,
                               latency_class="fast"))
        db.add_model(ModelInfo(model_id="gpt-4o-mini", provider="openai", display_name="GPT-4o Mini",
                               context_window=128000, input_price_per_mtok=0.15, output_price_per_mtok=0.60,
                               capabilities=ModelCapability.CHAT | ModelCapability.TOOL_CALLING | ModelCapability.STREAMING,
                               latency_class="very_fast"))
        db.add_model(ModelInfo(model_id="llama-local", provider="ollama", display_name="Llama Local",
                               context_window=4096, input_price_per_mtok=0, output_price_per_mtok=0,
                               capabilities=ModelCapability.CHAT | ModelCapability.STREAMING,
                               is_local=True, latency_class="fast"))
        return ModelSelector(db)

    def test_select_all(self):
        sel = self._setup()
        results = sel.select_models(ModelFilter())
        assert len(results) == 4

    def test_select_vision(self):
        sel = self._setup()
        results = sel.select_models(ModelFilter(vision=True))
        assert len(results) == 1
        assert results[0].model_id == "gpt-4o"

    def test_select_reasoning(self):
        sel = self._setup()
        results = sel.select_models(ModelFilter(reasoning=True))
        assert len(results) == 1
        assert results[0].model_id == "claude-sonnet-4"

    def test_select_cheap(self):
        sel = self._setup()
        results = sel.select_models(ModelFilter(cheap=True))
        assert len(results) == 2

    def test_select_local(self):
        sel = self._setup()
        results = sel.select_models(ModelFilter(local=True))
        assert len(results) == 1
        assert results[0].provider == "ollama"

    def test_select_cloud(self):
        sel = self._setup()
        results = sel.select_models(ModelFilter(cloud=True))
        assert len(results) == 3

    def test_select_by_provider(self):
        sel = self._setup()
        results = sel.select_models(ModelFilter(providers=["anthropic"]))
        assert len(results) == 1

    def test_select_with_query(self):
        sel = self._setup()
        results = sel.select_models(ModelFilter(query="mini"))
        assert len(results) == 1

    def test_suggest_for_task_vision(self):
        sel = self._setup()
        results = sel.suggest_for_task("vision")
        assert len(results) >= 1

    def test_suggest_for_task_code(self):
        sel = self._setup()
        results = sel.suggest_for_task("code")
        assert len(results) >= 1

    def test_suggest_for_task_reasoning(self):
        sel = self._setup()
        results = sel.suggest_for_task("reasoning")
        assert len(results) >= 1

    def test_suggest_for_task_cheap(self):
        sel = self._setup()
        results = sel.suggest_for_task("cheap")
        assert len(results) >= 1

    def test_suggest_for_task_fast(self):
        sel = self._setup()
        results = sel.suggest_for_task("fast")
        assert len(results) >= 1

    def test_suggest_for_task_large(self):
        sel = self._setup()
        results = sel.suggest_for_task("large")
        assert len(results) >= 1

    def test_suggest_for_task_local(self):
        sel = self._setup()
        results = sel.suggest_for_task("local")
        assert len(results) >= 1

    def test_suggest_for_task_streaming(self):
        sel = self._setup()
        results = sel.suggest_for_task("streaming")
        assert len(results) >= 1

    def test_suggest_for_task_unknown(self):
        sel = self._setup()
        results = sel.suggest_for_task("unknown")
        assert len(results) >= 0

    def test_compare_models(self):
        sel = self._setup()
        comparison = sel.compare_models(["openai/gpt-4o", "anthropic/claude-sonnet-4"])
        assert len(comparison.models) == 2
        assert "Context Window" in str(comparison.common_capabilities) or "Context Window" in str(comparison.differences)

    def test_compare_models_empty(self):
        sel = self._setup()
        comparison = sel.compare_models(["nonexistent/model"])
        assert len(comparison.models) == 0

    def test_format_comparison(self):
        sel = self._setup()
        comparison = sel.compare_models(["openai/gpt-4o", "anthropic/claude-sonnet-4"])
        formatted = sel.format_comparison(comparison)
        assert "Comparing" in formatted

    def test_browse_by_provider(self):
        sel = self._setup()
        by_provider = sel.browse_by_provider()
        assert "openai" in by_provider
        assert "anthropic" in by_provider

    def test_browse_by_capability(self):
        sel = self._setup()
        by_cap = sel.browse_by_capability()
        assert len(by_cap["vision"]) >= 1
        assert len(by_cap["reasoning"]) >= 1

    def test_search(self):
        sel = self._setup()
        results = sel.search("gpt")
        assert len(results) >= 1

    def test_get_providers_with_models(self):
        sel = self._setup()
        providers = sel.get_providers_with_models()
        assert "openai" in providers
        assert "anthropic" in providers


# ---------------------------------------------------------------------------
# DefaultModelRegistry tests
# ---------------------------------------------------------------------------

class TestDefaultModelRegistry:
    def test_initial_load(self):
        reg = DefaultModelRegistry()
        assignments = reg.get_all_assignments()
        assert len(assignments) >= 17

    def test_assign(self):
        reg = DefaultModelRegistry()
        assignment = reg.assign(TaskType.MAIN_CHAT, "anthropic", "claude-sonnet-4")
        assert assignment.provider == "anthropic"
        assert assignment.model_id == "claude-sonnet-4"

    def test_get_assignment(self):
        reg = DefaultModelRegistry()
        assignment = reg.get_assignment(TaskType.MAIN_CHAT)
        assert assignment is not None

    def test_get_provider(self):
        reg = DefaultModelRegistry()
        assert reg.get_provider(TaskType.MAIN_CHAT) == "openai"

    def test_get_model(self):
        reg = DefaultModelRegistry()
        assert reg.get_model(TaskType.MAIN_CHAT) == "gpt-4o"

    def test_get_provider_and_model(self):
        reg = DefaultModelRegistry()
        provider, model = reg.get_provider_and_model(TaskType.MAIN_CHAT)
        assert provider == "openai"
        assert model == "gpt-4o"

    def test_reset_to_default_task(self):
        reg = DefaultModelRegistry()
        reg.assign(TaskType.MAIN_CHAT, "anthropic", "claude-sonnet-4")
        reg.reset_to_default(TaskType.MAIN_CHAT)
        assert reg.get_provider(TaskType.MAIN_CHAT) == "openai"

    def test_reset_to_default_all(self):
        reg = DefaultModelRegistry()
        reg.assign(TaskType.MAIN_CHAT, "anthropic", "claude-sonnet-4")
        reg.reset_to_default()
        assert reg.get_provider(TaskType.MAIN_CHAT) == "openai"

    def test_get_task_display_name(self):
        reg = DefaultModelRegistry()
        assert reg.get_task_display_name(TaskType.MAIN_CHAT) == "Main Chat"

    def test_set_task_display_name(self):
        reg = DefaultModelRegistry()
        reg.set_task_display_name(TaskType.MAIN_CHAT, "Primary Chat")
        assert reg.get_task_display_name(TaskType.MAIN_CHAT) == "Primary Chat"

    def test_list_tasks(self):
        reg = DefaultModelRegistry()
        tasks = reg.list_tasks()
        assert TaskType.MAIN_CHAT in tasks

    def test_assign_bulk(self):
        reg = DefaultModelRegistry()
        reg.assign_bulk({
            TaskType.MAIN_CHAT: ("anthropic", "claude-sonnet-4"),
            TaskType.VISION: ("google", "gemini-2.0-flash"),
        })
        assert reg.get_provider(TaskType.MAIN_CHAT) == "anthropic"
        assert reg.get_provider(TaskType.VISION) == "google"

    def test_to_config_dict(self):
        reg = DefaultModelRegistry()
        config = reg.to_config_dict()
        assert "main_chat" in config

    def test_from_config_dict(self):
        reg = DefaultModelRegistry()
        reg.from_config_dict({"main_chat": {"provider": "anthropic", "model": "claude-sonnet-4"}})
        assert reg.get_provider(TaskType.MAIN_CHAT) == "anthropic"

    def test_from_config_dict_unknown_task(self):
        reg = DefaultModelRegistry()
        reg.from_config_dict({"unknown_task": {"provider": "x", "model": "y"}})
        assert reg.get_provider(TaskType.MAIN_CHAT) == "openai"

    def test_summary(self):
        reg = DefaultModelRegistry()
        s = reg.summary()
        assert "Default Model Assignments" in s


# ---------------------------------------------------------------------------
# FailoverManager tests
# ---------------------------------------------------------------------------

class TestFailoverManager:
    def test_configure(self):
        fm = FailoverManager()
        config = FailoverConfig(max_retries=5)
        fm.configure("openai", config)
        assert fm.get_config("openai").max_retries == 5

    def test_get_config_default(self):
        fm = FailoverManager()
        config = fm.get_config("unknown")
        assert config.max_retries == 3

    def test_execute_success(self):
        fm = FailoverManager()
        fm.set_call_function(lambda p, m, params: {"success": True})
        result = fm.execute("openai", "gpt-4o", {})
        assert result.success
        assert not result.used_fallback

    def test_execute_retry_then_success(self):
        fm = FailoverManager()
        attempts = [0]
        def call_fn(p, m, params):
            attempts[0] += 1
            if attempts[0] < 3:
                raise Exception("transient")
            return {"success": True}
        fm.set_call_function(call_fn)
        result = fm.execute("openai", "gpt-4o", {})
        assert result.success
        assert result.attempts == 3

    def test_execute_all_retries_fail(self):
        fm = FailoverManager()
        fm.set_call_function(lambda p, m, params: (_ for _ in ()).throw(Exception("fail")))
        result = fm.execute("openai", "gpt-4o", {})
        assert not result.success

    def test_execute_with_fallback_model(self):
        fm = FailoverManager()
        fm.configure("openai", FailoverConfig(fallback_models=["gpt-4o-mini"]))
        attempts = [0]
        def call_fn(p, m, params):
            attempts[0] += 1
            raise Exception("fail")
        fm.set_call_function(call_fn)
        result = fm.execute("openai", "gpt-4o", {})
        assert not result.success

    def test_circuit_breaker_opens(self):
        fm = FailoverManager()
        fm.configure("openai", FailoverConfig(circuit_breaker_threshold=3))
        fm.set_call_function(lambda p, m, params: (_ for _ in ()).throw(Exception("fail")))
        for _ in range(3):
            fm.execute("openai", "gpt-4o", {})
        result = fm.execute("openai", "gpt-4o", {})
        assert not result.success
        assert "Circuit breaker open" in result.error

    def test_circuit_breaker_records_success(self):
        fm = FailoverManager()
        fm.configure("openai", FailoverConfig(circuit_breaker_threshold=3))
        fm.set_call_function(lambda p, m, params: {"ok": True})
        fm.execute("openai", "gpt-4o", {})
        state = fm.get_circuit_state("openai")
        assert state.get("failures") == 0

    def test_reset_circuit_breaker(self):
        fm = FailoverManager()
        fm.configure("openai", FailoverConfig(circuit_breaker_threshold=1))
        fm.set_call_function(lambda p, m, params: (_ for _ in ()).throw(Exception("fail")))
        fm.execute("openai", "gpt-4o", {})
        fm.reset_circuit_breaker("openai")
        assert fm.get_circuit_state("openai") == {}

    def test_reset_all_circuit_breakers(self):
        fm = FailoverManager()
        fm._circuit_state["a"] = {"open": True}
        fm._circuit_state["b"] = {"open": True}
        fm.reset_all_circuit_breakers()
        assert fm._circuit_state == {}

    def test_calculate_delay(self):
        fm = FailoverManager()
        config = FailoverConfig(retry_delay_base=1.0, retry_delay_max=30.0, retry_jitter=0.1)
        delay = fm._calculate_delay(0, config)
        assert 1.0 <= delay <= 1.1
        delay2 = fm._calculate_delay(2, config)
        assert 4.0 <= delay2 <= 4.1

    def test_calculate_delay_capped(self):
        fm = FailoverManager()
        config = FailoverConfig(retry_delay_base=1.0, retry_delay_max=5.0, retry_jitter=0.1)
        delay = fm._calculate_delay(10, config)
        assert delay <= 5.1

    def test_fallback_chain_in_result(self):
        fm = FailoverManager()
        fm.configure("openai", FailoverConfig(fallback_models=["gpt-4o-mini"], fallback_providers=["anthropic"]))
        fm.set_call_function(lambda p, m, params: (_ for _ in ()).throw(Exception("fail")))
        result = fm.execute("openai", "gpt-4o", {})
        assert len(result.fallback_chain) > 1

    def test_circuit_status_summary(self):
        fm = FailoverManager()
        fm._circuit_state["openai"] = {"open": True, "failures": 5}
        s = fm.circuit_status_summary()
        assert "OPEN" in s
        assert "openai" in s

    def test_set_provider_manager(self):
        fm = FailoverManager()
        pm = ProviderManager()
        fm.set_provider_manager(pm)
        assert fm._provider_manager is pm

    def test_execute_no_call_fn(self):
        fm = FailoverManager()
        with patch("aetheros_providers.failover.MultiProviderOrchestrator") as MockOrch:
            mock_orch = MockOrch.return_value
            mock_orch.call_provider.return_value = {"result": "ok"}
            result = fm.execute("openai", "gpt-4o", {})
            assert result.success


# ---------------------------------------------------------------------------
# LocalModelManager tests
# ---------------------------------------------------------------------------

class TestLocalModelManager:
    def test_parse_host(self):
        assert LocalModelManager._parse_host("http://localhost:11434") == "localhost"
        assert LocalModelManager._parse_host("https://192.168.1.1:8080") == "192.168.1.1"
        assert LocalModelManager._parse_host("http://example.com") == "example.com"

    def test_parse_port(self):
        assert LocalModelManager._parse_port("http://localhost:11434") == 11434
        assert LocalModelManager._parse_port("http://localhost") == 80
        assert LocalModelManager._parse_port("http://example.com:8080") == 8080

    def test_detect_all_no_providers(self):
        lmm = LocalModelManager()
        with patch("socket.create_connection", side_effect=ConnectionRefusedError):
            results = lmm.detect_all(timeout=1.0)
            assert len(results) == 0

    def test_detect_all_some_connected(self):
        lmm = LocalModelManager()
        with patch("socket.create_connection", return_value=MagicMock()):
            with patch.object(lmm, "_fetch_local_models", return_value=[]):
                results = lmm.detect_all(timeout=1.0)
                assert len(results) == 5

    def test_detect_single(self):
        lmm = LocalModelManager()
        with patch("socket.create_connection", return_value=MagicMock()):
            with patch.object(lmm, "_fetch_local_models", return_value=[]):
                instance = lmm.detect_single(LocalProvider.OLLAMA, "http://localhost:11434")
                assert instance is not None
                assert instance.connected

    def test_detect_single_fails(self):
        lmm = LocalModelManager()
        with patch("socket.create_connection", side_effect=ConnectionRefusedError):
            instance = lmm.detect_single(LocalProvider.OLLAMA, "http://localhost:11434")
            assert instance is None

    def test_get_installed_models(self):
        lmm = LocalModelManager()
        instance = LocalProviderInstance(
            provider=LocalProvider.OLLAMA, base_url="http://localhost:11434",
            display_name="Ollama", connected=True, models=[{"name": "llama3"}],
        )
        lmm._instances["ollama@http://localhost:11434"] = instance
        models = lmm.get_installed_models("ollama@http://localhost:11434")
        assert len(models) == 1

    def test_get_installed_models_unknown(self):
        lmm = LocalModelManager()
        assert lmm.get_installed_models("unknown") == []

    def test_start_stop_monitoring(self):
        lmm = LocalModelManager()
        lmm.start_monitoring(interval=60)
        assert lmm._monitoring
        lmm.stop_monitoring()
        assert not lmm._monitoring

    def test_start_monitoring_idempotent(self):
        lmm = LocalModelManager()
        lmm.start_monitoring(interval=60)
        thread_id = id(lmm._monitor_thread)
        lmm.start_monitoring(interval=60)
        assert id(lmm._monitor_thread) == thread_id

    @property
    def test_get_gpu_info(self):
        lmm = LocalModelManager()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "0, NVIDIA RTX 4090, 24576, 10240, 42\n"
            info = lmm.get_gpu_info()
            assert info["available"]

    def test_get_gpu_info_no_nvidia_smi(self):
        lmm = LocalModelManager()
        with patch("subprocess.run", side_effect=FileNotFoundError):
            info = lmm.get_gpu_info()
            assert not info["available"]

    def test_properties(self):
        lmm = LocalModelManager()
        assert lmm.instances == {}
        assert lmm.connected_count == 0
        assert not lmm.is_any_connected

    def test_summary_no_providers(self):
        lmm = LocalModelManager()
        s = lmm.summary()
        assert "No local providers detected" in s

    def test_summary_with_providers(self):
        lmm = LocalModelManager()
        instance = LocalProviderInstance(
            provider=LocalProvider.OLLAMA, base_url="http://localhost:11434",
            display_name="Ollama", connected=True, latency_ms=5.0, models=[{"name": "llama3"}],
        )
        lmm._instances["ollama@http://localhost:11434"] = instance
        s = lmm.summary()
        assert "Ollama" in s


# ---------------------------------------------------------------------------
# ProviderSettingsManager tests
# ---------------------------------------------------------------------------

class TestProviderSettingsManager:
    def test_get_settings_default(self):
        psm = ProviderSettingsManager()
        settings = psm.get_settings("unknown")
        assert settings.temperature == 0.7
        assert settings.max_tokens == 4096

    def test_get_settings_known(self):
        psm = ProviderSettingsManager()
        settings = psm.get_settings("openai")
        assert settings.max_tokens == 8192

    def test_set_settings(self):
        psm = ProviderSettingsManager()
        custom = ProviderSettings(temperature=0.1, max_tokens=512)
        psm.set_settings("custom", custom)
        assert psm.get_settings("custom").temperature == 0.1

    def test_update_setting(self):
        psm = ProviderSettingsManager()
        assert psm.update_setting("openai", "temperature", 0.5)
        assert psm.get_settings("openai").temperature == 0.5

    def test_update_setting_unknown_provider(self):
        psm = ProviderSettingsManager()
        assert psm.update_setting("new_provider", "temperature", 0.5)
        assert psm.get_settings("new_provider").temperature == 0.5

    def test_update_setting_invalid_key(self):
        psm = ProviderSettingsManager()
        assert not psm.update_setting("openai", "nonexistent", "value")

    def test_get_setting(self):
        psm = ProviderSettingsManager()
        assert psm.get_setting("openai", "temperature") == 0.7
        assert psm.get_setting("openai", "nonexistent", "default") == "default"

    def test_reset_to_default_single(self):
        psm = ProviderSettingsManager()
        psm.update_setting("openai", "temperature", 0.1)
        psm.reset_to_default("openai")
        assert psm.get_settings("openai").temperature == 0.7

    def test_reset_to_default_all(self):
        psm = ProviderSettingsManager()
        psm.update_setting("openai", "temperature", 0.1)
        psm.reset_to_default()
        assert psm.get_settings("openai").temperature == 0.7

    def test_list_configured_providers(self):
        psm = ProviderSettingsManager()
        providers = psm.list_configured_providers()
        assert "openai" in providers

    def test_get_all_settings(self):
        psm = ProviderSettingsManager()
        all_settings = psm.get_all_settings()
        assert "openai" in all_settings
        assert "temperature" in all_settings["openai"]

    def test_build_api_kwargs(self):
        psm = ProviderSettingsManager()
        kwargs = psm.build_api_kwargs("openai")
        assert kwargs["temperature"] == 0.7
        assert kwargs["stream"] is True

    def test_build_api_kwargs_with_overrides(self):
        psm = ProviderSettingsManager()
        kwargs = psm.build_api_kwargs("openai", {"temperature": 0.1, "extra": True})
        assert kwargs["temperature"] == 0.1
        assert kwargs["extra"]

    def test_persistence(self, tmp_path):
        psm = ProviderSettingsManager(settings_dir=tmp_path)
        psm.update_setting("openai", "temperature", 0.3)
        assert (tmp_path / "provider_settings.json").exists()

        psm2 = ProviderSettingsManager(settings_dir=tmp_path)
        assert psm2.get_settings("openai").temperature == 0.3

    def test_summary(self):
        psm = ProviderSettingsManager()
        s = psm.summary()
        assert "Provider Settings" in s


# ---------------------------------------------------------------------------
# ModelValidator tests
# ---------------------------------------------------------------------------

class TestModelValidator:
    def test_validation_result_properties(self):
        result = ValidationResult(success=True, checks={"a": True, "b": False})
        assert not result.all_passed
        assert result.passed_checks == 1
        assert result.failed_checks == 1

    def test_validation_result_empty(self):
        result = ValidationResult(success=True)
        assert not result.all_passed
        assert result.passed_checks == 0

    def test_validation_result_summary(self):
        result = ValidationResult(success=True, checks={"a": True, "b": False}, errors={"b": "fail"})
        s = result.summary()
        assert "PASSED" in s or "FAILED" in s

    def test_validate_api_key_success(self):
        validator = ModelValidator()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = json.dumps({"data": [{"id": "gpt-4"}]}).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            result = validator.validate_api_key("openai", "sk-test", "https://api.openai.com/v1")
            assert result.success
            assert result.checks.get("api_key_valid")

    def test_validate_api_key_401(self):
        validator = ModelValidator()
        with patch("urllib.request.urlopen") as mock_urlopen:
            import urllib.error
            mock_urlopen.side_effect = urllib.error.HTTPError(
                "http://example.com", 401, "Unauthorized", {}, None
            )
            result = validator.validate_api_key("openai", "bad-key")
            assert not result.success
            assert "api_key_valid" in result.errors

    def test_validate_api_key_403(self):
        validator = ModelValidator()
        with patch("urllib.request.urlopen") as mock_urlopen:
            import urllib.error
            mock_urlopen.side_effect = urllib.error.HTTPError(
                "http://example.com", 403, "Forbidden", {}, None
            )
            result = validator.validate_api_key("openai", "bad-key")
            assert "Insufficient permissions" in result.errors.get("api_key_valid", "")

    def test_validate_api_key_429(self):
        validator = ModelValidator()
        with patch("urllib.request.urlopen") as mock_urlopen:
            import urllib.error
            mock_urlopen.side_effect = urllib.error.HTTPError(
                "http://example.com", 429, "Too Many Requests", {}, None
            )
            result = validator.validate_api_key("openai", "bad-key")
            assert "Rate limited" in result.errors.get("api_key_valid", "")

    def test_validate_api_key_connection_error(self):
        validator = ModelValidator()
        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            result = validator.validate_api_key("openai", "sk-test")
            assert not result.checks.get("endpoint_reachable", True)

    def test_validate_model(self):
        validator = ModelValidator()
        with patch.object(validator, "validate_api_key") as mock_key:
            mock_key.return_value = ValidationResult(
                success=True, checks={"api_key_valid": True, "endpoint_reachable": True},
                details={"models": [{"id": "gpt-4"}, {"id": "gpt-4o"}]},
            )
            result = validator.validate_model("openai", "gpt-4o", "sk-test")
            assert result.checks.get("model_exists")

    def test_validate_model_not_found(self):
        validator = ModelValidator()
        with patch.object(validator, "validate_api_key") as mock_key:
            mock_key.return_value = ValidationResult(
                success=True, checks={"api_key_valid": True, "endpoint_reachable": True},
                details={"models": [{"id": "gpt-4"}]},
            )
            result = validator.validate_model("openai", "nonexistent", "sk-test")
            assert "model_exists" in result.errors

    def test_validate_capabilities_streaming(self):
        validator = ModelValidator()
        result = validator.validate_capabilities("openai", "gpt-4", check_streaming=True)
        assert result.checks.get("streaming_supported")

    def test_validate_capabilities_vision(self):
        validator = ModelValidator()
        result = validator.validate_capabilities("openai", "gpt-4o", check_vision=True)
        assert result.checks.get("vision_supported")

    def test_validate_capabilities_tools(self):
        validator = ModelValidator()
        result = validator.validate_capabilities("openai", "gpt-4", check_tools=True)
        assert result.checks.get("tool_calling_supported")

    def test_validate_capabilities_reasoning(self):
        validator = ModelValidator()
        result = validator.validate_capabilities("openai", "o3-mini", check_reasoning=True)
        assert result.checks.get("reasoning_supported")

    def test_validate_capabilities_vision_not_supported(self):
        validator = ModelValidator()
        result = validator.validate_capabilities("openai", "gpt-4o-mini", check_vision=True)
        assert not result.checks.get("vision_supported", False)

    def test_validate_all(self):
        validator = ModelValidator()
        with patch.object(validator, "validate_model") as mock_model:
            mock_model.return_value = ValidationResult(
                success=True, checks={"api_key_valid": True, "model_exists": True},
            )
            with patch.object(validator, "validate_capabilities") as mock_cap:
                mock_cap.return_value = ValidationResult(
                    success=True, checks={"streaming_supported": True, "tool_calling_supported": True},
                )
                result = validator.validate_all("openai", "gpt-4", "sk-test")
                assert result.all_passed

    def test_check_streaming_support(self):
        assert ModelValidator._check_streaming_support("openai", "x")
        assert not ModelValidator._check_streaming_support("unknown", "x")

    def test_check_vision_support(self):
        assert ModelValidator._check_vision_support("openai", "gpt-4o-vision")
        assert not ModelValidator._check_vision_support("openai", "gpt-4o-mini")

    def test_check_tool_support(self):
        assert ModelValidator._check_tool_support("openai", "x")
        assert not ModelValidator._check_tool_support("lm_studio", "x")

    def test_check_reasoning_support(self):
        assert ModelValidator._check_reasoning_support("openai", "o3-mini")
        assert ModelValidator._check_reasoning_support("deepseek", "deepseek-r1")
        assert not ModelValidator._check_reasoning_support("openai", "gpt-4o-mini")

    def test_get_models_url(self):
        url = ModelValidator._get_models_url("openai")
        assert "api.openai.com" in url
        assert ModelValidator._get_models_url("unknown") == ""


# ---------------------------------------------------------------------------
# MultiProviderOrchestrator tests
# ---------------------------------------------------------------------------

class TestMultiProviderOrchestrator:
    def test_initial_stages(self):
        mpo = MultiProviderOrchestrator()
        stages = mpo.list_stages()
        assert "planner" in stages
        assert len(stages) >= 8

    def test_define_stage(self):
        mpo = MultiProviderOrchestrator()
        stage = mpo.define_stage("custom", "openai", "gpt-4o", temperature=0.5)
        assert stage.name == "custom"
        assert stage.provider == "openai"

    def test_get_stage(self):
        mpo = MultiProviderOrchestrator()
        stage = mpo.get_stage("planner")
        assert stage is not None
        assert stage.provider == "anthropic"

    def test_get_stage_nonexistent(self):
        mpo = MultiProviderOrchestrator()
        assert mpo.get_stage("nonexistent") is None

    def test_remove_stage(self):
        mpo = MultiProviderOrchestrator()
        mpo.define_stage("custom", "openai", "gpt-4o")
        assert mpo.remove_stage("custom")
        assert mpo.get_stage("custom") is None

    def test_remove_default_stage(self):
        mpo = MultiProviderOrchestrator()
        assert not mpo.remove_stage("planner")

    def test_reset_to_defaults(self):
        mpo = MultiProviderOrchestrator()
        mpo.define_stage("custom", "openai", "gpt-4o")
        mpo.reset_to_defaults()
        assert mpo.get_stage("custom") is None

    def test_stage_key(self):
        stage = WorkflowStage("Test", "openai", "gpt-4o")
        assert stage.key == "openai/gpt-4o"

    def test_call_provider(self):
        mpo = MultiProviderOrchestrator()
        with patch("aetheros_providers.multi_provider.httpx") as mock_httpx:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"choices": [{"message": {"content": "hello"}}]}
            mock_client.post.return_value = mock_response
            mock_httpx.Client.return_value.__enter__.return_value = mock_client

            with patch("aetheros_providers.multi_provider.get_provider_profile") as mock_profile:
                profile = MagicMock()
                profile.base_url = "https://api.openai.com"
                mock_profile.return_value = profile

                with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
                    result = mpo.call_provider("openai", "gpt-4o", {"messages": [{"role": "user", "content": "hi"}]})
                    assert result.get("success") is not False

    def test_call_provider_no_profile(self):
        mpo = MultiProviderOrchestrator()
        with patch("aetheros_providers.multi_provider.get_provider_profile", return_value=None):
            result = mpo.call_provider("unknown", "model", {})
            assert not result.get("success", True)

    def test_execute_stage(self):
        mpo = MultiProviderOrchestrator()
        with patch.object(mpo, "call_provider") as mock_call:
            mock_call.return_value = {"success": True, "choices": [{"message": {"content": "ok"}}]}
            result = mpo.execute_stage("planner", [{"role": "user", "content": "hi"}])
            assert result.get("success")

    def test_execute_stage_nonexistent(self):
        mpo = MultiProviderOrchestrator()
        result = mpo.execute_stage("nonexistent", [])
        assert not result.get("success", True)

    def test_execute_pipeline(self):
        mpo = MultiProviderOrchestrator()
        with patch.object(mpo, "execute_stage") as mock_exec:
            mock_exec.return_value = {"success": True, "output": "result"}
            results = mpo.execute_pipeline(["planner", "coder"], {"messages": [{"role": "user", "content": "test"}]})
            assert "planner" in results
            assert "coder" in results
            assert mock_exec.call_count == 2

    def test_multi_provider_chat(self):
        mpo = MultiProviderOrchestrator()
        with patch.object(mpo, "execute_stage") as mock_exec:
            mock_exec.return_value = {
                "success": True,
                "choices": [{"message": {"content": "response from stage"}}],
            }
            results = mpo.multi_provider_chat(["planner", "coder"], "hello")
            assert "planner" in results
            assert "coder" in results

    def test_multi_provider_chat_fails(self):
        mpo = MultiProviderOrchestrator()
        with patch.object(mpo, "execute_stage") as mock_exec:
            mock_exec.return_value = {"success": False, "error": "fail"}
            results = mpo.multi_provider_chat(["planner"], "hello")
            assert "planner" in results

    def test_resolve_api_key(self):
        mpo = MultiProviderOrchestrator()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-found"}):
            assert mpo._resolve_api_key("openai") == "sk-found"

    def test_resolve_api_key_missing(self):
        mpo = MultiProviderOrchestrator()
        with patch.dict(os.environ, {}, clear=True):
            assert mpo._resolve_api_key("openai") is None

    def test_summary(self):
        mpo = MultiProviderOrchestrator()
        s = mpo.summary()
        assert "Multi-Provider Orchestrator" in s
        assert "planner" in s


# ---------------------------------------------------------------------------
# Package __init__ tests
# ---------------------------------------------------------------------------

class TestPackageInit:
    def test_all_exports(self):
        from aetheros_providers import (
            ProviderManager, ProviderStatus, ProviderInfo,
            APIKeyManager, APIKeyInfo, KeyStatus,
            ModelDatabase, ModelInfo, ModelCapability,
            ModelSelector, ModelFilter,
            DefaultModelRegistry, TaskType,
            FailoverManager, FailoverStrategy,
            LocalModelManager, LocalProvider,
            ProviderSettingsManager, ProviderSettings,
            ModelValidator, ValidationResult,
            MultiProviderOrchestrator, WorkflowStage,
        )
        assert ProviderManager is not None
        assert APIKeyManager is not None
        assert ModelDatabase is not None
        assert ModelSelector is not None
        assert DefaultModelRegistry is not None
        assert FailoverManager is not None
        assert LocalModelManager is not None
        assert ProviderSettingsManager is not None
        assert ModelValidator is not None
        assert MultiProviderOrchestrator is not None