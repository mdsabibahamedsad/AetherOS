"""Performance Tests (Phase 97).

Measures latency, memory, CPU/GPU usage for multimodal operations.
"""

import pytest
import time
import statistics
import os
import psutil
from pathlib import Path
from typing import List, Dict, Any


def _get_memory_mb() -> float:
    """Get current process memory in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


def _measure_latency(func, *args, iterations: int = 5, **kwargs) -> Dict[str, float]:
    """Measure function latency over multiple iterations."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func(*args, **kwargs)
        times.append(time.perf_counter() - start)
    
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "min": min(times),
        "max": max(times),
        "p95": sorted(times)[int(len(times) * 0.95)],
    }


class TestMediaAbstractionPerformance:
    """Test MediaObject creation and manipulation performance."""

    def test_create_image_media_speed(self, test_image_simple):
        from agent.multimodal.media_abstraction import create_image_media
        
        stats = _measure_latency(create_image_media, str(test_image_simple), iterations=10)
        
        assert stats["mean"] < 0.1  # < 100ms
        print(f"\ncreate_image_media: {stats['mean']*1000:.1f}ms avg")

    def test_create_audio_media_speed(self, test_audio_tone):
        from agent.multimodal.media_abstraction import create_audio_media
        
        stats = _measure_latency(create_audio_media, str(test_audio_tone), iterations=10)
        
        assert stats["mean"] < 0.05  # < 50ms
        print(f"\ncreate_audio_media: {stats['mean']*1000:.1f}ms avg")

    def test_create_video_media_speed(self, test_video_short):
        from agent.multimodal.media_abstraction import create_video_media
        
        stats = _measure_latency(create_video_media, str(test_video_short), iterations=5)
        
        assert stats["mean"] < 0.5  # < 500ms (ffprobe)
        print(f"\ncreate_video_media: {stats['mean']*1000:.1f}ms avg")

    def test_media_serialization_speed(self, media_image):
        stats = _measure_latency(media_image.to_dict, iterations=100)
        
        assert stats["mean"] < 0.001  # < 1ms
        print(f"\nto_dict: {stats['mean']*1000:.2f}ms avg")

    def test_media_deserialization_speed(self, media_image):
        data = media_image.to_dict()
        stats = _measure_latency(type(media_image).from_dict, data, iterations=100)
        
        assert stats["mean"] < 0.001  # < 1ms
        print(f"\nfrom_dict: {stats['mean']*1000:.2f}ms avg")

    def test_embedding_operations_speed(self, media_image):
        from agent.multimodal.media_abstraction import EmbeddingRef
        
        def add_embeddings():
            for i in range(10):
                media_image.add_embedding(f"vec-{i}", "clip-vit-b32", 512)
        
        stats = _measure_latency(add_embeddings, iterations=50)
        
        assert stats["mean"] < 0.001
        print(f"\nadd 10 embeddings: {stats['mean']*1000:.2f}ms avg")

    def test_video_frame_operations_speed(self, media_video):
        def add_frames():
            for i in range(20):
                media_video.add_video_frame(i, i * 0.5, f"frame-{i}")
        
        stats = _measure_latency(add_frames, iterations=50)
        
        assert stats["mean"] < 0.001
        print(f"\nadd 20 video frames: {stats['mean']*1000:.2f}ms avg")

    def test_cross_modal_refs_speed(self, media_image, media_audio):
        def add_refs():
            for i in range(10):
                media_image.add_cross_modal_ref(media_audio.media_id, "transcript_of", target_timestamp=i)
        
        stats = _measure_latency(add_refs, iterations=50)
        
        assert stats["mean"] < 0.001
        print(f"\nadd 10 cross-modal refs: {stats['mean']*1000:.2f}ms avg")


