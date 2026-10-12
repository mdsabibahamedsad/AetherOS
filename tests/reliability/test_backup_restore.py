"""Tests for backup/restore: integrity, atomicity, rotation, rollback."""

import json
import zipfile

from aetheros_reliability.backup import (
    BACKUP_SCHEMA_VERSION,
    BackupIntegrity,
    BackupStore,
)
from aetheros_reliability.restore import RecoveryManager


def _seed_home(tmp_path):
    (tmp_path / "config.yaml").write_text("agent:\n  name: t\nmodel:\n  default: x\n")
    (tmp_path / "auth.json").write_text('{"key":"v"}')
    (tmp_path / "cron").mkdir()
    (tmp_path / "cron" / "jobs.json").write_text("[]")
    import sqlite3

    conn = sqlite3.connect(str(tmp_path / "state.db"))
    conn.execute("CREATE TABLE t (x)")
    conn.close()


class TestBackupStore:
    def test_create_and_list(self, tmp_path):
        _seed_home(tmp_path)
        store = BackupStore(root=tmp_path / "reliability" / "backups", source=tmp_path)
        entry = store.create(label="test")
        assert entry is not None
        assert entry.schema_version == BACKUP_SCHEMA_VERSION
        assert entry.file_count >= 2
        listed = store.list()
        assert listed[0].backup_id == entry.backup_id
        assert listed[0].valid is True

    def test_verify_passes(self, tmp_path):
        _seed_home(tmp_path)
        store = BackupStore(root=tmp_path / "reliability" / "backups", source=tmp_path)
        entry = store.create()
        ok, report = store.verify(entry.backup_id)
        assert ok is True
        assert report["checks"]["schema"] is True
        assert report["checks"]["manifest"] is True
        assert report["checks"]["required_files"] is True
        assert report["checks"]["checksums"] is True

    def test_verify_detects_corruption(self, tmp_path):
        _seed_home(tmp_path)
        store = BackupStore(root=tmp_path / "reliability" / "backups", source=tmp_path)
        entry = store.create()
        archive = tmp_path / "reliability" / "backups" / f"backup-{entry.backup_id}.zip"
        # Corrupt a byte in the archive body.
        data = bytearray(archive.read_bytes())
        data[len(data) // 2] ^= 0xFF
        archive.write_bytes(bytes(data))
        ok, report = BackupIntegrity.verify(archive)
        assert ok is False
        assert report["checks"]["zip"] is False or report["checks"]["checksums"] is False

    def test_verify_requires_manifest(self, tmp_path):
        _seed_home(tmp_path)
        store = BackupStore(root=tmp_path / "reliability" / "backups", source=tmp_path)
        entry = store.create()
        archive = tmp_path / "reliability" / "backups" / f"backup-{entry.backup_id}.zip"
        # Rewrite archive without the manifest.
        with zipfile.ZipFile(archive, "r") as zf:
            names = [n for n in zf.namelist() if n != "reliability-manifest.json"]
            data = {n: zf.read(n) for n in names}
        with zipfile.ZipFile(archive, "w") as zf:
            for n, d in data.items():
                zf.writestr(n, d)
        ok, report = BackupIntegrity.verify(archive)
        assert ok is False
        assert report["reason"] == "missing reliability manifest"

    def test_prune_keeps_newest(self, tmp_path):
        _seed_home(tmp_path)
        store = BackupStore(root=tmp_path / "reliability" / "backups", source=tmp_path)
        for i in range(4):
            entry = store.create(label=f"b{i}")
        assert len(store.list()) == 4
        removed = store.prune(keep=2)
        assert len(removed) == 2
        remaining = store.list()
        assert len(remaining) == 2
        assert remaining[0].created_at >= remaining[1].created_at

    def test_prune_never_deletes_only_valid(self, tmp_path):
        _seed_home(tmp_path)
        store = BackupStore(root=tmp_path / "reliability" / "backups", source=tmp_path)
        store.create()
        removed = store.prune(keep=0)
        assert removed == []
        assert len(store.list()) == 1

    def test_manifest_marks_secrets(self, tmp_path):
        _seed_home(tmp_path)
        store = BackupStore(root=tmp_path / "reliability" / "backups", source=tmp_path)
        entry = store.create()
        archive = tmp_path / "reliability" / "backups" / f"backup-{entry.backup_id}.zip"
        with zipfile.ZipFile(archive, "r") as zf:
            manifest = json.loads(zf.read("reliability-manifest.json"))
        assert manifest["files"]["auth.json"]["secret"] is True
        assert manifest["files"]["config.yaml"]["secret"] is False

    def test_corrupt_db_does_not_abort_backup(self, tmp_path):
        _seed_home(tmp_path)
        (tmp_path / "state.db").write_bytes(b"not-a-real-db")
        store = BackupStore(root=tmp_path / "reliability" / "backups", source=tmp_path)
        entry = store.create()
        assert entry is not None
        assert entry.file_count >= 3


class TestRecoveryManager:
    def test_preview_no_mutation(self, tmp_path):
        _seed_home(tmp_path)
        store = BackupStore(root=tmp_path / "reliability" / "backups", source=tmp_path)
        entry = store.create()
        mgr = RecoveryManager(store=store, target=tmp_path)
        before = (tmp_path / "config.yaml").read_text()
        pv = mgr.preview(entry.backup_id, scope="config")
        assert pv.valid is True
        assert pv.files_to_restore == 1
        assert (tmp_path / "config.yaml").read_text() == before

    def test_restore_config_scope(self, tmp_path):
        _seed_home(tmp_path)
        store = BackupStore(root=tmp_path / "reliability" / "backups", source=tmp_path)
        entry = store.create()
        # Break config, then restore it.
        (tmp_path / "config.yaml").write_text("broken: [unclosed")
        mgr = RecoveryManager(store=store, target=tmp_path)
        result = mgr.restore(entry.backup_id, scope="config", snapshot=True)
        assert result["restored"] is True
        assert result["verified"] is True
        assert "config.yaml" in result["files"]
        assert "agent" in (tmp_path / "config.yaml").read_text()

    def test_unknown_backup_returns_error(self, tmp_path):
        _seed_home(tmp_path)
        store = BackupStore(root=tmp_path / "reliability" / "backups", source=tmp_path)
        mgr = RecoveryManager(store=store, target=tmp_path)
        result = mgr.restore("nope", scope="config")
        assert result["restored"] is False
        assert "unknown backup" in result["error"]

    def test_snapshot_and_rollback(self, tmp_path):
        _seed_home(tmp_path)
        (tmp_path / "config.yaml").write_text("agent:\n  name: original\nmodel:\n  default: x\n")
        store = BackupStore(root=tmp_path / "reliability" / "backups", source=tmp_path)
        mgr = RecoveryManager(store=store, target=tmp_path)
        snap_id = mgr.create_restore_snapshot()
        assert snap_id in mgr.list_snapshots()
        # Mutate state.
        (tmp_path / "config.yaml").write_text("agent:\n  name: changed\nmodel:\n  default: x\n")
        restored = mgr.rollback(snap_id)
        assert restored >= 1
        assert "original" in (tmp_path / "config.yaml").read_text()

    def test_path_traversal_blocked(self, tmp_path):
        _seed_home(tmp_path)
        store = BackupStore(root=tmp_path / "reliability" / "backups", source=tmp_path)
        entry = store.create()
        archive = tmp_path / "reliability" / "backups" / f"backup-{entry.backup_id}.zip"
        # Inject a malicious entry with an absolute path.
        with zipfile.ZipFile(archive, "a") as zf:
            zf.writestr("../../evil.txt", "owned")
        mgr = RecoveryManager(store=store, target=tmp_path)
        result = mgr.restore(entry.backup_id, scope="full", snapshot=False)
        # Either it's blocked or integrity fails — never write outside home.
        assert (tmp_path.parent / "evil.txt").exists() is False
