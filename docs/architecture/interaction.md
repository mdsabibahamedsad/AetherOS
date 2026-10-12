# AetherOS Ambient Workspace Layer

## Interaction Architecture

The interaction layer provides a unified interface for voice, desktop, notifications, presence awareness, session continuity, and user interaction. It extends the AetherOS Kernel with ambient interaction capabilities while maintaining privacy, modularity, and plugin-based extensibility.

```
    ┌────────────────────────────────────────────────────────────┐
    │                    InteractionManager                       │
    │  Unified API for all interaction channels                   │
    │                                                             │
    │  ┌──────────────────┐  ┌────────────────────┐             │
    │  │   Desktop         │  │    Voice            │             │
    │  │  ┌──────────────┐ │  │  ┌────────────────┐│             │
    │  │  │WindowTracker │ │  │  │SpeechInput     ││             │
    │  │  │Workspace     │ │  │  │SpeechOutput    ││             │
    │  │  │Clipboard     │ │  │  │WakeWord        ││             │
    │  │  │Notifications │ │  │  │AudioPipeline   ││             │
    │  │  │Shortcuts     │ │  │  │Transcription   ││             │
    │  │  └──────────────┘ │  │  └────────────────┘│             │
    │  └──────────────────┘  └────────────────────┘             │
    │                                                             │
    │  ┌──────────────────┐  ┌────────────────────┐             │
    │  │   Presence        │  │    Session          │             │
    │  │  ┌──────────────┐ │  │  ┌────────────────┐│             │
    │  │  │ActivityDetect│ │  │  │SessionManager  ││             │
    │  │  │IdleMonitor   │ │  │  │History         ││             │
    │  │  │FocusMode     │ │  │  │Preferences     ││             │
    │  │  │ContextDetect │ │  │  │UI Events       ││             │
    │  │  └──────────────┘ │  │  └────────────────┘│             │
    │  └──────────────────┘  └────────────────────┘             │
    │                                                             │
    │  Permission Layer (Privacy-First)                          │
    └────────────────────────────────────────────────────────────┘
                    │
                    ▼
    ┌────────────────────────────────────────────────────────────┐
    │           AetherOS Kernel Infrastructure                    │
    │  EventBus │ Lifecycle │ Permissions │ State │ Memory        │
    └────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Privacy-First**: Every capability requires explicit permission. Microphone, clipboard, desktop context, and workspace metadata all have configurable permission levels.

2. **Modular**: Every subsystem is independently testable and optional. Voice, desktop, notifications, and presence can be enabled/disabled independently.

3. **Plugin-Extensible**: Voice providers (STT/TTS), desktop adapters, notification channels, and automation adapters are all registered through the plugin API. No core modifications needed.

4. **Backward Compatible**: Existing Aetheros voice mode, TTS, STT, notifications, and session management continue to work unchanged.

5. **Vendor-Agnostic**: No hardcoded vendor services. All providers are pluggable.

## Modules

### Interaction Manager (`interaction_manager.py`)

The central entry point for all interaction channels. Coordinates voice sessions, desktop events, notifications, and user actions.

**Key APIs:**
- `start_voice_session(session_type)` — Start a voice interaction session
- `stop_voice_session(session_id)` — End a voice session
- `notify(notification)` — Deliver a notification through all channels
- `capture_context()` — Capture workspace context
- `request_permission(permission)` — Request user permission
- `register_voice_adapter(name, fn)` — Register plugin voice adapter
- `register_desktop_adapter(name, fn)` — Register plugin desktop adapter
- `register_notification_adapter(name, fn)` — Register notification channel

**Events:**
- `interaction.voice_session_started/ended` — Voice session lifecycle
- `interaction.desktop_event` — Desktop interaction events
- `interaction.notification_delivered/action` — Notification lifecycle
- `interaction.workspace_changed` — Workspace context changes
- `interaction.permission_*` — Permission grant/deny events

### Session Manager (`session_manager.py`)

Manages session continuity across devices and time.

**Key APIs:**
- `create_session(user_id, device_id, platform)` — Create session
- `create_snapshot(session_id)` — Point-in-time snapshot
- `resume_session(snapshot_id, new_device, new_platform)` — Resume on any device
- `create_continuity(original_session_id)` — Link sessions across devices
- `end_session(session_id)` — End session

**Persistence:** Sessions, snapshots, and continuities are persisted to `~/.aetheros/interaction/sessions/session_state.json`.

### Desktop Integration (`desktop/`)

#### Desktop Manager (`desktop_manager.py`)
Coordinates window tracking, workspace detection, clipboard monitoring, notifications, and shortcuts. All features require explicit permission.

#### Window Tracker (`window_tracker.py`)
Monitors active window changes for context awareness.

#### Workspace Monitor (`workspace_monitor.py`)
Detects workspace/project context from VCS markers, current directory, and environment variables.

#### Clipboard Monitor (`clipboard.py`)
Permission-controlled clipboard monitoring with four permission levels:
- `DENIED`: No access
- `TEXT_ONLY`: Text content only
- `FULL`: All content types
- `METADATA`: Change notifications only

#### Notification Manager (`notifications.py`)
Structured notification delivery across channels. Supports priority levels, categories, actions, and per-channel delivery adapters.

#### Shortcut Manager (`shortcuts.py`)
Global keyboard shortcut registration with platform adapters.

### Voice Pipeline (`voice/`)

#### Voice Manager (`voice_manager.py`)
Coordinates voice session lifecycle. Supports push-to-talk, continuous, and wake-word session types.

#### Speech Input (`speech_input.py`)
Adapter-based STT management. Providers register through `SpeechInputAdapter` subclasses.

#### Speech Output (`speech_output.py`)
Adapter-based TTS management. Providers register through `SpeechOutputAdapter` subclasses.

#### Wake Word Engine (`wake_word.py`)
Modular wake word detection with pluggable engines, configurable sensitivity and cooldown.

#### Audio Pipeline (`audio_pipeline.py`)
Streaming audio capture, format conversion, level monitoring, and playback.

#### Transcription Engine (`transcription.py`)
STT configuration and management that wraps the existing Aetheros transcription infrastructure (`tools/transcription_tools.py`).

### Presence Awareness (`presence/`)

#### Activity Detector (`activity_detector.py`)
Monitors user activity combining input device activity, window focus, and system signals. Emits structured events for activity state transitions.

#### Idle Monitor (`idle_monitor.py`)
Tracks idle time with configurable thresholds:
- **Idle**: 2 minutes of inactivity
- **Long Idle**: 10 minutes
- **Away**: 30 minutes

#### Focus Mode (`focus_mode.py`)
Manages focus sessions (Pomodoro-style) with configurable duration, notification muting, and automation triggers.

#### Context Detector (`context_detector.py`)
Derives workspace context from active window, filesystem, VCS state, and ongoing workflows.

### Interaction History (`interaction_history.py`)

Records all interaction events for analysis and recall. Supports:
- Query by event type, channel, tags, time range, session
- Text search in summaries
- Summary statistics
- JSONL persistence

### UI Events (`ui_events.py`)

Central event dispatch hub. Provides type-safe event publishing and subscription for all interaction events.

### Preferences (`preferences.py`)

User preferences with four categories:
- **Accessibility**: Keyboard nav, screen reader, captions, high contrast
- **Notifications**: Desktop toasts, sounds, previews, quiet hours
- **Voice**: Push-to-talk key, wake word, speech speed, providers
- **Privacy**: Per-capability permission settings

## Voice Pipeline

```
    Microphone → AudioPipeline → SpeechInput → TranscriptionEngine
                                          ↕
    Speaker ← AudioPipeline ← SpeechOutput ← Text
                    ↕
              WakeWordEngine (optional)
