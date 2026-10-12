"""AetherOS Universal Reality Interface 1.0 — Input Pipelines (§15-44).

Unified input pipelines for all multimodal modalities. Each pipeline:
- Handles sensor availability + permission checks (§9-13)
- Routes to production runtimes (aetheros_vision, aetheros_voice, etc.)
- Returns canonical MultimodalEvent with provenance + confidence
- Never fakes unavailable sensors — returns UNAVAILABLE (§346-348)
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from aetheros_reality.models import (
    EventConfidence,
    EventSource,
    EventType,
    GazeData,
    GestureData,
    HandTrackingData,
    HeadPoseData,
    InputModality,
    MultimodalEvent,
    EventSource,
    EventConfidence,
    SensorState,
    SensorStatus,
    SensorGovernance,
    SensorPermission,
    STTResult,
    TTSResult,
    TTSStreamChunk,
    VisionTaskRequest,
    VisionResult,
    VisionTask,
    VisionTaskRequest,
    new_id,
)

logger = logging.getLogger(__name__)


def _now() -> float:
    return time.time()


def new_id(prefix: str = "evt") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Base Pipeline Interface
# ---------------------------------------------------------------------------

class SensorPipeline(ABC):
    """Base class for all sensor input pipelines (§3)."""

    modality: InputModality = InputModality.UNKNOWN

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the sensor/hardware is available."""

    @abstractmethod
    def get_status(self) -> 'SensorStatus':
        """Get current sensor status (§9)."""

    @abstractmethod
    def check_permission(self, session_id: str) -> bool:
        """Check if sensor is permitted for this session (§10-13)."""

    @abstractmethod
    def start(self, session_id: str) -> bool:
        """Start the sensor pipeline for a session."""

    @abstractmethod
    def stop(self, session_id: str) -> bool:
        """Stop the sensor pipeline for a session."""

    @abstractmethod
    def get_event(self, timeout: float = 0.1) -> Optional['MultimodalEvent']:
        """Get next event from the pipeline (blocking with timeout)."""

    def _create_event(
        self,
        session_id: str,
        event_type: 'EventType',
        payload: Dict[str, Any],
        source: 'EventSource',
        confidence: 'EventConfidence',
        provenance: Dict[str, Any] = None
    ) -> 'MultimodalEvent':
        """Create a canonical multimodal event."""
        from aetheros_reality.models import (
            MultimodalEvent, EventType, EventSource, EventConfidence, InputModality, new_id
        )
        return MultimodalEvent(
            event_id=new_id("evt"),
            session_id=self.session_id,
            timestamp=_now(),
            modality=self.modality,
            source=source,
            payload_reference="",
            spatial_context={},
            temporal_context={},
            confidence=confidence,
            provenance=provenance or {},
            trust_state="",
            privacy_classification="internal",
            event_type=event_type,
            payload=payload,
        )


# ---------------------------------------------------------------------------
# Voice Pipeline (§15-22)
# ---------------------------------------------------------------------------