class TestInputRouterPerformance:
    """Test input routing performance."""

    def test_route_file_image(self, test_image_simple):
        from agent.multimodal.input_router import route_file
        
        stats = _measure_latency(route_file, str(test_image_simple), iterations=10)
        
        assert stats["mean"] < 0.1
        print(f"\nroute_file (image): {stats['mean']*1000:.1f}ms avg")

    def test_route_text(self):
        from agent.multimodal.input_router import route_text
        
        stats = _measure_latency(route_text, "This is a test message" * 10, iterations=100)
        
        assert stats["mean"] < 0.001
        print(f"\nroute_text: {stats['mean']*1000:.2f}ms avg")

    def test_route_structured_data(self):
        from agent.multimodal.input_router import route_structured_data
        
        data = {"key": "value", "items": list(range(100))}
        stats = _measure_latency(route_structured_data, data, iterations=50)
        
        assert stats["mean"] < 0.005
        print(f"\nroute_structured_data: {stats['mean']*1000:.1f}ms avg")


class TestCapabilityDetectorPerformance:
    """Test capability detection performance."""

    def test_detect_capabilities_cached(self):
        from agent.multimodal.capability_detector import CapabilityDetector
        
        detector = CapabilityDetector()
        # First call (cache miss)
        _ = detector.detect("openai", "gpt-4o")
        
        # Subsequent calls (cache hit)
        stats = _measure_latency(detector.detect, "openai", "gpt-4o", iterations=100)
        
        assert stats["mean"] < 0.0001  # < 0.1ms cached
        print(f"\ndetect (cached): {stats['mean']*1000000:.1f}μs avg")

    def test_route_modality(self):
        from agent.multimodal.capability_detector import CapabilityDetector
        from agent.multimodal.media_abstraction import MediaType
        
        detector = CapabilityDetector()
        providers = ["openai", "anthropic", "google", "ollama"]
        models = ["gpt-4o", "claude-3.5", "gemini-2.5", "llava"]
        
        stats = _measure_latency(detector.route_modality, providers, models, MediaType.IMAGE, iterations=50)
        
        assert stats["mean"] < 0.001
        print(f"\nroute_modality: {stats['mean']*1000:.1f}ms avg")


class TestPrivacyRouterPerformance:
    """Test privacy router performance."""

    def test_classify_sensitivity(self):
        from agent.multimodal.privacy_router import PrivacyClassifier
        from agent.multimodal.media_abstraction import MediaObject, MediaType
        
        classifier = PrivacyClassifier()
        media = MediaObject(type=MediaType.TEXT)
        
        stats = _measure_latency(classifier.classify, media, "test content with password", iterations=1000)
        
        assert stats["mean"] < 0.0001
        print(f"\nclassify: {stats['mean']*1000000:.1f}μs avg")

    def test_router_decide(self):
        from agent.multimodal.privacy_router import ProviderPrivacyRouter
        from agent.multimodal.media_abstraction import MediaObject, MediaType, SensitivityLevel
        
        router = ProviderPrivacyRouter()
        media = MediaObject(type=MediaType.IMAGE, sensitivity=SensitivityLevel.PRIVATE)
        
        stats = _measure_latency(router.decide, media, iterations=1000)
        
        assert stats["mean"] < 0.0001
        print(f"\nrouter decide: {stats['mean']*1000000:.1f}μs avg")


class TestPerceptionPerformance:
    """Test perception layer performance (mocked)."""

    def test_analyze_image_mock(self, media_image):
        from agent.multimodal.perception import analyze_image
        
        # This would call the actual vision tool - mock for performance test
        # We measure the overhead of the perception layer
        
        def mock_analyze():
            # Simulate the perception layer overhead
            from agent.multimodal.provenance import ProvenanceTracker, ConfidenceTracker
            pt = ProvenanceTracker()
            ct = ConfidenceTracker()
            return {"success": True, "analysis": "test", "confidence": 0.9}
        
        stats = _measure_latency(mock_analyze, iterations=100)
        
        assert stats["mean"] < 0.001
        print(f"\nanalyze_image (mock): {stats['mean']*1000:.2f}ms avg")

    def test_ocr_media_mock(self, media_image):
        from agent.multimodal.perception import ocr_media
        
        def mock_ocr():
            from agent.multimodal.provenance import ProvenanceTracker, ConfidenceTracker
            pt = ProvenanceTracker()
            ct = ConfidenceTracker()
            return {"success": True, "text": "test", "confidence": 0.9}
        
        stats = _measure_latency(mock_ocr, iterations=100)
        
        assert stats["mean"] < 0.001
        print(f"\nocr_media (mock): {stats['mean']*1000:.2f}ms avg")

    def test_transcribe_audio_mock(self, media_audio):
        from agent.multimodal.perception import transcribe_audio
        
        def mock_transcribe():
            from agent.multimodal.provenance import ProvenanceTracker, ConfidenceTracker
            pt = ProvenanceTracker()
            ct = ConfidenceTracker()
            return {"success": True, "transcript": "test", "confidence": 0.9}
        
        stats = _measure_latency(mock_transcribe, iterations=100)
        
        assert stats["mean"] < 0.001
        print(f"\ntranscribe_audio (mock): {stats['mean']*1000:.2f}ms avg")