```

### Provider Resolution

1. **Built-in providers** (Edge TTS, faster-whisper, etc.) always have priority
2. **Command-type providers** (configured in config.yaml as `type: command`)
3. **Plugin providers** (registered via plugin API)
4. **Default fallback** (Edge TTS for output, faster-whisper for input)

## Desktop Integration Model

```
    ┌──────────────┐
    │DesktopManager│
    └──────┬───────┘
           │
    ┌──────┴───────┬──────────┬──────────────┬───────────┐
    │              │          │              │           │
    ▼              ▼          ▼              ▼           ▼
WindowTracker  Workspace   Clipboard   Notifications  Shortcuts
               Monitor    Monitor
```

Each sub-module:
1. Requires explicit permission before activation
2. Supports platform adapters for OS-specific implementation
3. Emits structured events on state changes
4. Can be enabled/disabled independently

## Permission Model

| Permission | Default | Purpose |
|------------|---------|---------|
| `microphone` | Ask | Voice input |
| `clipboard` | Deny | Clipboard content access |
| `desktop_context` | Ask | Active window info |
| `notifications` | Ask | Notification delivery |
| `workspace_metadata` | Ask | Project/files context |
| `file_selection` | Deny | File system awareness |

Permission levels:
- `always_allow` — Always grant
- `ask` — Prompt user each time
- `deny` — Always deny
- `granted_session` — Grant for current session
- `denied_session` — Deny for current session

## Session Continuity Flow

```
    ┌──────────┐         ┌────────────────┐         ┌──────────┐
    │ Session A │──snapshot──▶  Snapshot 1  │──resume──▶ Session B │
    └──────────┘         └────────────────┘         └──────────┘
         │ Device 1              │                       │ Device 2
         ▼                       ▼                       ▼
    SessionState           Persisted                SessionResumeContext
    (in memory)            (JSON file)              (restored from snapshot)
```

## Extension Guide

### Adding a Voice Provider

```python
from interaction.voice.speech_input import SpeechInputAdapter, SpeechInputResult

class MySTTAdapter(SpeechInputAdapter):
    def transcribe(self, audio_path, **kwargs):
        # Implement STT
        return SpeechInputResult(success=True, text="transcribed text")

# Register with the manager
manager.speech_input.register_adapter("my_provider", MySTTAdapter())
```

### Adding a Desktop Adapter

```python
# Register with the desktop manager
def my_window_adapter():
    return {"title": "My Window", "process": "my_app"}

desktop_manager.register_window_adapter("my_adapter", my_window_adapter)
```

### Adding a Notification Channel

```python
def my_notification_adapter(notification):
    # Send notification via your channel
    return True  # Return delivery success

interaction_manager.register_notification_adapter("my_channel", my_notification_adapter)
```

## Configuration

Interaction preferences are stored at `~/.aetheros/interaction_prefs.json` (configurable path).

Example preferences:
```json
{
    "version": 1,
    "voice": {
        "enabled": true,
        "push_to_talk_key": "Ctrl+Space",
        "wake_word": "aetheros",
        "speech_output_speed": 1.0
    },
    "privacy": {
        "microphone": "ask",
        "clipboard": "deny",
        "desktop_context": "ask"
    }
}
```