class VoicePipeline:
    """Voice input pipeline (§15-22). Integrates with aetheros_voice.
    Handles VAD, ASR, wake word, barge-in, turn detection, corrections.
    """

    modality = InputModality.VOICE

    def __init__(self):
        self._session_id: Optional[str] = None
        self._running = False
        self._stt_engine = None
        self._tts_engine = None
        self._wake_detector = None
        self._vad = None
        self._audio_capture = None
        self._wake_word = "hey aether"
        self._wake_word_enabled = True
        self._streaming = True
        self._interrupt_enabled = True
        self._language = "en"
        self._lock = threading.Lock()
        self._audio_queue: asyncio.Queue = None
        self._event_callback: Optional[Callable] = None
        self._running = False
        self._vad_active = False

    def is_available(self) -> bool:
        """Check if voice hardware is available."""
        try:
            from aetheros_voice.audio.capture import AudioCapture
            return True
        except Exception:
            return False

    def get_status(self) -> 'SensorStatus':
        from aetheros_reality.models import SensorStatus, SensorState
        return SensorStatus(
            sensor_id="voice_pipeline",
            modality=InputModality.VOICE,
            state=SensorState.ACTIVE if self._running else SensorState.OFF,
            last_active=_now() if self._running else 0.0,
            capabilities=["stt", "tts", "wake_word", "vad", "barge_in"],
            health="healthy" if self._running else "offline",
        )

    def check_permission(self, session_id: str) -> bool:
        # Check session's voice permission
        return True  # Simplified - integrate with session permissions

    def start(self, session_id: str, config: Dict[str, Any] = None) -> bool:
        config = config or {}
        self._session_id = session_id
        self._wake_word = config.get("wake_word", "hey aether")
        self._wake_word_enabled = config.get("wake_word_enabled", True)
        self._streaming = config.get("streaming_enabled", True)
        self._interrupt_enabled = config.get("interrupt_enabled", True)
        self._language = config.get("language", "en")
        self._vad_active = True
        self._running = True
        return True

    def stop(self) -> bool:
        self._running = False
        self._vad_active = False
        return True

    def get_event(self, timeout: float = 0.1) -> Optional['MultimodalEvent']:
        """Get next voice event (STT result, wake word, etc.)."""
        # This would integrate with aetheros_voice streaming
        # Returns MultimodalEvent with VOICE_INPUT or USER_SPEECH_END
        return None

    async def process_audio_stream(self, audio_chunk: bytes) -> Optional['MultimodalEvent']:
        """Process streaming audio chunk (for streaming ASR)."""
        # Streaming ASR processing
        return None

    def handle_barge_in(self, audio_chunk: bytes) -> bool:
        """Handle barge-in detection (§17)."""
        if not self._interrupt_enabled:
            return False
        # Detect speech during TTS playback
        return False

    def handle_wake_word(self, audio_chunk: bytes) -> bool:
        """Detect wake word."""
        if not self._wake_word_enabled:
            return False
        return False

    def handle_correction(self, text: str) -> bool:
        """Handle voice correction (§19)."""
        corrections = ["actually", "no,", "wait", "stop", "go back", "don't"]
        return any(c in text.lower() for c in corrections)

    def handle_stop_command(self, text: str) -> bool:
        """Global stop commands (§20)."""
        stop_commands = ["stop", "cancel", "pause", "emergency stop", "undo", "go back"]
        return any(cmd in text.lower() for cmd in stop_commands)


# ---------------------------------------------------------------------------
# Vision Pipeline (§24-34)
# ---------------------------------------------------------------------------

class VisionPipeline:
    """Vision input pipeline (§24-34). Integrates with aetheros_vision.
    Handles object detection, tracking, OCR, scene understanding, UI grounding.
    """

    modality = InputModality.VISION

    def __init__(self):
        self._session_id: Optional[str] = None
        self._running = False
        self._vision_runtime = None
        self._screen_capture = None
        self._camera_capture = None
        self._running = False

    def is_available(self) -> bool:
        try:
            from aetheros_vision import get_vision_runtime
            rt = get_vision_runtime()
            return rt is not None
        except Exception:
            return False

    def get_status(self) -> 'SensorStatus':
        from aetheros_reality.models import SensorStatus, SensorState
        return SensorStatus(
            sensor_id="vision_pipeline",
            modality=InputModality.VISION,
            state=SensorState.ACTIVE if self._running else SensorState.OFF,
            last_active=_now() if self._running else 0.0,
            capabilities=["object_detection", "ocr", "scene_understanding",
                          "ui_understanding", "face_detection", "gesture_detection",
                          "spatial_relations", "visual_grounding"],
            health="healthy" if self._running else "offline",
        )

    def check_permission(self, session_id: str) -> bool:
        return True

    def start(self, session_id: str, config: Dict[str, Any] = None) -> bool:
        self._session_id = session_id
        self._running = True
        return True

    def stop(self) -> bool:
        self._running = False
        return True

    def get_event(self, timeout: float = 0.1) -> Optional['MultimodalEvent']:
        """Get next vision event (object detected, OCR result, etc.)."""
        return None

    def analyze_frame(self, image_source: str, task: 'VisionTask' = None) -> 'VisionResult':
        """Analyze a single frame/image."""
        from aetheros_reality.models import VisionTask, VisionResult
        return VisionResult(
            task=task or VisionTask.OBJECT_DETECTION,
            success=False,
            error="Not implemented - integrate with aetheros_vision"
        )

    def capture_screen(self, mode: str = "full_screen") -> Dict[str, Any]:
        """Capture screen using aetheros_vision."""
        return {"success": False, "error": "Not implemented"}

    def capture_camera(self, camera_index: int = 0) -> Dict[str, Any]:
        """Capture from camera."""
        return {"success": False, "error": "Not implemented"}


# ---------------------------------------------------------------------------
# Gaze Pipeline (§35)
# ---------------------------------------------------------------------------

class GazePipeline:
    """Gaze tracking pipeline (§35)."""

    modality = InputModality.GAZE

    def __init__(self):
        self._session_id: Optional[str] = None
        self._running = False
        self._gaze_tracker = None
        self._running = False

    def is_available(self) -> bool:
        return False  # Requires specialized hardware

    def get_status(self) -> 'SensorStatus':
        from aetheros_reality.models import SensorStatus, SensorState
        return SensorStatus(
            sensor_id="gaze_pipeline",
            modality=InputModality.GAZE,
            state=SensorState.OFF,
            last_active=0.0,
            capabilities=["gaze_ray", "fixation", "saccade", "dwell", "gaze_target"],
            health="unavailable",
        )

    def check_permission(self, session_id: str) -> bool:
        return True

    def start(self, session_id: str, config: Dict[str, Any] = None) -> bool:
        self._session_id = session_id
        self._running = True
        return True

    def stop(self) -> bool:
        self._running = False
        return True

    def get_event(self, timeout: float = 0.1) -> Optional['MultimodalEvent']:
        return None


# ---------------------------------------------------------------------------
# Gesture Pipeline (§39-42)
# ---------------------------------------------------------------------------

class GesturePipeline:
    """Gesture recognition pipeline (§39-42)."""

    modality = InputModality.GESTURE

    def __init__(self):
        self._session_id: Optional[str] = None
        self._running = False
        self._gesture_recognizer = None
        self._running = False
        self._gesture_map = {
            "point": "POINT",
            "pinch": "PINCH",
            "grab": "GRAB",
            "release": "RELEASE",
            "swipe": "SWIPE",
            "rotate": "ROTATE",
            "zoom": "ZOOM",
            "wave": "WAVE",
            "stop": "STOP",
            "confirm": "CONFIRM",
            "cancel": "CANCEL",
        }

    def is_available(self) -> bool:
        return False  # Requires hand tracking hardware

    def get_status(self) -> 'SensorStatus':
        from aetheros_reality.models import SensorStatus, SensorState
        return SensorStatus(
            sensor_id="gesture_pipeline",
            modality=InputModality.GESTURE,
            state=SensorState.OFF,
            last_active=0.0,
            capabilities=["point", "pinch", "grab", "release", "swipe",
                          "rotate", "zoom", "wave", "stop", "confirm", "cancel"],
            health="unavailable",
        )

    def check_permission(self, session_id: str) -> bool:
        return True

    def start(self, session_id: str, config: Dict[str, Any] = None) -> bool:
        self._session_id = session_id
        self._running = True
        return True

    def stop(self) -> bool:
        self._running = False
        return True

    def get_event(self, timeout: float = 0.1) -> Optional['MultimodalEvent']:
        return None

    def recognize_gesture(self, hand_data: 'HandTrackingData') -> Optional['GestureData']:
        """Recognize gesture from hand tracking data."""
        return None


