"""Multimodal Functional Tests (Phase 94).

Tests core multimodal functionality across all modalities.
"""

import pytest
from pathlib import Path


class TestMediaAbstraction:
    """Test MediaObject creation and manipulation."""

    def test_create_text_media(self, media_text):
        assert media_text.type.value == "text"
        assert "content" in media_text.metadata

    def test_create_image_media(self, media_image):
        assert media_image.type.value == "image"
        assert media_image.size > 0
        assert media_image.dimensions.get("width", 0) > 0

    def test_create_audio_media(self, media_audio):
        assert media_audio.type.value == "audio"
        assert media_audio.duration >= 0

    def test_create_video_media(self, media_video):
        assert media_video.type.value == "video"
        assert media_video.duration >= 0

    def test_create_document_media(self, media_document):
        assert media_document.type.value == "document"
        assert media_document.size > 0

    def test_media_embeddings(self, media_image):
        media_image.add_embedding("vec-123", "clip-vit-b32", 512)
        embeddings = media_image.get_embeddings()
        assert len(embeddings) == 1
        assert embeddings[0].vector_id == "vec-123"

    def test_media_video_frames(self, media_video):
        media_video.add_video_frame(0, 0.0, "frame-1", is_keyframe=True)
        keyframes = media_video.get_keyframes()
        assert len(keyframes) == 1

    def test_media_cross_modal_refs(self, media_image, media_audio):
        media_image.add_cross_modal_ref(media_audio.media_id, "transcript_of", target_timestamp=1.5)
        refs = media_image.get_cross_modal_refs("transcript_of")
        assert len(refs) == 1

    def test_media_budget(self, media_image):
        media_image.set_budget("max_tokens", 1000)
        media_image.set_budget("tokens_used", 100)
        assert media_image.consume_budget("tokens_used", 50) is True
        assert media_image.get_budget("tokens_used") == 150


class TestInputRouter:
    """Test multimodal input routing."""

    def test_route_file_image(self, test_image_simple):
        from agent.multimodal.input_router import route_file
        media = route_file(str(test_image_simple))
        assert media.type.value == "image"

    def test_route_file_audio(self, test_audio_tone):
        from agent.multimodal.input_router import route_file
        media = route_file(str(test_audio_tone))
        assert media.type.value == "audio"

    def test_route_file_document(self, test_pdf_simple):
        from agent.multimodal.input_router import route_file
        media = route_file(str(test_pdf_simple))
        assert media.type.value == "document"

    def test_route_text(self):
        from agent.multimodal.input_router import route_text
        media = route_text("Hello world")
        assert media.type.value == "text"

    def test_route_structured_data(self):
        from agent.multimodal.input_router import route_structured_data
        media = route_structured_data({"key": "value"})
        assert media.type.value == "structured_data"

    def test_route_base64_image(self, test_image_base64):
        from agent.multimodal.input_router import route_base64
        media = route_base64(base64.b64decode(test_image_base64), mime_type="image/png")
        assert media.type.value == "image"


class TestCapabilityDetector:
    """Test model capability detection."""

    def test_local_vision_models(self):
        from agent.multimodal.capability_detector import CapabilityDetector, CapabilityType
        detector = CapabilityDetector()
        caps = detector.detect("ollama", "llava")
        assert CapabilityType.VISION in caps.capabilities
        assert CapabilityType.VISION_OCR in caps.capabilities

    def test_gpt4o_capabilities(self):
        from agent.multimodal.capability_detector import CapabilityDetector, CapabilityType
        detector = CapabilityDetector()
        caps = detector.detect("openai", "gpt-4o")
        assert CapabilityType.VISION in caps.capabilities
        assert CapabilityType.TOOL_CALLING in caps.capabilities

    def test_whisper_stt(self):
        from agent.multimodal.capability_detector import CapabilityDetector, CapabilityType
        detector = CapabilityDetector()
        caps = detector.detect("openai", "whisper-1")
        assert CapabilityType.AUDIO_TRANSCRIBE in caps.capabilities

    def test_route_modality_image(self):
        from agent.multimodal.capability_detector import CapabilityDetector
        from agent.multimodal.media_abstraction import MediaType
        detector = CapabilityDetector()
        model = detector.route_modality(["openai"], ["gpt-4o"], MediaType.IMAGE)
        assert model is not None
        assert model.supports_modality(MediaType.IMAGE)

    def test_route_modality_audio(self):
        from agent.multimodal.capability_detector import CapabilityDetector
        from agent.multimodal.media_abstraction import MediaType
        detector = CapabilityDetector()
        model = detector.route_modality(["openai"], ["whisper-1"], MediaType.AUDIO)
        assert model is not None
        assert model.supports_modality(MediaType.AUDIO)


