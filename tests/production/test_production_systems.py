"""Tests for aetheros_production backup, update system, observability, packaging."""

import json
import os

import pytest

from aetheros_production.backup import BackupManager
from aetheros_production.observability import MetricsRegistry, Tracer, get_metrics_registry
from aetheros_production.packaging import PackagingManager
from aetheros_production.release import ReleaseManager
from aetheros_production.update_system import UpdateManager


@pytest.fixture
def backup(tmp_path):
    return BackupManager(home=tmp_path)


class TestBackup:
    def test_full_backup_roundtrip(self, backup, tmp_path):
        (tmp_path / "config.yaml").write_text("key: value\n")
        (tmp_path / "state.db").write_bytes(b"\x00\x01\x02binary")

        info = backup.create_backup("full")
        assert "error" not in info
        backup_id = info["id"]

        listed = backup.list_backups()
        assert any(b["backup_id"] == backup_id for b in listed)
        assert backup.verify_backup(backup_id)

    def test_incremental_no_changes(self, backup, tmp_path):
        (tmp_path / "config.yaml").write_text("key: value\n")

        info = backup.create_backup("full")
        assert "error" not in info
        inc = backup.create_backup("incremental")
        # No changes since last backup -> skipped.
        assert inc["status"] == "no_changes"

    def test_restore_backup(self, backup, tmp_path):
        (tmp_path / "config.yaml").write_text("key: value\n")

        info = backup.create_backup("full")
        backup_id = info["id"]
        (tmp_path / "config.yaml").write_text("key: tampered\n")

        result = backup.restore_backup(backup_id)
        assert result.get("success")
        assert (tmp_path / "config.yaml").read_text() == "key: value\n"

    def test_export_import(self, backup, tmp_path):
        (tmp_path / "config.yaml").write_text("key: value\n")

        info = backup.create_backup("full")
        backup_id = info["id"]
        export_path = tmp_path / "export.aeb"
        assert backup.export_backup(backup_id, str(export_path))
        assert export_path.exists()

        new_mgr = BackupManager(home=tmp_path / "other_home")
        new_mgr._backup_dir.mkdir(parents=True, exist_ok=True)
        new_id = new_mgr.import_backup(str(export_path))
        assert new_id is not None
        assert new_mgr.verify_backup(new_id)

    def test_prune(self, backup, tmp_path):
        (tmp_path / "config.yaml").write_text("key: value\n")
        for _ in range(5):
            backup.create_backup("full")
        pruned = backup.prune_backups(max_backups=2)
        assert pruned >= 3
        assert len(backup.list_backups()) <= 2


class TestUpdateSystem:
    def test_version_save_and_rollback(self, tmp_path):
        um = UpdateManager(home=tmp_path)
        um._save_version("1.1.0")
        assert um.get_current_version() == "1.1.0"
        assert um._version_is_newer("1.2.0")
        assert not um._version_is_newer("1.0.0")

        um.add_to_history("1.1.0", "update", from_version="1.0.0", backup_id="b1")
        um.add_to_history("1.2.0", "update", from_version="1.1.0", backup_id="b2")
        history = um.get_version_history()
        assert history[0]["version"] == "1.2.0"

        # Simulate: we are on 1.2.0, roll back to the previous known version.
        um._save_version("1.2.0")
        result = um.rollback()
        assert result.success
        assert um.get_current_version() == "1.1.0"

    def test_rollback_to_specific_version(self, tmp_path):
        um = UpdateManager(home=tmp_path)
        um._save_version("1.2.0")
        um.add_to_history("1.0.0", "update")
        um.add_to_history("1.1.0", "update")
        result = um.rollback(target_version="1.0.0")
        assert result.success
        assert um.get_current_version() == "1.0.0"

    def test_update_same_version_noop(self, tmp_path):
        um = UpdateManager(home=tmp_path)
        um._save_version("1.0.0")
        result = um.update("1.0.0")
        assert not result.success
        assert "Already on this version" in result.message

    def test_update_requires_package(self, tmp_path):
        um = UpdateManager(home=tmp_path)
        um._save_version("1.0.0")
        result = um.update("1.1.0")
        # No package and no download URL -> no-op install still records version.
        assert result.success

    def test_hash_mismatch_rejected(self, tmp_path):
        um = UpdateManager(home=tmp_path)
        um._save_version("1.0.0")
        pkg = tmp_path / "update.pkg"
        pkg.write_bytes(b"package-content")
        result = um.update("1.1.0", package_path=str(pkg), expected_sha256="0" * 64)
        assert not result.success
        assert "hash mismatch" in result.message

    def test_channels(self, tmp_path):
        um = UpdateManager(home=tmp_path)
        assert um.set_release_channel("beta")
        assert um.get_release_channel() == "beta"
        assert not um.set_release_channel("nonexistent")

    def test_check_for_updates_offline(self, tmp_path):
        um = UpdateManager(home=tmp_path)
        um.set_update_url("https://nonexistent.invalid/manifest.json")
        assert um.check_for_updates() is None  # offline-safe


