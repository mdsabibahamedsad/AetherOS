"""Tests for config recovery, database recovery, startup, shutdown, modes,
RCA, SLA metrics, diagnostics, and the service facade."""

import os

from aetheros_reliability.checkpoint import CheckpointStore
from aetheros_reliability.config_recovery import ConfigRecovery
from aetheros_reliability.database import DatabaseRecovery
from aetheros_reliability.diagnostics import ReliabilityDiagnostics
from aetheros_reliability.modes import AetherOSMode, ModeController
from aetheros_reliability.rca import RCAConfidence, RootCauseAnalyzer
from aetheros_reliability.service import ReliabilityService
from aetheros_reliability.shutdown import ShutdownCoordinator, StageOutcome
from aetheros_reliability.slas import RecoverySLAMetrics
from aetheros_reliability.startup import StartupRecovery


def _seed_config(tmp_path):
    (tmp_path / "config.yaml").write_text(
        "agent:\n  name: t\nmodel:\n  default: x\n"
    )


class TestConfigRecovery:
    def test_validate_ok(self, tmp_path):
        _seed_config(tmp_path)
        cr = ConfigRecovery(home=tmp_path)
        assert cr.validate().valid is True

    def test_validate_bad_yaml(self, tmp_path):
        (tmp_path / "config.yaml").write_text("broken: [unclosed")
        cr = ConfigRecovery(home=tmp_path)
        assert cr.validate().valid is False

    def test_update_and_read_lkg(self, tmp_path):
        _seed_config(tmp_path)
        cr = ConfigRecovery(home=tmp_path)
        assert cr.update_last_known_good() is True
        assert cr.has_last_known_good() is True
        assert cr.last_known_good() is not None

    def test_recover_from_lkg(self, tmp_path):
        _seed_config(tmp_path)
        cr = ConfigRecovery(home=tmp_path)
        cr.update_last_known_good()
        # Corrupt the live config.
        (tmp_path / "config.yaml").write_text("broken: [unclosed")
        res = cr.recover()
        assert res["recovered_from"] == "last_known_good"
        assert res["lkg_used"] is True
        assert "agent" in (tmp_path / "config.yaml").read_text()
        # Evidence preserved.
        assert (tmp_path / "config.yaml.invalid").exists()

    def test_refuses_lkg_when_invalid(self, tmp_path):
        (tmp_path / "config.yaml").write_text("broken: [unclosed")
        cr = ConfigRecovery(home=tmp_path)
        assert cr.update_last_known_good() is False


class TestDatabaseRecovery:
    def test_missing_db_reported(self, tmp_path):
        dr = DatabaseRecovery(home=tmp_path)
        health = dr.check("state")
        assert health.ok is False
        assert "missing" in health.message

    def test_valid_sqlite_db(self, tmp_path):
        import sqlite3

        conn = sqlite3.connect(str(tmp_path / "state.db"))
        conn.execute("CREATE TABLE t (x)")
        conn.close()
        dr = DatabaseRecovery(home=tmp_path)
        health = dr.check("state")
        assert health.ok is True

    def test_corrupt_db_quarantined(self, tmp_path):
        (tmp_path / "state.db").write_bytes(b"not-a-real-db")
        dr = DatabaseRecovery(home=tmp_path)
        health = dr.check("state")
        assert health.ok is False
        dest = dr.quarantine("state")
        assert dest is not None
        assert dest.exists()
        assert not (tmp_path / "state.db").exists()
        assert len(dr.quarantined()) == 1

    def test_recover_retries(self, tmp_path):
        import sqlite3

        conn = sqlite3.connect(str(tmp_path / "state.db"))
        conn.execute("CREATE TABLE t (x)")
        conn.close()
        dr = DatabaseRecovery(home=tmp_path)
        health = dr.recover("state", retries=2, retry_delay=0)
        assert health.ok is True


class TestStartupRecovery:
    def test_unclean_detection(self, tmp_path):
        sr = StartupRecovery(home=tmp_path)
        report = sr.analyze()
        assert report.unclean_shutdown is True

    def test_clean_marker(self, tmp_path):
        sr = StartupRecovery(home=tmp_path)
        assert sr.mark_clean_shutdown() is True
        report = StartupRecovery(home=tmp_path).analyze()
        assert report.unclean_shutdown is False

    def test_stale_lock_detection(self, tmp_path):
        import time

        lock = tmp_path / "cron" / ".tick.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text("old")
        old = time.time() - 7200
        os.utime(lock, (old, old))
        sr = StartupRecovery(home=tmp_path)
        report = sr.analyze()
        assert len(report.stale_locks) >= 1


class TestShutdownCoordinator:
    def test_order_and_timeout(self):
        sc = ShutdownCoordinator()
        order = []
        sc.register("stop_workers", lambda: order.append("workers"))
        sc.register("stop_new_work", lambda: order.append("new_work"))
        sc.register("close_databases", lambda: order.append("dbs"))
        results = sc.shutdown()
        # Canonical order: stop_new_work, ..., close_databases, stop_workers.
        assert order == ["new_work", "dbs", "workers"]
        assert all(r.outcome == StageOutcome.OK for r in results)

    def test_timeout_forced(self):
        import time

        sc = ShutdownCoordinator()

        def hang():
            time.sleep(10)

        sc.register("stop_gateway", hang, timeout=0.1)
        results = sc.shutdown()
        assert results[0].outcome == StageOutcome.TIMEOUT
        assert results[0].force_killed is True

    def test_idempotent(self):
        sc = ShutdownCoordinator()
        sc.register("stop_workers", lambda: None)
        first = sc.shutdown()
        second = sc.shutdown()
        assert len(second) == len(first) == 1


class TestModeController:
    def test_safe_mode_transitions(self):
        mc = ModeController()
        assert mc.active() == AetherOSMode.NORMAL
        assert mc.enter_safe_mode(reason="test") is True
        assert mc.is_safe_mode()
        assert mc.exit_safe_mode() is True
        assert mc.active() == AetherOSMode.NORMAL

    def test_recovery_mode(self):
        mc = ModeController()
        assert mc.enter_recovery_mode(reason="operator") is True
        assert mc.is_recovery_mode()
        assert mc.exit_recovery_mode() is True

    def test_degraded_components(self):
        mc = ModeController()
        mc.enter_degraded("db", "connection lost")
        assert mc.is_degraded()
        assert mc.degraded_components() == {"db": "connection lost"}
        mc.clear_degraded("db")
        assert mc.active() == AetherOSMode.NORMAL

    def test_history(self):
        mc = ModeController()
        mc.enter_safe_mode(reason="a")
        mc.enter_recovery_mode(reason="b")
        assert len(mc.history()) == 2


class TestRootCauseAnalyzer:
    def test_unknown_without_evidence(self):
        rca = RootCauseAnalyzer()
        assert rca.analyze("gateway") is None

    def test_possible_with_trigger(self):
        rca = RootCauseAnalyzer()
        rca.record("gateway", "CRASH", trigger="oom")
        analysis = rca.analyze("gateway")
        assert analysis.occurrences == 1
        assert analysis.confidence == RCAConfidence.POSSIBLE

    def test_likely_with_repeat_failures(self):
        rca = RootCauseAnalyzer()
        for _ in range(3):
            rca.record("gateway", "CRASH", trigger="oom")
            rca.record_recovery("gateway", "success")
        analysis = rca.analyze("gateway")
        assert analysis.confidence == RCAConfidence.LIKELY
        assert analysis.recovery_attempts == 3


class TestRecoverySLAMetrics:
    def test_mttr(self):
        sla = RecoverySLAMetrics()
        sla.record_recovery("gateway", 100, True)
        sla.record_recovery("gateway", 300, True)
        assert sla.mttr() == 200.0

    def test_success_rate(self):
        sla = RecoverySLAMetrics()
        sla.record_recovery("gateway", 100, True)
        sla.record_recovery("gateway", 100, False)
        assert sla.success_rate("recovery") == 0.5

    def test_no_data(self):
        sla = RecoverySLAMetrics()
        assert sla.mttr() is None
        assert sla.success_rate("backup") is None


class TestDiagnostics:
    def test_bundle_shape(self):
        diag = ReliabilityDiagnostics()
        b = diag.bundle()
        assert b["type"] == "reliability"
        assert b["health"] is not None
        assert "platform" in b

    def test_validate_clean(self):
        diag = ReliabilityDiagnostics()
        b = diag.bundle()
        assert diag.validate(b)["valid"] is True

    def test_secret_blocklist(self):
        diag = ReliabilityDiagnostics()
        b = diag.bundle(config={"api_key": "sk-secret", "model": {"default": "x"}})
        blob = str(b)
        assert "sk-secret" not in blob

    def test_export_writes_json(self, tmp_path):
        diag = ReliabilityDiagnostics()
        out = tmp_path / "diag.json"
        assert diag.export(diag.bundle(), str(out)) is True
        assert out.exists()


class TestReliabilityService:
    def test_status_shape(self):
        svc = ReliabilityService()
        s = svc.status()
        assert s["mode"] in ("normal", "safe_mode", "recovery_mode", "degraded")
        assert "watchdog_running" in s
        assert "sla" in s
        assert "journal" in s

    def test_health(self):
        svc = ReliabilityService()
        h = svc.health()
        assert "ok" in h
        assert "mode" in h

    def test_record_recovery(self):
        svc = ReliabilityService()
        svc.record_recovery("gateway", "restart", "success", duration_ms=50)
        assert svc.sla.summary()["recovery_attempts"] >= 1
        assert len(svc.events.recent()) >= 1

    def test_watchdog_lifecycle(self):
        svc = ReliabilityService()
        svc.start_watchdog()
        assert svc.watchdog_running
        svc.stop_watchdog()
        assert not svc.watchdog_running

    def test_summary_str(self):
        svc = ReliabilityService()
        assert "mode=" in svc.summary()
