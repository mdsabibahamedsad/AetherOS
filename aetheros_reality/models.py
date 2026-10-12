"""AetherOS Universal Reality Interface 1.0 — Canonical Models (§6).

Canonical multimodal event and session models. All multimodal
observations, inferences, intents, authorizations, actions, and
verifications flow through these types. Every event carries enough
metadata to be rendered, logged, persisted, and replayed without
re-reading the source sensor data.
"""
from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


def _now() -> float:
    return time.time()


def new_id(prefix: str = "evt") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# §3: Universal Input/Output Modalities
# ---------------------------------------------------------------------------

class InputModality(str, enum.Enum):
    """Input modalities the Universal Reality Interface can observe."""
    TEXT = "text"
    VOICE = "voice"
    AUDIO = "audio"
    VISION = "vision"
    SCREEN = "screen"
    CAMERA = "camera"
    VIDEO = "video"
    OCR = "ocr"
    DOCUMENTS = "documents"
    TOUCH = "touch"
    MOUSE = "mouse"
    KEYBOARD = "keyboard"
    GAZE = "gaze"
    HEAD_POSE = "head_pose"
    HAND_TRACKING = "hand_tracking"
    GESTURE = "gesture"
    FACIAL_EXPRESSION = "facial_expression"
    BODY_POSE = "body_pose"
    SPATIAL_POSITION = "spatial_position"
    SPATIAL_AUDIO = "spatial_audio"
    HAPTICS = "haptics"
    SENSORS = "sensors"
    ENVIRONMENTAL_DATA = "environmental_data"
    ROBOTICS_TELEMETRY = "robotics_telemetry"
    XR = "xr"
    UNKNOWN = "unknown"


class OutputModality(str, enum.Enum):
    """Output modalities the Universal Reality Interface can produce."""
    TEXT = "text"
    VOICE = "voice"
    TTS = "tts"
    SCREEN_UI = "screen_ui"
    VISUAL_OVERLAY = "visual_overlay"
    HIGHLIGHT = "highlight"
    POINTER = "pointer"
    CURSOR = "cursor"
    GESTURE = "gesture"
    AVATAR = "avatar"
    SPATIAL_AUDIO = "spatial_audio"
    HAPTICS = "haptics"
    AR_ANNOTATION = "ar_annotation"
    XR_OBJECT = "xr_object"
    ROBOT_ACTION = "robot_action"
    PHYSICAL_ACTUATION = "physical_actuation"


# ---------------------------------------------------------------------------
# §6: Event Types
# ---------------------------------------------------------------------------

class EventType(str, enum.Enum):
    """Canonical event types in the multimodal event stream."""
    VOICE_INPUT = "voice_input"
    AUDIO_EVENT = "audio_event"
    VISION_FRAME = "vision_frame"
    SCREEN_FRAME = "screen_frame"
    OBJECT_DETECTED = "object_detected"
    FACE_DETECTED = "face_detected"
    PERSON_DETECTED = "person_detected"
    HAND_DETECTED = "hand_detected"
    GESTURE_DETECTED = "gesture_detected"
    GAZE_EVENT = "gaze_event"
    HEAD_POSE = "head_pose"
    TOUCH_EVENT = "touch_event"
    MOUSE_EVENT = "mouse_event"
    KEYBOARD_EVENT = "keyboard_event"
    SPATIAL_POSITION = "spatial_position"
    SPATIAL_AUDIO_EVENT = "spatial_audio_event"
    SENSOR_EVENT = "sensor_event"
    USER_SPEECH_ACTIVITY = "user_speech_activity"
    USER_SPEECH_END = "user_speech_end"
    ENVIRONMENT_CHANGE = "environment_change"
    DEVICE_CHANGE = "device_change"
    USER_STATE_CHANGE = "user_state_change"