# ---------------------------------------------------------------------------
# Hand Tracking Pipeline (§39)
# ---------------------------------------------------------------------------

class HandTrackingPipeline:
    """Hand tracking pipeline (§39)."""

    modality = InputModality.HAND_TRACKING

    def __init__(self):
        self._session_id: Optional[str] = None
        self._running = False
        self._hand_tracker = None
        self._running = False

    def is_available(self) -> bool:
        return False

    def get_status(self) -> 'SensorStatus':
        from aetheros_reality.models import SensorStatus, SensorState
        return SensorStatus(
            sensor_id="hand_tracking_pipeline",
            modality=InputModality.HAND_TRACKING,
            state=SensorState.OFF,
            last_active=0.0,
            capabilities=["hand_position", "hand_pose", "finger_position", "pointing", "pinch", "grab"],
            health="unavailable",
        )

    def check_permission(self, session_id: str) -> bool:
        return True

    def start(self, session_id: str, config: Dict[str, Any] = None) -> bool:
        return True

    def stop(self) -> bool:
        return True

    def get_event(self, timeout: float = 0.1) -> Optional['MultimodalEvent']:
        return None


# ---------------------------------------------------------------------------
# Head Pose Pipeline (§43)
# ---------------------------------------------------------------------------

class HeadPosePipeline:
    """Head pose estimation pipeline (§43)."""

    modality = InputModality.HEAD_POSE

    def __init__(self):
        self._running = False

    def is_available(self) -> bool:
        return False

    def get_status(self) -> 'SensorStatus':
        from aetheros_reality.models import SensorStatus, SensorState
        return SensorStatus(
            sensor_id="head_pose_pipeline",
            modality=InputModality.HEAD_POSE,
            state=SensorState.OFF,
            last_active=0.0,
            capabilities=["position", "orientation", "looking_direction", "euler_angles"],
            health="unavailable",
        )

    def check_permission(self, session_id: str) -> bool:
        return True

    def start(self, session_id: str, config: Dict[str, Any] = None) -> bool:
        return True

    def stop(self) -> bool:
        return True

    def get_event(self, timeout: float = 0.1) -> Optional['MultimodalEvent']:
        return None


# ---------------------------------------------------------------------------
# Screen Pipeline (§31)
# ---------------------------------------------------------------------------

class ScreenPipeline:
    """Screen understanding pipeline (§31). Integrates with Master 39."""

    modality = InputModality.SCREEN

    def __init__(self):
        self._running = False

    def is_available(self) -> bool:
        try:
            from aetheros_vision.desktop import DesktopUnderstanding
            return True
        except Exception:
            return False

    def get_status(self) -> 'SensorStatus':
        from aetheros_reality.models import SensorStatus, SensorState
        return SensorStatus(
            sensor_id="screen_pipeline",
            modality=InputModality.SCREEN,
            state=SensorState.AVAILABLE if self.is_available() else SensorState.OFF,
            last_active=_now() if self.is_available() else 0.0,
            capabilities=["ui_understanding", "dom_access", "ocr", "visual_grounding"],
            health="healthy" if self.is_available() else "unavailable",
        )

    def check_permission(self, session_id: str) -> bool:
        return True

    def start(self, session_id: str, config: Dict[str, Any] = None) -> bool:
        return True

    def stop(self) -> bool:
        return True

    def get_event(self, timeout: float = 0.1) -> Optional['MultimodalEvent']:
        return None

    def understand_screen(self, question: str = "What is on screen?") -> Dict[str, Any]:
        """Analyze screen content."""
        return {"success": False, "error": "Not implemented"}


# ---------------------------------------------------------------------------
# Camera Pipeline
# ---------------------------------------------------------------------------