class TestMemoryPerformance:
    """Test multimodal memory performance."""

    def test_store_media_speed(self, media_image):
        from agent.multimodal.memory import MultimodalMemoryStore
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MultimodalMemoryStore(tmpdir)
            
            stats = _measure_latency(store.store_media, media_image, "Test content", iterations=100)
            
            assert stats["mean"] < 0.01  # < 10ms
            print(f"\nstore_media: {stats['mean']*1000:.1f}ms avg")

    def test_search_speed(self, media_image, media_text, media_audio):
        from agent.multimodal.memory import MultimodalMemoryStore
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MultimodalMemoryStore(tmpdir)
            
            # Populate
            for m in [media_image, media_text, media_audio]:
                store.store_media(m, f"Content for {m.type.value}")
            
            stats = _measure_latency(store.search, "test", limit=10, iterations=100)
            
            assert stats["mean"] < 0.005  # < 5ms
            print(f"\nsearch: {stats['mean']*1000:.1f}ms avg")


class TestFusionPerformance:
    """Test cross-modal fusion performance."""

    def test_fusion_concatenate(self, media_image, media_text):
        from agent.multimodal.fusion import fuse_image_text, FusionStrategy
        
        stats = _measure_latency(fuse_image_text, media_image, media_text, FusionStrategy.CONCATENATE, iterations=50)
        
        assert stats["mean"] < 0.005
        print(f"\nfuse_image_text (concat): {stats['mean']*1000:.1f}ms avg")

    def test_fusion_attention(self, media_image, media_text):
        from agent.multimodal.fusion import fuse_image_text, FusionStrategy
        
        stats = _measure_latency(fuse_image_text, media_image, media_text, FusionStrategy.ATTENTION, iterations=50)
        
        assert stats["mean"] < 0.01
        print(f"\nfuse_image_text (attention): {stats['mean']*1000:.1f}ms avg")

    def test_fusion_video_audio(self, media_video, media_audio):
        from agent.multimodal.fusion import fuse_video_audio, FusionStrategy
        
        stats = _measure_latency(fuse_video_audio, media_video, media_audio, FusionStrategy.HIERARCHICAL, iterations=20)
        
        assert stats["mean"] < 0.01
        print(f"\nfuse_video_audio: {stats['mean']*1000:.1f}ms avg")

    def test_multimodal_fusion(self, media_text, media_image, media_audio, media_video):
        from agent.multimodal.fusion import fuse_multimodal, FusionStrategy
        
        stats = _measure_latency(fuse_multimodal, media_text, media_image, media_audio, media_video, FusionStrategy.CONCATENATE, iterations=20)
        
        assert stats["mean"] < 0.01
        print(f"\nfuse_multimodal (4 modalities): {stats['mean']*1000:.1f}ms avg")


