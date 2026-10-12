"""Tests for proactive suggestions and daily briefing (aetheros_jarvis)."""

from datetime import datetime, timedelta

from aetheros_jarvis.briefing import DailyBriefingEngine
from aetheros_jarvis.models import ContextSnapshot, SuggestionStatus
from aetheros_jarvis.proactive import ProactiveEngine


def _future(minutes=10):
    return (datetime.now() + timedelta(minutes=minutes)).isoformat()


class TestProactiveEngine:
    def test_disabled_engine_produces_nothing(self):
        engine = ProactiveEngine()
        engine.set_enabled(False)
        assert engine.observe(ContextSnapshot()) == []

    def test_absent_user_produces_nothing(self):
        engine = ProactiveEngine()
        engine.set_presence_fn(lambda: False)
        assert engine.observe(ContextSnapshot()) == []

    def test_battery_suggestion(self):
        engine = ProactiveEngine()
        suggestions = engine.observe(ContextSnapshot(battery_percent=12))
        assert len(suggestions) == 1
        assert suggestions[0].source == "battery"
        assert suggestions[0].action == "open_battery_settings"
        assert "12" in suggestions[0].body

    def test_healthy_battery_no_suggestion(self):
        engine = ProactiveEngine()
        assert engine.observe(ContextSnapshot(battery_percent=85)) == []

    def test_calendar_suggestion(self):
        engine = ProactiveEngine()
        engine.set_calendar([{"title": "Standup", "start": _future(5)}])
        suggestions = engine.observe(ContextSnapshot())
        assert any(s.source == "calendar" for s in suggestions)
        assert any("Standup" in s.title for s in suggestions)

    def test_far_future_event_not_suggested(self):
        engine = ProactiveEngine()
        engine.set_calendar([{"title": "Review", "start": _future(120)}])
        assert engine.observe(ContextSnapshot()) == []

    def test_task_deadline_suggestion(self):
        engine = ProactiveEngine()
        engine.set_tasks([{"title": "Submit PR", "due": _future(minutes=60)}])
        suggestions = engine.observe(ContextSnapshot())
        assert any(s.source == "tasks" for s in suggestions)
        assert any("Submit PR" in s.title for s in suggestions)

    def test_workspace_suggestion(self):
        engine = ProactiveEngine()
        suggestions = engine.observe(ContextSnapshot(project="hermes-agent"))
        assert any(s.source == "workspace" for s in suggestions)

    def test_cooldown_suppresses_repeat_emission(self):
        engine = ProactiveEngine()
        engine.set_min_interval(30)
        first = engine.observe(ContextSnapshot(battery_percent=10))
        assert len(first) == 1
        second = engine.observe(ContextSnapshot(battery_percent=10))
        assert second == []  # within cooldown window

    def test_listener_receives_suggestions(self):
        engine = ProactiveEngine()
        received = []
        engine.on_suggestion(received.append)
        engine.observe(ContextSnapshot(battery_percent=5))
        assert len(received) == 1

    def test_accept_and_dismiss(self):
        engine = ProactiveEngine()
        engine.observe(ContextSnapshot(battery_percent=5))
        suggestion = engine.list_suggestions()[0]
        assert engine.dismiss(suggestion.id) is True
        assert engine.list_suggestions(status=SuggestionStatus.DISMISSED)
        assert engine.accept(suggestion.id) is True
        assert engine.list_suggestions(status=SuggestionStatus.ACCEPTED)
        assert engine.dismiss("missing") is False

    def test_every_suggestion_is_explainable(self):
        engine = ProactiveEngine()
        engine.set_calendar([{"title": "Sync", "start": _future(3)}])
        engine.set_tasks([{"title": "Ship", "due": _future(minutes=30)}])
        suggestions = engine.observe(ContextSnapshot(battery_percent=8))
        assert len(suggestions) >= 1
        for s in suggestions:
            assert s.reason
            assert s.title
            assert s.body


class TestDailyBriefing:
    def test_generate_with_data(self):
        engine = DailyBriefingEngine()
        engine.set_calendar([{"title": "Standup", "start": "2026-01-01T09:00:00"}])
        engine.set_tasks([{"title": "Ship v0.16", "due": "2026-01-02"}])
        engine.set_emails([{"subject": "Review", "from": "teo"}])
        engine.set_activity(["Worked on CLI"])
        engine.set_reminders(["Water plants"])
        engine.set_weather("Sunny, 21C")
        briefing = engine.generate()
        assert briefing.date
        titles = [s.title for s in briefing.sections]
        assert "Today's Agenda" in titles
        assert "Pending Tasks" in titles
        assert "Weather" in titles
        md = briefing.to_markdown()
        assert "# Daily Briefing" in md
        assert "Standup" in md
        assert "Ship v0.16" in md

    def test_empty_sections_render_empty_message(self):
        engine = DailyBriefingEngine()
        briefing = engine.generate()
        sections = {s.title: s for s in briefing.sections}
        assert sections["Pending Tasks"].items == []
        assert sections["Pending Tasks"].empty_message
        md = briefing.to_markdown()
        assert "No pending tasks." in md

    def test_done_tasks_excluded(self):
        engine = DailyBriefingEngine()
        engine.set_tasks([
            {"title": "Done task", "status": "done"},
            {"title": "Open task"},
        ])
        briefing = engine.generate()
        section = [s for s in briefing.sections if s.title == "Pending Tasks"][0]
        assert "Open task" in section.items
        assert not any("Done task" in item for item in section.items)

    def test_weather_omitted_when_unset(self):
        engine = DailyBriefingEngine()
        briefing = engine.generate()
        assert "Weather" not in [s.title for s in briefing.sections]

    def test_to_markdown_before_generate(self):
        engine = DailyBriefingEngine()
        assert "No briefing generated yet." in engine.to_markdown()

    def test_snapshot(self):
        engine = DailyBriefingEngine()
        engine.set_emails([{"subject": "x", "from": "y"}])
        snap = engine.snapshot()
        assert snap["generated"] is False
        assert snap["emails"] == 1
