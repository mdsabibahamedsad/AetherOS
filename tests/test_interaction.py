"""
Tests for the AetherOS Interaction Layer (Phase 9).

Covers: interaction manager, session continuity, desktop integration,
voice pipeline, presence awareness, history, preferences, and UI events.
"""

import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kernel.event_bus import EventBus

# ============================================================================
# Interaction Manager
# ============================================================================

class TestInteractionManager:
    """Test the InteractionManager lifecycle and APIs."""

    def test_initialization(self):
        """Test manager initializes correctly."""
        from interaction.interaction_manager import (
            InteractionManager, InteractionConfig, InteractionState,
        )
        mgr = InteractionManager()
        assert mgr.state == InteractionState.STOPPED

        mgr.initialize()
        assert mgr.state == InteractionState.READY

    def test_initialization_with_event_bus(self):
        """Test initialization emits events."""
        from interaction.interaction_manager import (
            InteractionManager, InteractionConfig, InteractionEvent,
        )
        events = []
        bus = EventBus()
        bus.subscribe(InteractionEvent.INTERACTION_STARTED.value,
                      lambda e: events.append(e))

        mgr = InteractionManager(event_bus=bus)
        mgr.initialize()
        mgr.shutdown()

        assert len(events) == 1
        assert events[0].topic == InteractionEvent.INTERACTION_STARTED.value

    def test_config_propagation(self):
        """Test config is propagated correctly."""
        from interaction.interaction_manager import (
            InteractionManager, InteractionConfig,
        )
        config = InteractionConfig(
            enable_voice=False,
            enable_desktop=False,
            enable_notifications=True,
            permissions_required=False,
        )
        mgr = InteractionManager(config=config)
        assert mgr.config.enable_voice is False
        assert mgr.config.enable_desktop is False
        assert mgr.config.enable_notifications is True
        assert mgr.config.permissions_required is False

    def test_voice_session_lifecycle(self):
        """Test voice session start/stop."""
        from interaction.interaction_manager import (
            InteractionManager, InteractionConfig,
        )
        mgr = InteractionManager()
        mgr.initialize()

        # Voice is disabled by default if no explicit config
        mgr.config.enable_voice = True
        mgr._permissions["microphone"] = True

        result = mgr.start_voice_session()
        assert result.success is True
        assert "session_id" in result.data

        session_id = result.data["session_id"]
        stop_result = mgr.stop_voice_session(session_id)
        assert stop_result.success is True

    def test_voice_session_microphone_permission(self):
        """Test voice session requires microphone permission."""
        from interaction.interaction_manager import (
            InteractionManager, InteractionConfig,
        )
        mgr = InteractionManager(config=InteractionConfig(permissions_required=True))
        mgr.initialize()
        mgr.config.enable_voice = True

        result = mgr.start_voice_session()
        assert result.success is False

    def test_permission_management(self):
        """Test permission grant/deny/check."""
        from interaction.interaction_manager import InteractionManager
        mgr = InteractionManager()
        mgr.initialize()

        assert mgr.has_permission("microphone") is False
        assert mgr.has_permission("clipboard") is False

        mgr.grant_permission("microphone")
        assert mgr.has_permission("microphone") is True
        assert mgr.has_permission("clipboard") is False

        mgr.deny_permission("microphone")
        assert mgr.has_permission("microphone") is False

    def test_workspace_context(self):
        """Test workspace context capture and update."""
        from interaction.interaction_manager import InteractionManager
        mgr = InteractionManager()
        mgr.initialize()
        mgr.config.enable_desktop = True
        mgr._permissions["workspace_metadata"] = True

        mgr.update_workspace_context({
            "project": "test-project",
            "files": ["main.py"],
        })

        ctx = mgr.capture_context()
        assert ctx is not None
        assert ctx["workspace"]["project"] == "test-project"

    def test_notification(self):
        """Test notification delivery."""
        from interaction.interaction_manager import InteractionManager
        from interaction.desktop.notifications import Notification, NotificationPriority

        mgr = InteractionManager()
        mgr.initialize()
        mgr.config.enable_notifications = True
        mgr._permissions["notifications"] = True

        notification = Notification(
            title="Test Notification",
            message="This is a test",
            priority=NotificationPriority.NORMAL,
        )

        result = mgr.notify(notification)
        assert result.success is True

    def test_shutdown(self):
        """Test shutdown transitions to STOPPED."""
        from interaction.interaction_manager import (
            InteractionManager, InteractionState,
        )
        mgr = InteractionManager()
        mgr.initialize()
        mgr.shutdown()
        assert mgr.state == InteractionState.SHUTDOWN

    def test_status(self):
        """Test status reporting."""
        from interaction.interaction_manager import InteractionManager
        mgr = InteractionManager()
        mgr.initialize()
        status = mgr.status()
        assert "state" in status
        assert "voice" in status
        assert "desktop" in status
        assert "notifications" in status

    def test_health(self):
        """Test health reporting."""
        from interaction.interaction_manager import InteractionManager
        mgr = InteractionManager()
        mgr.initialize()
        health = mgr.health()
        assert health["ready"] is True
        assert health["state"] == "ready"

    def test_plugin_adapter_registration(self):
        """Test adapter registration lifecycle."""
        from interaction.interaction_manager import InteractionManager
        mgr = InteractionManager()
        mgr.initialize()

        def my_adapter(*args):
            return True

        mgr.register_voice_adapter("test_voice", my_adapter)
        mgr.register_desktop_adapter("test_desktop", my_adapter)
        mgr.register_notification_adapter("test_notif", my_adapter)

        status = mgr.status()
        assert "test_voice" in status["voice"]["adapters"]
        assert "test_desktop" in status["desktop"]["adapters"]
        assert "test_notif" in status["notifications"]["adapters"]

        assert mgr.unregister_voice_adapter("test_voice") is True
        assert mgr.unregister_desktop_adapter("test_desktop") is True
        assert mgr.unregister_notification_adapter("test_notif") is True

    def test_history_recording(self):
        """Test interaction history tracking."""
        from interaction.interaction_manager import InteractionManager
        mgr = InteractionManager()
        mgr.initialize()
        mgr.config.enable_voice = True
        mgr._permissions["microphone"] = True

        mgr.start_voice_session()
        history = mgr.get_history()
        assert len(history) >= 1
        assert history[-1]["event_type"] == "voice_session_started"