class EventSource(str, enum.Enum):
    """Source of an event (hardware, software, inferred, etc.)."""
    CAMERA = "camera"
    MICROPHONE = "microphone"
    SCREEN = "screen"
    OS_API = "os_api"
    APPLICATION = "application"
    VISION_MODEL = "vision_model"
    ASR_MODEL = "asr_model"
    GAZE_TRACKER = "gaze_tracker"
    HAND_TRACKER = "hand_tracker"
    POSE_ESTIMATOR = "pose_estimator"
    GESTURE_RECOGNIZER = "gesture_recognizer"
    OCR_ENGINE = "ocr_engine"
    FACE_DETECTOR = "face_detector"
    OBJECT_DETECTOR = "object_detector"
    GAZE_ESTIMATOR = "gaze_estimator"
    SPATIAL_MAPPER = "spatial_mapper"
    USER_INPUT = "user_input"
    MODEL_INFERENCE = "model_inference"
    SIMULATION = "simulation"
    REPLAY = "replay"
    UNKNOWN = "unknown"


class EventConfidence(str, enum.Enum):
    """Confidence classification for an event (§84)."""
    OBSERVED = "observed"
    INFERRED = "inferred"
    PREDICTED = "predicted"
    REQUESTED = "requested"
    AUTHORIZED = "authorized"
    EXECUTED = "executed"
    VERIFIED = "verified"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# §5: Canonical Multimodal Event
# ---------------------------------------------------------------------------

@dataclass
class MultimodalEvent:
    """Canonical multimodal event (§5). Every observation, inference,
    intent, authorization, action, and verification flows through this type.
    Every event carries enough metadata to be rendered, logged, persisted,
    and replayed without re-reading the source sensor data.
    """
    event_id: str = field(default_factory=lambda: new_id("evt"))
    session_id: str = ""
    timestamp: float = field(default_factory=_now)
    modality: InputModality = InputModality.UNKNOWN
    source: EventSource = EventSource.UNKNOWN
    payload_reference: str = ""  # Reference to payload (e.g., file path, memory address)
    spatial_context: Dict[str, Any] = field(default_factory=dict)  # Spatial location, coordinates, frame
    temporal_context: Dict[str, Any] = field(default_factory=dict)  # Temporal offset, sequence, duration
    confidence: EventConfidence = EventConfidence.UNKNOWN
    provenance: Dict[str, Any] = field(default_factory=dict)  # Sensor, model, pipeline, processing info
    trust_state: str = ""  # Trust Fabric state at event time
    privacy_classification: str = "internal"  # public, internal, confidential, restricted
    event_type: EventType = EventType.VISION_FRAME
    payload: Dict[str, Any] = field(default_factory=dict)  # Event-specific payload

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "modality": self.modality.value,
            "source": self.source.value,
            "payload_reference": self.payload_reference,
            "spatial_context": self.spatial_context,
            "temporal_context": self.temporal_context,
            "confidence": self.confidence.value,
            "provenance": self.provenance,
            "trust_state": self.trust_state,
            "privacy_classification": self.privacy_classification,
            "event_type": self.event_type.value,
            "payload": self.payload,
        }


# ---------------------------------------------------------------------------
# §7: Multimodal Session
# ---------------------------------------------------------------------------

class SessionMode(str, enum.Enum):
    """Session interaction modes (§8)."""
    CHAT = "chat"
    VOICE = "voice"
    VISION = "vision"
    VOICE_VISION = "voice_vision"
    DESKTOP = "desktop"
    AMBIENT = "ambient"
    MOBILE = "mobile"
    XR = "xr"
    ROBOT = "robot"
    LAB = "lab"
    DRIVING = "driving"
    PRESENTATION = "presentation"
    MEETING = "meeting"
    ACCESSIBILITY = "accessibility"
    EMERGENCY = "emergency"


class SensorState(str, enum.Enum):
    """Sensor state (§9)."""
    OFF = "off"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    PERMISSION_REQUIRED = "permission_required"
    ACTIVE = "active"
    PAUSED = "paused"
    BLOCKED = "blocked"
    ERROR = "error"


