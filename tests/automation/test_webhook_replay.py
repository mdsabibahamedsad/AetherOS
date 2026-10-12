"""Master-13 slice 2: webhook replay-window protection (Phase 13)."""

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

pytest.importorskip("aiohttp")

from gateway.platforms.webhook import WebhookAdapter


class _Req:
    def __init__(self, headers=None):
        self.headers = headers or {}


class TestReplayWindow:
    def test_no_timestamp_header_still_accepted(self):
        req = _Req({"X-Webhook-Signature": "abc"})
        assert WebhookAdapter._check_replay_window(None, req) is True

    def test_fresh_seconds_timestamp_accepted(self):
        req = _Req({"X-Webhook-Timestamp": str(int(time.time()))})
        assert WebhookAdapter._check_replay_window(None, req) is True

    def test_stale_seconds_timestamp_rejected(self):
        stale = str(int(time.time()) - 3600)
        req = _Req({"X-Webhook-Timestamp": stale})
        assert WebhookAdapter._check_replay_window(None, req) is False

    def test_milliseconds_variant(self):
        now_ms = str(int(time.time() * 1000))
        assert WebhookAdapter._check_replay_window(None, _Req({
            "X-Webhook-Timestamp-MS": now_ms
        })) is True

    def test_garbage_timestamp_rejected(self):
        req = _Req({"X-Webhook-Timestamp": "not-a-number"})
        assert WebhookAdapter._check_replay_window(None, req) is False

    def test_custom_tolerance(self):
        recent = str(int(time.time()) - 120)
        req = _Req({"X-Webhook-Timestamp": recent})
        assert WebhookAdapter._check_replay_window(None, req, tolerance_seconds=60) is False
        assert WebhookAdapter._check_replay_window(None, req, tolerance_seconds=300) is True
