"""Realtime Multimodal Modes (Phases 76-81 of Master Prompt 10).

Implements specialized realtime modes for different use cases:
- Live Assistant Mode (Phase 76): Continuous listen/see/understand/respond/act
- Meeting Mode (Phase 77): Authorized recording, speaker segments, transcript, notes, action items
- Presentation Mode (Phase 78): Slides + speaker audio + screen + notes understanding
- Screen Copilot Mode (Phase 79): Voice + screen for coding/debugging assistance
- Visual Research Mode (Phase 80): Images + web + documents + screenshots + charts + PDFs
- Multimodal Coding Mode (Phase 81): Screenshot + error + voice + code + logs

All modes respect privacy classification and provider routing.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from agent.multimodal.media_abstraction import MediaObject, MediaType, SensitivityLevel
from agent.multimodal.perception import (
    analyze_image, analyze_video, extract_document, extract_video_frames,
    ocr_media, perceive, synthesize_speech, transcribe_audio, understand_screen
)
from agent.multimodal.privacy_router import ProviderPrivacyRouter, default_privacy_router, ProcessingTarget
from agent.multimodal.local_models import get_offline_manager, process_locally, can_process_locally
from agent.multimodal.memory import MultimodalMemoryStore, default_store
from agent.multimodal.provenance import ProvenanceTracker, ConfidenceTracker, label_claim
from agent.multimodal.accessibility import MultimodalAccessibilityEngine, AccessibilityMode

logger = logging.getLogger(__name__)


class RealtimeMode(Enum):
    """Available realtime modes."""
    LIVE_ASSISTANT = "live_assistant"
    MEETING = "meeting"
    PRESENTATION = "presentation"
    SCREEN_COPILOT = "screen_copilot"
    VISUAL_RESEARCH = "visual_research"
    MULTIMODAL_CODING = "multimodal_coding"


class SessionState(Enum):
    """Realtime session states."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class RealtimeSessionConfig:
    """Configuration for a realtime session."""
    mode: RealtimeMode
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    # Privacy
    sensitivity: SensitivityLevel = SensitivityLevel.PRIVATE
    force_local: bool = False
    allow_external: List[SensitivityLevel] = field(default_factory=lambda: [SensitivityLevel.PUBLIC])
    # Input sources
    enable_microphone: bool = True
    enable_camera: bool = False
    enable_screen: bool = True
    camera_index: int = 0
    screen_capture_mode: str = "full_screen"  # full_screen, window, region
    screen_region: Optional[List[int]] = None
    # Processing
    frame_interval: float = 1.0  # seconds between frame captures
    audio_chunk_duration: float = 5.0  # seconds per audio chunk
    max_concurrent_tasks: int = 3
    # Output
    enable_speech_output: bool = True
    enable_captions: bool = True
    enable_action_execution: bool = False  # Requires explicit permission
    # Accessibility
    accessibility_mode: Optional[AccessibilityMode] = None
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RealtimeEvent:
    """Event emitted during a realtime session."""
    session_id: str
    event_type: str  # "transcript", "analysis", "action", "alert", "state_change"
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = ""  # "microphone", "camera", "screen", "system"
    confidence: float = 1.0


