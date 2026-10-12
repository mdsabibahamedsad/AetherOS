"""Tests for notification intelligence and voice commands (aetheros_jarvis)."""

from aetheros_jarvis.models import NotificationPriority
from aetheros_jarvis.notifications import NotificationIntelligence
from aetheros_jarvis.permissions import PermissionLayer
from aetheros_jarvis.voice_commands import VoiceCommandRegistry


class TestNotificationIntelligence:
    def test_ingest_returns_item(self):
        n = NotificationIntelligence()
        item = n.ingest(title="Build passed", body="all green", source="ci")
        assert item is not None
        assert item.title == "Build passed"

    def test_duplicate_grouping(self):
        n = NotificationIntelligence()
        n.ingest(title="Build passed", body="first", source="ci")
        second = n.ingest(title="Build passed", body="second", source="ci")
        assert second is not None
        assert "+1 more" in second.body
        assert n.history()[-1]["duplicates"] == 2

    def test_mute_suppresses(self):
        n = NotificationIntelligence()
        n.mute("ci", seconds=60)
        assert n.ingest(title="Build passed", source="ci") is None
        n.unmute("ci")
        assert n.ingest(title="Build passed", source="ci") is not None

    def test_priority_queue_orders_by_priority(self):
        n = NotificationIntelligence()
        n.ingest(title="low", priority=NotificationPriority.LOW)
        n.ingest(title="urgent", priority=NotificationPriority.URGENT)
        n.ingest(title="high", priority=NotificationPriority.HIGH)
        queue = n.priority_queue()
        assert [i.title for i in queue] == ["urgent", "high", "low"]

    def test_urgent_filter(self):
        n = NotificationIntelligence()
        n.ingest(title="a", priority=NotificationPriority.HIGH)
        n.ingest(title="b", priority=NotificationPriority.URGENT)
        assert [i.title for i in n.urgent()] == ["b"]

    def test_escalate(self):
        n = NotificationIntelligence()
        item = n.ingest(title="quiet", priority=NotificationPriority.LOW)
        n.escalate(item)
        assert item.priority == NotificationPriority.URGENT
        assert n.urgent()[0].title == "quiet"

    def test_summarize(self):
        n = NotificationIntelligence()
        n.ingest(title="t1", priority=NotificationPriority.HIGH)
        n.ingest(title="t1", priority=NotificationPriority.HIGH)
        text = n.summarize()
        assert "HIGH" in text
        assert "t1" in text
        assert "+1 duplicate" in text

    def test_summarize_empty(self):
        assert NotificationIntelligence().summarize() == "No notifications."

    def test_listener(self):
        n = NotificationIntelligence()
        received = []
        n.on_notification(received.append)
        n.ingest(title="hi")
        assert len(received) == 1

    def test_snapshot(self):
        n = NotificationIntelligence()
        n.ingest(title="x", source="mail")
        snap = n.snapshot()
        assert snap["total"] == 1
        assert snap["muted_sources"] == []


class _FakePermissions:
    def __init__(self, allow=True):
        self._allow = allow
        self.calls = []

    def require(self, permission, *, requester="", reason="", action="", target=""):
        self.calls.append(permission)
        return self._allow


class TestVoiceCommandRegistry:
    def test_match_longest_phrase(self):
        reg = VoiceCommandRegistry()
        match = reg.match("please open application now")
        assert match["name"] == "open_app"
        assert match["action"] == "open_app"

    def test_no_match(self):
        reg = VoiceCommandRegistry()
        assert reg.match("sing me a song") is None
        assert reg.execute("sing me a song")["ok"] is False

    def test_command_names(self):
        reg = VoiceCommandRegistry()
        assert "help" in reg.command_names()
        assert "open_app" in reg.command_names()

    def test_permission_gate_denies(self):
        perms = _FakePermissions(allow=False)
        reg = VoiceCommandRegistry(perms)
        reg.register("open_app", lambda **kw: "launched")
        result = reg.execute("open application")
        assert result["ok"] is False
        assert result["error"] == "Permission denied"
        assert perms.calls == ["system:change"]

    def test_permission_gate_allows_and_runs_handler(self):
        perms = _FakePermissions(allow=True)
        reg = VoiceCommandRegistry(perms)
        reg.register("open_app", lambda **kw: "launched")
        result = reg.execute("open application")
        assert result["ok"] is True
        assert result["result"] == "launched"
        assert perms.calls == ["system:change"]

    def test_help_needs_no_permission(self):
        reg = VoiceCommandRegistry(_FakePermissions(allow=False))
        reg.register("help", lambda **kw: "I can help")
        result = reg.execute("help")
        assert result["ok"] is True
        assert result["result"] == "I can help"

    def test_no_handler(self):
        reg = VoiceCommandRegistry()
        result = reg.execute("open application")
        assert result["ok"] is False
        assert result["error"] == "No handler registered"

    def test_handler_error_recorded(self):
        reg = VoiceCommandRegistry()
        reg.register("help", lambda **kw: (_ for _ in ()).throw(RuntimeError("kaboom")))
        result = reg.execute("help")
        assert result["ok"] is False
        assert "kaboom" in result["error"]
        assert reg.execution_log()[-1]["ok"] is False

    def test_execution_log(self):
        reg = VoiceCommandRegistry()
        reg.register("open_app", lambda **kw: "launched")
        result = reg.execute("open application")
        assert result["ok"] is True
        log = reg.execution_log()
        assert log[-1]["ok"] is True
        assert log[-1]["command"] == "open_app"

    def test_unmatched_utterance_not_logged(self):
        reg = VoiceCommandRegistry()
        reg.execute("sing me a song")
        assert reg.execution_log() == []

    def test_integration_with_real_permission_layer(self):
        layer = PermissionLayer()
        layer.set_approval_resolver(lambda ctx: True)
        reg = VoiceCommandRegistry(layer)
        reg.register("search_files", lambda **kw: "results")
        result = reg.execute("search files for notes")
        assert result["ok"] is True
        assert result["result"] == "results"
