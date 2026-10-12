"""Tests for persistence-backed Jarvis subsystems (config, memory, personalization, accessibility)."""


from aetheros_jarvis.accessibility import AccessibilityManager
from aetheros_jarvis.config import JarvisConfigManager
from aetheros_jarvis.memory import JarvisMemory
from aetheros_jarvis.models import JarvisMode
from aetheros_jarvis.personalization import VoicePersonalization


class TestJarvisConfigManager:
    def test_defaults(self, tmp_path):
        mgr = JarvisConfigManager(home=tmp_path)
        assert mgr.config.enabled is True
        assert mgr.config.mode == JarvisMode.INTERACTIVE

    def test_update_and_reload(self, tmp_path):
        mgr = JarvisConfigManager(home=tmp_path)
        mgr.update(proactive_enabled=False, stt_provider="edge")
        assert mgr.config.proactive_enabled is False

        fresh = JarvisConfigManager(home=tmp_path)
        assert fresh.config.proactive_enabled is False
        assert fresh.config.stt_provider == "edge"

    def test_set_mode_persists(self, tmp_path):
        mgr = JarvisConfigManager(home=tmp_path)
        mgr.set_mode(JarvisMode.QUIET)
        fresh = JarvisConfigManager(home=tmp_path)
        assert fresh.config.mode == JarvisMode.QUIET

    def test_export_roundtrip(self, tmp_path):
        mgr = JarvisConfigManager(home=tmp_path)
        mgr.update(voice_speed=1.4)
        data = mgr.export()
        assert data["voice_speed"] == 1.4
        assert data["mode"] == "interactive"

    def test_get(self, tmp_path):
        mgr = JarvisConfigManager(home=tmp_path)
        assert mgr.get("wake_phrases") == ["aether", "jarvis"]
        assert mgr.get("missing", "fallback") == "fallback"

    def test_unknown_key_ignored(self, tmp_path):
        mgr = JarvisConfigManager(home=tmp_path)
        mgr.update(not_a_real_setting=123)
        assert not hasattr(mgr.config, "not_a_real_setting")


class TestJarvisMemory:
    def test_remember_recall(self, tmp_path):
        mem = JarvisMemory(home=tmp_path)
        assert mem.remember("theme", "dark", category="preference")
        assert mem.recall("theme") == "dark"
        assert mem.recall("missing", default="x") == "x"

    def test_entries_and_categories(self, tmp_path):
        mem = JarvisMemory(home=tmp_path)
        mem.remember("a", 1, category="facts")
        mem.remember("b", 2, category="facts")
        mem.remember("c", 3, category="prefs")
        assert len(mem.category("facts")) == 2
        assert set(mem.keys()) == {"a", "b", "c"}
        assert len(mem.all()) == 3

    def test_forget(self, tmp_path):
        mem = JarvisMemory(home=tmp_path)
        mem.remember("k", "v")
        assert mem.forget("k") is True
        assert mem.forget("k") is False
        assert mem.recall("k") is None

    def test_persistence_across_instances(self, tmp_path):
        mem = JarvisMemory(home=tmp_path)
        mem.remember("name", "Ada", category="profile")
        fresh = JarvisMemory(home=tmp_path)
        assert fresh.recall("name") == "Ada"

    def test_recall_entry_returns_metadata(self, tmp_path):
        mem = JarvisMemory(home=tmp_path)
        mem.remember("k", "v", category="facts", source="test")
        entry = mem.recall_entry("k")
        assert entry["value"] == "v"
        assert entry["category"] == "facts"
        assert entry["source"] == "test"
        assert mem.recall_entry("none") is None


class TestVoicePersonalization:
    def test_default_profile_exists(self, tmp_path):
        vp = VoicePersonalization(home=tmp_path)
        assert vp.get("default") is not None
        assert vp.active.name == "default"

    def test_create_and_activate(self, tmp_path):
        vp = VoicePersonalization(home=tmp_path)
        vp.create("bright", voice="nova", speed=1.2, language="fr")
        assert vp.get("bright").speed == 1.2
        assert vp.set_active("bright") is True
        assert vp.active.name == "bright"

    def test_update(self, tmp_path):
        vp = VoicePersonalization(home=tmp_path)
        vp.create("calm")
        vp.update("calm", pitch=0.9)
        assert vp.get("calm").pitch == 0.9
        assert vp.update("nope", pitch=1.0) is None

    def test_delete_protects_default(self, tmp_path):
        vp = VoicePersonalization(home=tmp_path)
        assert vp.delete("default") is False
        vp.create("temp")
        assert vp.delete("temp") is True

    def test_persistence(self, tmp_path):
        vp = VoicePersonalization(home=tmp_path)
        vp.create("bright", voice="nova")
        vp.set_active("bright")
        fresh = VoicePersonalization(home=tmp_path)
        assert fresh.active.name == "bright"
        assert fresh.get("bright").voice == "nova"

    def test_apply_to_target(self, tmp_path):
        class Target:
            voice = ""
            speed = 1.0
            pitch = 1.0
            language = "en"
            emotion = "professional"

        target = Target()
        vp = VoicePersonalization(home=tmp_path)
        vp.create("bright", voice="nova", speed=1.2)
        vp.set_active("bright")
        applied = vp.apply_to(target)
        assert applied["voice"] == "nova"
        assert target.voice == "nova"
        assert target.speed == 1.2


class TestAccessibilityManager:
    def test_defaults(self, tmp_path):
        a = AccessibilityManager(home=tmp_path)
        assert a.keyboard_shortcuts is True
        assert a.captions is False

    def test_set_toggles(self, tmp_path):
        a = AccessibilityManager(home=tmp_path)
        a.set(captions=True, high_contrast=True, reduced_motion=True)
        assert a.captions is True
        assert a.high_contrast is True
        assert a.reduced_motion is True

    def test_persistence(self, tmp_path):
        a = AccessibilityManager(home=tmp_path)
        a.set(captions=True, screen_reader=True)
        fresh = AccessibilityManager(home=tmp_path)
        assert fresh.captions is True
        assert fresh.screen_reader is True

    def test_shortcuts(self, tmp_path):
        a = AccessibilityManager(home=tmp_path)
        assert a.shortcut("push_to_talk") == "Ctrl+Alt+V"
        assert a.shortcut("unknown") == ""

    def test_describe(self, tmp_path):
        a = AccessibilityManager(home=tmp_path)
        a.set(captions=True)
        assert "Captions: on" in a.describe()

    def test_snapshot(self, tmp_path):
        a = AccessibilityManager(home=tmp_path)
        snap = a.snapshot()
        assert snap["keyboard_shortcuts"] is True
        assert "shortcuts" in snap
