"""Universal Media Abstraction for Aetheros Multimodal OS.

Implements Phase 1 of Master Prompt 10: a normalized representation for every
modality the system can perceive — text, image, audio, video, document, screen,
camera, and structured data.

Design rules (from the MASTER 10 contract):
- Model-agnostic and provider-agnostic.
- Every media object carries: media_id, type, mime_type, size, duration,
  dimensions, source, timestamp, metadata, hash, permissions, sensitivity,
  storage_location, provenance.
- Never store raw media content inside the object when a path/URL suffices.
- Sensitivity defaults to PRIVATE; external sharing is policy-checked.
- Provenance is append-only: every processing step is recorded.

This module deliberately does not import agent.memory_os (that module is an
unwired island). Media storage is profile-aware via aetheros_constants.
"""

from __future__ import annotations

import hashlib
import logging
import mimetypes
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class MediaType(Enum):
    """Modalities understood by the Universal Media Abstraction."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    SCREEN = "screen"
    CAMERA = "camera"
    STRUCTURED_DATA = "structured_data"


class SensitivityLevel(Enum):
    """Privacy classification for media content (Phase 71)."""

    PUBLIC = "public"          # Free to share/process with external providers
    PRIVATE = "private"        # Personal data; requires user consent to share
    SENSITIVE = "sensitive"    # PII, credentials, financial data, etc.
    RESTRICTED = "restricted"  # Highly restricted; legal/compliance constraints


class PermissionLevel(IntEnum):
    """Access control for a media object (bitmask)."""

    NONE = 0
    READ = 1
    WRITE = 2
    EXECUTE = 4
    SHARE = 8
    READ_WRITE = READ | WRITE
    READ_WRITE_EXECUTE = READ | WRITE | EXECUTE
    FULL = READ | WRITE | EXECUTE | SHARE


class EmbeddingModel(Enum):
    """Known embedding models for media embeddings."""

    CLIP_VIT_B32 = "clip-vit-b32"
    CLIP_VIT_L14 = "clip-vit-l14"
    OPENAI_EMBED_3_SMALL = "text-embedding-3-small"
    OPENAI_EMBED_3_LARGE = "text-embedding-3-large"
    OPENAI_EMBED_ADA_002 = "text-embedding-ada-002"
    VOYAGE_2 = "voyage-2"
    VOYAGE_3 = "voyage-3"
    COHERE_EMBED_V3 = "cohere-embed-v3"
    GOOGLE_EMBED_001 = "text-embedding-001"
    CUSTOM = "custom"


@dataclass
class EmbeddingRef:
    """Reference to a vector embedding for this media object."""

    vector_id: str                    # ID in vector store
    model: Union[EmbeddingModel, str] # Embedding model used
    dimensions: int                   # Vector dimensions
    scope: str = "global"             # global | session | task
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class VideoFrameRef:
    """Reference to a sampled video frame."""

    frame_index: int                  # Sequential frame number
    timestamp: float                  # Media timestamp (seconds)
    media_id: str                     # MediaObject ID of the frame image
    is_keyframe: bool = False
    is_scene_change: bool = False
    sampling_method: str = "uniform"  # uniform | scene_change | event | adaptive
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CrossModalRef:
    """Reference linking this media to another modality."""

    target_media_id: str              # MediaObject ID of linked media
    relation: str                     # "transcript_of" | "frame_of" | "ocr_of" | "describes" | "annotates"
    target_timestamp: float = 0.0     # Timestamp in target media (if applicable)
    target_region: Optional[Dict[str, int]] = None  # x, y, w, h in target
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MediaObject:
    """Normalized representation of any media content (Phase 1)."""

    media_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MediaType = MediaType.TEXT
    mime_type: str = "text/plain"
    size: int = 0                     # bytes
    duration: float = 0.0             # seconds (time-based media)
    dimensions: Dict[str, int] = field(default_factory=dict)  # width/height/...
    source: str = ""                  # local path, URL, device id, ...
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    hash: str = ""                    # SHA-256 content hash
    permissions: PermissionLevel = PermissionLevel.READ
    sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE
    storage_location: str = ""        # where the bytes physically live
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    # Phase 1 extensions
    embeddings: List[EmbeddingRef] = field(default_factory=list)
    video_frames: List[VideoFrameRef] = field(default_factory=list)
    cross_modal_refs: List[CrossModalRef] = field(default_factory=list)
    budget: Dict[str, float] = field(default_factory=dict)  # modality budget tracking
    processing_hints: Dict[str, Any] = field(default_factory=dict)  # hints for downstream processors

    def __post_init__(self) -> None:
        if isinstance(self.type, str):
            self.type = MediaType(self.type)
        if isinstance(self.permissions, int) and not isinstance(self.permissions, PermissionLevel):
            self.permissions = PermissionLevel(self.permissions)
        if isinstance(self.sensitivity, str):
            self.sensitivity = SensitivityLevel(self.sensitivity)
        if self.mime_type == "text/plain" and self.source:
            guessed, _ = mimetypes.guess_type(self.source)
            if guessed:
                self.mime_type = guessed
        if not self.hash and self.source and os.path.isfile(self.source):
            self.hash = self._calculate_file_hash()
        # Convert embedding refs if they came as dicts
        if self.embeddings and isinstance(self.embeddings[0], dict):
            self.embeddings = [EmbeddingRef(**e) if isinstance(e, dict) else e for e in self.embeddings]
        if self.video_frames and isinstance(self.video_frames[0], dict):
            self.video_frames = [VideoFrameRef(**v) if isinstance(v, dict) else v for v in self.video_frames]
        if self.cross_modal_refs and isinstance(self.cross_modal_refs[0], dict):
            self.cross_modal_refs = [CrossModalRef(**c) if isinstance(c, dict) else c for c in self.cross_modal_refs]

    # -- content -----------------------------------------------------------
    def _calculate_file_hash(self) -> str:
        try:
            h = hashlib.sha256()
            with open(self.source, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    h.update(chunk)
            return h.hexdigest()
        except OSError as e:
            logger.warning("Could not hash %s: %s", self.source, e)
            return ""

    # -- serialization -----------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "media_id": self.media_id,
            "type": self.type.value,
            "mime_type": self.mime_type,
            "size": self.size,
            "duration": self.duration,
            "dimensions": self.dimensions,
            "source": self.source,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "hash": self.hash,
            "permissions": self.permissions.value,
            "sensitivity": self.sensitivity.value,
            "storage_location": self.storage_location,
            "provenance": self.provenance,
            "embeddings": [e.__dict__ if hasattr(e, '__dict__') else e for e in self.embeddings],
            "video_frames": [v.__dict__ if hasattr(v, '__dict__') else v for v in self.video_frames],
            "cross_modal_refs": [c.__dict__ if hasattr(c, '__dict__') else c for c in self.cross_modal_refs],
            "budget": self.budget,
            "processing_hints": self.processing_hints,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MediaObject":
        obj = cls()
        obj.media_id = data.get("media_id") or str(uuid.uuid4())
        obj.type = MediaType(data.get("type", MediaType.TEXT.value))
        obj.mime_type = data.get("mime_type", "text/plain")
        obj.size = data.get("size", 0)
        obj.duration = data.get("duration", 0.0)
        obj.dimensions = data.get("dimensions", {}) or {}
        obj.source = data.get("source", "")
        obj.timestamp = data.get("timestamp", time.time())
        obj.metadata = data.get("metadata", {}) or {}
        obj.hash = data.get("hash", "")
        obj.permissions = PermissionLevel(data.get("permissions", PermissionLevel.READ.value))
        obj.sensitivity = SensitivityLevel(data.get("sensitivity", SensitivityLevel.PRIVATE.value))
        obj.storage_location = data.get("storage_location", "")
        obj.provenance = data.get("provenance", []) or []
        obj.embeddings = data.get("embeddings", []) or []
        obj.video_frames = data.get("video_frames", []) or []
        obj.cross_modal_refs = data.get("cross_modal_refs", []) or []
        obj.budget = data.get("budget", {}) or {}
        obj.processing_hints = data.get("processing_hints", {}) or {}
        return obj

    # -- provenance --------------------------------------------------------
    def add_provenance_step(
        self,
        step: str,
        actor: str = "system",
        timestamp: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a step in the chain of custody (Phase 57)."""
        self.provenance.append(
            {
                "step": step,
                "actor": actor,
                "timestamp": timestamp or time.time(),
                "metadata": metadata or {},
            }
        )

    # -- embeddings ------------------------------------------------------
    def add_embedding(
        self,
        vector_id: str,
        model: Union[EmbeddingModel, str],
        dimensions: int,
        scope: str = "global",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EmbeddingRef:
        """Add an embedding reference (Phase 55)."""
        if isinstance(model, EmbeddingModel):
            model_val = model
        else:
            model_val = model
        ref = EmbeddingRef(
            vector_id=vector_id,
            model=model_val,
            dimensions=dimensions,
            scope=scope,
            metadata=metadata or {},
        )
        self.embeddings.append(ref)
        return ref

    def get_embeddings(self, scope: Optional[str] = None) -> List[EmbeddingRef]:
        """Get embeddings, optionally filtered by scope."""
        if scope is None:
            return list(self.embeddings)
        return [e for e in self.embeddings if e.scope == scope]

    # -- video frames ----------------------------------------------------
    def add_video_frame(
        self,
        frame_index: int,
        timestamp: float,
        frame_media_id: str,
        is_keyframe: bool = False,
        is_scene_change: bool = False,
        sampling_method: str = "uniform",
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VideoFrameRef:
        """Add a video frame reference (Phase 33)."""
        ref = VideoFrameRef(
            frame_index=frame_index,
            timestamp=timestamp,
            media_id=frame_media_id,
            is_keyframe=is_keyframe,
            is_scene_change=is_scene_change,
            sampling_method=sampling_method,
            confidence=confidence,
            metadata=metadata or {},
        )
        self.video_frames.append(ref)
        return ref

    def get_keyframes(self) -> List[VideoFrameRef]:
        """Get only keyframes."""
        return [f for f in self.video_frames if f.is_keyframe]

    def get_scene_changes(self) -> List[VideoFrameRef]:
        """Get only scene change frames."""
        return [f for f in self.video_frames if f.is_scene_change]

    def get_frames_in_range(self, start: float, end: float) -> List[VideoFrameRef]:
        """Get frames within a timestamp range."""
        return [f for f in self.video_frames if start <= f.timestamp <= end]

    # -- cross-modal references ------------------------------------------
    def add_cross_modal_ref(
        self,
        target_media_id: str,
        relation: str,
        target_timestamp: float = 0.0,
        target_region: Optional[Dict[str, int]] = None,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CrossModalRef:
        """Add a cross-modal reference (Phase 37-38)."""
        ref = CrossModalRef(
            target_media_id=target_media_id,
            relation=relation,
            target_timestamp=target_timestamp,
            target_region=target_region,
            confidence=confidence,
            metadata=metadata or {},
        )
        self.cross_modal_refs.append(ref)
        return ref

    def get_cross_modal_refs(self, relation: Optional[str] = None) -> List[CrossModalRef]:
        """Get cross-modal references, optionally filtered by relation."""
        if relation is None:
            return list(self.cross_modal_refs)
        return [r for r in self.cross_modal_refs if r.relation == relation]

    # -- budget tracking -------------------------------------------------
    def set_budget(self, key: str, value: float) -> None:
        """Set a modality budget value (Phase 51)."""
        self.budget[key] = value

    def get_budget(self, key: str, default: float = 0.0) -> float:
        """Get a modality budget value."""
        return self.budget.get(key, default)

    def consume_budget(self, key: str, amount: float) -> bool:
        """Consume budget amount. Returns True if budget allows."""
        current = self.budget.get(key, 0.0)
        if current + amount <= self.budget.get(f"max_{key}", float('inf')):
            self.budget[key] = current + amount
            return True
        return False

    # -- processing hints ------------------------------------------------
    def set_hint(self, key: str, value: Any) -> None:
        """Set a processing hint for downstream processors."""
        self.processing_hints[key] = value

    def get_hint(self, key: str, default: Any = None) -> Any:
        """Get a processing hint."""
        return self.processing_hints.get(key, default)

    # -- privacy -----------------------------------------------------------
    def is_sensitive(self) -> bool:
        return self.sensitivity in (SensitivityLevel.SENSITIVE, SensitivityLevel.RESTRICTED)

    def can_be_shared_externally(self, policy: Optional[Dict[str, Any]] = None) -> bool:
        """Whether external processing is allowed, per optional policy override.

        Default: PUBLIC media may go external.  An explicit policy may widen or
        narrow this (used by the provider privacy router, Phase 72).
        """
        if policy:
            allow = policy.get("allow_external_sensitivity", [])
            if self.sensitivity.value in allow:
                return True
            return self.sensitivity == SensitivityLevel.PUBLIC
        return self.sensitivity == SensitivityLevel.PUBLIC

    def get_size_mb(self) -> float:
        return self.size / (1024.0 * 1024.0)

    def get_duration_hms(self) -> str:
        hours = int(self.duration // 3600)
        minutes = int((self.duration % 3600) // 60)
        seconds = int(self.duration % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"MediaObject(id={self.media_id[:8]}, type={self.type.value}, "
            f"mime={self.mime_type}, size={self.size}, sens={self.sensitivity.value})"
        )


# ---------------------------------------------------------------------------
# Factory functions (keep public names stable from the earlier draft)
# ---------------------------------------------------------------------------


def create_text_media(
    content: str,
    source: str = "",
    sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE,
) -> MediaObject:
    media = MediaObject(
        type=MediaType.TEXT,
        mime_type="text/plain",
        size=len(content.encode("utf-8")),
        source=source,
        sensitivity=sensitivity,
    )
    media.metadata["content"] = content
    return media


def _guess_image_dimensions(source: str) -> Dict[str, int]:
    try:
        from PIL import Image

        with Image.open(source) as img:
            return {"width": img.width, "height": img.height}
    except Exception as e:  # Pillow missing or unreadable
        logger.warning("Could not read image dimensions for %s: %s", source, e)
        return {}


def _guess_audio_duration(source: str) -> float:
    try:
        from mutagen import File as MFile

        m = MFile(source)
        if m is not None and getattr(m, "info", None) is not None:
            return float(getattr(m.info, "length", 0.0))
    except Exception as e:  # mutagen optional / file unsupported
        logger.debug("Could not read audio duration for %s: %s", source, e)
    return 0.0


def create_image_media(
    source: str,
    sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE,
    metadata: Optional[Dict[str, Any]] = None,
) -> MediaObject:
    if not os.path.isfile(source):
        raise FileNotFoundError(f"Image file not found: {source}")
    media = MediaObject(
        type=MediaType.IMAGE,
        size=os.path.getsize(source),
        source=source,
        dimensions=_guess_image_dimensions(source),
        sensitivity=sensitivity,
        metadata=metadata or {},
    )
    guessed, _ = mimetypes.guess_type(source)
    if guessed and guessed.startswith("image/"):
        media.mime_type = guessed
    return media


def create_image_media_from_bytes(
    data: bytes,
    mime_type: str = "image/png",
    sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE,
    metadata: Optional[Dict[str, Any]] = None,
    source: str = "",
) -> MediaObject:
    """Create image media from raw bytes (for screenshots, generated images)."""
    import tempfile
    ext = mimetypes.guess_extension(mime_type) or ".png"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        f.write(data)
        path = f.name
    media = MediaObject(
        type=MediaType.IMAGE,
        size=len(data),
        source=path,
        dimensions={},  # Will be filled by processor
        sensitivity=sensitivity,
        metadata=metadata or {},
        mime_type=mime_type,
        storage_location=path,
    )
    media.add_provenance_step("created_from_bytes", actor="factory")
    return media


def create_audio_media(
    source: str,
    sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE,
    metadata: Optional[Dict[str, Any]] = None,
) -> MediaObject:
    if not os.path.isfile(source):
        raise FileNotFoundError(f"Audio file not found: {source}")
    media = MediaObject(
        type=MediaType.AUDIO,
        size=os.path.getsize(source),
        source=source,
        duration=_guess_audio_duration(source),
        sensitivity=sensitivity,
        metadata=metadata or {},
    )
    guessed, _ = mimetypes.guess_type(source)
    if guessed and guessed.startswith("audio/"):
        media.mime_type = guessed
    return media


def create_video_media(
    source: str,
    sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE,
    metadata: Optional[Dict[str, Any]] = None,
) -> MediaObject:
    if not os.path.isfile(source):
        raise FileNotFoundError(f"Video file not found: {source}")
    media = MediaObject(
        type=MediaType.VIDEO,
        size=os.path.getsize(source),
        source=source,
        sensitivity=sensitivity,
        metadata=metadata or {},
    )
    guessed, _ = mimetypes.guess_type(source)
    if guessed and guessed.startswith("video/"):
        media.mime_type = guessed
    # Best-effort metadata via ffprobe if available
    try:
        import subprocess
        import shutil
        import json

        probe = shutil.which("ffprobe")
        if probe:
            out = subprocess.run(
                [probe, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", source],
                capture_output=True, text=True, timeout=10,
            )
            info = json.loads(out.stdout or "{}")
            fmt = info.get("format", {})
            duration = float(fmt.get("duration", 0.0) or 0.0)
            if duration:
                media.duration = duration
            for stream in info.get("streams", []):
                if stream.get("codec_type") == "video":
                    media.dimensions = {
                        "width": int(stream.get("width", 0) or 0),
                        "height": int(stream.get("height", 0) or 0),
                        "fps": int(round(float(stream.get("avg_frame_rate", "0").split("/")[0] or 0) / float(
                            stream.get("avg_frame_rate", "1").split("/")[1] or 1)
                        ))
                        if stream.get("avg_frame_rate") else 0,
                    }
                    media.metadata["codec"] = stream.get("codec_name", "")
                    media.metadata["has_audio"] = any(
                        s.get("codec_type") == "audio" for s in info.get("streams", [])
                    )
                    media.metadata["codec_long_name"] = stream.get("codec_long_name", "")
                    media.metadata["bit_rate"] = stream.get("bit_rate", "")
                    # Estimate total frames
                    if media.dimensions.get("fps", 0) > 0 and duration > 0:
                        media.metadata["estimated_frames"] = int(media.dimensions["fps"] * duration)
    except Exception as e:
        logger.debug("Could not read video metadata for %s: %s", source, e)
    return media


def create_video_media_from_frames(
    frame_media_ids: List[str],
    timestamps: List[float],
    sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE,
    metadata: Optional[Dict[str, Any]] = None,
) -> MediaObject:
    """Create a virtual video media object from frame references (Phase 33)."""
    media = MediaObject(
        type=MediaType.VIDEO,
        size=0,  # Virtual - no single file
        source="virtual://frames",
        sensitivity=sensitivity,
        metadata=metadata or {},
    )
    media.duration = timestamps[-1] if timestamps else 0.0
    for i, (frame_id, ts) in enumerate(zip(frame_media_ids, timestamps)):
        media.add_video_frame(
            frame_index=i,
            timestamp=ts,
            frame_media_id=frame_id,
            sampling_method="event",
        )
    return media


def create_document_media(
    source: str,
    sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE,
    metadata: Optional[Dict[str, Any]] = None,
) -> MediaObject:
    if not os.path.isfile(source):
        raise FileNotFoundError(f"Document file not found: {source}")
    media = MediaObject(
        type=MediaType.DOCUMENT,
        size=os.path.getsize(source),
        source=source,
        sensitivity=sensitivity,
        metadata=metadata or {},
    )
    guessed, _ = mimetypes.guess_type(source)
    if guessed:
        media.mime_type = guessed
    return media


def create_screen_media(
    source: str = "",
    sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE,
    metadata: Optional[Dict[str, Any]] = None,
    capture_mode: str = "full_screen",
    monitor: int = 0,
    region: Optional[List[int]] = None,
) -> MediaObject:
    media = MediaObject(
        type=MediaType.SCREEN,
        sensitivity=sensitivity,
        metadata=metadata or {},
    )
    media.metadata["capture_mode"] = capture_mode
    media.metadata["monitor"] = monitor
    if region:
        media.metadata["region"] = region
    if source:
        media.source = source
        if os.path.isfile(source):
            media.size = os.path.getsize(source)
            media.dimensions = _guess_image_dimensions(source)
            guessed, _ = mimetypes.guess_type(source)
            if guessed and guessed.startswith("image/"):
                media.mime_type = guessed
    return media


def create_camera_media(
    source: str = "",
    sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE,
    metadata: Optional[Dict[str, Any]] = None,
    camera_index: int = 0,
    capture_mode: str = "still",
) -> MediaObject:
    media = MediaObject(
        type=MediaType.CAMERA,
        sensitivity=sensitivity,
        metadata=metadata or {},
    )
    media.metadata["camera_index"] = camera_index
    media.metadata["capture_mode"] = capture_mode
    if source:
        media.source = source
    return media


def create_structured_data_media(
    data: Union[Dict[str, Any], List[Any], str],
    schema: Optional[Dict[str, Any]] = None,
    format: str = "json",
    sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE,
    metadata: Optional[Dict[str, Any]] = None,
) -> MediaObject:
    """Create structured data media with optional schema validation (Phase 18).

    Supported formats: 'json', 'csv', 'parquet', 'yaml'.
    Optional schema validation using JSON Schema (draft-07).
    """
    import json

    if format == "json":
        if isinstance(data, (dict, list)):
            payload = json.dumps(data)
        else:
            payload = str(data)
        mime_type = "application/json"
    elif format == "csv":
        import csv
        import io
        output = io.StringIO()
        if isinstance(data, list) and data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        elif isinstance(data, dict):
            writer = csv.DictWriter(output, fieldnames=data.keys())
            writer.writeheader()
            writer.writerow(data)
        payload = output.getvalue()
        mime_type = "text/csv"
    elif format == "yaml":
        import yaml
        payload = yaml.dump(data)
        mime_type = "application/yaml"
    elif format == "parquet":
        try:
            import pyarrow.parquet as pq
            import pyarrow as pa
            table = pa.Table.from_pandas(data) if hasattr(data, 'to_pandas') else pa.Table.from_pydict(data)
            import io
            buf = io.BytesIO()
            pq.write_table(table, buf)
            payload = buf.getvalue()
            mime_type = "application/parquet"
        except ImportError:
            raise ValueError("parquet format requires pyarrow")
    else:
        raise ValueError(f"Unsupported format: {format}")

    if isinstance(payload, str):
        payload_bytes = payload.encode("utf-8")
    else:
        payload_bytes = payload

    # Schema validation if provided
    if schema:
        try:
            import jsonschema
            jsonschema.validate(data, schema)
        except ImportError:
            logger.warning("jsonschema not installed, skipping schema validation")
        except jsonschema.exceptions.ValidationError as e:
            raise ValueError(f"Schema validation failed: {e}")

    media = MediaObject(
        type=MediaType.STRUCTURED_DATA,
        mime_type=mime_type,
        size=len(payload_bytes),
        sensitivity=sensitivity,
        metadata=metadata or {},
    )
    media.metadata["data"] = data
    media.metadata["format"] = format
    if schema:
        media.metadata["schema"] = schema
    return media


def create_stream_media(
    stream_id: str,
    stream_type: str,  # "audio" | "video" | "screen" | "camera"
    source: str = "",
    sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE,
    metadata: Optional[Dict[str, Any]] = None,
) -> MediaObject:
    """Create a media object representing a live stream (Phase 46)."""
    media = MediaObject(
        type=MediaType.VIDEO if stream_type in ("video", "screen", "camera") else MediaType.AUDIO,
        sensitivity=sensitivity,
        metadata=metadata or {},
    )
    media.metadata["stream_id"] = stream_id
    media.metadata["stream_type"] = stream_type
    media.metadata["is_live"] = True
    if source:
        media.source = source
    return media


# -- Media conversion utilities ----------------------------------------

def extract_frames_from_video(
    video: MediaObject,
    max_frames: int = 24,
    mode: str = "uniform",
) -> List[MediaObject]:
    """Extract frame references from a video (delegates to perception layer).
    
    Returns list of MediaObject references for each frame.
    Actual frame extraction happens in perception layer.
    """
    # This is a placeholder - actual extraction happens in perception.py
    # This just creates the frame reference structure
    frames = []
    if video.duration > 0 and max_frames > 0:
        if mode == "uniform":
            interval = video.duration / max_frames
            timestamps = [i * interval for i in range(max_frames)]
        else:
            timestamps = [0.0]  # fallback
        
        for i, ts in enumerate(timestamps):
            frame_media = MediaObject(
                type=MediaType.IMAGE,
                source=f"frame://{video.media_id}/{i}",
                timestamp=ts,
                metadata={
                    "source_video_id": video.media_id,
                    "frame_index": i,
                    "sampling_mode": mode,
                },
            )
            frames.append(frame_media)
            video.add_video_frame(
                frame_index=i,
                timestamp=ts,
                frame_media_id=frame_media.media_id,
                sampling_method=mode,
            )
    return frames


def merge_media_objects(
    primary: MediaObject,
    *others: MediaObject,
    relation: str = "supplements",
) -> MediaObject:
    """Merge multiple media objects into a composite with cross-modal refs."""
    for other in others:
        primary.add_cross_modal_ref(
            target_media_id=other.media_id,
            relation=relation,
            confidence=1.0,
            metadata={"merged_at": time.time()},
        )
        # Merge budgets
        for k, v in other.budget.items():
            primary.budget[k] = primary.budget.get(k, 0.0) + v
        # Merge processing hints (other overrides primary)
        primary.processing_hints.update(other.processing_hints)
    return primary


def create_media_collection(
    medias: List[MediaObject],
    collection_type: str = "multimodal",
) -> MediaObject:
    """Create a collection media object referencing multiple media items."""
    # Sensitivity levels have an order: PUBLIC < PRIVATE < SENSITIVE < RESTRICTED
    sens_order = {SensitivityLevel.PUBLIC: 0, SensitivityLevel.PRIVATE: 1, 
                  SensitivityLevel.SENSITIVE: 2, SensitivityLevel.RESTRICTED: 3}
    max_sens = max((m.sensitivity for m in medias), default=SensitivityLevel.PRIVATE, 
                   key=lambda s: sens_order.get(s, 1))
    collection = MediaObject(
        type=MediaType.STRUCTURED_DATA,
        mime_type="application/x.aetheros.media-collection",
        sensitivity=max_sens,
        metadata={
            "collection_type": collection_type,
            "item_count": len(medias),
            "item_types": [m.type.value for m in medias],
        },
    )
    for m in medias:
        collection.add_cross_modal_ref(
            target_media_id=m.media_id,
            relation="contains",
        )
    return collection


# ---------------------------------------------------------------------------
# Validation & sanitization (Phase 1 + security hooks)
# ---------------------------------------------------------------------------


def validate_media_object(media_obj: MediaObject) -> List[str]:
    """Return a list of validation errors (empty == valid)."""
    errors: List[str] = []
    if not media_obj.media_id:
        errors.append("media_id is required")
    if not isinstance(media_obj.type, MediaType):
        errors.append("Invalid media type")
    if media_obj.size < 0:
        errors.append("Size cannot be negative")
    if media_obj.duration < 0:
        errors.append("Duration cannot be negative")
    for key, value in media_obj.dimensions.items():
        if not isinstance(value, int) or value < 0:
            errors.append(f"Dimension '{key}' must be a non-negative integer")
    if not isinstance(media_obj.permissions, PermissionLevel):
        errors.append("Invalid permission level")
    if not isinstance(media_obj.sensitivity, SensitivityLevel):
        errors.append("Invalid sensitivity level")
    # Validate embeddings
    for emb in media_obj.embeddings:
        if not emb.vector_id:
            errors.append("Embedding missing vector_id")
        if emb.dimensions <= 0:
            errors.append("Embedding dimensions must be positive")
    # Validate video frames
    for frame in media_obj.video_frames:
        if frame.frame_index < 0:
            errors.append("Video frame_index cannot be negative")
        if frame.timestamp < 0:
            errors.append("Video frame timestamp cannot be negative")
        if not frame.media_id:
            errors.append("Video frame missing media_id")
    # Validate cross-modal refs
    for ref in media_obj.cross_modal_refs:
        if not ref.target_media_id:
            errors.append("Cross-modal ref missing target_media_id")
        if not ref.relation:
            errors.append("Cross-modal ref missing relation")
    return errors


def sanitize_media_source(source: str) -> str:
    """Sanitize a media source path/URL for security (path traversal defense)."""
    if ".." in source or source.startswith("//"):
        raise ValueError("Potential path traversal detected in source")
    if source.startswith(("file://", "http://", "https://", "ftp://")):
        return source
    return os.path.normpath(source)


def classify_sensitivity_from_content(
    content: str,
    media_type: MediaType,
    metadata: Optional[Dict[str, Any]] = None,
) -> SensitivityLevel:
    """Heuristic sensitivity classification from content (Phase 71)."""
    from agent.multimodal.security import assess_extracted_text, MediaTrust
    
    if media_type == MediaType.TEXT or media_type == MediaType.STRUCTURED_DATA:
        risk = assess_extracted_text(content, media_type.value, metadata)
        if risk.trust == MediaTrust.UNTRUSTED or risk.trust == MediaTrust.SUSPICIOUS:
            return SensitivityLevel.RESTRICTED
        elif risk.trust == MediaTrust.DATA_WITH_EMBEDDED_INSTRUCTIONS:
            return SensitivityLevel.SENSITIVE
    return SensitivityLevel.PRIVATE


def get_media_type_from_mime(mime_type: str) -> MediaType:
    """Map MIME type to MediaType enum."""
    mime_map = {
        "text/plain": MediaType.TEXT,
        "text/markdown": MediaType.TEXT,
        "text/html": MediaType.TEXT,
        "text/csv": MediaType.TEXT,
        "application/json": MediaType.STRUCTURED_DATA,
        "application/xml": MediaType.STRUCTURED_DATA,
        "application/pdf": MediaType.DOCUMENT,
        "image/jpeg": MediaType.IMAGE,
        "image/png": MediaType.IMAGE,
        "image/gif": MediaType.IMAGE,
        "image/webp": MediaType.IMAGE,
        "image/bmp": MediaType.IMAGE,
        "image/tiff": MediaType.IMAGE,
        "audio/mpeg": MediaType.AUDIO,
        "audio/wav": MediaType.AUDIO,
        "audio/wave": MediaType.AUDIO,
        "audio/ogg": MediaType.AUDIO,
        "audio/flac": MediaType.AUDIO,
        "audio/aac": MediaType.AUDIO,
        "video/mp4": MediaType.VIDEO,
        "video/webm": MediaType.VIDEO,
        "video/quicktime": MediaType.VIDEO,
        "video/x-msvideo": MediaType.VIDEO,
        "application/msword": MediaType.DOCUMENT,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": MediaType.DOCUMENT,
        "application/vnd.ms-excel": MediaType.DOCUMENT,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": MediaType.DOCUMENT,
        "application/vnd.ms-powerpoint": MediaType.DOCUMENT,
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": MediaType.DOCUMENT,
    }
    return mime_map.get(mime_type, MediaType.TEXT)
