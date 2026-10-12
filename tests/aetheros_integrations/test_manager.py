"""Tests for aetheros_integrations.manager — lifecycle, credentials, health, permissions."""

import pytest

from aetheros_integrations.config import IntegrationsSettings
from aetheros_integrations.manager import IntegrationManager
from aetheros_integrations.models import HealthStatus, IntegrationStatus


@pytest.fixture
def settings():
    return IntegrationsSettings(data_dir="integrations")


@pytest.fixture
def manager(tmp_path, settings):
    return IntegrationManager(settings, dirpath=tmp_path)


class TestLifecycle:
    def test_install(self, manager):
        inst = manager.install("sqlite", label="local db", config={"database": "x.db"})
        assert inst.provider_key == "sqlite"
        assert inst.label == "local db"
        assert manager.count() == 1

    def test_install_unknown_provider_raises(self, manager):
        with pytest.raises(KeyError):
            manager.install("nope")

    def test_default_status_installed_when_auto_enable_off(self, manager):
        inst = manager.install("sqlite")
        assert inst.status == IntegrationStatus.INSTALLED

    def test_auto_enable(self, tmp_path):
        settings = IntegrationsSettings(data_dir="integrations", auto_enable_on_install=True)
        mgr = IntegrationManager(settings, dirpath=tmp_path)
        inst = mgr.install("sqlite")
        assert inst.status == IntegrationStatus.ENABLED

    def test_enable_disable(self, manager):
        inst = manager.install("sqlite")
        manager.enable(inst.id)
        assert manager.get(inst.id).status == IntegrationStatus.ENABLED
        manager.disable(inst.id)
        assert manager.get(inst.id).status == IntegrationStatus.DISABLED

    def test_update_label_and_config(self, manager):
        inst = manager.install("sqlite", label="old")
        before = inst.version
        updated = manager.update(inst.id, label="new", config={"database": "y.db"})
        assert updated.label == "new"
        assert updated.config["database"] == "y.db"
        assert updated.version != before

    def test_remove(self, manager):
        inst = manager.install("sqlite")
        assert manager.remove(inst.id) is True
        assert manager.remove(inst.id) is False
        assert manager.count() == 0

    def test_list_filters(self, manager):
        a = manager.install("sqlite", label="a")
        manager.enable(a.id)
        manager.install("sqlite", label="b")
        assert len(manager.list(provider_key="sqlite")) == 2
        assert len(manager.list(status="enabled")) == 1

    def test_get_missing_raises(self, manager):
        with pytest.raises(KeyError):
            manager.get("missing")


class TestCredentials:
    def test_store_credential_then_install_with_it(self, manager):
        cid = manager._auth.store_api_key("github", "ghp_secret_abc")
        inst = manager.install("github", credential_id=cid)
        manager.enable(inst.id)
        provider = manager.get_provider(inst.id)
        assert provider._headers()["Authorization"] == "Bearer ghp_secret_abc"

    def test_remove_deletes_credential(self, manager):
        cid = manager._auth.store_api_key("github", "ghp_secret_abc")
        inst = manager.install("github", credential_id=cid)
        assert manager._vault.get(cid) is not None
        manager.remove(inst.id)
        assert manager._vault.get(cid) is None


class TestHealth:
    def test_health_check_disabled_returns_unavailable(self, manager):
        inst = manager.install("sqlite")
        result = manager.health_check(inst.id)
        assert result["health"] == HealthStatus.UNAVAILABLE.value

    def test_health_check_sqlite_healthy(self, manager, tmp_path):
        db = tmp_path / "h.db"
        db.touch()
        inst = manager.install("sqlite", config={"database": str(db)})
        manager.enable(inst.id)
        result = manager.health_check(inst.id)
        assert result["health"] == HealthStatus.HEALTHY.value

    def test_health_check_missing_database_unhealthy(self, manager):
        inst = manager.install("sqlite", config={"database": str(manager._dir / "missing.db")})
        manager.enable(inst.id)
        result = manager.health_check(inst.id)
        assert result["health"] == HealthStatus.UNHEALTHY.value

    def test_health_all(self, manager):
        inst = manager.install("sqlite")
        results = manager.health_all()
        assert results[0]["integration_id"] == inst.id

    def test_diagnostics_redacts_config(self, manager):
        inst = manager.install("sqlite", config={"api_key": "secret-xyz", "database": "x.db"})
        diag = manager.diagnostics(inst.id)
        assert diag["config"]["api_key"] == "<redacted>"
        assert diag["has_credentials"] is False


class TestPermissions:
    def test_can_deny_by_default(self, manager):
        inst = manager.install("sqlite")
        assert manager.can(inst.id, "run_query") is False

    def test_set_permissions_grants(self, manager):
        inst = manager.install("sqlite")
        manager.set_permissions(inst.id, {"allow": ["run_query"]})
        assert manager.can(inst.id, "run_query") is True
        assert manager.can(inst.id, "run_statement") is False

    def test_get_provider_requires_enabled(self, manager):
        inst = manager.install("sqlite")
        with pytest.raises(RuntimeError):
            manager.get_provider(inst.id)
        manager.enable(inst.id)
        assert manager.get_provider(inst.id) is not None


class TestPersistence:
    def test_instances_persist_across_instances(self, tmp_path, settings):
        mgr1 = IntegrationManager(settings, dirpath=tmp_path)
        inst = mgr1.install("sqlite", label="persist-me")
        mgr2 = IntegrationManager(settings, dirpath=tmp_path)
        assert mgr2.get(inst.id).label == "persist-me"
        assert mgr2.count() == 1

    def test_audit_trail_written(self, manager):
        inst = manager.install("sqlite")
        entries = manager._audit.query(action="integration.installed")
        assert any(e.target == inst.id for e in entries)


class TestListProviders:
    def test_list_providers(self, manager):
        providers = manager.list_providers()
        assert len(providers) >= 40
        assert all("key" in p and "category" in p and "capabilities" in p for p in providers)

    def test_list_providers_by_category(self, manager):
        messaging = manager.list_providers("messaging")
        assert messaging
        assert all(p["category"] == "messaging" for p in messaging)

    def test_provider_available(self, manager):
        assert manager.provider_available("sqlite") is True
        assert manager.provider_available("nope") is False