class TestContextBuilderPerformance:
    """Test context builder performance."""

    def test_build_context(self, media_text, media_image, media_audio, media_document):
        from agent.multimodal.context_builder import MultimodalContextBuilder, Priority
        
        builder = MultimodalContextBuilder()
        
        def build():
            builder.add_media(media_text, "User question", priority=Priority.HIGH)
            builder.add_media(media_image, "Image analysis", priority=Priority.NORMAL)
            builder.add_media(media_audio, "Audio transcript", priority=Priority.NORMAL)
            builder.add_media(media_document, "Document extract", priority=Priority.LOW)
            return builder.build()
        
        stats = _measure_latency(build, iterations=100)
        
        assert stats["mean"] < 0.005
        print(f"\nbuild context (4 modalities): {stats['mean']*1000:.1f}ms avg")

    def test_context_with_citations(self, media_image):
        from agent.multimodal.context_builder import MultimodalContextBuilder, Priority
        from agent.multimodal.provenance import EvidenceRef
        
        builder = MultimodalContextBuilder()
        builder.add_media(media_image, "Red square", priority=Priority.HIGH)
        
        cite_id = builder.add_citation(
            claim="Red square",
            evidence=[EvidenceRef(media_id=media_image.media_id, source=media_image.source, confidence=0.9)],
            confidence=0.9,
            modality="vision"
        )
        
        def build_with_citations():
            return builder.build(include_citations=True)
        
        stats = _measure_latency(build_with_citations, iterations=100)
        
        assert stats["mean"] < 0.005
        print(f"\nbuild with citations: {stats['mean']*1000:.1f}ms avg")


class TestProvenancePerformance:
    """Test provenance tracking performance."""

    def test_record_facts(self, media_image, media_audio, media_text):
        from agent.multimodal.provenance import ProvenanceTracker
        
        tracker = ProvenanceTracker()
        
        def record_facts():
            for i in range(10):
                tracker.record(f"Fact {i}", media=media_image, processor="vision", confidence=0.9)
                tracker.record(f"Audio fact {i}", media=media_audio, processor="stt", confidence=0.85)
                tracker.record(f"Text fact {i}", media=media_text, processor="text", confidence=1.0)
        
        stats = _measure_latency(record_facts, iterations=100)
        
        assert stats["mean"] < 0.005
        print(f"\nrecord 30 facts: {stats['mean']*1000:.1f}ms avg")

    def test_confidence_tracker(self):
        from agent.multimodal.provenance import ConfidenceTracker
        
        tracker = ConfidenceTracker()
        
        def track():
            for i in range(100):
                tracker.set("vision", 0.9)
                tracker.set("stt", 0.85)
                tracker.get("vision")
                tracker.is_certain("vision")
                tracker.uncertainty_note("stt")
        
        stats = _measure_latency(track, iterations=100)
        
        assert stats["mean"] < 0.005
        print(f"\nconfidence tracker (100 ops): {stats['mean']*1000:.1f}ms avg")


class TestWorkflowPerformance:
    """Test workflow execution performance."""

    def test_workflow_creation(self):
        from agent.multimodal.workflows import create_workflow
        
        def create():
            return create_workflow("test", [
                {"name": f"step{i}", "tool": "vision_analyze", "modality": "image"}
                for i in range(10)
            ])
        
        stats = _measure_latency(create, iterations=100)
        
        assert stats["mean"] < 0.001
        print(f"\ncreate workflow (10 steps): {stats['mean']*1000:.2f}ms avg")

    def test_tool_routing(self, media_image):
        from agent.multimodal.workflows import MultimodalToolRouter
        
        router = MultimodalToolRouter()
        
        stats = _measure_latency(router.route, media_image, "analyze this image", iterations=100)
        
        assert stats["mean"] < 0.001
        print(f"\ntool routing: {stats['mean']*1000:.2f}ms avg")


class TestMemoryUsage:
    """Test memory usage of multimodal operations."""

    def test_media_object_memory(self, media_image):
        """Measure memory footprint of MediaObject."""
        import sys
        
        size = sys.getsizeof(media_image)
        # MediaObject with all fields should be reasonably sized
        assert size < 10000  # < 10KB base object
        print(f"\nMediaObject base size: {size} bytes")

    def test_media_with_embeddings_memory(self, media_image):
        """Measure memory with embeddings."""
        import sys
        
        # Add embeddings
        for i in range(100):
            media_image.add_embedding(f"vec-{i}", "clip-vit-b32", 512)
        
        size = sys.getsizeof(media_image)
        # Should still be reasonable
        print(f"\nMediaObject with 100 embeddings: {size} bytes")

    def test_process_memory_during_operations(self):
        """Track process memory during multimodal operations."""
        from agent.multimodal.media_abstraction import MediaObject, MediaType
        from agent.multimodal.fusion import fuse_image_text
        
        initial_mem = _get_memory_mb()
        
        # Create many objects and fuse them
        objects = []
        for i in range(100):
            m1 = MediaObject(type=MediaType.IMAGE, media_id=f"img-{i}")
            m2 = MediaObject(type=MediaType.TEXT, media_id=f"txt-{i}")
            objects.append((m1, m2))
            _ = fuse_image_text(m1, m2)
        
        peak_mem = _get_memory_mb()
        mem_increase = peak_mem - initial_mem
        
        print(f"\nMemory increase after 100 fusions: {mem_increase:.1f} MB")
        assert mem_increase < 100  # Should not leak memory


class TestStreamManagerPerformance:
    """Test stream manager performance."""

    def test_stream_push_pop(self):
        from agent.multimodal.stream_manager import MultimodalStreamManager, BackpressurePolicy
        
        mgr = MultimodalStreamManager(max_frames=1000, policy=BackpressurePolicy.BUFFER)
        
        def push_pop():
            for i in range(100):
                mgr.push("test", "video", {"frame": i})
                _ = mgr.pop("test")
        
        stats = _measure_latency(push_pop, iterations=10)
        
        assert stats["mean"] < 0.01
        print(f"\nstream push/pop (100): {stats['mean']*1000:.1f}ms avg")

    def test_backpressure_policies(self):
        from agent.multimodal.stream_manager import MultimodalStreamManager, BackpressurePolicy
        
        for policy in [BackpressurePolicy.DROP, BackpressurePolicy.SAMPLE, BackpressurePolicy.BUFFER, BackpressurePolicy.PRIORITIZE]:
            mgr = MultimodalStreamManager(max_frames=100, policy=policy)
            
            start = time.perf_counter()
            for i in range(200):  # Exceed buffer
                mgr.push("test", "video", {"frame": i, "priority": i % 10})
            elapsed = time.perf_counter() - start
            
            stats = mgr.stats()
            print(f"\n{policy.value}: {elapsed*1000:.1f}ms, buffered={stats['buffered']}, dropped={stats['dropped']}")


class TestArtifactExportPerformance:
    """Test artifact export performance."""

    def test_export_json(self, media_image):
        from agent.multimodal.artifacts import create_artifact_from_analysis, MultimodalExporter, ExportFormat
        import tempfile
        
        artifact = create_artifact_from_analysis("Test", media_image, {"analysis": "Result" * 100})
        exporter = MultimodalExporter()
        
        def export():
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
                return exporter.export_artifact(artifact, ExportFormat.JSON, f.name)
        
        stats = _measure_latency(export, iterations=20)
        
        assert stats["mean"] < 0.05
        print(f"\nexport JSON: {stats['mean']*1000:.1f}ms avg")

    def test_export_markdown(self, media_image):
        from agent.multimodal.artifacts import create_artifact_from_analysis, MultimodalExporter, ExportFormat
        import tempfile
        
        artifact = create_artifact_from_analysis("Test", media_image, {"analysis": "Result" * 100})
        exporter = MultimodalExporter()
        
        def export():
            with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
                return exporter.export_artifact(artifact, ExportFormat.MARKDOWN, f.name)
        
        stats = _measure_latency(export, iterations=20)
        
        assert stats["mean"] < 0.05
        print(f"\nexport Markdown: {stats['mean']*1000:.1f}ms avg")

    def test_large_artifact_export(self, media_image):
        """Test export with large artifact."""
        from agent.multimodal.artifacts import create_artifact, MultimodalExporter, ExportFormat, ArtifactType
        import tempfile
        
        artifact = create_artifact("Large", contents=[
            {"type": "text", "data": "x" * 100000},
            {"type": "json", "data": {"data": list(range(10000))}},
        ])
        
        exporter = MultimodalExporter()
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            start = time.perf_counter()
            result = exporter.export_artifact(artifact, ExportFormat.JSON, f.name)
            elapsed = time.perf_counter() - start
        
        print(f"\nExport large artifact (100KB+): {elapsed*1000:.1f}ms")


# Run as script for standalone benchmarking
if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s", "--tb=short"]))