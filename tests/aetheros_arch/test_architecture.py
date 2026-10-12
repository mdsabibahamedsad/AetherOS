"""Tests for AetherOS Architecture Foundation."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from aetheros_arch.config_manager import (
    ConfigManager,
    ConfigMode,
    ConfigScope,
    ConfigValidationError,
)
from aetheros_arch.health_checker import HealthChecker, HealthStatus, check_filesystem, ping_component
from aetheros_arch.error_handler import ErrorHandler, AetherOSError, ConfigError, ErrorLevel, ErrorCategory
from aetheros_arch.service_container import ServiceContainer, ServiceLifecycle
from aetheros_arch.state_manager import StateManager, AppState, ComponentState
from aetheros_arch.security_foundation import SecurityFoundation
from aetheros_arch.performance import PerformanceOptimizer, LazyLoader, BackgroundLoader


# ---------------------------------------------------------------------------
# ConfigManager tests
# ---------------------------------------------------------------------------

class TestConfigManager:
    def test_load_all(self, tmp_path):
        cm = ConfigManager(aetheros_home=tmp_path, auto_load=False)
        assert not cm._files[ConfigScope.CORE].loaded
        cm.load_all()
        assert cm._files[ConfigScope.CORE].loaded is False  # no file yet

    def test_set_and_get(self, tmp_path):
        cm = ConfigManager(aetheros_home=tmp_path, auto_load=False)
        cm.set("agent.max_iterations", 90)
        assert cm.get("agent.max_iterations") == 90

    def test_get_default(self, tmp_path):
        cm = ConfigManager(aetheros_home=tmp_path, auto_load=False)
        assert cm.get("nonexistent.key", "fallback") == "fallback"

    def test_has(self, tmp_path):
        cm = ConfigManager(aetheros_home=tmp_path, auto_load=False)
        cm.set("test.key", "value")
        assert cm.has("test.key")
        assert not cm.has("missing.key")

    def test_save_and_load(self, tmp_path):
        cm = ConfigManager(aetheros_home=tmp_path, auto_load=False)
        cm.set("test.value", 42)
        cm.save(ConfigScope.CORE)

        cm2 = ConfigManager(aetheros_home=tmp_path, auto_load=False)
        cm2.load(ConfigScope.CORE)
        assert cm2.get("test.value") == 42

    def test_scope_get(self, tmp_path):
        cm = ConfigManager(aetheros_home=tmp_path, auto_load=False)
        cm.set("key", "core_value", ConfigScope.CORE)
        cm.set("key", "settings_value", ConfigScope.SETTINGS)

        assert cm.get_scope(ConfigScope.CORE, "key") == "core_value"
        assert cm.get_scope(ConfigScope.SETTINGS, "key") == "settings_value"

    def test_validate(self, tmp_path):
        cm = ConfigManager(aetheros_home=tmp_path, auto_load=False)
        cm.load_all()
        errors = cm.validate_all()
        assert isinstance(errors, list)

    def test_mode(self, tmp_path):
        cm = ConfigManager(aetheros_home=tmp_path, mode=ConfigMode.PRODUCTION)
        assert cm.is_production()
        assert not cm.is_development()
        cm.mode = ConfigMode.DEVELOPMENT
        assert cm.is_development()


# ---------------------------------------------------------------------------
# HealthChecker tests
# ---------------------------------------------------------------------------

class TestHealthChecker:
    def test_register_and_run(self):
        hc = HealthChecker()
        hc.register("test", lambda: (HealthStatus.HEALTHY, "OK"))
        result = hc.run("test")
        assert result is not None
        assert result.status == HealthStatus.HEALTHY
        assert result.is_healthy

    def test_unregister(self):
        hc = HealthChecker()
        hc.register("test", lambda: (HealthStatus.HEALTHY, "OK"))
        hc.unregister("test")
        assert hc.run("test") is None

    def test_run_all(self):
        hc = HealthChecker()
        hc.register("a", lambda: (HealthStatus.HEALTHY, "OK"))
        hc.register("b", lambda: (HealthStatus.DEGRADED, "Slow"))
        hc.register("c", lambda: (_ for _ in ()).throw(Exception("Fail")))  # raises
        summary = hc.run_all()
        assert summary.total == 3
        assert summary.healthy == 1
        assert summary.degraded == 1
        assert summary.unhealthy == 1

    def test_run_category(self):
        hc = HealthChecker()
        hc.register("gateway.http", lambda: (HealthStatus.HEALTHY, "OK"))
        hc.register("provider.openai", lambda: (HealthStatus.HEALTHY, "OK"))
        hc.register("gateway.ws", lambda: (HealthStatus.DEGRADED, "Slow"))
        summary = hc.run_category("gateway")
        assert summary.total == 2

    def test_all_healthy(self):
        hc = HealthChecker()
        hc.register("a", lambda: (HealthStatus.HEALTHY, "OK"))
        hc.register("b", lambda: (HealthStatus.HEALTHY, "OK"))
        summary = hc.run_all()
        assert summary.all_healthy

    def test_score(self):
        hc = HealthChecker()
        hc.register("a", lambda: (HealthStatus.HEALTHY, "OK"))
        hc.register("b", lambda: (HealthStatus.UNHEALTHY, "Down"))
        summary = hc.run_all()
        assert summary.score == 0.5

    def test_check_filesystem(self, tmp_path):
        status, msg = check_filesystem(str(tmp_path))
        assert status == HealthStatus.HEALTHY

        status, msg = check_filesystem(str(tmp_path / "nonexistent"))
        assert status == HealthStatus.UNHEALTHY


# ---------------------------------------------------------------------------
# ErrorHandler tests
# ---------------------------------------------------------------------------

class TestErrorHandler:
    def test_handle_basic_exception(self):
        eh = ErrorHandler()
        report = eh.handle(ValueError("test error"))
        assert "test error" in report.message
        assert report.level == ErrorLevel.ERROR

    def test_handle_aetheros_error(self):
        eh = ErrorHandler()
        err = ConfigError("Bad config")
        report = eh.handle(err)
        assert report.category == ErrorCategory.CONFIG

    def test_suggest_fix(self):
        assert "API key" in ErrorHandler.suggest_fix("invalid api key")
        assert "Check that the service is running" in ErrorHandler.suggest_fix("connection refused")
        assert ErrorHandler.suggest_fix("unknown error") == ""

    def test_recent_errors(self):
        eh = ErrorHandler()
        eh.handle(ValueError("error 1"))
        eh.handle(ValueError("error 2"))
        recent = eh.recent_errors(1)
        assert len(recent) == 1
        assert "error 2" in recent[0].message

    def test_clear_history(self):
        eh = ErrorHandler()
        eh.handle(ValueError("test"))
        eh.clear_history()
        assert len(eh.recent_errors()) == 0

    def test_user_message_no_traceback(self):
        eh = ErrorHandler()
        report = eh.handle(ValueError("test"), suggestion="Try again")
        msg = report.user_message()
        assert "test" in msg
        assert "Try again" in msg
        assert "Traceback" not in msg


# ---------------------------------------------------------------------------
# ServiceContainer tests
# ---------------------------------------------------------------------------

class TestServiceContainer:
    def test_register_and_resolve(self):
        c = ServiceContainer()
        c.register("math", lambda container: 42)
        assert c.resolve("math") == 42

    def test_singleton(self):
        c = ServiceContainer()
        c.register("counter", lambda container: object())
        assert c.resolve("counter") is c.resolve("counter")

    def test_transient(self):
        c = ServiceContainer()
        c.register("counter", lambda container: object(), ServiceLifecycle.TRANSIENT)
        assert c.resolve("counter") is not c.resolve("counter")

    def test_register_instance(self):
        c = ServiceContainer()
        obj = {"key": "value"}
        c.register_instance("test", obj)
        assert c.resolve("test") is obj

    def test_has(self):
        c = ServiceContainer()
        c.register("exists", lambda c: True)
        assert c.has("exists")
        assert not c.has("missing")

    def test_try_resolve(self):
        c = ServiceContainer()
        assert c.try_resolve("missing", default=42) == 42
        c.register("exists", lambda c: "found")
        assert c.try_resolve("exists") == "found"

    def test_start_all(self):
        c = ServiceContainer()
        c.register("a", lambda c: object())
        c.register("b", lambda c: object())
        started = c.start_all()
        assert len(started) == 2

    def test_stop_all(self):
        c = ServiceContainer()
        c.register("a", lambda c: object())
        c.start("a")
        c.stop_all()
        assert len(c.started_services) == 0


# ---------------------------------------------------------------------------
# StateManager tests
# ---------------------------------------------------------------------------

class TestStateManager:
    def test_app_state(self):
        sm = StateManager()
        assert sm.app_state == AppState.INITIALIZING
        sm.app_state = AppState.RUNNING
        assert sm.is_running

    def test_set_and_get(self):
        sm = StateManager()
        sm.set("key", "value")
        assert sm.get("key") == "value"

    def test_get_default(self):
        sm = StateManager()
        assert sm.get("missing", 42) == 42

    def test_has(self):
        sm = StateManager()
        sm.set("key", "value")
        assert sm.has("key")
        assert not sm.has("missing")

    def test_delete(self):
        sm = StateManager()
        sm.set("key", "value")
        assert sm.delete("key")
        assert not sm.has("key")

    def test_update(self):
        sm = StateManager()
        sm.update({"a": 1, "b": 2})
        assert sm.get("a") == 1
        assert sm.get("b") == 2

    def test_component_state(self):
        sm = StateManager()
        sm.set_component_state("gateway", ComponentState.READY)
        assert sm.component_is_ready("gateway")
        assert sm.get_component_state("gateway") == ComponentState.READY

    def test_snapshot(self):
        sm = StateManager()
        sm.set("key", "value")
        snap = sm.snapshot()
        assert "app_state" in snap
        assert "store" in snap
        assert snap["store"]["key"] == "value"

    def test_persist_and_load(self, tmp_path):
        persist = tmp_path / "state.json"
        sm = StateManager(persist_path=persist)
        sm.set("key", "value")
        sm.persist_now()

        sm2 = StateManager(persist_path=persist)
        assert sm2.get("key") == "value"


# ---------------------------------------------------------------------------
# SecurityFoundation tests
# ---------------------------------------------------------------------------

class TestSecurityFoundation:
    def test_hash_string(self):
        h = SecurityFoundation.hash_string("test")
        assert isinstance(h, str)
        assert len(h) == 64

    def test_hash_api_key(self):
        h = SecurityFoundation.hash_api_key("sk-abc123")
        assert h.startswith("ak_")
        assert len(h) == 19

    def test_encrypt_decrypt(self):
        sf = SecurityFoundation()
        try:
            from cryptography.fernet import Fernet
            import base64, os
            key = Fernet.generate_key()
            sf.initialize(key)
            assert sf.is_initialized

            encrypted = sf.encrypt("secret-value")
            assert encrypted != "secret-value"

            decrypted = sf.decrypt(encrypted)
            assert decrypted == "secret-value"
        except ImportError:
            pytest.skip("cryptography not installed")

    def test_is_secret_key(self):
        assert SecurityFoundation._is_secret_key("api_key")
        assert SecurityFoundation._is_secret_key("OPENAI_API_KEY")
        assert SecurityFoundation._is_secret_key("password")
        assert not SecurityFoundation._is_secret_key("display_name")
        assert not SecurityFoundation._is_secret_key("max_iterations")


# ---------------------------------------------------------------------------
# PerformanceOptimizer tests
# ---------------------------------------------------------------------------

class TestPerformanceOptimizer:
    def test_guard_init(self):
        po = PerformanceOptimizer()
        assert po.guard_init("module_a")
        assert not po.guard_init("module_a")

    def test_timing(self):
        po = PerformanceOptimizer()
        po.start_timer("test")
        import time
        time.sleep(0.01)
        elapsed = po.stop_timer("test")
        assert elapsed > 0

    def test_timing_report(self):
        po = PerformanceOptimizer()
        po.start_timer("test")
        po.stop_timer("test")
        report = po.timing_report()
        assert "test" in report
        assert "Performance Timings" in report

    def test_is_initialized(self):
        po = PerformanceOptimizer()
        po.mark_init("module_a")
        assert po.is_initialized("module_a")


class TestLazyLoader:
    def test_lazy_loading(self):
        call_count = 0
        def factory():
            nonlocal call_count
            call_count += 1
            return 42

        loader = LazyLoader(factory)
        assert not loader.is_loaded
        assert loader.value == 42
        assert loader.is_loaded
        assert loader.value == 42
        assert call_count == 1

    def test_reset(self):
        loader = LazyLoader(lambda: 42)
        _ = loader.value
        loader.reset()
        assert not loader.is_loaded


class TestBackgroundLoader:
    def test_submit_and_result(self):
        bl = BackgroundLoader()
        bl.submit("test", lambda: 42)
        assert bl.result("test", timeout=5) == 42

    def test_is_done(self):
        bl = BackgroundLoader()
        bl.submit("test", lambda: 42)
        bl.result("test", timeout=5)
        assert bl.is_done("test")