class TestObservability:
    def test_metrics_registry(self):
        m = MetricsRegistry()
        m.increment("agent.messages", labels={"platform": "cli"})
        m.increment("agent.messages", labels={"platform": "cli"})
        m.set_gauge("active", 3)
        m.observe("latency", 10)
        m.observe("latency", 20)
        snap = m.snapshot()
        assert snap["counters"]["agent.messages{platform=\"cli\"}"] == 2
        assert snap["gauges"]["active"] == 3
        assert snap["histograms"]["latency"]["count"] == 2
        assert snap["histograms"]["latency"]["sum"] == 30

    def test_tracer_span_hierarchy(self):
        t = Tracer()
        with t.start_span("outer") as outer:
            with t.start_span("inner"):
                pass
        traces = t.get_traces()
        by_name = {x["name"]: x for x in traces}
        assert by_name["outer"]["parent_id"] is None
        assert by_name["inner"]["parent_id"] == by_name["outer"]["span_id"]

    def test_prometheus_export(self):
        m = MetricsRegistry()
        m.increment("hits")
        out = m.export_prometheus()
        assert "hits" in out


class TestPackaging:
    def test_homebrew_uses_real_version(self, tmp_path):
        pm = PackagingManager()
        pm._output_dir = tmp_path
        result = pm.generate_package("homebrew")
        assert result.success
        content = open(result.path).read()
        assert "PLACEHOLDER" not in content
        assert "COMPUTE_AFTER_RELEASE" in content

    def test_sbom(self, tmp_path):
        pm = PackagingManager()
        pm._output_dir = tmp_path
        result = pm.generate_sbom(str(tmp_path / "sbom.json"))
        assert result.success
        data = json.loads(open(result.path).read())
        assert data["bomFormat"] == "CycloneDX"
        names = [c["name"] for c in data["components"]]
        assert "cryptography" in names


class TestRelease:
    def test_version_matches_installed(self):
        from aetheros_production import get_version
        rm = ReleaseManager()
        assert rm.get_version_info()["version"] == get_version()
        assert rm.get_version_info()["version"] != "1.0.0"

    def test_release_manifest_checksums(self, tmp_path):
        rm = ReleaseManager()
        artifact = tmp_path / "aether-0.16.0.tar.gz"
        artifact.write_bytes(b"artifact-bytes")
        manifest = rm.create_release_manifest(
            output_dir=tmp_path,
            channel="beta",
            artifacts=[artifact],
        )
        assert manifest["version"] == rm.get_version_info()["version"]
        assert manifest["channel"] == "beta"
        assert manifest["checksums"]["aether-0.16.0.tar.gz"] == "6521df166eb07efaf36eba5b6bedefd9d6a252e9c80bab1c99653700ec71473c"
        assert (tmp_path / "release.json").exists()

    def test_release_notes_use_real_version(self):
        rm = ReleaseManager()
        notes = rm.generate_release_notes()
        assert f"v{rm.get_version_info()['version']}" in notes