class TestPerception:
    """Test multimodal perception layer."""

    def test_perceive_image(self, media_image):
        from agent.multimodal.perception import perceive
        result = perceive(media_image, "Describe this image")
        assert "success" in result

    def test_perceive_text(self, media_text):
        from agent.multimodal.perception import perceive
        result = perceive(media_text)
        assert result["success"] is True

    def test_analyze_image(self, media_image):
        from agent.multimodal.perception import analyze_image
        result = analyze_image(media_image, "What do you see?")
        assert "success" in result

    def test_ocr_media(self, media_image):
        from agent.multimodal.perception import ocr_media
        result = ocr_media(media_image)
        assert "success" in result

    def test_transcribe_audio(self, media_audio, monkeypatch):
        from agent.multimodal.perception import transcribe_audio
        
        # Mock the transcription to avoid loading whisper model
        def mock_transcribe(media, model=None, tracker=None, confidence=None):
            return {"success": True, "transcript": "test transcript", "confidence": 0.9, "provider": "mock"}
        
        monkeypatch.setattr("tools.transcription_tools.transcribe_audio", mock_transcribe)
        
        result = transcribe_audio(media_audio)
        assert "success" in result

    def test_extract_document(self, media_document):
        from agent.multimodal.perception import extract_document
        result = extract_document(media_document)
        assert "success" in result


class TestPrivacyRouter:
    """Test privacy classification and routing."""

    def test_classify_public(self):
        from agent.multimodal.privacy_router import PrivacyClassifier, SensitivityLevel
        from agent.multimodal.media_abstraction import MediaObject, MediaType
        classifier = PrivacyClassifier()
        media = MediaObject(type=MediaType.TEXT, sensitivity=SensitivityLevel.PUBLIC)
        assert classifier.classify(media, "public information") == SensitivityLevel.PUBLIC

    def test_classify_sensitive(self):
        from agent.multimodal.privacy_router import PrivacyClassifier, SensitivityLevel
        from agent.multimodal.media_abstraction import MediaObject, MediaType
        classifier = PrivacyClassifier()
        media = MediaObject(type=MediaType.TEXT)
        assert classifier.classify(media, "my password is secret123") == SensitivityLevel.SENSITIVE

    def test_router_force_local(self):
        from agent.multimodal.privacy_router import ProviderPrivacyRouter, ProcessingTarget
        from agent.multimodal.media_abstraction import MediaObject, MediaType, SensitivityLevel
        router = ProviderPrivacyRouter()
        router.configure_policy(force_local=True)
        media = MediaObject(type=MediaType.IMAGE, sensitivity=SensitivityLevel.PRIVATE)
        decision = router.decide(media)
        assert decision.target == ProcessingTarget.LOCAL

    def test_router_allow_public_external(self):
        from agent.multimodal.privacy_router import ProviderPrivacyRouter, ProcessingTarget
        from agent.multimodal.media_abstraction import MediaObject, MediaType, SensitivityLevel
        router = ProviderPrivacyRouter()
        media = MediaObject(type=MediaType.IMAGE, sensitivity=SensitivityLevel.PUBLIC)
        decision = router.decide(media)
        assert decision.target == ProcessingTarget.EXTERNAL


class TestLocalModels:
    """Test local model registry and offline mode."""

    def test_list_local_models(self):
        from agent.multimodal.local_models import list_local_models
        models = list_local_models()
        assert isinstance(models, list)

    def test_offline_mode_manager(self):
        from agent.multimodal.local_models import get_offline_manager, OfflineModeManager
        mgr = get_offline_manager()
        assert isinstance(mgr, OfflineModeManager)

    def test_enable_disable_offline_mode(self):
        from agent.multimodal.local_models import get_offline_manager, enable_offline_mode, disable_offline_mode
        mgr = get_offline_manager()
        enable_offline_mode()
        assert mgr.offline_mode is True
        disable_offline_mode()
        assert mgr.offline_mode is False

    def test_get_local_capabilities(self):
        from agent.multimodal.local_models import get_local_capabilities
        caps = get_local_capabilities()
        assert isinstance(caps, list)


class TestAccessibility:
    """Test accessibility features."""

    def test_screen_describer(self):
        from agent.multimodal.accessibility import ScreenDescriber, AccessibilityProfile
        profile = AccessibilityProfile()
        describer = ScreenDescriber(profile)
        assert describer is not None

    def test_document_reader(self):
        from agent.multimodal.accessibility import DocumentReader, AccessibilityProfile
        profile = AccessibilityProfile()
        reader = DocumentReader(profile)
        assert reader is not None

    def test_voice_command_processor(self):
        from agent.multimodal.accessibility import VoiceCommandProcessor, AccessibilityProfile
        profile = AccessibilityProfile()
        processor = VoiceCommandProcessor(profile)
        result = processor.process("describe screen")
        assert result is not None
        assert "describe_screen" in result

    def test_caption_manager(self):
        from agent.multimodal.accessibility import CaptionManager, AccessibilityProfile
        profile = AccessibilityProfile()
        captions = CaptionManager(profile)
        captions.add_caption("Hello world", "speaker1")
        current = captions.get_current()
        assert "speaker1" in current
        assert "Hello world" in current

    def test_visual_alert_system(self):
        from agent.multimodal.accessibility import VisualAlertSystem
        alerts = VisualAlertSystem()
        alerts.alert("Test warning", "warning")
        active = alerts.get_active_alerts()
        assert len(active) == 1

    def test_accessibility_engine(self):
        from agent.multimodal.accessibility import MultimodalAccessibilityEngine, AccessibilityMode
        engine = MultimodalAccessibilityEngine()
        engine.enable_mode(AccessibilityMode.SCREEN_READER)
        assert engine.is_mode_enabled(AccessibilityMode.SCREEN_READER)
        assert engine.profile.auto_describe_images is True


class TestRealtimeModes:
    """Test realtime multimodal session modes."""

    def test_live_assistant_session(self):
        from agent.multimodal.realtime_modes import RealtimeMode, RealtimeSessionConfig, LiveAssistantSession
        config = RealtimeSessionConfig(mode=RealtimeMode.LIVE_ASSISTANT, user_id="test")
        session = LiveAssistantSession(config)
        assert session.config.mode == RealtimeMode.LIVE_ASSISTANT

    def test_meeting_session(self):
        from agent.multimodal.realtime_modes import RealtimeMode, RealtimeSessionConfig, MeetingSession
        import time
        config = RealtimeSessionConfig(mode=RealtimeMode.MEETING, user_id="test")
        session = MeetingSession(config)
        session.add_speaker_segment("Alice", "Hello everyone", time.time())
        session.add_action_item("Review PR #123", "Bob", "2024-01-15")
        notes = session.finalize()
        assert len(notes.participants) == 1
        assert len(notes.action_items) == 1

    def test_presentation_session(self):
        from agent.multimodal.realtime_modes import RealtimeMode, RealtimeSessionConfig, PresentationSession
        config = RealtimeSessionConfig(mode=RealtimeMode.PRESENTATION, user_id="test")
        session = PresentationSession(config)
        assert session.current_slide == -1

    def test_screen_copilot_session(self):
        from agent.multimodal.realtime_modes import RealtimeMode, RealtimeSessionConfig, ScreenCopilotSession
        config = RealtimeSessionConfig(mode=RealtimeMode.SCREEN_COPILOT, user_id="test")
        session = ScreenCopilotSession(config)
        assert session.last_error == ""

    def test_visual_research_session(self):
        from agent.multimodal.realtime_modes import RealtimeMode, RealtimeSessionConfig, VisualResearchSession
        config = RealtimeSessionConfig(mode=RealtimeMode.VISUAL_RESEARCH, user_id="test")
        session = VisualResearchSession(config)
        assert len(session.research_sources) == 0

    def test_multimodal_coding_session(self):
        from agent.multimodal.realtime_modes import RealtimeMode, RealtimeSessionConfig, MultimodalCodingSession
        config = RealtimeSessionConfig(mode=RealtimeMode.MULTIMODAL_CODING, user_id="test")
        session = MultimodalCodingSession(config)
        assert len(session.code_files) == 0


class TestWorkflows:
    """Test multimodal workflows and agent handoff."""

    def test_tool_router(self):
        from agent.multimodal.workflows import MultimodalToolRouter, ToolCategory
        from agent.multimodal.media_abstraction import MediaObject, MediaType
        router = MultimodalToolRouter()
        media = MediaObject(type=MediaType.IMAGE)
        routes = router.route(media, "analyze this image")
        assert len(routes) > 0
        assert routes[0].modality == MediaType.IMAGE

    def test_agent_coordinator(self):
        from agent.multimodal.workflows import MultimodalAgentCoordinator, AgentRole
        coordinator = MultimodalAgentCoordinator()
        result = coordinator._vision_agent("analyze", [], {})
        assert result["agent"] == "vision"

    def test_agent_handoff(self, test_image_simple):
        from agent.multimodal.workflows import MultimodalAgentCoordinator, AgentRole
        from agent.multimodal.media_abstraction import create_image_media
        coordinator = MultimodalAgentCoordinator()
        media = [create_image_media(str(test_image_simple))]
        handoff = coordinator.handoff(AgentRole.COORDINATOR, AgentRole.VISION, "analyze image", media)
        assert handoff.from_agent == AgentRole.COORDINATOR
        assert handoff.to_agent == AgentRole.VISION
        assert handoff.status == "completed"

    def test_cross_modal_pipeline(self, test_image_simple):
        from agent.multimodal.workflows import CrossModalHandoffManager, AgentRole
        from agent.multimodal.media_abstraction import create_image_media
        manager = CrossModalHandoffManager()
        media = [create_image_media(str(test_image_simple))]
        steps = [
            {"from": AgentRole.COORDINATOR, "to": AgentRole.VISION, "task": "Analyze image"},
            {"from": AgentRole.VISION, "to": AgentRole.RESEARCH, "task": "Find sources"},
        ]
        handoffs = manager.create_pipeline(steps, media, "Research task")
        assert len(handoffs) == 2

    def test_workflow_engine(self):
        from agent.multimodal.workflows import MultimodalWorkflowEngine, create_workflow
        from agent.multimodal.media_abstraction import MediaObject, MediaType
        engine = MultimodalWorkflowEngine()
        wf = create_workflow("test", [
            {"name": "step1", "tool": "vision_analyze", "modality": "image"},
            {"name": "step2", "tool": "document_extract", "modality": "document"},
        ])
        media = [MediaObject(type=MediaType.IMAGE)]
        execution = engine.execute(wf, media)
        assert execution.status in ("completed", "failed")


class TestArtifacts:
    """Test multimodal artifacts and export."""

    def test_create_artifact(self):
        from agent.multimodal.artifacts import create_artifact, ArtifactType
        artifact = create_artifact(
            title="Test",
            contents=[{"type": "text", "data": "Hello"}],
            tags=["test"]
        )
        assert artifact.title == "Test"
        assert len(artifact.contents) == 1

    def test_artifact_from_analysis(self, media_image):
        from agent.multimodal.artifacts import create_artifact_from_analysis
        artifact = create_artifact_from_analysis("Analysis", media_image, {"analysis": "Test result"})
        assert artifact.title == "Analysis"
        assert len(artifact.contents) == 1

    def test_export_json(self, media_image):
        from agent.multimodal.artifacts import create_artifact_from_analysis, ExportFormat, MultimodalExporter
        import tempfile
        artifact = create_artifact_from_analysis("Test", media_image, {"analysis": "Result"})
        exporter = MultimodalExporter()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            result = exporter.export_artifact(artifact, ExportFormat.JSON, f.name)
            assert result["success"] is True

    def test_export_markdown(self, media_image):
        from agent.multimodal.artifacts import create_artifact_from_analysis, ExportFormat, MultimodalExporter
        import tempfile
        artifact = create_artifact_from_analysis("Test", media_image, {"analysis": "Result"})
        exporter = MultimodalExporter()
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            result = exporter.export_artifact(artifact, ExportFormat.MARKDOWN, f.name)
            assert result["success"] is True

    def test_export_csv(self, media_image):
        from agent.multimodal.artifacts import create_artifact, ExportFormat, MultimodalExporter, ArtifactType
        import tempfile
        artifact = create_artifact("Test", contents=[
            {"type": "table", "data": [{"col1": "a", "col2": 1}]}
        ])
        exporter = MultimodalExporter()
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            result = exporter.export_artifact(artifact, ExportFormat.CSV, f.name)
            assert result["success"] is True

    def test_export_transcript(self):
        from agent.multimodal.artifacts import export_transcript, ExportFormat
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            result = export_transcript("Speaker 1: Hello\nSpeaker 2: Hi", f.name)
            assert result["success"] is True

    def test_artifact_store(self):
        from agent.multimodal.artifacts import create_artifact, ArtifactStore
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArtifactStore(tmpdir)
            artifact = create_artifact("Test", contents=[{"type": "text", "data": "Hello"}])
            store.store(artifact)
            retrieved = store.get(artifact.artifact_id)
            assert retrieved is not None
            assert retrieved.title == "Test"


