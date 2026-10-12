"""Tests for mobile contracts (Master 67). All executable here."""

from aetheros_platform.mobile_contract import (
    MOBILE_ROUTES,
    DeviceRecord,
    DeviceTrust,
    OfflineClass,
    OfflineOp,
    parse_deep_link,
    validate_push_payload,
    verify_against_backend,
)


def test_backend_serves_every_mobile_route():
    """Real contract check: import api_server, assert handlers exist."""
    results = verify_against_backend()
    assert len(results) == len(MOBILE_ROUTES)
    for handler, present in results.items():
        assert present, f"backend missing handler {handler}"


def test_deep_link_valid():
    assert parse_deep_link("aetheros://task/abc-123") == ("task", "abc-123")
    assert parse_deep_link("aetheros://approval?id=XYZ_9") == ("approval", "XYZ_9")


def test_deep_link_rejects():
    assert parse_deep_link("https://evil.com/task/1") is None
    assert parse_deep_link("aetheros://approve-all/yes") is None
    assert parse_deep_link("aetheros://task/") is None
    assert parse_deep_link("aetheros://task/" + "x" * 200) is None
    assert parse_deep_link("aetheros://task/a;b") is None
    assert parse_deep_link("aetheros://task/$(rm)") is None


def test_push_forbids_secrets():
    ok, _ = validate_push_payload({"notification_id": "n1", "task_id": "t1",
                                   "title": "Approval requested"})
    assert ok
    ok, problems = validate_push_payload({"task_id": "t1",
                                          "access_token": "sek"})
    assert not ok and any("access_token" in p for p in problems)
    ok, problems = validate_push_payload({"transcript": "..."})
    assert not ok


def test_offline_classification():
    now = 1_700_000_000.0
    q = OfflineOp("o1", "create_task", "low", now, now + 3600, "k1")
    assert q.classify() == OfflineClass.QUEUEABLE
    assert q.replayable(now + 10)
    assert not q.replayable(now + 7200)  # expired
    hi = OfflineOp("o2", "approve", "critical", now, now + 3600, "k2")
    assert hi.classify() == OfflineClass.HIGH_RISK_ONLINE_REQUIRED
    assert not hi.replayable(now + 10)  # never blind-replayed
    rd = OfflineOp("o3", "search", "low", now, now + 60, "k3")
    assert rd.classify() == OfflineClass.SAFE_OFFLINE


def test_device_trust():
    d = DeviceRecord("d", "i", "ios", "18.0", "1.0.0")
    assert not d.authorize()
    d.trust = DeviceTrust.KNOWN
    assert d.authorize()
    d.trust = DeviceTrust.REVOKED
    assert not d.authorize()
