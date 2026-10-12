"""Tests for the Jarvis wake word engine (aetheros_jarvis.wake_word)."""

import struct


from aetheros_jarvis.models import WakeWordSource
from aetheros_jarvis.wake_word import WakeWordEngine


def _pcm(amplitude: int, samples: int) -> bytes:
    return struct.pack(f"<{samples}h", *([amplitude] * samples))


def _silence(samples: int) -> bytes:
    return _pcm(0, samples)


class TestWakeWordConfig:
    def test_default_phrases_normalized(self):
        engine = WakeWordEngine()
        assert engine.phrases == ["aether", "jarvis"]

    def test_set_phrases(self):
        engine = WakeWordEngine()
        engine.set_phrases(["computer", "HELLO  "])
        assert engine.phrases == ["computer", "hello"]

    def test_enabled_toggle(self):
        engine = WakeWordEngine()
        assert engine.enabled
        engine.set_enabled(False)
        assert not engine.enabled

    def test_snapshot(self):
        engine = WakeWordEngine(phrases=["jarvis"])
        snap = engine.snapshot()
        assert snap["phrases"] == ["jarvis"]
        assert snap["enabled"] is True
        assert "available" in snap
        assert "listeners" in snap


class TestWakeWordDetection:
    def test_disabled_engine_never_detects(self):
        engine = WakeWordEngine(enabled=False)
        event = engine.process_frame(_pcm(8000, 32000))
        assert event is None

    def test_silence_is_not_a_wake_event(self):
        engine = WakeWordEngine()
        event = engine.process_frame(_silence(32000))
        assert event is None

    def test_brief_noise_is_not_a_wake_event(self):
        engine = WakeWordEngine()
        event = engine.process_frame(_pcm(8000, 320))  # 20 ms only
        assert event is None

    def test_sustained_speech_trips_detector(self):
        engine = WakeWordEngine()
        event = engine.process_frame(_pcm(8000, 32000))  # ~1 s of speech
        assert event is not None
        assert event.trigger == "wake_phrase"
        assert event.source == WakeWordSource.VOICE

    def test_push_to_talk_always_emits(self):
        engine = WakeWordEngine()
        received = []
        engine.on_wake(lambda e: received.append(e))
        event = engine.push_to_talk(phrase="user")
        assert event.source == WakeWordSource.PUSH_TO_TALK
        assert event.verified is True
        assert event.confidence == 1.0
        assert len(received) == 1
        assert received[0].phrase == "user"

    def test_listener_notified_on_wake(self):
        engine = WakeWordEngine()
        received = []
        engine.on_wake(received.append)
        engine.push_to_talk()
        assert len(received) == 1