class TestAPI:
    """Test multimodal API surface."""

    def test_media_ingest(self, test_image_simple):
        from agent.multimodal.api import media_ingest
        result = media_ingest(str(test_image_simple))
        assert result["success"] is True
        assert "media" in result

    def test_media_inspect(self, test_image_simple):
        from agent.multimodal.api import media_ingest, media_inspect
        from agent.multimodal.media_abstraction import MediaObject
        ingest = media_ingest(str(test_image_simple))
        # media_ingest returns a dict with "media" as a dict, convert to MediaObject
        media_obj = MediaObject.from_dict(ingest["media"])
        result = media_inspect(media_obj)
        assert result["success"] is True

    def test_media_analyze(self, test_image_simple):
        from agent.multimodal.api import media_ingest, media_analyze
        from agent.multimodal.media_abstraction import MediaObject
        ingest = media_ingest(str(test_image_simple))
        media_obj = MediaObject.from_dict(ingest["media"])
        result = media_analyze(media_obj, "What is this?")
        assert "success" in result

    def test_media_ocr(self, test_image_simple):
        from agent.multimodal.api import media_ingest, media_ocr
        from agent.multimodal.media_abstraction import MediaObject
        ingest = media_ingest(str(test_image_simple))
        media_obj = MediaObject.from_dict(ingest["media"])
        result = media_ocr(media_obj)
        assert "success" in result

    def test_media_transcribe(self, test_audio_tone, monkeypatch):
        from agent.multimodal.api import media_ingest, media_transcribe
        from agent.multimodal.media_abstraction import MediaObject
        
        # Mock the transcription to avoid loading whisper model
        def mock_transcribe(media, model=None, tracker=None, confidence=None):
            return {"success": True, "transcript": "test transcript", "confidence": 0.9, "provider": "mock"}
        
        monkeypatch.setattr("tools.transcription_tools.transcribe_audio", mock_transcribe)
        
        ingest = media_ingest(str(test_audio_tone))
        media_obj = MediaObject.from_dict(ingest["media"])
        result = media_transcribe(media_obj)
        assert "success" in result

    def test_media_search(self):
        from agent.multimodal.api import media_search
        result = media_search("test query")
        assert result["success"] is True

    def test_media_convert(self, test_image_simple):
        from agent.multimodal.api import media_ingest, media_convert
        from agent.multimodal.media_abstraction import MediaObject
        import tempfile
        ingest = media_ingest(str(test_image_simple))
        media_obj = MediaObject.from_dict(ingest["media"])
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            result = media_convert(media_obj, "jpeg", f.name)
            assert result["success"] is True

    def test_media_export(self, test_image_simple):
        from agent.multimodal.api import media_ingest, media_export
        from agent.multimodal.media_abstraction import MediaObject
        import tempfile
        ingest = media_ingest(str(test_image_simple))
        media_obj = MediaObject.from_dict(ingest["media"])
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            result = media_export(media_obj, f.name)
            assert result["success"] is True


class TestCLICommands:
    """Test CLI command registration."""

    def test_media_commands_registered(self):
        from aetheros_cli.commands import COMMAND_REGISTRY
        media_cmds = [c for c in COMMAND_REGISTRY if c.name in ("media", "audio", "video", "screen", "camera", "document", "ocr", "describe")]
        assert len(media_cmds) == 8

    def test_media_subcommands(self):
        from aetheros_cli.commands import COMMAND_REGISTRY
        media_cmd = next(c for c in COMMAND_REGISTRY if c.name == "media")
        assert "inspect" in media_cmd.subcommands
        assert "analyze" in media_cmd.subcommands
        assert "transcribe" in media_cmd.subcommands
        assert "ocr" in media_cmd.subcommands

    def test_resolve_media_command(self):
        from aetheros_cli.commands import resolve_command
        cmd = resolve_command("media")
        assert cmd is not None
        assert cmd.name == "media"

    def test_audio_subcommands(self):
        from aetheros_cli.commands import COMMAND_REGISTRY
        audio_cmd = next(c for c in COMMAND_REGISTRY if c.name == "audio")
        assert "record" in audio_cmd.subcommands
        assert "play" in audio_cmd.subcommands
        assert "transcribe" in audio_cmd.subcommands
        assert "synthesize" in audio_cmd.subcommands
        assert "devices" in audio_cmd.subcommands


# Need to import base64 for test_image_base64
import base64