# ============================================================================
# Session Manager
# ============================================================================

class TestSessionManager:
    """Test session continuity and management."""

    def test_create_and_get_session(self):
        """Test session creation and retrieval."""
        from interaction.session_manager import SessionManager
        sm = SessionManager()
        sm.initialize()

        session = sm.create_session(user_id="user-1", device_id="device-1", platform="desktop")
        assert session.session_id is not None
        assert session.status == "active"

        retrieved = sm.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.user_id == "user-1"

    def test_update_session(self):
        """Test session updates."""
        from interaction.session_manager import SessionManager
        sm = SessionManager()
        sm.initialize()

        session = sm.create_session()
        updated = sm.update_session(session.session_id, platform="mobile")
        assert updated is not None
        assert updated.platform == "mobile"

    def test_end_session(self):
        """Test session ending."""
        from interaction.session_manager import SessionManager
        sm = SessionManager()
        sm.initialize()

        session = sm.create_session()
        ended = sm.end_session(session.session_id)
        assert ended is not None
        assert ended.status == "ended"

    def test_active_sessions(self):
        """Test listing active sessions."""
        from interaction.session_manager import SessionManager
        sm = SessionManager()
        sm.initialize()

        s1 = sm.create_session()
        s2 = sm.create_session()
        assert len(sm.list_active_sessions()) == 2

        sm.end_session(s1.session_id)
        assert len(sm.list_active_sessions()) == 1

    def test_snapshot_lifecycle(self):
        """Test snapshot creation and retrieval."""
        from interaction.session_manager import SessionManager
        sm = SessionManager()
        sm.initialize()

        session = sm.create_session()
        snapshot = sm.create_snapshot(
            session.session_id,
            workflow_state={"step": "testing"},
            active_tasks=[{"id": "task-1"}],
            open_files=["test.py"],
        )
        assert snapshot is not None
        assert snapshot.workflow_state["step"] == "testing"

        retrieved = sm.get_snapshot(snapshot.snapshot_id)
        assert retrieved is not None

        snapshots = sm.list_snapshots(session.session_id)
        assert len(snapshots) == 1

    def test_snapshot_unknown_session(self):
        """Test snapshot with unknown session returns None."""
        from interaction.session_manager import SessionManager
        sm = SessionManager()
        sm.initialize()
        snapshot = sm.create_snapshot("nonexistent")
        assert snapshot is None

    def test_continuity_lifecycle(self):
        """Test continuity creation and finding."""
        from interaction.session_manager import SessionManager
        sm = SessionManager()
        sm.initialize()

        session = sm.create_session(user_id="user-1")
        continuity = sm.create_continuity(
            original_session_id=session.session_id,
            user_id="user-1",
        )
        assert continuity is not None

        found = sm.find_continuities_for_user("user-1")
        assert len(found) == 1
        assert found[0].original_session_id == session.session_id

    def test_resume_session(self):
        """Test session resume from snapshot."""
        from interaction.session_manager import SessionManager
        sm = SessionManager()
        sm.initialize()

        session = sm.create_session()
        snapshot = sm.create_snapshot(
            session.session_id,
            workflow_state={"step": "halfway"},
            active_tasks=[{"id": "task-1"}],
        )

        resume_ctx = sm.resume_session(
            snapshot.snapshot_id,
            new_device_id="device-2",
            new_platform="mobile",
        )
        assert resume_ctx is not None
        assert resume_ctx.previous_session_id == session.session_id
        assert resume_ctx.workflow_state["step"] == "halfway"
        assert len(resume_ctx.active_tasks) == 1

    def test_resume_nonexistent_snapshot(self):
        """Test resume with unknown snapshot returns None."""
        from interaction.session_manager import SessionManager
        sm = SessionManager()
        sm.initialize()
        ctx = sm.resume_session("nonexistent")
        assert ctx is None

    def test_delete_snapshot(self):
        """Test snapshot deletion."""
        from interaction.session_manager import SessionManager
        sm = SessionManager()
        sm.initialize()

        session = sm.create_session()
        snapshot = sm.create_snapshot(session.session_id)
        assert sm.delete_snapshot(snapshot.snapshot_id) is True
        assert sm.delete_snapshot("nonexistent") is False

    def test_persistence(self):
        """Test session state persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from interaction.session_manager import SessionManager
            sm = SessionManager(storage_dir=tmpdir)
            sm.initialize()

            session = sm.create_session(user_id="user-1")
            sm.create_snapshot(session.session_id, workflow_state={"step": "test"})

            # Shutdown first instance to persist state
            sm.shutdown()

            # Create new instance and verify data was persisted
            sm2 = SessionManager(storage_dir=tmpdir)
            sm2.initialize()

            assert len(sm2.list_active_sessions()) == 1
            snapshots = sm2.list_snapshots(session.session_id)
            assert len(snapshots) == 1

    def test_get_stats(self):
        """Test stats reporting."""
        from interaction.session_manager import SessionManager
        sm = SessionManager()
        sm.initialize()

        for _ in range(3):
            sm.create_session()

        stats = sm.get_stats()
        assert stats["total_sessions"] == 3


# ============================================================================
# Desktop Integration
# ============================================================================

class TestDesktopManager:
    """Test desktop integration features."""

    def test_initialization(self):
        """Test desktop manager init."""
        from interaction.desktop.desktop_manager import (
            DesktopManager, DesktopConfig,
        )
        dm = DesktopManager()
        dm.initialize()
        stats = dm.get_stats()
        assert stats["initialized"] is True

    def test_permission_check(self):
        """Test desktop permission management."""
        from interaction.desktop.desktop_manager import (
            DesktopManager, DesktopPermission,
        )
        dm = DesktopManager()
        dm.initialize()

        assert dm.check_permission(DesktopPermission.WINDOW_ACCESS) is False
        dm.grant_permission(DesktopPermission.WINDOW_ACCESS)
        assert dm.check_permission(DesktopPermission.WINDOW_ACCESS) is True
        dm.revoke_permission(DesktopPermission.WINDOW_ACCESS)
        assert dm.check_permission(DesktopPermission.WINDOW_ACCESS) is False

    def test_workspace_context(self):
        """Test workspace context detection."""
        from interaction.desktop.desktop_manager import (
            DesktopManager, DesktopPermission,
        )
        dm = DesktopManager()
        dm.initialize()
        dm.grant_permission(DesktopPermission.WORKSPACE_CONTEXT)

        # Without window adapter, context should be None
        ctx = dm.get_workspace_context()
        assert ctx is None or "detected_at" in ctx


class TestWindowTracker:
    """Test window tracking."""

    def test_initialization(self):
        """Test window tracker init."""
        from interaction.desktop.window_tracker import WindowTracker
        wt = WindowTracker()
        wt.initialize()

    def test_get_active_window(self):
        """Test getting active window with adapter."""
        from interaction.desktop.window_tracker import WindowTracker, WindowInfo
        wt = WindowTracker()

        def adapter():
            return WindowInfo(
                window_id="123",
                title="Test Window",
                process_name="test_app",
                is_focused=True,
            )

        wt.set_platform_adapter(adapter)
        window = wt.get_active_window()
        assert window is not None
        assert window.title == "Test Window"
        assert window.process_name == "test_app"

    def test_subscribe(self):
        """Test subscription lifecycle."""
        from interaction.desktop.window_tracker import WindowTracker
        wt = WindowTracker()
        received = []

        def callback(event, info):
            received.append((event, info))

        unsub = wt.subscribe(callback)
        assert callable(unsub)

    def test_window_history(self):
        """Test window history."""
        from interaction.desktop.window_tracker import WindowTracker
        wt = WindowTracker()
        history = wt.get_window_history()
        assert isinstance(history, list)


class TestWorkspaceMonitor:
    """Test workspace monitoring."""

    def test_initialization(self):
        """Test workspace monitor init."""
        from interaction.desktop.workspace_monitor import WorkspaceMonitor
        wm = WorkspaceMonitor()
        wm.initialize()

    def test_detect_from_current_dir(self):
        """Test workspace detection from current directory."""
        from interaction.desktop.workspace_monitor import WorkspaceMonitor
        info = WorkspaceMonitor._detect_from_current_dir()
        assert info is not None
        assert info.name is not None

    def test_subscribe(self):
        """Test subscription lifecycle."""
        from interaction.desktop.workspace_monitor import WorkspaceMonitor
        wm = WorkspaceMonitor()
        received = []

        def callback(change):
            received.append(change)

        unsub = wm.subscribe(callback)
        assert callable(unsub)

    def test_register_detector(self):
        """Test custom detector registration."""
        from interaction.desktop.workspace_monitor import WorkspaceMonitor, WorkspaceInfo
        wm = WorkspaceMonitor()
        wm.initialize()

        def my_detector():
            return WorkspaceInfo(path="/test", name="test-project", type="custom")

        wm.register_detector(my_detector)
        info = wm.detect_workspace()
        assert info is not None
        assert info.name == "test-project"


class TestClipboardMonitor:
    """Test clipboard monitoring."""

    def test_initialization(self):
        """Test clipboard monitor init."""
        from interaction.desktop.clipboard import (
            ClipboardMonitor, ClipboardPermission,
        )
        cm = ClipboardMonitor()
        assert cm.permission == ClipboardPermission.DENIED
        cm.initialize()

    def test_permission_default(self):
        """Test default permission is DENIED."""
        from interaction.desktop.clipboard import (
            ClipboardMonitor, ClipboardPermission,
        )
        cm = ClipboardMonitor()
        assert cm.permission == ClipboardPermission.DENIED

    def test_permission_change(self):
        """Test changing permission level."""
        from interaction.desktop.clipboard import (
            ClipboardMonitor, ClipboardPermission,
        )
        cm = ClipboardMonitor()
        cm.set_permission(ClipboardPermission.TEXT_ONLY)
        assert cm.permission == ClipboardPermission.TEXT_ONLY

    def test_get_latest_no_permission(self):
        """Test get_latest returns None with DENIED."""
        from interaction.desktop.clipboard import ClipboardMonitor
        cm = ClipboardMonitor()
        assert cm.get_latest() is None

    def test_get_text_no_permission(self):
        """Test get_text returns None with DENIED."""
        from interaction.desktop.clipboard import ClipboardMonitor
        cm = ClipboardMonitor()
        assert cm.get_text() is None


class TestNotificationManager:
    """Test notification delivery."""

    def test_initialization(self):
        """Test notification manager init."""
        from interaction.desktop.notifications import NotificationManager
        nm = NotificationManager()
        nm.initialize()
        stats = nm.get_stats()
        assert "in_memory" in stats["channels"]

    def test_send_notification(self):
        """Test sending a notification."""
        from interaction.desktop.notifications import (
            NotificationManager, Notification, NotificationPriority,
        )
        nm = NotificationManager()
        nm.initialize()

        notification = Notification(
            title="Test",
            message="Test message",
            priority=NotificationPriority.NORMAL,
        )
        result = nm.send(notification)
        assert result is True

    def test_send_notification_helper(self):
        """Test convenience helper."""
        from interaction.desktop.notifications import (
            NotificationManager, NotificationPriority,
        )
        nm = NotificationManager()
        nm.initialize()

        n = nm.send_notification(
            title="Test",
            message="Test message",
            priority=NotificationPriority.HIGH,
            category="test",
        )
        assert n.title == "Test"

    def test_channel_management(self):
        """Test channel CRUD."""
        from interaction.desktop.notifications import (
            NotificationManager, NotificationChannel, NotificationPriority,
        )
        nm = NotificationManager()
        nm.initialize()

        nm.add_channel(NotificationChannel(
            name="test_channel",
            priority_threshold=NotificationPriority.LOW,
        ))
        stats = nm.get_stats()
        assert "test_channel" in stats["channels"]

        nm.remove_channel("test_channel")
        stats = nm.get_stats()
        assert "test_channel" not in stats["channels"]

    def test_action_handling(self):
        """Test notification action handling."""
        from interaction.desktop.notifications import (
            NotificationManager, Notification, NotificationAction,
            NotificationPriority,
        )
        nm = NotificationManager()
        nm.initialize()

        n = Notification(
            title="Actionable",
            message="Take action",
            actions=[NotificationAction.APPROVE, NotificationAction.DENY],
        )
        nm.send(n)
        assert nm.handle_action(n.id, NotificationAction.APPROVE) is True

    def test_history_filter(self):
        """Test notification history filtering."""
        from interaction.desktop.notifications import (
            NotificationManager, Notification, NotificationPriority,
        )
        nm = NotificationManager()
        nm.initialize()

        nm.send_notification(title="A", message="Aa", category="test")
        nm.send_notification(title="B", message="Bb", category="other")

        history = nm.get_history(category="test")
        assert len(history) == 1

    def test_delivery_adapter(self):
        """Test custom delivery adapter."""
        from interaction.desktop.notifications import (
            NotificationManager, Notification,
        )
        nm = NotificationManager()
        nm.initialize()
        delivered = []

        def my_adapter(n):
            delivered.append(n)
            return True

        nm.register_delivery_adapter("test_channel", my_adapter)
        nm.add_channel(__import__('interaction.desktop.notifications',
                                   fromlist=['NotificationChannel']).NotificationChannel(
            name="test_channel",
        ))

        nm.send(Notification(title="Test", message="Hello"))
        assert len(delivered) == 1


class TestShortcutManager:
    """Test shortcut management."""

    def test_initialization(self):
        """Test shortcut manager init."""
        from interaction.desktop.shortcuts import ShortcutManager
        sm = ShortcutManager()
        sm.initialize()

    def test_register_and_trigger(self):
        """Test shortcut registration and triggering."""
        from interaction.desktop.shortcuts import (
            ShortcutManager, GlobalShortcut, ShortcutAction,
        )
        sm = ShortcutManager()
        sm.initialize()

        triggered = []

        def my_action():
            triggered.append(True)

        shortcut = GlobalShortcut(
            name="Test Shortcut",
            keys="Ctrl+Shift+T",
            action=ShortcutAction.CUSTOM,
            action_fn=my_action,
        )
        assert sm.register(shortcut) is True

        sm.trigger(shortcut.id)
        assert len(triggered) == 1

    def test_find_by_keys(self):
        """Test finding shortcuts by key combination."""
        from interaction.desktop.shortcuts import (
            ShortcutManager, GlobalShortcut, ShortcutAction,
        )
        sm = ShortcutManager()
        sm.initialize()

        sm.register(GlobalShortcut(
            name="Test", keys="Ctrl+Shift+X", action=ShortcutAction.CUSTOM,
        ))
        found = sm.find_by_keys("Ctrl+Shift+X")
        assert found is not None
        assert found.name == "Test"

    def test_enable_disable(self):
        """Test enabling and disabling shortcuts."""
        from interaction.desktop.shortcuts import (
            ShortcutManager, GlobalShortcut, ShortcutAction,
        )
        sm = ShortcutManager()
        sm.initialize()

        shortcut = GlobalShortcut(
            name="Test", keys="Ctrl+Shift+Z", action=ShortcutAction.CUSTOM,
        )
        sm.register(shortcut)

        assert sm.disable(shortcut.id) is True
        s = sm.get_shortcut(shortcut.id)
        assert s.enabled is False

        assert sm.enable(shortcut.id) is True
        s = sm.get_shortcut(shortcut.id)
        assert s.enabled is True


# ============================================================================
# Voice Pipeline
# ============================================================================

class TestVoiceManager:
    """Test voice session management."""

    def test_initialization(self):
        """Test voice manager init."""
        from interaction.voice.voice_manager import VoiceManager
        vm = VoiceManager()
        vm.initialize()

    def test_session_lifecycle(self):
        """Test voice session lifecycle."""
        from interaction.voice.voice_manager import (
            VoiceManager, VoiceSessionType,
        )
        vm = VoiceManager()
        vm.initialize()

        session = vm.start_session(VoiceSessionType.PUSH_TO_TALK)
        assert session.id is not None
        assert vm.get_session(session.id) is not None

        assert vm.end_session(session.id) is True
        assert vm.get_session(session.id) is None

    def test_listening_control(self):
        """Test listening start/stop."""
        from interaction.voice.voice_manager import (
            VoiceManager, VoiceSessionType,
        )
        vm = VoiceManager()
        vm.initialize()

        session = vm.start_session()
        assert vm.start_listening(session.id) is True
        assert vm.stop_listening(session.id) is True

    def test_transcription_notification(self):
        """Test transcription notification."""
        from interaction.voice.voice_manager import (
            VoiceManager, VoiceSessionType,
        )
        vm = VoiceManager()
        vm.initialize()

        session = vm.start_session()
        vm.notify_transcription(session.id, "hello world", is_final=True)
        updated = vm.get_session(session.id)
        assert updated.transcribed_text == "hello world"

    def test_plugin_registration(self):
        """Test plugin provider registration."""
        from interaction.voice.voice_manager import VoiceManager
        vm = VoiceManager()

        vm.register_speech_input("test_stt", lambda: None)
        vm.register_speech_output("test_tts", lambda: None)
        vm.register_wake_word("test_ww", lambda: None)
        vm.register_transcription("test_trans", lambda: None)

        stats = vm.get_stats()
        assert "test_stt" in stats["adapters"]["speech_input"]

    def test_subscriber_lifecycle(self):
        """Test subscription lifecycle."""
        from interaction.voice.voice_manager import VoiceManager, VoiceEvent
        vm = VoiceManager()
        received = []

        def cb(data):
            received.append(data)

        unsub = vm.subscribe(VoiceEvent.SESSION_STARTED, cb)
        assert callable(unsub)
        unsub()


class TestSpeechInput:
    """Test speech input adapter management."""

    def test_adapter_registration(self):
        """Test adapter registration and dispatch."""
        from interaction.voice.speech_input import (
            SpeechInputManager, SpeechInputAdapter, SpeechInputResult,
        )
        mgr = SpeechInputManager()

        class TestAdapter(SpeechInputAdapter):
            def transcribe(self, audio_path, **kwargs):
                return SpeechInputResult(
                    success=True,
                    text="transcribed text",
                    provider=self.name,
                )

        mgr.register_adapter("test", TestAdapter())
        result = mgr.transcribe("/test/audio.wav")
        assert result.success is True
        assert result.text == "transcribed text"

    def test_default_adapter(self):
        """Test default adapter selection."""
        from interaction.voice.speech_input import (
            SpeechInputManager, SpeechInputAdapter,
        )
        mgr = SpeechInputManager()
        a1 = SpeechInputAdapter(name="a1")
        a2 = SpeechInputAdapter(name="a2")
        mgr.register_adapter("a1", a1)
        mgr.register_adapter("a2", a2)

        assert mgr.set_default_adapter("a2") is True

    def test_no_adapter_error(self):
        """Test error when no adapter available."""
        from interaction.voice.speech_input import SpeechInputManager
        mgr = SpeechInputManager()
        result = mgr.transcribe("/test.wav")
        assert result.success is False

    def test_adapter_availability(self):
        """Test listing adapter availability."""
        from interaction.voice.speech_input import (
            SpeechInputManager, SpeechInputAdapter,
        )
        mgr = SpeechInputManager()
        mgr.register_adapter("test", SpeechInputAdapter())
        adapters = mgr.list_adapters()
        assert "test" in adapters


class TestSpeechOutput:
    """Test speech output adapter management."""

    def test_synthesize(self):
        """Test speech synthesis through adapter."""
        from interaction.voice.speech_output import (
            SpeechOutputManager, SpeechOutputAdapter, SpeechOutputResult,
        )
        mgr = SpeechOutputManager()

        class TestAdapter(SpeechOutputAdapter):
            def synthesize(self, text, **kwargs):
                return SpeechOutputResult(
                    success=True,
                    audio_path="/tmp/test.mp3",
                    text=text,
                    provider=self.name,
                )

        mgr.register_adapter("test", TestAdapter())
        result = mgr.synthesize("Hello world")
        assert result.success is True


class TestWakeWord:
    """Test wake word engine."""

    def test_load_cycle(self):
        """Test wake word engine load/unload cycle."""
        from interaction.voice.wake_word import WakeWordEngine, WakeWordConfig
        engine = WakeWordEngine(WakeWordConfig(wake_word="aetheros"))
        assert engine.load() is True
        engine.unload()

    def test_listening_lifecycle(self):
        """Test listening start/stop."""
        from interaction.voice.wake_word import (
            WakeWordEngine, WakeWordConfig,
        )
        engine = WakeWordEngine(WakeWordConfig())
        engine.load()
        assert engine.start_listening() is True
        engine.stop_listening()

    def test_detection_adapter(self):
        """Test detection adapter integration."""
        from interaction.voice.wake_word import (
            WakeWordEngine, WakeWordConfig, WakeWordEvent,
        )
        engine = WakeWordEngine(WakeWordConfig(wake_word="testword"))
        engine.load()

        detected = []

        def cb(event, data):
            detected.append((event, data))

        engine.subscribe(cb)
        engine.set_detection_adapter(lambda: True)
        engine.detect()

        assert len(detected) >= 1

    def test_cooldown(self):
        """Test detection cooldown."""
        from interaction.voice.wake_word import (
            WakeWordEngine, WakeWordConfig, WakeWordEvent,
        )
        engine = WakeWordEngine(WakeWordConfig(wake_word="test", cooldown_seconds=10.0))
        engine.load()

        count = []
        def cb(event, data):
            count.append(1)

        engine.subscribe(cb)
        engine.set_detection_adapter(lambda: True)
        engine.detect()
        engine.detect()  # Should be blocked by cooldown
        assert len(count) == 1


class TestAudioPipeline:
    """Test audio pipeline."""

    def test_initialization(self):
        """Test pipeline init."""
        from interaction.voice.audio_pipeline import (
            AudioPipeline, AudioConfig,
        )
        pipeline = AudioPipeline(AudioConfig(sample_rate=16000))
        assert pipeline.config.sample_rate == 16000

    def test_capture_lifecycle(self):
        """Test capture start/stop/cancel."""
        from interaction.voice.audio_pipeline import AudioPipeline
        pipeline = AudioPipeline()
        assert pipeline.start_capture() is True
        assert pipeline.is_capturing is True
        pipeline.cancel_capture()
        assert pipeline.is_capturing is False

    def test_capture_elapsed(self):
        """Test capture timing."""
        from interaction.voice.audio_pipeline import AudioPipeline
        pipeline = AudioPipeline()
        pipeline.start_capture()
        time.sleep(0.01)
        elapsed = pipeline.capture_elapsed
        assert elapsed > 0
        pipeline.cancel_capture()


class TestTranscriptionEngine:
    """Test transcription engine."""

    def test_initialization(self):
        """Test transcription engine init."""
        from interaction.voice.transcription import (
            TranscriptionEngine, TranscriptionConfig,
        )
        engine = TranscriptionEngine(TranscriptionConfig(provider="local"))
        assert engine.config.provider == "local"

    def test_get_config(self):
        """Test config retrieval."""
        from interaction.voice.transcription import (
            TranscriptionEngine, TranscriptionConfig,
        )
        engine = TranscriptionEngine(TranscriptionConfig(provider="test"))
        config = engine.get_config()
        assert config["provider"] == "test"
        assert config["enabled"] is True


# ============================================================================
# Presence Awareness
# ============================================================================

class TestActivityDetector:
    """Test activity detection."""

    def test_initialization(self):
        """Test activity detector init."""
        from interaction.presence.activity_detector import ActivityDetector
        ad = ActivityDetector()
        ad.start_monitoring()
        assert ad.get_current_activity() is not None
        ad.stop_monitoring()

    def test_input_adapter(self):
        """Test input activity adapter."""
        from interaction.presence.activity_detector import ActivityDetector
        ad = ActivityDetector()
        ad.set_input_adapter(lambda: 0.8)
        ad.start_monitoring()
        time.sleep(0.1)
        activity = ad.get_current_activity()
        ad.stop_monitoring()

    def test_subscribe(self):
        """Test subscription lifecycle."""
        from interaction.presence.activity_detector import ActivityDetector
        ad = ActivityDetector()
        received = []

        def cb(event, data):
            received.append((event, data))

        unsub = ad.subscribe(cb)
        assert callable(unsub)


class TestIdleMonitor:
    """Test idle monitoring."""

    def test_default_state(self):
        """Test default state is ACTIVE."""
        from interaction.presence.idle_monitor import IdleMonitor, IdleState
        im = IdleMonitor()
        assert im.state == IdleState.ACTIVE

    def test_active_check(self):
        """Test is_idle returns False when active."""
        from interaction.presence.idle_monitor import IdleMonitor
        im = IdleMonitor()
        assert im.is_idle() is False

    def test_touch(self):
        """Test touch resets idle timer."""
        from interaction.presence.idle_monitor import IdleMonitor
        im = IdleMonitor()
        im.touch()
        assert im.idle_duration < 1.0

    def test_activity_adapter(self):
        """Test adapter integration."""
        from interaction.presence.idle_monitor import IdleMonitor
        im = IdleMonitor()
        im.set_activity_adapter(lambda: 0.0)
        im.start()
        time.sleep(0.1)
        im.stop()


class TestFocusMode:
    """Test focus mode."""

    def test_initialization(self):
        """Test focus mode init."""
        from interaction.presence.focus_mode import FocusMode, FocusConfig
        fm = FocusMode(FocusConfig(default_duration=25))
        fm.initialize()
        assert fm.enabled is True

    def test_focus_session_lifecycle(self):
        """Test focus session lifecycle."""
        from interaction.presence.focus_mode import FocusMode
        fm = FocusMode()
        fm.initialize()

        session = fm.start_focus(duration_minutes=25, task="Test task")
        assert session.id is not None
        assert fm.is_focusing is True

        assert fm.end_focus(session.id, completed=True) is True
        assert fm.is_focusing is False

    def test_pause_resume(self):
        """Test pause and resume."""
        from interaction.presence.focus_mode import FocusMode
        fm = FocusMode()
        fm.initialize()

        session = fm.start_focus(duration_minutes=60)
        assert fm.pause_focus() is True
        assert fm.resume_focus() is True
        fm.end_focus(session.id)

    def test_extend_focus(self):
        """Test extending focus session."""
        from interaction.presence.focus_mode import FocusMode, FocusConfig
        fm = FocusMode(FocusConfig(default_duration=25, max_duration=120))
        fm.initialize()

        session = fm.start_focus(duration_minutes=25)
        assert fm.extend_focus(10) is True
        fm.end_focus(session.id)

    def test_extend_beyond_max(self):
        """Test extending beyond max duration."""
        from interaction.presence.focus_mode import FocusMode, FocusConfig
        fm = FocusMode(FocusConfig(default_duration=25, max_duration=30))
        fm.initialize()

        session = fm.start_focus(duration_minutes=25)
        assert fm.extend_focus(10) is False  # Would exceed max 30
        fm.end_focus(session.id)


class TestContextDetector:
    """Test context detection."""

    def test_initialization(self):
        """Test context detector init."""
        from interaction.presence.context_detector import ContextDetector
        cd = ContextDetector()
        cd.initialize()

    def test_capture(self):
        """Test context capture."""
        from interaction.presence.context_detector import ContextDetector
        cd = ContextDetector()
        context = cd.capture()
        assert context.timestamp > 0

    def test_register_source(self):
        """Test custom context source."""
        from interaction.presence.context_detector import ContextDetector
        cd = ContextDetector()

        def my_source():
            return {"project_name": "my-project", "language": "python"}

        cd.register_source(my_source)
        context = cd.capture()
        assert context.project_name == "my-project"

    def test_get_last_context(self):
        """Test last context retrieval."""
        from interaction.presence.context_detector import ContextDetector
        cd = ContextDetector()
        assert cd.get_last_context() is None

    def test_history(self):
        """Test context history."""
        from interaction.presence.context_detector import ContextDetector
        cd = ContextDetector()
        cd.capture()
        cd.capture()
        history = cd.get_history(limit=5)
        assert len(history) >= 1


# ============================================================================
# Interaction History
# ============================================================================

class TestInteractionHistory:
    """Test interaction history."""

    def test_initialization(self):
        """Test history init."""
        from interaction.interaction_history import InteractionHistory
        ih = InteractionHistory()
        ih.initialize()

    def test_record_and_query(self):
        """Test recording and querying entries."""
        from interaction.interaction_history import InteractionHistory
        ih = InteractionHistory()
        ih.initialize()

        ih.record("voice_command", "voice", summary="User said hello")
        ih.record("desktop_event", "desktop", summary="Window changed")

        results = ih.query()
        assert len(results) == 2

    def test_query_filter_by_event_type(self):
        """Test query filtering."""
        from interaction.interaction_history import (
            InteractionHistory, HistoryQuery,
        )
        ih = InteractionHistory()
        ih.initialize()

        ih.record("voice_command", "voice", summary="Hello")
        ih.record("desktop_event", "desktop", summary="Window change")

        query = HistoryQuery(event_type="voice_command")
        results = ih.query(query)
        assert len(results) == 1
        assert results[0].event_type == "voice_command"

    def test_query_filter_by_channel(self):
        """Test query filtering by channel."""
        from interaction.interaction_history import (
            InteractionHistory, HistoryQuery,
        )
        ih = InteractionHistory()
        ih.initialize()

        ih.record("cmd1", "voice", summary="Voice test")
        ih.record("cmd2", "desktop", summary="Desktop test")

        query = HistoryQuery(channel="voice")
        results = ih.query(query)
        assert len(results) == 1

    def test_query_text_search(self):
        """Test text search in summaries."""
        from interaction.interaction_history import (
            InteractionHistory, HistoryQuery,
        )
        ih = InteractionHistory()
        ih.initialize()

        ih.record("cmd", "voice", summary="Hello world")
        ih.record("cmd", "desktop", summary="Goodbye")

        query = HistoryQuery(text_search="Hello")
        results = ih.query(query)
        assert len(results) == 1

    def test_summarize(self):
        """Test summary generation."""
        from interaction.interaction_history import InteractionHistory
        ih = InteractionHistory()
        ih.initialize()

        ih.record("voice", "voice", summary="A")
        ih.record("desktop", "desktop", summary="B")
        ih.record("voice", "voice", summary="C")

        summary = ih.summarize()
        assert summary.total_entries == 3
        assert summary.event_counts["voice"] == 2
        assert summary.event_counts["desktop"] == 1

    def test_get_event_types(self):
        """Test distinct event types."""
        from interaction.interaction_history import InteractionHistory
        ih = InteractionHistory()
        ih.initialize()

        ih.record("type_a", "voice", summary="A")
        ih.record("type_b", "desktop", summary="B")
        types = ih.get_event_types()
        assert "type_a" in types
        assert "type_b" in types

    def test_record_many(self):
        """Test bulk recording."""
        from interaction.interaction_history import (
            InteractionHistory, HistoryEntry,
        )
        ih = InteractionHistory()
        ih.initialize()

        entries = [
            HistoryEntry(event_type="a", channel="voice", summary="A"),
            HistoryEntry(event_type="b", channel="desktop", summary="B"),
        ]
        ih.record_many(entries)
        assert len(ih.query()) == 2

    def test_clear(self):
        """Test clearing history."""
        from interaction.interaction_history import InteractionHistory
        ih = InteractionHistory()
        ih.initialize()

        ih.record("test", "test", summary="Test")
        ih.clear()
        assert len(ih.query()) == 0

    def test_persistence(self):
        """Test JSONL persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from interaction.interaction_history import InteractionHistory
            ih = InteractionHistory(storage_dir=tmpdir)
            ih.initialize()

            ih.record("voice", "voice", summary="Test record")
            ih.record("desktop", "desktop", summary="Test desktop")

            # Verify the file was written
            path = Path(tmpdir) / "interaction_history.jsonl"
            assert path.exists()
            lines = path.read_text(encoding="utf-8").strip().split("\n")
            assert len(lines) == 2

            # Create new instance and verify data was loaded
            ih2 = InteractionHistory(storage_dir=tmpdir)
            ih2.initialize()
            assert len(ih2.query()) == 2


