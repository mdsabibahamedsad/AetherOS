"""Master-13 slice 4: MCP Tasks adapter + notification preferences."""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestServerSupportsTasks:
    def test_capability_variants(self):
        from automation.mcp_tasks import server_supports_tasks

        assert server_supports_tasks({"tasks": {}}) is True
        assert server_supports_tasks({"tasks": {"cancel": {}}}) is True
        assert not server_supports_tasks({"tools": {}})
        assert not server_supports_tasks(None)


class TestNormalizeMcpTask:
    def test_state_mapping_preserves_source(self):
        from automation.mcp_tasks import normalize_mcp_task

        raw = {
            "taskId": "t-1",
            "status": "input_required",
            "statusMessage": "awaiting user",
            "customField": "keep-me",
        }
        mapped = normalize_mcp_task(raw)
        assert mapped["task_id"] == "t-1"
        assert mapped["status"] == "waiting_approval"
        assert mapped["mcp"]["customField"] == "keep-me"

    def test_unknown_status_maps_safe(self):
        from automation.mcp_tasks import normalize_mcp_task

        mapped = normalize_mcp_task({"id": "x", "status": "warp-drive"})
        assert mapped["status"] == "unknown"
        mapped2 = normalize_mcp_task("garbage")
        assert mapped2["status"] == "unknown"


class TestPollTask:
    def test_returns_immediately_when_terminal(self):
        from automation.mcp_tasks import poll_task

        result = poll_task(lambda: {"taskId": "t", "status": "completed"}, timeout=5)
        assert result["status"] == "completed"

    def test_bounded_backoff_then_none(self, monkeypatch):
        import automation.mcp_tasks as mt

        sleeps = []
        monkeypatch.setattr(mt.time, "sleep", lambda s: sleeps.append(s))
        result = mt.poll_task(
            lambda: None, interval=1.0, max_interval=4.0, timeout=0.001
        )
        assert result is None


class TestRequestCancellation:
    def test_sent(self):
        from automation.mcp_tasks import request_cancellation

        seen = []
        assert request_cancellation(lambda tid: (seen.append(tid), {"ok": True})[1], "t1") == "sent"
        assert seen == ["t1"]

    def test_unsupported_without_capability(self):
        from automation.mcp_tasks import request_cancellation

        assert request_cancellation(None, "t") == "unsupported"

    def test_error_reported(self):
        from automation.mcp_tasks import request_cancellation

        def boom(_tid):
            raise RuntimeError("nope")

        assert request_cancellation(boom, "t") == "failed"

    def test_error_payload_reported(self):
        from automation.mcp_tasks import request_cancellation

        assert request_cancellation(lambda _t: {"error": "denied"}, "t") == "failed"


CFG_QUIET = {
    "automation": {
        "notifications": {
            "events": [],
            "quiet_hours": {"start": "22:30", "end": "07:00"},
        }
    }
}


class TestNotificationPreferences:
    def test_default_set_notifies_off_hours(self):
        from automation.notifications import should_notify

        noon = datetime(2026, 8, 22, 12, 0)
        assert should_notify("automation.failed", cfg=CFG_QUIET, now=noon)
        assert not should_notify("automation.some.custom", cfg=CFG_QUIET, now=noon)

    def test_quiet_hours_suppress_non_critical(self):
        from automation.notifications import should_notify

        late = datetime(2026, 8, 22, 23, 30)
        early = datetime(2026, 8, 22, 6, 0)
        assert not should_notify("automation.failed", cfg=CFG_QUIET, now=late)
        assert not should_notify("automation.failed", cfg=CFG_QUIET, now=early)

    def test_critical_events_bypass_quiet_hours(self):
        from automation.notifications import should_notify

        late = datetime(2026, 8, 22, 23, 30)
        assert should_notify("automation.quarantined", cfg=CFG_QUIET, now=late)
        assert should_notify("automation.waiting_approval", cfg=CFG_QUIET, now=late)

    def test_allowlist_with_wildcard(self):
        from automation.notifications import should_notify

        cfg = {
            "automation": {
                "notifications": {
                    "events": ["automation.completed"],
                    "quiet_hours": {},
                }
            }
        }
        noon = datetime(2026, 8, 22, 12, 0)
        assert should_notify("automation.completed", cfg=cfg, now=noon)
        assert not should_notify("automation.failed", cfg=cfg, now=noon)


class TestRetentionConfig:
    def test_default_and_override(self):
        from automation.notifications import retention_days

        assert retention_days({}) == 30
        assert (
            retention_days({"automation": {"history": {"retention_days": 7}}}) == 7
        )