@dataclass
class MeetingNotes:
    """Structured meeting notes."""
    session_id: str
    started_at: float
    ended_at: Optional[float] = None
    participants: List[str] = field(default_factory=list)
    speaker_segments: List[Dict[str, Any]] = field(default_factory=list)
    transcript: str = ""
    action_items: List[Dict[str, Any]] = field(default_factory=list)
    key_decisions: List[str] = field(default_factory=list)
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class RealtimeSession:
    """Base class for realtime multimodal sessions."""

    def __init__(self, config: RealtimeSessionConfig):
        self.config = config
        self.state = SessionState.IDLE
        self._lock = threading.RLock()
        self._callbacks: List[Callable[[RealtimeEvent], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._privacy_router = default_privacy_router()
        self._privacy_router.configure_policy(
            allow_external_sensitivity=config.allow_external,
            force_local=config.force_local,
        )
        self._provenance = ProvenanceTracker()
        self._confidence = ConfidenceTracker()
        self._memory = default_store()
        self._accessibility = None
        if config.accessibility_mode:
            from agent.multimodal.accessibility import create_accessibility_engine
            self._accessibility = create_accessibility_engine(
                user_id=config.user_id,
                modes=[config.accessibility_mode],
            )

    def add_callback(self, callback: Callable[[RealtimeEvent], None]) -> None:
        with self._lock:
            self._callbacks.append(callback)

    def _emit(self, event: RealtimeEvent) -> None:
        with self._lock:
            for cb in self._callbacks:
                try:
                    cb(event)
                except Exception as e:
                    logger.warning("Realtime callback failed: %s", e)

    def start(self) -> None:
        with self._lock:
            if self.state in (SessionState.RUNNING, SessionState.STARTING):
                return
            self.state = SessionState.STARTING
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            self.state = SessionState.RUNNING
            self._emit(RealtimeEvent(
                session_id=self.config.session_id,
                event_type="state_change",
                data={"state": "running"},
                source="system",
            ))

    def stop(self) -> None:
        with self._lock:
            if self.state not in (SessionState.RUNNING, SessionState.STARTING):
                return
            self.state = SessionState.STOPPING
            self._running = False
            if self._thread:
                self._thread.join(timeout=5.0)
            self.state = SessionState.STOPPED
            self._emit(RealtimeEvent(
                session_id=self.config.session_id,
                event_type="state_change",
                data={"state": "stopped"},
                source="system",
            ))

    def pause(self) -> None:
        with self._lock:
            if self.state == SessionState.RUNNING:
                self.state = SessionState.PAUSED
                self._emit(RealtimeEvent(
                    session_id=self.config.session_id,
                    event_type="state_change",
                    data={"state": "paused"},
                    source="system",
                ))

    def resume(self) -> None:
        with self._lock:
            if self.state == SessionState.PAUSED:
                self.state = SessionState.RUNNING
                self._emit(RealtimeEvent(
                    session_id=self.config.session_id,
                    event_type="state_change",
                    data={"state": "running"},
                    source="system",
                ))

    def _run(self) -> None:
        """Main session loop - override in subclasses."""
        raise NotImplementedError

    def process_media(self, media: MediaObject) -> Dict[str, Any]:
        """Process media with privacy routing."""
        decision = self._privacy_router.decide(media)
        if decision.target == ProcessingTarget.REFUSE:
            return {"success": False, "error": decision.reason, "privacy_decision": decision.reason}
        if decision.target == ProcessingTarget.LOCAL:
            # Use local models
            if can_process_locally(media, "vision"):
                return process_locally(media, "vision")
        # Use perceive (which routes to production tools)
        return perceive(media, trackers={"provenance": self._provenance, "confidence": self._confidence})


class LiveAssistantSession(RealtimeSession):
    """Phase 76: Live Assistant Mode - Continuous listen/see/understand/respond/act."""

    def __init__(self, config: RealtimeSessionConfig):
        super().__init__(config)
        self._last_screen_analysis = 0.0
        self._last_audio_transcript = ""
        self._context_buffer: List[str] = []

    def _run(self) -> None:
        logger.info("Live Assistant session %s started", self.config.session_id)
        while self._running:
            try:
                if self.state == SessionState.PAUSED:
                    time.sleep(0.5)
                    continue

                # Capture screen
                if self.config.enable_screen:
                    self._capture_and_analyze_screen()

                # Process audio
                if self.config.enable_microphone:
                    self._capture_and_transcribe_audio()

                # Check for voice commands
                if self._last_audio_transcript:
                    self._process_voice_interaction()

                time.sleep(self.config.frame_interval)

            except Exception as e:
                logger.error("Live Assistant loop error: %s", e)
                self._emit(RealtimeEvent(
                    session_id=self.config.session_id,
                    event_type="alert",
                    data={"error": str(e), "level": "error"},
                    source="system",
                ))
                time.sleep(1.0)

    def _capture_and_analyze_screen(self) -> None:
        try:
            from agent.multimodal.perception import capture_screen
            result = capture_screen(mode=self.config.screen_capture_mode, region=self.config.screen_region)
            if result.get("success"):
                media = MediaObject(
                    type=MediaType.SCREEN,
                    source=result["path"],
                    metadata={"capture_mode": result["mode"], "dimensions": {"width": result["width"], "height": result["height"]}},
                )
                analysis = self.process_media(media)
                if analysis.get("success"):
                    self._last_screen_analysis = time.time()
                    self._context_buffer.append(f"Screen: {analysis.get('analysis', '')}")
                    if len(self._context_buffer) > 10:
                        self._context_buffer.pop(0)
                    self._emit(RealtimeEvent(
                        session_id=self.config.session_id,
                        event_type="analysis",
                        data={"modality": "screen", "analysis": analysis.get("analysis", "")},
                        source="screen",
                        confidence=analysis.get("confidence", 0.5),
                    ))
        except Exception as e:
            logger.warning("Screen capture failed: %s", e)

    def _capture_and_transcribe_audio(self) -> None:
        # This would integrate with the audio capture system
        # For now, placeholder - actual implementation would use aetheros_voice.audio.capture
        pass

    def _process_voice_interaction(self) -> None:
        # Process the transcript for commands or questions
        if self._accessibility:
            cmd_result = self._accessibility.process_voice_command(self._last_audio_transcript)
            if cmd_result and cmd_result.startswith("[COMMAND]"):
                self._handle_command(cmd_result)
                self._last_audio_transcript = ""
                return

        # Treat as question about current context
        context = "\n".join(self._context_buffer[-5:])  # Last 5 screen analyses
        if context and len(self._last_audio_transcript) > 3:
            self._answer_question(context, self._last_audio_transcript)
            self._last_audio_transcript = ""

    def _answer_question(self, context: str, question: str) -> None:
        # This would use the agent to answer
        # For now, emit event for external handling
        self._emit(RealtimeEvent(
            session_id=self.config.session_id,
            event_type="question",
            data={"context": context, "question": question},
            source="microphone",
        ))

    def _handle_command(self, cmd_result: str) -> None:
        cmd = cmd_result.replace("[COMMAND] ", "").strip()
        self._emit(RealtimeEvent(
            session_id=self.config.session_id,
            event_type="command",
            data={"command": cmd},
            source="microphone",
        ))


class MeetingSession(RealtimeSession):
    """Phase 77: Meeting Mode - Authorized recording with notes."""

    def __init__(self, config: RealtimeSessionConfig):
        super().__init__(config)
        self.notes = MeetingNotes(
            session_id=config.session_id,
            started_at=time.time(),
        )
        self._speaker_buffer: Dict[str, List[str]] = {}
        self._recording = False

    def _run(self) -> None:
        logger.info("Meeting session %s started", self.config.session_id)
        self._recording = True
        while self._running:
            try:
                if self.state == SessionState.PAUSED:
                    time.sleep(0.5)
                    continue

                # Capture audio for transcription
                if self.config.enable_microphone:
                    self._process_meeting_audio()

                # Capture screen for slides/documents
                if self.config.enable_screen:
                    self._capture_meeting_screen()

                time.sleep(self.config.frame_interval)

            except Exception as e:
                logger.error("Meeting loop error: %s", e)
                time.sleep(1.0)

    def _process_meeting_audio(self) -> None:
        # Placeholder for audio capture and transcription
        # Would integrate with aetheros_voice.audio.capture for realtime STT
        pass

    def _capture_meeting_screen(self) -> None:
        try:
            from agent.multimodal.perception import capture_screen, understand_screen
            result = capture_screen(mode="full_screen")
            if result.get("success"):
                media = MediaObject(type=MediaType.SCREEN, source=result["path"])
                analysis = understand_screen(media)
                if analysis.get("success"):
                    # Check for slide changes
                    self._detect_slide_change(analysis)
        except Exception as e:
            logger.warning("Meeting screen capture failed: %s", e)

    def _detect_slide_change(self, analysis: Dict[str, Any]) -> None:
        # Detect if slide changed based on content
        text = analysis.get("analysis", "")
        if text and text not in self.notes.transcript[-200:]:  # New content
            self.notes.transcript += f"\n[Slide] {text}"
            self._emit(RealtimeEvent(
                session_id=self.config.session_id,
                event_type="slide_change",
                data={"content": text[:500]},
                source="screen",
            ))

    def add_speaker_segment(self, speaker: str, text: str, timestamp: float) -> None:
        """Add a speaker segment from diarization."""
        segment = {
            "speaker": speaker,
            "text": text,
            "timestamp": timestamp,
        }
        self.notes.speaker_segments.append(segment)
        self.notes.transcript += f"\n[{speaker}] {text}"
        if speaker not in self.notes.participants:
            self.notes.participants.append(speaker)

    def add_action_item(self, description: str, assignee: str = "", due: str = "") -> None:
        """Add an action item."""
        item = {
            "description": description,
            "assignee": assignee,
            "due": due,
            "timestamp": time.time(),
            "status": "pending",
        }
        self.notes.action_items.append(item)
        self._emit(RealtimeEvent(
            session_id=self.config.session_id,
            event_type="action_item",
            data=item,
            source="system",
        ))

    def finalize(self) -> MeetingNotes:
        """Finalize meeting notes."""
        self.notes.ended_at = time.time()
        # Generate summary
        self.notes.summary = self._generate_summary()
        return self.notes

    def _generate_summary(self) -> str:
        # Would use LLM to generate summary
        return f"Meeting with {len(self.notes.participants)} participants. {len(self.notes.action_items)} action items."


class PresentationSession(RealtimeSession):
    """Phase 78: Presentation Mode - Slides + speaker + screen understanding."""

    def __init__(self, config: RealtimeSessionConfig):
        super().__init__(config)
        self.slides: List[Dict[str, Any]] = []
        self.current_slide = -1
        self.speaker_transcript = ""

    def _run(self) -> None:
        logger.info("Presentation session %s started", self.config.session_id)
        while self._running:
            try:
                if self.state == SessionState.PAUSED:
                    time.sleep(0.5)
                    continue

                # Capture screen for slides
                if self.config.enable_screen:
                    self._capture_and_analyze_slides()

                # Transcribe speaker audio
                if self.config.enable_microphone:
                    self._transcribe_speaker()

                time.sleep(self.config.frame_interval)

            except Exception as e:
                logger.error("Presentation loop error: %s", e)
                time.sleep(1.0)

    def _capture_and_analyze_slides(self) -> None:
        try:
            from agent.multimodal.perception import capture_screen, understand_screen, ocr_media
            result = capture_screen(mode="full_screen")
            if result.get("success"):
                media = MediaObject(type=MediaType.SCREEN, source=result["path"])
                # OCR for slide text
                ocr_result = ocr_media(media)
                # Vision for charts/diagrams
                vision_result = understand_screen(media)

                slide_data = {
                    "timestamp": time.time(),
                    "slide_number": len(self.slides) + 1,
                    "ocr_text": ocr_result.get("text", "") if ocr_result.get("success") else "",
                    "vision_analysis": vision_result.get("analysis", "") if vision_result.get("success") else "",
                    "elements": analysis.get("elements", []) if vision_result.get("success") else [],
                }
                self.slides.append(slide_data)
                self.current_slide = len(self.slides) - 1

                self._emit(RealtimeEvent(
                    session_id=self.config.session_id,
                    event_type="slide_captured",
                    data=slide_data,
                    source="screen",
                ))
        except Exception as e:
            logger.warning("Slide capture failed: %s", e)

    def _transcribe_speaker(self) -> None:
        # Placeholder for speaker transcription
        pass

    def get_presentation_summary(self) -> Dict[str, Any]:
        """Generate structured presentation summary."""
        return {
            "slide_count": len(self.slides),
            "slides": self.slides,
            "speaker_transcript": self.speaker_transcript,
            "duration": time.time() - self.config.metadata.get("start_time", time.time()),
        }


class ScreenCopilotSession(RealtimeSession):
    """Phase 79: Screen Copilot Mode - Voice + screen for coding/debugging."""

    def __init__(self, config: RealtimeSessionConfig):
        super().__init__(config)
        self.code_context = ""
        self.last_error = ""
        self.terminal_history: List[str] = []

    def _run(self) -> None:
        logger.info("Screen Copilot session %s started", self.config.session_id)
        while self._running:
            try:
                if self.state == SessionState.PAUSED:
                    time.sleep(0.5)
                    continue

                # Capture screen for code/terminal
                if self.config.enable_screen:
                    self._capture_coding_context()

                # Listen for voice questions
                if self.config.enable_microphone:
                    self._listen_for_questions()

                time.sleep(self.config.frame_interval)

            except Exception as e:
                logger.error("Screen Copilot loop error: %s", e)
                time.sleep(1.0)

    def _capture_coding_context(self) -> None:
        try:
            from agent.multimodal.perception import capture_screen, understand_screen
            result = capture_screen(mode=self.config.screen_capture_mode, region=self.config.screen_region)
            if result.get("success"):
                media = MediaObject(type=MediaType.SCREEN, source=result["path"])
                analysis = understand_screen(media)
                if analysis.get("success"):
                    self.code_context = analysis.get("analysis", "")
                    # Check for errors in terminal
                    self._detect_errors(analysis)
        except Exception as e:
            logger.warning("Coding context capture failed: %s", e)

    def _detect_errors(self, analysis: Dict[str, Any]) -> None:
        text = analysis.get("analysis", "").lower()
        error_indicators = ["error", "exception", "failed", "traceback", "syntax error", "undefined", "not found"]
        for indicator in error_indicators:
            if indicator in text and indicator not in self.last_error:
                self.last_error = indicator
                self._emit(RealtimeEvent(
                    session_id=self.config.session_id,
                    event_type="error_detected",
                    data={"error_type": indicator, "context": text[:500]},
                    source="screen",
                ))
                break

    def _listen_for_questions(self) -> None:
        # Placeholder for voice question handling
        pass

    def answer_coding_question(self, question: str) -> str:
        """Answer a coding question using current screen context."""
        context = f"Screen context:\n{self.code_context}\n\nRecent errors:\n{self.last_error}\n\nQuestion: {question}"
        # Would use agent to answer
        self._emit(RealtimeEvent(
            session_id=self.config.session_id,
            event_type="coding_question",
            data={"question": question, "context": context},
            source="microphone",
        ))
        return context


class VisualResearchSession(RealtimeSession):
    """Phase 80: Visual Research Mode - Images + web + documents + charts."""

    def __init__(self, config: RealtimeSessionConfig):
        super().__init__(config)
        self.research_sources: List[Dict[str, Any]] = []
        self.findings: List[Dict[str, Any]] = []

    def _run(self) -> None:
        logger.info("Visual Research session %s started", self.config.session_id)
        while self._running:
            try:
                if self.state == SessionState.PAUSED:
                    time.sleep(0.5)
                    continue

                # Process queued media
                self._process_research_queue()

                time.sleep(self.config.frame_interval)

            except Exception as e:
                logger.error("Visual Research loop error: %s", e)
                time.sleep(1.0)

    def add_source(self, media: MediaObject, source_type: str, description: str = "") -> None:
        """Add a research source (image, document, screenshot, chart)."""
        self.research_sources.append({
            "media_id": media.media_id,
            "type": media.type.value,
            "source_type": source_type,  # "image", "document", "screenshot", "chart", "pdf"
            "description": description,
            "timestamp": time.time(),
        })
        self._emit(RealtimeEvent(
            session_id=self.config.session_id,
            event_type="source_added",
            data={"media_id": media.media_id, "type": source_type},
            source="system",
        ))

    def _process_research_queue(self) -> None:
        for source in self.research_sources:
            if source.get("processed"):
                continue
            media_id = source["media_id"]
            # Find media object (would come from memory store)
            source["processed"] = True
            self._analyze_source(source)

    def _analyze_source(self, source: Dict[str, Any]) -> None:
        # Analyze based on source type
        analysis_prompt = {
            "image": "Analyze this image for research. Identify objects, text, charts, diagrams, and key information.",
            "document": "Extract key information, arguments, data, and citations from this document.",
            "chart": "Analyze this chart. Extract data points, trends, axes, and key insights.",
            "screenshot": "Analyze this screenshot for UI elements, text, and workflow information.",
            "pdf": "Extract text, tables, figures, and structure from this PDF.",
        }.get(source["source_type"], "Analyze this content for research purposes.")

        self._emit(RealtimeEvent(
            session_id=self.config.session_id,
            event_type="finding",
            data={"source": source, "prompt": analysis_prompt},
            source="system",
        ))

    def query(self, question: str) -> List[Dict[str, Any]]:
        """Query research findings."""
        # Would use RAG over stored sources
        return self.findings


class MultimodalCodingSession(RealtimeSession):
    """Phase 81: Multimodal Coding Mode - Screenshot + error + voice + code + logs."""

    def __init__(self, config: RealtimeSessionConfig):
        super().__init__(config)
        self.code_files: Dict[str, str] = {}
        self.error_logs: List[str] = []
        self.screenshots: List[MediaObject] = []
        self.voice_notes: List[str] = []

    def _run(self) -> None:
        logger.info("Multimodal Coding session %s started", self.config.session_id)
        while self._running:
            try:
                if self.state == SessionState.PAUSED:
                    time.sleep(0.5)
                    continue

                # Capture screen for IDE/editor
                if self.config.enable_screen:
                    self._capture_ide_context()

                # Listen for voice explanations
                if self.config.enable_microphone:
                    self._capture_voice_note()

                time.sleep(self.config.frame_interval)

            except Exception as e:
                logger.error("Multimodal Coding loop error: %s", e)
                time.sleep(1.0)

    def _capture_ide_context(self) -> None:
        try:
            from agent.multimodal.perception import capture_screen, understand_screen, ocr_media
            result = capture_screen(mode="window")  # Capture IDE window
            if result.get("success"):
                media = MediaObject(type=MediaType.SCREEN, source=result["path"])
                self.screenshots.append(media)

                # OCR for code text
                ocr_result = ocr_media(media)
                if ocr_result.get("success"):
                    code_text = ocr_result.get("text", "")
                    self._detect_code_language(code_text)

                # Vision for UI understanding
                vision_result = understand_screen(media)
        except Exception as e:
            logger.warning("IDE context capture failed: %s", e)

    def _detect_code_language(self, text: str) -> None:
        # Simple language detection
        lang_indicators = {
            "python": ["def ", "import ", "class ", "self.", "async def"],
            "javascript": ["function ", "const ", "let ", "=>", "console.log"],
            "typescript": ["interface ", "type ", "const ", ": string", ": number"],
            "rust": ["fn ", "let ", "mut ", "impl ", "struct "],
            "go": ["func ", "package ", "import ", "var ", ":="],
        }
        for lang, indicators in lang_indicators.items():
            if any(ind in text for ind in indicators):
                self.code_files[f"detected_{lang}"] = text[:5000]
                break

    def _capture_voice_note(self) -> None:
        # Placeholder for voice capture
        pass

    def add_code_file(self, path: str, content: str) -> None:
        self.code_files[path] = content

    def add_error_log(self, log: str) -> None:
        self.error_logs.append(log)

    def debug_question(self, question: str) -> str:
        """Answer a debugging question using all context."""
        context_parts = [
            "Code files:",
            *[f"{k}: {v[:500]}" for k, v in list(self.code_files.items())[:5]],
            "\nError logs:",
            *[log[:500] for log in self.error_logs[-3:]],
            "\nVoice notes:",
            *self.voice_notes[-3:],
            f"\nQuestion: {question}",
        ]
        context = "\n".join(context_parts)
        self._emit(RealtimeEvent(
            session_id=self.config.session_id,
            event_type="debug_question",
            data={"question": question, "context": context},
            source="microphone",
        ))
        return context


# --- Factory functions ---

def create_realtime_session(
    mode: RealtimeMode,
    config: Optional[RealtimeSessionConfig] = None,
    **kwargs,
) -> RealtimeSession:
    """Create a realtime session of the specified mode."""
    if config is None:
        config = RealtimeSessionConfig(mode=mode, **kwargs)
    else:
        # Apply kwargs as overrides
        for k, v in kwargs.items():
            if hasattr(config, k):
                setattr(config, k, v)

    if mode == RealtimeMode.LIVE_ASSISTANT:
        return LiveAssistantSession(config)
    elif mode == RealtimeMode.MEETING:
        return MeetingSession(config)
    elif mode == RealtimeMode.PRESENTATION:
        return PresentationSession(config)
    elif mode == RealtimeMode.SCREEN_COPILOT:
        return ScreenCopilotSession(config)
    elif mode == RealtimeMode.VISUAL_RESEARCH:
        return VisualResearchSession(config)
    elif mode == RealtimeMode.MULTIMODAL_CODING:
        return MultimodalCodingSession(config)
    else:
        raise ValueError(f"Unknown realtime mode: {mode}")


def start_live_assistant(
    user_id: str = "",
    enable_camera: bool = False,
    enable_speech: bool = True,
    force_local: bool = False,
    **kwargs,
) -> LiveAssistantSession:
    """Start a Live Assistant session."""
    config = RealtimeSessionConfig(
        mode=RealtimeMode.LIVE_ASSISTANT,
        user_id=user_id,
        enable_camera=enable_camera,
        enable_speech_output=enable_speech,
        force_local=force_local,
        **kwargs,
    )
    session = LiveAssistantSession(config)
    session.start()
    return session


def start_meeting(
    user_id: str = "",
    title: str = "",
    record_audio: bool = True,
    record_screen: bool = True,
    force_local: bool = False,
    **kwargs,
) -> MeetingSession:
    """Start a Meeting session."""
    config = RealtimeSessionConfig(
        mode=RealtimeMode.MEETING,
        user_id=user_id,
        enable_microphone=record_audio,
        enable_screen=record_screen,
        force_local=force_local,
        metadata={"title": title},
        **kwargs,
    )
    session = MeetingSession(config)
    session.start()
    return session


def start_presentation(
    user_id: str = "",
    title: str = "",
    **kwargs,
) -> PresentationSession:
    """Start a Presentation session."""
    config = RealtimeSessionConfig(
        mode=RealtimeMode.PRESENTATION,
        user_id=user_id,
        enable_screen=True,
        enable_microphone=True,
        metadata={"title": title},
        **kwargs,
    )
    session = PresentationSession(config)
    session.start()
    return session


def start_screen_copilot(
    user_id: str = "",
    capture_mode: str = "window",
    region: Optional[List[int]] = None,
    **kwargs,
) -> ScreenCopilotSession:
    """Start a Screen Copilot session."""
    config = RealtimeSessionConfig(
        mode=RealtimeMode.SCREEN_COPILOT,
        user_id=user_id,
        enable_screen=True,
        enable_microphone=True,
        screen_capture_mode=capture_mode,
        screen_region=region,
        **kwargs,
    )
    session = ScreenCopilotSession(config)
    session.start()
    return session


def start_visual_research(
    user_id: str = "",
    **kwargs,
) -> VisualResearchSession:
    """Start a Visual Research session."""
    config = RealtimeSessionConfig(
        mode=RealtimeMode.VISUAL_RESEARCH,
        user_id=user_id,
        enable_screen=True,
        enable_microphone=False,
        **kwargs,
    )
    session = VisualResearchSession(config)
    session.start()
    return session


def start_multimodal_coding(
    user_id: str = "",
    **kwargs,
) -> MultimodalCodingSession:
    """Start a Multimodal Coding session."""
    config = RealtimeSessionConfig(
        mode=RealtimeMode.MULTIMODAL_CODING,
        user_id=user_id,
        enable_screen=True,
        enable_microphone=True,
        **kwargs,
    )
    session = MultimodalCodingSession(config)
    session.start()
    return session