# ============================================================================
# UI Events
# ============================================================================

class TestUIEvents:
    """Test UI event dispatch."""

    def test_publish_and_subscribe(self):
        """Test publishing and subscribing to events."""
        from interaction.ui_events import EventDispatch, UIEventType
        dispatch = EventDispatch()
        received = []

        def handler(event):
            received.append(event)

        dispatch.subscribe(UIEventType.INTERACTION_STARTED, handler)
        dispatch.publish(UIEventType.INTERACTION_STARTED, {"test": True})

        assert len(received) == 1
        assert received[0].type == UIEventType.INTERACTION_STARTED

    def test_subscribe_all(self):
        """Test subscribing to all events."""
        from interaction.ui_events import EventDispatch, UIEventType
        dispatch = EventDispatch()
        received = []

        def handler(event):
            received.append(event)

        unsub = dispatch.subscribe_all(handler)
        dispatch.publish(UIEventType.VOICE_SESSION_START, {})
        dispatch.publish(UIEventType.DESKTOP_WINDOW_CHANGED, {})

        assert len(received) == 2
        unsub()

    def test_event_history(self):
        """Test event history."""
        from interaction.ui_events import EventDispatch, UIEventType
        dispatch = EventDispatch()

        dispatch.publish(UIEventType.NOTIFICATION_SENT, {})
        dispatch.publish(UIEventType.SESSION_CREATED, {})

        history = dispatch.get_history()
        assert len(history) == 2

    def test_filtered_history(self):
        """Test filtered event history."""
        from interaction.ui_events import EventDispatch, UIEventType
        dispatch = EventDispatch()

        dispatch.publish(UIEventType.VOICE_SESSION_START, {})
        dispatch.publish(UIEventType.DESKTOP_WINDOW_CHANGED, {})

        history = dispatch.get_history(event_type=UIEventType.VOICE_SESSION_START)
        assert len(history) == 1
        assert history[0].type == UIEventType.VOICE_SESSION_START