@dataclass
class SensorStatus:
    """Status of a sensor (§9)."""
    sensor_id: str
    modality: InputModality
    state: SensorState = SensorState.OFF
    last_active: float = 0.0
    capabilities: List[str] = field(default_factory=list)
    health: str = "unknown"
    last_error: Optional[str] = None


class PrivacyMode(str, enum.Enum):
    """Privacy mode for the session."""
    PUBLIC = "public"
    PRIVATE = "private"
    CONFIDENTIAL = "confidential"
    AIR_GAPPED = "air_gapped"
    LOCAL_ONLY = "local_only"
    TEMPORARY = "temporary"


class InteractionState(str, enum.Enum):
    """Current interaction state."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class MultimodalSession:
    """Multimodal session state (§7)."""
    session_id: str = field(default_factory=lambda: new_id("sess"))
    user_id: str = ""
    device_id: str = ""
    active_modalities: List[InputModality] = field(default_factory=list)
    environment: str = "desktop"
    privacy_mode: PrivacyMode = PrivacyMode.PRIVATE
    interaction_mode: SessionMode = SessionMode.CHAT
    attention_state: str = "idle"
    spatial_reference: Dict[str, Any] = field(default_factory=dict)
    conversation_state: Dict[str, Any] = field(default_factory=dict)
    authorization_state: Dict[str, Any] = field(default_factory=dict)
    sensor_status: Dict[str, SensorStatus] = field(default_factory=dict)
    privacy_mode_active: PrivacyMode = PrivacyMode.PRIVATE
    interaction_mode_active: SessionMode = SessionMode.CHAT
    interaction_state: InteractionState = InteractionState.IDLE
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "active_modalities": [m.value for m in self.active_modalities],
            "environment": self.environment,
            "privacy_mode": self.privacy_mode.value,
            "interaction_mode": self.interaction_mode.value,
            "attention_state": self.attention_state,
            "spatial_reference": self.spatial_reference,
            "conversation_state": self.conversation_state,
            "authorization_state": self.authorization_state,
            "sensor_status": {k: v.__dict__ for k, v in self.sensor_status.items()},
            "privacy_mode_active": self.privacy_mode_active.value,
            "interaction_mode_active": self.interaction_mode_active.value,
            "interaction_state": self.interaction_state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# §10-13: Sensor Governance
# ---------------------------------------------------------------------------

class SensorPermission(str, enum.Enum):
    """Sensor permission levels."""
    GRANTED = "granted"
    DENIED = "denied"
    PENDING = "pending"
    NOT_REQUESTED = "not_requested"


@dataclass
class SensorGovernance:
    """Sensor governance state (§10-13)."""
    sensor_id: str
    modality: InputModality
    permission: SensorPermission = SensorPermission.NOT_REQUESTED
    session_scope: str = ""
    user_consent: bool = False
    data_classification: str = "internal"
    last_checked: float = 0.0
    policy_version: str = "1.0"


# ---------------------------------------------------------------------------
# §15-19: Speech Pipeline Models
# ---------------------------------------------------------------------------

class SpeechSegmentType(str, enum.Enum):
    """Type of speech segment."""
    USER_SPEECH = "user_speech"
    ASSISTANT_SPEECH = "assistant_speech"
    BACKGROUND = "background"
    UNKNOWN = "unknown"


@dataclass
class SpeechSegment:
    """A segment of speech from ASR."""
    segment_id: str = field(default_factory=lambda: new_id("seg"))
    text: str = ""
    confidence: float = 0.0
    language: str = "en"
    is_final: bool = False
    duration: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0
    speaker_id: Optional[str] = None
    segment_type: SpeechSegmentType = SpeechSegmentType.USER_SPEECH
    modality: InputModality = InputModality.VOICE
    confidence: float = 0.0
    segments: List[Dict[str, Any]] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "text": self.text,
            "confidence": self.confidence,
            "language": self.language,
            "is_final": self.is_final,
            "duration": self.duration,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "speaker_id": self.speaker_id,
            "segment_type": self.segment_type.value,
        }


# ---------------------------------------------------------------------------
# §20-22: Voice/TTS Models (re-export from voice models where possible)
# ---------------------------------------------------------------------------

@dataclass
class STTResult:
    """Speech-to-text result."""
    text: str = ""
    confidence: float = 0.0
    language: str = "en"
    is_final: bool = True
    duration: float = 0.0
    segments: List[Dict[str, Any]] = field(default_factory=list)
    error: str = ""
    is_partial: bool = False
    modality: InputModality = InputModality.VOICE


@dataclass
class TTSResult:
    """Text-to-speech result."""
    audio_data: bytes = b""
    text: str = ""
    duration: float = 0.0
    format: str = "wav"
    sample_rate: int = 24000
    error: str = ""
    voice_id: str = ""
    streaming: bool = False


@dataclass
class TTSStreamChunk:
    """Streaming TTS chunk."""
    chunk_id: str = field(default_factory=lambda: new_id("tts"))
    audio_data: bytes = b""
    text: str = ""
    is_final: bool = False
    sequence: int = 0
    timestamp: float = field(default_factory=_now)


# ---------------------------------------------------------------------------
# §24-34: Vision Engine Models
# ---------------------------------------------------------------------------

class VisionTask(str, enum.Enum):
    """Vision processing tasks."""
    OBJECT_DETECTION = "object_detection"
    OBJECT_TRACKING = "object_tracking"
    OCR = "ocr"
    SCENE_UNDERSTANDING = "scene_understanding"
    DOCUMENT_UNDERSTANDING = "document_understanding"
    UI_UNDERSTANDING = "ui_understanding"
    FACE_DETECTION = "face_detection"
    PERSON_DETECTION = "person_detection"
    POSE_ESTIMATION = "pose_estimation"
    GESTURE_DETECTION = "gesture_detection"
    SPATIAL_RELATIONSHIPS = "spatial_relationships"
    VISUAL_GROUNDING = "visual_grounding"
    VQA = "vqa"
    VISUAL_CHANGE_DETECTION = "visual_change_detection"


@dataclass
class VisionTaskRequest:
    """Request for a vision task."""
    task: VisionTask
    image_source: str = ""  # path, URL, base64, screen, camera
    question: str = ""  # for VQA
    region: Optional[Tuple[float, float, float, float]] = None  # x, y, w, h
    confidence_threshold: float = 0.5
    tracking: bool = False
    return_visualization: bool = False


@dataclass
class VisionResult:
    """Vision processing result."""
    task: VisionTask
    success: bool
    objects: List[Dict[str, Any]] = field(default_factory=list)  # label, confidence, bbox
    text: str = ""  # OCR text
    labels: List[str] = field(default_factory=list)
    caption: str = ""
    spatial_relations: List[Dict[str, Any]] = field(default_factory=list)
    processing_time_ms: float = 0.0
    error: Optional[str] = None
    visualization: Optional[bytes] = None


# ---------------------------------------------------------------------------
# §35-44: Gaze/Gesture/Hand Tracking
# ---------------------------------------------------------------------------

@dataclass
class GazeData:
    """Gaze tracking data (§35)."""
    gaze_ray_origin: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    gaze_ray_direction: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    fixation_point: Optional[Tuple[float, float, float]] = None
    fixation_duration: float = 0.0
    saccade: bool = False
    gaze_target: Optional[str] = None
    gaze_confidence: float = 0.0
    head_direction: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    timestamp: float = field(default_factory=_now)
    modality: InputModality = InputModality.GAZE
    confidence: float = 0.0


@dataclass
class GestureData:
    """Gesture recognition data (§40)."""
    gesture_type: str = ""  # POINT, PINCH, GRAB, RELEASE, SWIPE, ROTATE, ZOOM, WAVE, STOP, CONFIRM, CANCEL
    hand: str = "right"  # left, right, both
    hand_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    hand_orientation: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    finger_positions: List[Tuple[float, float, float]] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: float = field(default_factory=_now)
    modality: InputModality = InputModality.GESTURE
    confidence: float = 0.0
    hand_pose: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HandTrackingData:
    """Hand tracking data (§39)."""
    hand_id: str = ""
    hand: str = "right"
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    orientation: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    finger_positions: List[Tuple[float, float, float]] = field(default_factory=list)
    finger_tips: List[Tuple[float, float, float]] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: float = field(default_factory=_now)
    modality: InputModality = InputModality.HAND_TRACKING
    confidence: float = 0.0


@dataclass
class HeadPoseData:
    """Head pose data (§43)."""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    orientation: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)  # quaternion
    euler_angles: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # pitch, yaw, roll
    looking_direction: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    confidence: float = 0.0
    timestamp: float = field(default_factory=_now)
    modality: InputModality = InputModality.HEAD_POSE
    confidence: float = 0.0


# ---------------------------------------------------------------------------
# §44-45: Attention Model
# ---------------------------------------------------------------------------

@dataclass
class AttentionState:
    """Attention state (§44)."""
    gaze_target: Optional[str] = None
    head_target: Optional[str] = None
    speech_target: Optional[str] = None
    active_window: Optional[str] = None
    interaction_target: Optional[str] = None
    environment_target: Optional[str] = None
    confidence: float = 0.0
    timestamp: float = field(default_factory=_now)


# ---------------------------------------------------------------------------
# §46-47: Intent Resolution
# ---------------------------------------------------------------------------

@dataclass
class IntentHypothesis:
    """Intent hypothesis from multimodal fusion (§46)."""
    intent: str = ""
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    ambiguity: float = 0.0
    alternative_interpretations: List[str] = field(default_factory=list)
    modality_contributions: Dict[InputModality, float] = field(default_factory=dict)
    source_events: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# §49-50: Clarification
# ---------------------------------------------------------------------------

@dataclass
class ClarificationRequest:
    """Clarification request (§49)."""
    request_id: str = field(default_factory=lambda: new_id("clarify"))
    question: str = ""
    options: List[str] = field(default_factory=list)
    context: str = ""
    ambiguity_type: str = "ambiguous_intent"
    target_intent_ids: List[str] = field(default_factory=list)
    urgency: str = "normal"


@dataclass
class ClarificationResponse:
    """Clarification response."""
    request_id: str = ""
    selected_option: Optional[int] = None
    custom_response: str = ""
    timestamp: float = field(default_factory=_now)


# ---------------------------------------------------------------------------
# §52-61: Environment & Spatial Models
# ---------------------------------------------------------------------------

class SpatialRelation(str, enum.Enum):
    LEFT_OF = "left_of"
    RIGHT_OF = "right_of"
    ABOVE = "above"
    BELOW = "below"
    INSIDE = "inside"
    CONTAINS = "contains"
    NEAR = "near"
    FAR = "far"
    IN_FRONT_OF = "in_front_of"
    BEHIND = "behind"
    TOUCHING = "touching"
    OVERLAPPING = "overlapping"
    ATTACHED_TO = "attached_to"
    FACING = "facing"
    POINTING_TO = "pointing_to"
    LOOKING_AT = "looking_at"
    MOVING_TOWARD = "moving_toward"
    MOVING_AWAY = "moving_away"


@dataclass
class SpatialEntity:
    """An entity in the spatial world model."""
    entity_id: str = field(default_factory=lambda: new_id("ent"))
    entity_type: str = ""  # object, person, device, surface, landmark, room
    label: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    orientation: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    bounding_box: Optional[Tuple[float, float, float, float, float, float]] = None  # x,y,z,w,h,d
    semantic_label: str = ""
    confidence: float = 1.0
    last_observed: float = field(default_factory=_now)
    properties: Dict[str, Any] = field(default_factory=dict)
    relations: List[Tuple[str, SpatialRelation, str]] = field(default_factory=list)  # (subject, relation, object)


@dataclass
class SpatialWorldModel:
    """Spatial world model (§54)."""
    entities: Dict[str, SpatialEntity] = field(default_factory=dict)
    rooms: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    surfaces: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    paths: Dict[str, List[Tuple[float, float, float]]] = field(default_factory=dict)
    zones: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    coordinate_frames: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    last_updated: float = field(default_factory=_now)
    version: int = 1

    def add_entity(self, entity: SpatialEntity) -> None:
        self.entities[entity.entity_id] = entity
        self.version += 1

    def remove_entity(self, entity_id: str) -> bool:
        if entity_id in self.entities:
            del self.entities[entity_id]
            self.version += 1
            return True
        return False

    def get_entity(self, entity_id: str) -> Optional[SpatialEntity]:
        return self.entities.get(entity_id)

    def query_near(self, position: Tuple[float, float, float], radius: float) -> List[SpatialEntity]:
        results = []
        for entity in self.entities.values():
            if entity.position:
                dist = sum((a - b) ** 2 for a, b in zip(entity.position[:3], position[:3])) ** 0.5
                if dist <= radius:
                    results.append(entity)
        return results


@dataclass
class LandmarkMemory:
    """Landmark memory (§58)."""
    landmark_id: str = field(default_factory=lambda: new_id("lm"))
    name: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    visual_features: Dict[str, Any] = field(default_factory=dict)
    semantic_meaning: str = ""
    confidence: float = 1.0
    last_seen: float = field(default_factory=_now)
    visit_count: int = 0


@dataclass
class RouteMemory:
    """Route memory (§59)."""
    route_id: str = field(default_factory=lambda: new_id("route"))
    origin: str = ""
    destination: str = ""
    path: List[Tuple[float, float, float]] = field(default_factory=list)
    waypoints: List[Tuple[float, float, float]] = field(default_factory=list)
    obstacles: List[str] = field(default_factory=list)
    estimated_time: float = 0.0
    confidence: float = 1.0
    last_used: float = field(default_factory=_now)
    use_count: int = 0


@dataclass
class SurveyMemory:
    """Survey memory (§60)."""
    survey_id: str = field(default_factory=lambda: new_id("survey"))
    room_graph: Dict[str, List[str]] = field(default_factory=dict)
    building_graph: Dict[str, List[str]] = field(default_factory=dict)
    device_graph: Dict[str, List[str]] = field(default_factory=dict)
    workspace_graph: Dict[str, List[str]] = field(default_factory=dict)
    last_updated: float = field(default_factory=_now)


# ---------------------------------------------------------------------------
# §63-70: Temporal Fusion & Timeline
# ---------------------------------------------------------------------------

@dataclass
class TimestampedEvent:
    """A timestamped event for temporal fusion."""
    event_id: str = field(default_factory=lambda: new_id("tevt"))
    event_type: EventType = EventType.VISION_FRAME
    modality: InputModality = InputModality.UNKNOWN
    timestamp: float = field(default_factory=_now)
    source: EventSource = EventSource.UNKNOWN
    data: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    source_device: str = ""


@dataclass
class MultimodalTimeline:
    """Multimodal timeline (§68)."""
    timeline_id: str = field(default_factory=lambda: new_id("tl"))
    session_id: str = ""
    events: List[TimestampedEvent] = field(default_factory=list)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def add_event(self, event: TimestampedEvent) -> None:
        self.events.append(event)
        self.events.sort(key=lambda e: e.timestamp)
        self.updated_at = _now()

    def get_events_in_range(self, start: float, end: float) -> List[TimestampedEvent]:
        return [e for e in self.events if start <= e.timestamp <= end]

    def get_recent(self, seconds: float = 60.0) -> List[TimestampedEvent]:
        now = _now()
        return [e for e in self.events if now - e.timestamp <= seconds]


# ---------------------------------------------------------------------------
# §71-78: Visual/Voice Memory + Research
# ---------------------------------------------------------------------------

@dataclass
class VisualMemoryEntry:
    """Visual memory entry (§194)."""
    memory_id: str = field(default_factory=lambda: new_id("vmem"))
    content: str = ""
    image_source: str = ""
    caption: str = ""
    objects: List[str] = field(default_factory=list)
    scene_summary: str = ""
    confidence: float = 1.0
    timestamp: float = field(default_factory=_now)
    authorized: bool = False


@dataclass
class VoiceMemoryEntry:
    """Voice interaction memory entry."""
    memory_id: str = field(default_factory=lambda: new_id("vmem"))
    transcript: str = ""
    intent: str = ""
    response: str = ""
    modality: InputModality = InputModality.VOICE
    confidence: float = 1.0
    timestamp: float = field(default_factory=_now)
    authorized: bool = False


# ---------------------------------------------------------------------------
# §115-120: Visual/Audio Prompt Injection Defense
# ---------------------------------------------------------------------------

@dataclass
class UntrustedContent:
    """External content classified as untrusted (§141-146)."""
    content_id: str = field(default_factory=lambda: new_id("uct"))
    source: str = ""  # webpage, screen, document, audio, qr, image
    content_type: str = ""  # text, image, audio, qr, barcode
    raw_content: str = ""
    classification: str = "untrusted"  # untrusted, suspicious, benign
    detected_patterns: List[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: float = field(default_factory=_now)
    treated_as_data: bool = True  # never as authority


# ---------------------------------------------------------------------------
# §147-150: Multimodal Command Authenticity
# ---------------------------------------------------------------------------

@dataclass
class MultimodalCommand:
    """A multimodal command with full authenticity metadata (§147)."""
    command_id: str = field(default_factory=lambda: new_id("cmd"))
    source: str = ""  # voice, gaze, gesture, touch, multimodal
    speaker: str = ""
    addressed_to: str = ""  # aetheros, other_person, media, uncertain
    confidence: float = 0.0
    speaker_confidence: float = 0.0
    addressed_to_confidence: float = 0.0
    authentication: str = ""  # none, voice, biometric, mfa
    authorization: str = ""  # none, pending, approved, denied
    source_modalities: List[InputModality] = field(default_factory=list)
    raw_input: str = ""
    timestamp: float = field(default_factory=_now)


# ---------------------------------------------------------------------------
# §158-162: Device Capability Matrix & Discovery
# ---------------------------------------------------------------------------

@dataclass
class DeviceCapability:
    """Device capability entry (§158)."""
    device_id: str
    device_type: str = ""
    modalities: List[InputModality] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    performance: Dict[str, float] = field(default_factory=dict)
    privacy: str = "unknown"
    trust: str = "unknown"
    connection: str = ""
    firmware: str = ""
    manufacturer: str = ""
    model: str = ""
    serial: str = ""
    status: str = "unknown"


# ---------------------------------------------------------------------------
# §157-162: Device Memory/Continuity
# ---------------------------------------------------------------------------

@dataclass
class DeviceMemoryEntry:
    """Device-specific memory entry."""
    device_id: str
    key: str
    value: Any = None
    at: float = field(default_factory=_now)
    ttl_s: float = 3600.0
    environment: str = ""
    provenance: str = "observation"
    confidence: float = 0.8

    def alive(self) -> bool:
        from time import time
        return time.time() - self.at < self.ttl_s


# ---------------------------------------------------------------------------
# §170-172: Knowledge Graph
# ---------------------------------------------------------------------------

@dataclass
class KnowledgeGraphEntity:
    """Entity in the multimodal knowledge graph (§197)."""
    entity_id: str
    entity_type: str  # Person, Device, Room, Object, Document, Screen, Application, Task, Robot, Location, Event
    attributes: Dict[str, Any] = field(default_factory=dict)
    relationships: List[Tuple[str, str, str]] = field(default_factory=list)  # (subject, relation, object)


@dataclass
class MultimodalKnowledgeGraph:
    """Multimodal knowledge graph (§197)."""
    entities: Dict[str, KnowledgeGraphEntity] = field(default_factory=dict)
    relations: List[Tuple[str, str, str]] = field(default_factory=list)

    def add_entity(self, entity: KnowledgeGraphEntity) -> None:
        self.entities[entity.entity_id] = entity

    def add_relation(self, subject: str, relation: str, object_: str, provenance: str = "") -> None:
        self.relations.append((subject, relation, object_))

    def query(self, subject: str = "", relation: str = "", object_: str = "") -> List[Tuple[str, str, str]]:
        results = []
        for s, r, o in self.relations:
            if (not subject or s == subject) and (not relation or r == relation) and (not object_ or o == object_):
                results.append((s, r, o))
        return results


# ---------------------------------------------------------------------------
# §199-201: Discovery/Validation
# ---------------------------------------------------------------------------

class RealityConfidence(str, enum.Enum):
    OBSERVED = "observed"
    SUPPORTED = "supported"
    INFERRED = "inferred"
    PREDICTED = "predicted"
    UNKNOWN = "unknown"
    CONTRADICTED = "contradicted"


@dataclass
class MultimodalFact:
    """A multimodal fact with evidence chain (§289)."""
    fact_id: str = field(default_factory=lambda: new_id("fact"))
    claim: str = ""
    evidence_chain: List[str] = field(default_factory=list)
    confidence: RealityConfidence = RealityConfidence.UNKNOWN
    sources: List[str] = field(default_factory=list)
    modality_contributions: Dict[InputModality, float] = field(default_factory=dict)
    contradicted_by: List[str] = field(default_factory=list)
    last_verified: float = field(default_factory=_now)


# ---------------------------------------------------------------------------
# §294-293: Language/Explanation
# ---------------------------------------------------------------------------

@dataclass
class MultimodalExplanation:
    """Explanation for a multimodal decision (§294)."""
    question: str = ""
    answer: str = ""
    evidence_chain: List[str] = field(default_factory=list)
    confidence: str = "uncertain"
    sources: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# §354-356: Final System Loop
# ---------------------------------------------------------------------------

@dataclass
class RealityLoopState:
    """State of the reality processing loop (§355)."""
    phase: str = "SENSE"
    iteration: int = 0
    current_task: str = ""
    last_update: float = field(default_factory=_now)
    metrics: Dict[str, float] = field(default_factory=dict)


def new_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _now() -> float:
    return time.time()


__all__ = [
    # Modalities
    "InputModality",
    "OutputModality",
    # Event types
    "EventType",
    "EventSource",
    "EventConfidence",
    # Event
    "MultimodalEvent",
    # Session
    "MultimodalSession",
    "SessionMode",
    "SensorState",
    "SensorStatus",
    "PrivacyMode",
    "InteractionState",
    # Sensor governance
    "SensorPermission",
    "SensorGovernance",
    "SensorStatus",
    # Speech
    "SpeechSegmentType",
    "SpeechSegment",
    "STTResult",
    "TTSResult",
    "TTSStreamChunk",
    # Vision
    "VisionTask",
    "VisionTaskRequest",
    "VisionResult",
    # Gaze/Gesture/Hand/Head
    "GazeData",
    "GestureData",
    "HandTrackingData",
    "HeadPoseData",
    # Attention
    "AttentionState",
    # Intent
    "IntentHypothesis",
    # Clarification
    "ClarificationRequest",
    "ClarificationResponse",
    # Spatial
    "SpatialRelation",
    "SpatialEntity",
    "SpatialWorldModel",
    "LandmarkMemory",
    "RouteMemory",
    "SurveyMemory",
    # Timeline
    "TimestampedEvent",
    "MultimodalTimeline",
    # Memory
    "VisualMemoryEntry",
    "VoiceMemoryEntry",
    # Untrusted content
    "UntrustedContent",
    # Command
    "MultimodalCommand",
    # Device
    "DeviceCapability",
    "DeviceMemoryEntry",
    # Knowledge graph
    "KnowledgeGraphEntity",
    "MultimodalKnowledgeGraph",
    # Discovery
    "RealityConfidence",
    "MultimodalFact",
    # Explanation
    "MultimodalExplanation",
    # Loop
    "RealityLoopState",
    # Utilities
    "new_id",
]


import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple