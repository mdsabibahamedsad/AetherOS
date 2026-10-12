"""Tests for tone, context awareness, voice wrapper, and the Jarvis facade."""


import aetheros_jarvis
from aetheros_jarvis.models import VoiceTone
from aetheros_jarvis.tone import ToneEngine
from aetheros_jarvis.context import ContextAwareness


class TestToneEngine:
    def test_preference_wins(self):
        engine = ToneEngine()
        assert engine.for_task("error", prefs={"tone": "concise"}) == VoiceTone.CONCISE

    def test_user_tone_overrides_task_map(self):
        engine = ToneEngine()
        engine.set_user_tone(VoiceTone.FRIENDLY)
        assert engine.for_task("error") == VoiceTone.FRIENDLY

    def test_task_mapping(self):
        engine = ToneEngine()
        assert engine.for_task("error") == VoiceTone.EMPATHETIC
        assert engine.for_task("warning") == VoiceTone.URGENT
        assert engine.for_task("summary") == VoiceTone.CONCISE

    def test_style_fallback(self):
        engine = ToneEngine()
        assert engine.for_task("general", style="friendly") == VoiceTone.FRIENDLY

    def test_default_tone(self):
        engine = ToneEngine()
        engine.set_default_tone(VoiceTone.CONCISE)
        assert engine.for_task("general", style="weird-style") == VoiceTone.CONCISE
        assert engine.for_task() == VoiceTone.PROFESSIONAL

    def test_render_professional_preserves_text(self):
        engine = ToneEngine()
        assert engine.render("Compile done", VoiceTone.PROFESSIONAL) == "Compile done"
        assert engine.render("Done", VoiceTone.CONCISE) == "Done"

    def test_render_adds_expected_prefixes(self):
        engine = ToneEngine()
        assert engine.render("watch out", VoiceTone.URGENT) == "Heads up: watch out"
        assert engine.render("you got this", VoiceTone.ENCOURAGING) == "You're making progress: you got this"

    def test_render_empty(self):
        engine = ToneEngine()
        assert engine.render("", VoiceTone.URGENT) == ""

    def test_invalid_pref_ignored(self):
        engine = ToneEngine()
        assert engine.for_task("general", prefs={"tone": "angry"}) == VoiceTone.PROFESSIONAL


class TestContextAwareness:
    def test_capture_returns_snapshot(self):
        ctx = ContextAwareness()
        snap = ctx.capture()
        assert snap.to_dict()
        assert isinstance(snap.workspace, list)
        assert isinstance(snap.open_files, list)

    def test_providers_registered(self):
        ctx = ContextAwareness()
        ctx.set_providers(["openai", "anthropic"])
        assert ctx.capture().providers == ["openai", "anthropic"]
        ctx.register_provider("deepseek")
        assert "deepseek" in ctx.capture().providers

    def test_last_snapshot_cached(self):
        ctx = ContextAwareness()
        first = ctx.capture()
        assert ctx.last is first

    def test_clipboard_opt_in(self):
        ctx = ContextAwareness()
        assert ctx.capture().clipboard == ""  # privacy-first: disabled by default
        ctx.set_clipboard_enabled(True)
        assert isinstance(ctx.capture().clipboard, str)

    def test_to_dict(self):
        ctx = ContextAwareness()
        assert isinstance(ctx.to_dict(), dict)


class TestVoiceWrapper:
    def test_wrapper_degraded_without_engine(self, monkeypatch):
        import aetheros_jarvis.voice as voice_mod

        monkeypatch.setattr(voice_mod, "VoiceEngine", None)
        wrapper = voice_mod.VoiceEngineWrapper()
        assert wrapper.available is False
        assert wrapper.stt_available() is False
        assert wrapper.tts_available() is False
        assert wrapper.list_microphones() == []
        assert wrapper.list_speakers() == []
        wrapper.interrupt()  # no crash
        wrapper.set_interruption(False)
        assert wrapper.interruption_enabled is False

    def test_wrapper_honest_reporting(self):
        import aetheros_jarvis.voice as voice_mod

        wrapper = voice_mod.VoiceEngineWrapper()
        if wrapper.available:
            assert isinstance(wrapper.stt_available(), bool)
            assert isinstance(wrapper.tts_available(), bool)
            snap = wrapper.snapshot()
            assert snap["available"] is True
            assert "state" in snap


class TestJarvisFacade:
    def test_get_jarvis_singleton(self):
        first = aetheros_jarvis.get_jarvis()
        second = aetheros_jarvis.get_jarvis()
        assert first is second

    def test_version_resolves(self):
        assert aetheros_jarvis.__version__ == "0.16.0"

    def test_status_shape(self):
        jarvis = aetheros_jarvis.get_jarvis()
        status = jarvis.status()
        for key in ("version", "runtime", "presence", "performance", "wake_word", "voice", "conversation", "mission"):
            assert key in status
        assert status["runtime"]["state"] in ("running", "stopped", "initializing", "sleeping", "paused", "shutdown")

    def test_runtime_lifecycle_via_facade(self):
        jarvis = aetheros_jarvis.Jarvis()
        assert jarvis.runtime.state.value == "stopped"
        assert jarvis.start() is True
        assert jarvis.runtime.is_running
        assert jarvis.sleep() is True
        assert jarvis.wake() is True
        assert jarvis.pause() is True
        assert jarvis.resume() is True
        assert jarvis.stop() is True
        assert jarvis.runtime.state.value == "shutdown"

    def test_handle_utterance_non_command(self):
        jarvis = aetheros_jarvis.get_jarvis()
        reply = jarvis.handle_utterance("good morning")
        assert "Understood" in reply

    def test_observe(self):
        jarvis = aetheros_jarvis.get_jarvis()
        result = jarvis.observe()
        assert "context" in result
        assert "suggestions" in result

    def test_briefing_markdown(self):
        jarvis = aetheros_jarvis.get_jarvis()
        md = jarvis.briefing_markdown()
        assert isinstance(md, str)
        assert md.startswith("# Daily Briefing")
