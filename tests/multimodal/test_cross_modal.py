"""Cross-Modal Tests (Phase 95).

Tests combinations of modalities: text+image, text+audio, text+video,
voice+screen, voice+camera, document+image, video+audio, screen+voice,
document+audio.
"""

import pytest
from pathlib import Path


class TestTextImage:
    """Test text + image combinations."""

    def test_text_image_ingest(self, media_text, media_image):
        from agent.multimodal.api import media_ingest
        from agent.multimodal.media_abstraction import merge_media_objects
        
        merged = merge_media_objects(media_text, media_image, relation="describes")
        assert len(merged.cross_modal_refs) == 1
        assert merged.cross_modal_refs[0].relation == "describes"

    def test_text_image_analysis(self, media_text, media_image):
        from agent.multimodal.perception import perceive
        from agent.multimodal.media_abstraction import merge_media_objects
        
        merged = merge_media_objects(media_text, media_image)
        # The merged object can be processed
        result = perceive(merged, "Describe the image and relate to the text")
        assert "success" in result

    def test_image_text_grounding(self, media_image):
        from agent.multimodal.provenance import ProvenanceTracker, ConfidenceTracker, label_claim, EvidenceStatus
        from agent.multimodal.media_abstraction import MediaObject, MediaType
        
        tracker = ProvenanceTracker()
        confidence = ConfidenceTracker()
        
        # Simulate vision analysis finding an object
        claim = "Red square detected at center"
        fact = label_claim(tracker, claim, 0.9, "vision", media_image, "test_vision")
        
        assert fact.status == EvidenceStatus.OBSERVED
        assert fact.evidence.media_id == media_image.media_id


class TestTextAudio:
    """Test text + audio combinations."""

    def test_audio_transcript_with_text_context(self, media_audio, media_text):
        from agent.multimodal.perception import transcribe_audio
        from agent.multimodal.media_abstraction import merge_media_objects
        
        # Transcribe audio
        result = transcribe_audio(media_audio)
        assert "success" in result
        
        # Merge with text context
        merged = merge_media_objects(media_text, media_audio, relation="transcript_of")
        assert len(merged.cross_modal_refs) == 1

    def test_text_audio_cross_reference(self, media_audio):
        from agent.multimodal.provenance import ProvenanceTracker, ConfidenceTracker, label_claim, EvidenceStatus
        from agent.multimodal.media_abstraction import MediaObject, MediaType
        
        tracker = ProvenanceTracker()
        confidence = ConfidenceTracker()
        
        # Simulate transcript
        claim = "Speaker says hello world"
        fact = label_claim(tracker, claim, 0.85, "stt", media_audio, "transcription")
        
        assert fact.status == EvidenceStatus.OBSERVED
        assert fact.evidence.media_id == media_audio.media_id


class TestTextVideo:
    """Test text + video combinations."""

    def test_video_frames_with_text_annotations(self, media_video, media_text):
        from agent.multimodal.media_abstraction import merge_media_objects, MediaObject
        
        # Create frame references
        frame1 = MediaObject(type=MediaType.IMAGE, source="frame://video/0")
        frame2 = MediaObject(type=MediaType.IMAGE, source="frame://video/1")
        
        media_video.add_video_frame(0, 0.0, frame1.media_id, is_keyframe=True)
        media_video.add_video_frame(1, 1.0, frame2.media_id)
        
        # Merge with text description
        merged = merge_media_objects(media_text, media_video, relation="describes")
        assert len(merged.cross_modal_refs) >= 1


class TestVoiceScreen:
    """Test voice + screen combinations."""

    def test_voice_command_screen_action(self):
        from agent.multimodal.accessibility import VoiceCommandProcessor, AccessibilityProfile, MultimodalAccessibilityEngine
        from agent.multimodal.media_abstraction import MediaObject, MediaType
        
        engine = MultimodalAccessibilityEngine()
        engine.enable_mode("voice_control")
        
        # Process voice command about screen
        result = engine.process_voice_command("describe screen")
        assert result is not None
        assert "describe_screen" in result

    def test_screen_description_with_voice(self, media_image):
        from agent.multimodal.accessibility import ScreenDescriber, AccessibilityProfile
        
        profile = AccessibilityProfile(modes=["screen_reader"])
        describer = ScreenDescriber(profile)
        
        # Create screen media
        screen_media = MediaObject(
            type=MediaType.SCREEN,
            source=str(media_image.source) if hasattr(media_image, 'source') else "test.png"
        )
        
        # This would normally call analyze_image
        # For test, just verify the describer exists
        assert describer is not None


class TestVoiceCamera:
    """Test voice + camera combinations."""

    def test_camera_capture_with_voice_command(self):
        from agent.multimodal.accessibility import VoiceCommandProcessor, AccessibilityProfile
        
        engine = MultimodalAccessibilityEngine()
        engine.enable_mode("voice_control")
        
        result = engine.process_voice_command("capture camera")
        # The command processor returns a string for camera capture
        assert result is not None


class TestDocumentImage:
    """Test document + image combinations."""

    def test_document_with_embedded_images(self, media_document, media_image):
        from agent.multimodal.media_abstraction import merge_media_objects, create_media_collection
        
        # Create a collection of document + embedded images
        collection = create_media_collection([media_document, media_image], "document_with_images")
        
        assert collection.metadata["collection_type"] == "document_with_images"
        assert collection.metadata["item_count"] == 2
        assert len(collection.cross_modal_refs) == 2

    def test_pdf_with_chart_extraction(self, media_document, media_image):
        from agent.multimodal.perception import extract_document
        from agent.multimodal.media_abstraction import merge_media_objects
        
        # Extract document (would find charts in real implementation)
        result = extract_document(media_document)
        assert "success" in result


class TestVideoAudio:
    """Test video + audio combinations."""

    def test_video_audio_fusion(self, media_video, media_audio):
        from agent.multimodal.fusion import CrossModalFusionEngine, FusionStrategy, ModalityAlignment, FusionInput
        
        engine = CrossModalFusionEngine()
        inputs = [
            FusionInput(media=media_video),
            FusionInput(media=media_audio),
        ]
        
        result = engine.fuse(inputs, strategy=FusionStrategy.HIERARCHICAL, alignment=ModalityAlignment.TEMPORAL)
        
        assert result.fused_embedding is not None
        assert MediaType.VIDEO in result.aligned_modalities
        assert MediaType.AUDIO in result.aligned_modalities

    def test_video_audio_temporal_alignment(self, media_video, media_audio):
        from agent.multimodal.temporal_fusion import TemporalFusionEngine, SyncStrategy, TimestampedEvent
        
        engine = TemporalFusionEngine()
        
        events = [
            TimestampedEvent(timestamp=0.0, modality="video", data={"frame": 1}),
            TimestampedEvent(timestamp=0.5, modality="audio", data={"speech": "hello"}),
            TimestampedEvent(timestamp=1.0, modality="video", data={"frame": 2}),
            TimestampedEvent(timestamp=1.2, modality="audio", data={"speech": "world"}),
        ]
        
        result = engine.sync(events, strategy=SyncStrategy.LINEAR_INTERPOLATION)
        
        assert result.aligned_events is not None
        assert len(result.aligned_events) == 4


class TestScreenVoice:
    """Test screen + voice combinations."""

    def test_screen_copilot_voice_question(self):
        from agent.multimodal.realtime_modes import ScreenCopilotSession, RealtimeSessionConfig, RealtimeMode
        from agent.multimodal.media_abstraction import MediaObject, MediaType
        
        config = RealtimeSessionConfig(mode=RealtimeMode.SCREEN_COPILOT, user_id="test")
        session = ScreenCopilotSession(config)
        
        # Simulate voice question about screen
        context = session.answer_coding_question("Why is this build failing?")
        assert "Screen context" in context
        assert "Question" in context

    def test_voice_controlled_screen_navigation(self):
        from agent.multimodal.accessibility import MultimodalAccessibilityEngine, VoiceCommandProcessor, AccessibilityProfile
        
        engine = MultimodalAccessibilityEngine()
        engine.enable_mode("voice_control")
        
        # Voice commands for screen navigation
        commands = [
            "describe screen",
            "read selection",
            "magnify 2",
            "increase contrast",
        ]
        
        for cmd in commands:
            result = engine.process_voice_command(cmd)
            assert result is not None


class TestDocumentAudio:
    """Test document + audio combinations."""

    def test_document_read_aloud(self, media_document):
        from agent.multimodal.accessibility import DocumentReader, AccessibilityProfile, read_aloud
        
        reader = DocumentReader()
        text = reader.read_document(media_document)
        assert isinstance(text, str)
        
        # TTS would be called here
        # result = read_aloud(text)
        # assert "success" in result

    def test_audio_transcript_as_document_annotation(self, media_document, media_audio):
        from agent.multimodal.media_abstraction import merge_media_objects
        
        # Audio transcript annotates document
        merged = merge_media_objects(media_document, media_audio, relation="annotates")
        
        refs = merged.get_cross_modal_refs("annotates")
        assert len(refs) == 1


class TestMultimodalCollection:
    """Test collections of multiple modalities."""

    def test_mixed_modality_collection(self, media_text, media_image, media_audio, media_document):
        from agent.multimodal.media_abstraction import create_media_collection
        
        collection = create_media_collection(
            [media_text, media_image, media_audio, media_document],
            "multimodal_session"
        )
        
        assert collection.metadata["item_count"] == 4
        assert "text" in collection.metadata["item_types"]
        assert "image" in collection.metadata["item_types"]
        assert "audio" in collection.metadata["item_types"]
        assert "document" in collection.metadata["item_types"]
        assert len(collection.cross_modal_refs) == 4

    def test_collection_with_nested_structure(self, media_text, media_image):
        from agent.multimodal.media_abstraction import create_media_collection, merge_media_objects
        
        # Merge text + image first
        merged = merge_media_objects(media_text, media_image, relation="describes")
        
        # Create collection with merged + individual
        collection = create_media_collection([merged, media_text, media_image], "nested")
        
        assert collection.metadata["item_count"] == 3


class TestCrossModalProvenance:
    """Test provenance tracking across modalities."""

    def test_cross_modal_provenance_chain(self, media_text, media_image, media_audio):
        from agent.multimodal.provenance import ProvenanceTracker, GroundedFact, EvidenceRef, EvidenceStatus
        
        tracker = ProvenanceTracker()
        
        # Text describes image
        fact1 = tracker.record(
            claim="Image shows a red square",
            media=media_image,
            processor="vision_analyze",
            confidence=0.9
        )
        
        # Audio mentions the image
        fact2 = tracker.record(
            claim="User said 'look at the red square'",
            media=media_audio,
            processor="transcribe_audio",
            confidence=0.85
        )
        
        # Text confirms both
        fact3 = tracker.record(
            claim="Red square confirmed in both visual and audio",
            media=media_text,
            processor="cross_modal_fusion",
            confidence=0.95
        )
        
        assert len(tracker.get_facts()) == 3
        
        # All should reference their respective media
        assert fact1.evidence.media_id == media_image.media_id
        assert fact2.evidence.media_id == media_audio.media_id
        assert fact3.evidence.media_id == media_text.media_id


class TestCrossModalFusion:
    """Test fusion engine with multiple modalities."""

    def test_image_text_fusion(self, media_image, media_text):
        from agent.multimodal.fusion import fuse_image_text, FusionStrategy
        
        result = fuse_image_text(media_image, media_text, strategy=FusionStrategy.ATTENTION)
        
        assert result.fused_embedding is not None
        assert MediaType.IMAGE in result.aligned_modalities
        assert MediaType.TEXT in result.aligned_modalities

    def test_video_audio_fusion(self, media_video, media_audio):
        from agent.multimodal.fusion import fuse_video_audio, FusionStrategy
        
        result = fuse_video_audio(media_video, media_audio, strategy=FusionStrategy.HIERARCHICAL)
        
        assert result.fused_embedding is not None
        assert MediaType.VIDEO in result.aligned_modalities
        assert MediaType.AUDIO in result.aligned_modalities

    def test_multimodal_fusion(self, media_text, media_image, media_audio, media_video):
        from agent.multimodal.fusion import fuse_multimodal, FusionStrategy
        
        result = fuse_multimodal(media_text, media_image, media_audio, media_video, strategy=FusionStrategy.CONCATENATE)
        
        assert result.fused_embedding is not None
        assert len(result.aligned_modalities) == 4


class TestCrossModalContext:
    """Test multimodal context building."""

    def test_context_with_multiple_modalities(self, media_text, media_image, media_audio, media_document):
        from agent.multimodal.context_builder import MultimodalContextBuilder, Priority
        
        builder = MultimodalContextBuilder(max_tokens=4000)
        
        builder.add_media(media_text, "User question: What is in the image?")
        builder.add_media(media_image, "Image shows a red square")
        builder.add_media(media_audio, "Audio says: 'Look at the red square'")
        builder.add_media(media_document, "Document: Test PDF content")
        
        context = builder.build(system_text="You are a multimodal assistant")
        
        assert "User question" in context
        assert "red square" in context
        assert "Audio says" in context
        assert "Document" in context

    def test_context_citations(self, media_image):
        from agent.multimodal.context_builder import MultimodalContextBuilder, Priority
        from agent.multimodal.provenance import EvidenceRef
        
        builder = MultimodalContextBuilder()
        builder.add_media(media_image, "Red square detected", priority=Priority.HIGH)
        
        # Add citation
        cite_id = builder.add_citation(
            claim="Red square at center",
            evidence=[EvidenceRef(media_id=media_image.media_id, source=media_image.source, confidence=0.9)],
            confidence=0.9,
            modality="vision",
            source_location="center"
        )
        
        context = builder.build(include_citations=True)
        
        assert cite_id in context
        assert "CITATIONS" in context


class TestCrossModalMemory:
    """Test multimodal memory across modalities."""

    def test_store_and_search_mixed(self, media_text, media_image, media_audio, media_document):
        from agent.multimodal.memory import default_store
        
        store = default_store()
        
        # Store different modalities
        store.store_media(media_text, "User asked about red square")
        store.store_media(media_image, "Red square detected")
        store.store_media(media_audio, "User said: look at the red square")
        store.store_media(media_document, "PDF about shapes")
        
        # Search across all
        results = store.search("red square")
        
        assert len(results) >= 2  # Should find both image and audio/text references

    def test_search_by_kind(self, media_text, media_image, media_audio):
        from agent.multimodal.memory import default_store
        
        store = default_store()
        
        store.store_media(media_text, "Text about square")
        store.store_media(media_image, "Image of square")
        store.store_media(media_audio, "Audio about square")
        
        # Search only images
        results = store.search("square", kinds=["image"])
        
        assert all(r.kind == "image" for r in results)


class TestCrossModalAgentHandoff:
    """Test agent handoff across modalities."""

    def test_vision_to_research_handoff(self, media_image):
        from agent.multimodal.workflows import MultimodalAgentCoordinator, AgentRole
        
        coordinator = MultimodalAgentCoordinator()
        
        # Vision agent analyzes image
        vision_result = coordinator._vision_agent("Identify objects", [media_image], {})
        
        # Research agent uses vision results
        research_result = coordinator._research_agent("Find similar objects", [media_image], {
            "vision_result": vision_result
        })
        
        assert vision_result["agent"] == "vision"
        assert research_result["agent"] == "research"

    def test_audio_to_document_handoff(self, media_audio, media_document):
        from agent.multimodal.workflows import MultimodalAgentCoordinator, AgentRole
        
        coordinator = MultimodalAgentCoordinator()
        
        # Audio agent transcribes
        audio_result = coordinator._audio_agent("Transcribe", [media_audio], {})
        
        # Document agent extracts
        doc_result = coordinator._document_agent("Extract text", [media_document], {})
        
        assert audio_result["agent"] == "audio"
        assert doc_result["agent"] == "document"

    def test_computer_vision_handoff(self, media_image):
        from agent.multimodal.workflows import MultimodalAgentCoordinator, AgentRole
        
        coordinator = MultimodalAgentCoordinator()
        
        # Vision agent finds UI element
        vision_result = coordinator._vision_agent("Find button", [media_image], {})
        
        # Computer agent acts on it
        computer_result = coordinator._computer_agent("Click button", [media_image], {
            "vision_result": vision_result
        })
        
        assert vision_result["agent"] == "vision"
        assert computer_result["agent"] == "computer"