"""Tests for aetheros_integrations.providers — registration, sqlite, availability."""

import sqlite3

import pytest

from aetheros_integrations.models import HealthStatus
from aetheros_integrations.providers import registry as provider_registry


class TestRegistry:
    def test_providers_registered(self):
        defs = provider_registry.list_definitions()
        assert len(defs) >= 40
        keys = {d.key for d in defs}
        for expected in ("telegram", "gmail", "google_calendar", "github", "slack", "notion", "jira", "sqlite", "hubspot"):
            assert expected in keys, f"missing provider {expected}"

    def test_categories_present(self):
        counts = provider_registry.categories()
        for cat in ("messaging", "email", "calendar", "storage", "devops", "knowledge", "productivity", "crm", "database"):
            assert counts.get(cat, 0) >= 1, f"missing category {cat}"

    def test_definitions_have_capabilities(self):
        for d in provider_registry.list_definitions():
            assert d.capabilities, f"provider {d.key} has no capabilities"

    def test_get_class(self):
        cls = provider_registry.get_class("sqlite")
        assert cls.definition.key == "sqlite"

    def test_unknown_provider_raises(self):
        with pytest.raises(KeyError):
            provider_registry.get_class("does-not-exist")


class TestSQLiteProvider:
    @pytest.fixture
    def db_path(self, tmp_path):
        path = tmp_path / "test.db"
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE widgets (id INTEGER PRIMARY KEY, name TEXT, qty INTEGER)")
        conn.executemany(
            "INSERT INTO widgets (name, qty) VALUES (?, ?)",
            [("bolt", 5), ("nut", 3), ("screw", 8)],
        )
        conn.commit()
        conn.close()
        return str(path)

    def test_ping_healthy(self, db_path):
        provider = provider_registry.get("sqlite", {"database": db_path})
        assert provider.ping() == HealthStatus.HEALTHY

    def test_ping_unhealthy_no_path(self):
        provider = provider_registry.get("sqlite", {})
        assert provider.ping() == HealthStatus.UNHEALTHY

    def test_run_query(self, db_path):
        provider = provider_registry.get("sqlite", {"database": db_path})
        rows = provider.run_query("SELECT name, qty FROM widgets ORDER BY id")
        assert len(rows) == 3
        assert rows[0] == {"name": "bolt", "qty": 5}

    def test_run_query_with_params(self, db_path):
        provider = provider_registry.get("sqlite", {"database": db_path})
        rows = provider.run_query("SELECT name FROM widgets WHERE qty > ?", params=[4])
        assert [r["name"] for r in rows] == ["bolt", "screw"]

    def test_run_statement(self, db_path):
        provider = provider_registry.get("sqlite", {"database": db_path})
        result = provider.run_statement("INSERT INTO widgets (name, qty) VALUES (?, ?)", params=["washer", 2])
        assert result["success"] is True
        rows = provider.run_query("SELECT count(*) AS n FROM widgets")
        assert rows[0]["n"] == 4

    def test_run_query_returns_error_dict_on_sql_error(self, db_path):
        provider = provider_registry.get("sqlite", {"database": db_path})
        rows = provider.run_query("SELECT * FROM missing_table")
        assert "error" in rows[0]

    def test_availability_honest(self, db_path):
        provider = provider_registry.get("sqlite", {"database": db_path})
        avail = provider.availability()
        assert avail["available"] is True
        assert "run_query" in avail["capabilities"]


class TestDriverProviders:
    """Driver-based providers must report UNAVAILABLE honestly without drivers."""

    @pytest.mark.parametrize("key", ["postgresql", "mysql", "mssql", "mongodb", "redis", "elastic"])
    def test_unavailable_without_driver(self, key):
        provider = provider_registry.get(key, {})
        assert provider.ping() == HealthStatus.UNAVAILABLE

    def test_availability_marks_unavailable(self):
        provider = provider_registry.get("redis", {})
        avail = provider.availability()
        assert avail["available"] is False
        assert avail["health"] == HealthStatus.UNAVAILABLE.value