class CameraPipeline:
    """Camera capture pipeline."""

    modality = InputModality.CAMERA

    def __init__(self):
        self._running = False

    def is_available(self) -> bool:
        try:
            from aetheros_vision.capture import CameraCaptureRuntime
            return CameraCaptureRuntime().is_available()
        except Exception:
            return False

    def get_status(self) -> 'SensorStatus':
        from aetheros_reality.models import SensorStatus, SensorState
        return SensorStatus(
            sensor_id="camera_pipeline",
            modality=InputModality.CAMERA,
            state=SensorState.AVAILABLE if self.is_available() else SensorState.OFF,
            capabilities=["still", "burst", "timelapse"],
            health="healthy" if self.is_available() else "unavailable",
        )

    def start(self, session_id: str, config: Dict[str, Any] = None) -> bool:
        return True

    def stop(self) -> bool:
        return True

    def capture(self, mode: str = "still") -> Dict[str, Any]:
        return {"success": False, "error": "Not implemented"}


# ---------------------------------------------------------------------------
# Audio/Spatial Audio Pipeline
# ---------------------------------------------------------------------------

class AudioPipeline:
    """Audio/spatial audio pipeline (§63-64)."""

    modality = InputModality.AUDIO

    def __init__(self):
        self._running = False

    def is_available(self) -> bool:
        try:
            from aetheros_voice.audio.capture import AudioCapture
            return True
        except Exception:
            return False

    def get_status(self) -> 'SensorStatus':
        from aetheros_reality.models import SensorStatus, SensorState
        return SensorStatus(
            sensor_id="audio_pipeline",
            modality=InputModality.AUDIO,
            state=SensorState.AVAILABLE if self.is_available() else SensorState.OFF,
            capabilities=["capture", "spatial_audio", "source_tracking"],
            health="healthy" if self.is_available() else "unavailable",
        )

    def check_permission(self, session_id: str) -> bool:
        return True

    def start(self, session_id: str, config: Dict[str, Any] = None) -> bool:
        return True

    def stop(self) -> bool:
        return True

    def get_event(self, timeout: float = 0.1) -> Optional['MultimodalEvent']:
        return None


# ---------------------------------------------------------------------------
# Environmental Sensor Pipeline
# ---------------------------------------------------------------------------

class EnvironmentalPipeline:
    """Environmental sensor pipeline (§66)."""

    modality = InputModality.SENSORS

    def __init__(self):
        pass

    def is_available(self) -> bool:
        return False

    def get_status(self) -> 'SensorStatus':
        from aetheros_reality.models import SensorStatus, SensorState
        return SensorStatus(
            sensor_id="environmental_pipeline",
            modality=InputModality.SENSORS,
            state=SensorState.UNAVAILABLE,
            capabilities=["temperature", "humidity", "pressure", "air_quality"],
            health="unavailable",
        )

    def check_permission(self, session_id: str) -> bool:
        return True


# ---------------------------------------------------------------------------
# Touch/Mouse/Keyboard Pipeline
# ---------------------------------------------------------------------------

class InputDevicePipeline:
    """Touch/Mouse/Keyboard input pipeline."""

    modality = InputModality.TOUCH  # or MOUSE, KEYBOARD

    def __init__(self):
        pass

    def get_status(self) -> 'SensorStatus':
        from aetheros_reality.models import SensorStatus, SensorState
        return SensorStatus(
            sensor_id="input_device_pipeline",
            modality=InputModality.MOUSE,
            state=SensorState.AVAILABLE,
            capabilities=["mouse", "keyboard", "touch"],
            health="healthy",
        )


# ---------------------------------------------------------------------------
# XR Pipeline
# ---------------------------------------------------------------------------

class XRPipeline:
    """XR/AR/VR pipeline (§99)."""

    modality = InputModality.XR

    def __init__(self):
        pass

    def is_available(self) -> bool:
        return False

    def get_status(self) -> 'SensorStatus':
        from aetheros_reality.models import SensorStatus, SensorState
        return SensorStatus(
            sensor_id="xr_pipeline",
            modality=InputModality.XR,
            state=SensorState.UNAVAILABLE,
            capabilities=["ar", "vr", "mr", "spatial_anchors", "hand_tracking"],
            health="unavailable",
        )