# ============================================================================
# Preferences
# ============================================================================

class TestPreferences:
    """Test interaction preferences."""

    def test_default_preferences(self):
        """Test default preference values."""
        from interaction.preferences import InteractionPreferences
        prefs = InteractionPreferences()
        assert prefs.voice.push_to_talk_key == "Ctrl+Space"
        assert prefs.privacy.clipboard.value == "deny"
        assert prefs.privacy.microphone.value == "ask"

    def test_save_and_load(self):
        """Test preferences persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from interaction.preferences import PreferencesManager, InteractionPreferences
            path = Path(tmpdir) / "prefs.json"

            mgr = PreferencesManager(str(path))
            prefs = InteractionPreferences()
            prefs.voice.push_to_talk_key = "Ctrl+Shift+V"
            prefs.voice.speech_output_speed = 1.5

            assert mgr.save(prefs) is True
            assert path.exists()

            loaded = mgr.load()
            assert loaded.voice.push_to_talk_key == "Ctrl+Shift+V"
            assert loaded.voice.speech_output_speed == 1.5

    def test_reset(self):
        """Test resetting preferences to defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from interaction.preferences import PreferencesManager, InteractionPreferences
            path = Path(tmpdir) / "prefs.json"

            mgr = PreferencesManager(str(path))
            mgr.save(InteractionPreferences())
            mgr.reset()
            assert not path.exists()

    def test_privacy_permission_roundtrip(self):
        """Test privacy permission serialization."""
        from interaction.preferences import (
            InteractionPreferences, PermissionSetting,
            PreferencesManager,
        )
        prefs = InteractionPreferences()
        prefs.privacy.microphone = PermissionSetting.ALWAYS_ALLOW
        prefs.privacy.clipboard = PermissionSetting.DENY

        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = PreferencesManager(str(Path(tmpdir) / "prefs.json"))
            mgr.save(prefs)

            loaded = mgr.load()
            assert loaded.privacy.microphone == PermissionSetting.ALWAYS_ALLOW
            assert loaded.privacy.clipboard == PermissionSetting.DENY


# ============================================================================
# EventBus integration
# ============================================================================

class TestEventBusIntegration:
    """Test integration with kernel EventBus."""

    def test_interaction_manager_emits_events(self):
        """Test InteractionManager emits events through EventBus."""
        from interaction.interaction_manager import (
            InteractionManager, InteractionEvent,
        )
        bus = EventBus()
        received = []

        bus.subscribe(InteractionEvent.INTERACTION_STARTED.value,
                      lambda e: received.append(e))

        mgr = InteractionManager(event_bus=bus)
        mgr.initialize()
        mgr.shutdown()

        assert len(received) >= 1

    def test_voice_manager_emits_events(self):
        """Test VoiceManager emits events through EventBus."""
        from interaction.voice.voice_manager import VoiceManager, VoiceEvent
        bus = EventBus()
        received = []

        bus.subscribe(VoiceEvent.VOICE_INITIALIZED.value,
                      lambda e: received.append(e))

        vm = VoiceManager(event_bus=bus)
        vm.initialize()
        vm.shutdown()

        assert len(received) >= 1