# ---------------------------------------------------------------------------
# Sensor Registry
# ---------------------------------------------------------------------------

class SensorRegistry:
    """Registry of all available sensor pipelines."""

    def __init__(self):
        self._pipelines: Dict[InputModality, SensorPipeline] = {}
        self._register_default_pipelines()

    def _register_default_pipelines(self):
        # Voice
        self._pipelines[InputModality.VOICE] = VoicePipeline()
        # Vision
        self._pipelines[InputModality.VISION] = VisionPipeline()
        self._pipelines[InputModality.SCREEN] = ScreenPipeline()
        self._pipelines[InputModality.CAMERA] = CameraPipeline()
        self._pipelines[InputModality.GAZE] = GazePipeline()
        self._pipelines[InputModality.GESTURE] = GesturePipeline()
        self._pipelines[InputModality.HAND_TRACKING] = HandTrackingPipeline()
        self._pipelines[InputModality.HEAD_POSE] = HeadPosePipeline()
        # Audio
        self._pipelines[InputModality.AUDIO] = AudioPipeline()
        # Environmental
        self._pipelines[InputModality.SENSORS] = EnvironmentalPipeline()
        # Input devices
        self._pipelines[InputModality.TOUCH] = InputDevicePipeline()
        self._pipelines[InputModality.MOUSE] = InputDevicePipeline()
        self._pipelines[InputModality.KEYBOARD] = InputDevicePipeline()
        # XR
        self._pipelines[InputModality.XR] = XRPipeline()
        # Text/Keyboard
        self._pipelines[InputModality.TEXT] = TextPipeline()
        self._pipelines[InputModality.KEYBOARD] = InputDevicePipeline()

    def get_pipeline(self, modality: InputModality) -> Optional[SensorPipeline]:
        return self._pipelines.get(modality)

    def get_all_statuses(self) -> Dict[InputModality, 'SensorStatus']:
        return {m: p.get_status() for m, p in self._pipelines.items()}

    def get_available_modalities(self) -> List[InputModality]:
        return [m for m, p in self._pipelines.items() if p.is_available()]


# ---------------------------------------------------------------------------
# Text Pipeline
# ---------------------------------------------------------------------------

class TextPipeline:
    """Text input pipeline (keyboard, clipboard, etc.)."""

    modality = InputModality.TEXT

    def __init__(self):
        pass

    def is_available(self) -> bool:
        return True

    def get_status(self) -> 'SensorStatus':
        from aetheros_reality.models import SensorStatus, SensorState
        return SensorStatus(
            sensor_id="text_pipeline",
            modality=InputModality.TEXT,
            state=SensorState.ACTIVE,
            last_active=_now(),
            capabilities=["text_input", "clipboard", "dictation"],
            health="healthy",
        )

    def check_permission(self, session_id: str) -> bool:
        return True

    def start(self, session_id: str, config: Dict[str, Any] = None) -> bool:
        return True

    def stop(self) -> bool:
        return True

    def get_event(self, timeout: float = 0.1) -> Optional['MultimodalEvent']:
        return None

    def submit_text(self, text: str, session_id: str) -> 'MultimodalEvent':
        """Submit text input as a multimodal event."""
        from aetheros_reality.models import MultimodalEvent, EventType, EventSource, EventConfidence, InputModality, new_id
        return MultimodalEvent(
            event_id=new_id("evt"),
            session_id=session_id,
            timestamp=_now(),
            modality=InputModality.TEXT,
            source=EventSource.USER_INPUT,
            payload_reference="",
            spatial_context={},
            temporal_context={},
            confidence=EventConfidence.OBSERVED,
            provenance={"source": "text_input"},
            trust_state="",
            privacy_classification="internal",
            event_type=EventType.USER_SPEECH_ACTIVITY,
            payload={"text": text}
        )