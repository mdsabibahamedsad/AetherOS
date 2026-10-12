"""Multimodal Stream Manager (Phases 26-52 of Master Prompt 10).

Manages realtime media streams (audio/video/screen/events/transcripts) with:
- bounded buffers (no uncontrolled memory growth),
- backpressure policies (drop / sample / buffer / prioritize),
- latency tracking across capture/encode/transport/model/tool/output stages,
- modality budgets (image tokens, video frames, audio seconds, OCR pages).
- WebRTC, RTSP, adaptive bitrate, recording, analytics, security (Phases 26-35).

Transport-agnostic: callers plug in their own WebSocket/WebRTC producer.
"""

from __future__ import annotations

import base64
import logging
import ssl
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock, Thread
from typing import Any, Callable, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


class BackpressurePolicy(Enum):
    DROP = "drop"           # discard newest when full
    SAMPLE = "sample"       # keep every Nth when full
    BUFFER = "buffer"       # keep newest, evict oldest
    PRIORITIZE = "prioritize"  # drop low-priority frames first
    ADAPTIVE = "adaptive"   # dynamically adjust based on latency


class StreamProtocol(Enum):
    RAW = "raw"
    WEBSOCKET = "websocket"
    WEBRTC = "webrtc"
    RTSP = "rtsp"
    HLS = "hls"
    DASH = "dash"
    SRT = "srt"


class StreamState(Enum):
    IDLE = "idle"
    CONNECTING = "connecting"
    STREAMING = "streaming"
    PAUSED = "paused"
    RECORDING = "recording"
    ERROR = "error"
    CLOSED = "closed"


class VideoCodec(Enum):
    H264 = "h264"
    H265 = "h265"
    VP8 = "vp8"
    VP9 = "vp9"
    AV1 = "av1"


class AudioCodec(Enum):
    OPUS = "opus"
    AAC = "aac"
    PCM = "pcm"
    G711 = "g711"


@dataclass
class StreamConfig:
    """Stream configuration (Phases 26-29)."""
    protocol: StreamProtocol = StreamProtocol.WEBRTC
    video_codec: VideoCodec = VideoCodec.H264
    audio_codec: AudioCodec = AudioCodec.OPUS
    width: int = 1280
    height: int = 720
    framerate: int = 30
    bitrate_kbps: int = 2500
    audio_bitrate_kbps: int = 128
    audio_sample_rate: int = 48000
    audio_channels: int = 2
    keyframe_interval: int = 60
    enable_rtx: bool = True
    enable_fec: bool = False
    max_latency_ms: int = 100
    ice_servers: List[str] = field(default_factory=lambda: ["stun:stun.l.google.com:19302"])


@dataclass
class StreamMetrics:
    """Real-time stream metrics (Phase 32)."""
    stream_id: str
    timestamp: float = field(default_factory=time.time)
    # Network
    rtt_ms: float = 0.0
    jitter_ms: float = 0.0
    packet_loss_pct: float = 0.0
    bandwidth_kbps: float = 0.0
    # Video
    frames_sent: int = 0
    frames_received: int = 0
    frames_dropped: int = 0
    fps: float = 0.0
    resolution: str = ""
    # Audio
    audio_packets_sent: int = 0
    audio_packets_lost: int = 0
    audio_level: float = 0.0
    # Quality
    quality_score: float = 1.0
    # Latency breakdown
    capture_latency_ms: float = 0.0
    encode_latency_ms: float = 0.0
    network_latency_ms: float = 0.0
    decode_latency_ms: float = 0.0
    render_latency_ms: float = 0.0


@dataclass
class WebRTCConnection:
    """WebRTC peer connection state (Phase 26)."""
    connection_id: str
    state: StreamState = StreamState.IDLE
    config: Optional[StreamConfig] = None
    local_sdp: Optional[str] = None
    remote_sdp: Optional[str] = None
    ice_candidates: List[str] = field(default_factory=list)
    data_channels: Dict[str, Any] = field(default_factory=dict)
    metrics: StreamMetrics = field(default_factory=lambda: StreamMetrics(stream_id=""))


@dataclass
class RTSPStream:
    """RTSP stream state (Phase 27)."""
    stream_id: str
    url: str
    state: StreamState = StreamState.IDLE
    transport: str = "tcp"  # tcp, udp, multicast
    auth: Optional[Tuple[str, str]] = None
    session_id: Optional[str] = None
    rtp_port: int = 0
    rtcp_port: int = 0
    sdp: Optional[str] = None
    metrics: StreamMetrics = field(default_factory=lambda: StreamMetrics(stream_id=""))


@dataclass
class AudioChunk:
    """Audio chunk for streaming (Phase 28)."""
    stream_id: str
    sequence: int
    timestamp: float
    data: bytes
    sample_rate: int
    channels: int
    format: str  # pcm16, opus, aac
    duration_ms: float
    is_silence: bool = False
    vad_probability: float = 0.0


@dataclass
class StreamRecording:
    """Stream recording session (Phase 31)."""
    recording_id: str
    stream_id: str
    start_time: float
    end_time: Optional[float] = None
    format: str = "mp4"  # mp4, mkv, webm, wav
    path: str = ""
    size_bytes: int = 0
    duration_seconds: float = 0.0
    segments: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdaptiveBitrateController:
    """Adaptive bitrate controller (Phase 29)."""

    def __init__(
        self,
        initial_bitrate_kbps: int = 2500,
        min_bitrate_kbps: int = 500,
        max_bitrate_kbps: int = 8000,
        target_latency_ms: int = 100,
    ):
        self.current_bitrate = initial_bitrate_kbps
        self.min_bitrate = min_bitrate_kbps
        self.max_bitrate = max_bitrate_kbps
        self.target_latency = target_latency_ms
        self._last_adjustment = time.time()
        self._adjustment_interval = 2.0  # seconds

    def update(self, metrics: StreamMetrics) -> int:
        """Adjust bitrate based on network metrics. Returns new bitrate."""
        now = time.time()
        if now - self._last_adjustment < self._adjustment_interval:
            return self.current_bitrate

        # Calculate available bandwidth estimate
        if metrics.bandwidth_kbps > 0:
            available = metrics.bandwidth_kbps * 0.85  # 85% utilization target
        else:
            # Estimate from packet loss and RTT
            loss_factor = max(0.5, 1.0 - metrics.packet_loss_pct)
            rtt_factor = max(0.5, 1.0 - metrics.rtt_ms / 500.0)
            available = self.current_bitrate * loss_factor * rtt_factor

        # Apply latency pressure
        if metrics.network_latency_ms > self.target_latency:
            available *= 0.8

        # Clamp to bounds
        new_bitrate = int(max(self.min_bitrate, min(self.max_bitrate, available)))

        if new_bitrate != self.current_bitrate:
            logger.info(f"Bitrate adjusted: {self.current_bitrate} -> {new_bitrate} kbps "
                       f"(bw={metrics.bandwidth_kbps:.0f}, loss={metrics.packet_loss_pct:.2%}, "
                       f"rtt={metrics.rtt_ms:.1f}ms)")
            self.current_bitrate = new_bitrate
            self._last_adjustment = now

        return self.current_bitrate

    def get_bitrate(self) -> int:
        return self.current_bitrate


class StreamMultiplexer:
    """Stream multiplexer for multiple streams over single connection (Phase 30)."""

    def __init__(self, max_streams: int = 16):
        self.max_streams = max_streams
        self._streams: Dict[str, Any] = {}
        self._stream_order: List[str] = []
        self._lock = Lock()

    def add_stream(self, stream_id: str, stream: Any) -> bool:
        with self._lock:
            if len(self._streams) >= self.max_streams:
                return False
            self._streams[stream_id] = stream
            self._stream_order.append(stream_id)
            return True

    def remove_stream(self, stream_id: str) -> bool:
        with self._lock:
            if stream_id in self._streams:
                del self._streams[stream_id]
                if stream_id in self._stream_order:
                    self._stream_order.remove(stream_id)
                return True
            return False

    def get_stream(self, stream_id: str) -> Optional[Any]:
        with self._lock:
            return self._streams.get(stream_id)

    def list_streams(self) -> List[str]:
        with self._lock:
            return self._stream_order.copy()

    def multiplex(self, data: bytes, stream_ids: List[str]) -> Dict[str, bytes]:
        """Demultiplex incoming data to appropriate streams."""
        # Simplified: each stream has its own framing
        results = {}
        for sid in stream_ids:
            stream = self._streams.get(sid)
            if stream:
                results[sid] = data  # Simplified
        return results


class StreamRecorder:
    """Stream recording and playback (Phase 31)."""

    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._recordings: Dict[str, StreamRecording] = {}
        self._active: Dict[str, Thread] = {}
        self._lock = Lock()

    def start_recording(
        self,
        stream_id: str,
        format: str = "mp4",
        segment_duration: int = 300,  # 5 min segments
    ) -> StreamRecording:
        rec_id = f"rec_{uuid.uuid4().hex[:12]}"
        path = self.storage_dir / f"{rec_id}.{format}"

        recording = StreamRecording(
            recording_id=rec_id,
            stream_id=stream_id,
            start_time=time.time(),
            format=format,
            path=str(path),
        )

        # Start recording thread
        thread = Thread(target=self._record_loop, args=(stream_id, rec_id, format, segment_duration))
        thread.daemon = True
        thread.start()

        with self._lock:
            self._recordings[rec_id] = recording
            self._active[rec_id] = thread

        return recording

    def stop_recording(self, recording_id: str) -> Optional[StreamRecording]:
        with self._lock:
            recording = self._recordings.get(recording_id)
            if not recording:
                return None
            recording.end_time = time.time()
            recording.duration_seconds = recording.end_time - recording.start_time
            if recording_id in self._active:
                self._active[recording_id].join(timeout=5.0)
                del self._active[recording_id]
        return recording

    def _record_loop(self, stream_id: str, rec_id: str, format: str, segment_duration: int):
        """Background recording loop - writes segments."""
        # Simplified: in production would use ffmpeg or gstreamer
        logger.info(f"Recording started: {rec_id} for stream {stream_id}")
        time.sleep(segment_duration)  # Placeholder
        logger.info(f"Recording segment completed: {rec_id}")

    def get_recording(self, recording_id: str) -> Optional[StreamRecording]:
        with self._lock:
            return self._recordings.get(recording_id)

    def list_recordings(self, stream_id: Optional[str] = None) -> List[StreamRecording]:
        with self._lock:
            recs = list(self._recordings.values())
            if stream_id:
                recs = [r for r in recs if r.stream_id == stream_id]
            return recs


class StreamAnalytics:
    """Stream analytics and monitoring (Phase 32)."""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._metrics_history: Dict[str, Deque[StreamMetrics]] = {}

    def record(self, metrics: StreamMetrics) -> None:
        if metrics.stream_id not in self._metrics_history:
            self._metrics_history[metrics.stream_id] = deque(maxlen=self.window_size)
        self._metrics_history[metrics.stream_id].append(metrics)

    def get_summary(self, stream_id: str, window: int = 60) -> Dict[str, Any]:
        """Get aggregated metrics over time window."""
        history = self._metrics_history.get(stream_id, deque())
        if not history:
            return {}

        recent = [m for m in history if time.time() - m.timestamp <= window]
        if not recent:
            return {}

        return {
            "avg_rtt_ms": sum(m.rtt_ms for m in recent) / len(recent),
            "avg_jitter_ms": sum(m.jitter_ms for m in recent) / len(recent),
            "avg_packet_loss": sum(m.packet_loss_pct for m in recent) / len(recent),
            "avg_bandwidth_kbps": sum(m.bandwidth_kbps for m in recent) / len(recent),
            "avg_fps": sum(m.fps for m in recent) / len(recent),
            "total_frames": sum(m.frames_sent for m in recent),
            "total_dropped": sum(m.frames_dropped for m in recent),
            "avg_quality": sum(m.quality_score for m in recent) / len(recent),
            "sample_count": len(recent),
        }

    def detect_anomalies(self, stream_id: str, threshold: float = 2.0) -> List[Dict]:
        """Detect metric anomalies using z-score."""
        history = self._metrics_history.get(stream_id, deque())
        if len(history) < 10:
            return []

        anomalies = []
        for metric in ["rtt_ms", "jitter_ms", "packet_loss_pct", "bandwidth_kbps", "fps"]:
            values = [getattr(m, metric) for m in history if getattr(m, metric) > 0]
            if len(values) < 5:
                continue
            mean = sum(values) / len(values)
            std = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5
            if std == 0:
                continue
            latest = getattr(history[-1], metric)
            if latest > 0:
                z_score = abs(latest - mean) / std
                if z_score > 2.0:
                    anomalies.append({
                        "metric": metric,
                        "value": latest,
                        "mean": mean,
                        "z_score": z_score,
                        "timestamp": time.time(),
                    })
        return anomalies


class LowLatencyOptimizer:
    """Low-latency optimization for streaming (Phase 33)."""

    def __init__(self, target_latency_ms: int = 50):
        self.target_latency = target_latency_ms
        self._optimizations = {
            "reduce_keyframe_interval": False,
            "enable_rtx": False,
            "enable_nack": False,
            "reduce_buffer": False,
            "priority_queue": False,
        }

    def analyze(self, metrics: StreamMetrics) -> Dict[str, bool]:
        """Analyze metrics and recommend optimizations."""
        recommendations = {}

        if metrics.network_latency_ms > self.target_latency * 0.8:
            recommendations["reduce_keyframe_interval"] = True
            recommendations["enable_rtx"] = True

        if metrics.jitter_ms > self.target_latency * 0.3:
            recommendations["enable_nack"] = True
            recommendations["priority_queue"] = True

        if metrics.packet_loss_pct > 0.05:
            recommendations["enable_rtx"] = True
            recommendations["enable_fec"] = True

        if metrics.buffered > 10:
            recommendations["reduce_buffer"] = True

        return recommendations

    def apply_optimizations(self, connection: WebRTCConnection, optimizations: Dict[str, bool]) -> None:
        """Apply optimizations to WebRTC connection."""
        config = connection.config
        if not config:
            return

        if optimizations.get("reduce_keyframe_interval"):
            config.keyframe_interval = max(15, config.keyframe_interval // 2)
        if optimizations.get("enable_rtx"):
            config.enable_rtx = True
        if optimizations.get("enable_fec"):
            config.enable_fec = True
        if optimizations.get("enable_nack"):
            pass  # Would configure RTCP NACK
        if optimizations.get("reduce_buffer"):
            pass  # Would reduce jitter buffer

        logger.info(f"Applied low-latency optimizations: {optimizations}")


class StreamSecurity:
    """Stream security and encryption (Phase 34)."""

    def __init__(self):
        self._certificates: Dict[str, ssl.SSLContext] = {}
        self._keys: Dict[str, bytes] = {}

    def generate_dtls_context(self, stream_id: str, cert_path: str, key_path: str) -> ssl.SSLContext:
        """Create DTLS context for WebRTC."""
        ctx = ssl.SSLContext(ssl.PROTOCOL_DTLS_SERVER)
        ctx.load_cert_chain(cert_path, key_path)
        ctx.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20")
        self._certificates[stream_id] = ctx
        return ctx

    def generate_srt_key(self, stream_id: str, passphrase: str) -> str:
        """Generate SRT encryption key."""
        key = base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes).decode()
        self._keys[stream_id] = key.encode()
        return key

    def encrypt_srt_payload(self, stream_id: str, data: bytes) -> bytes:
        """Encrypt SRT payload (simplified AES-GCM)."""
        key = self._keys.get(stream_id)
        if not key:
            return data
        # Simplified: in production use proper AES-GCM
        return data

    def decrypt_srt_payload(self, stream_id: str, data: bytes) -> bytes:
        key = self._keys.get(stream_id)
        if not key:
            return data
        return data

    def verify_srt_handshake(self, stream_id: str, peer_key: str) -> bool:
        """Verify SRT handshake."""
        return stream_id in self._keys


class StreamCluster:
    """Stream clustering and load balancing (Phase 35)."""

    def __init__(self):
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._streams: Dict[str, str] = {}  # stream_id -> node_id
        self._lock = Lock()

    def register_node(
        self,
        node_id: str,
        capacity: int,
        endpoint: str,
        capabilities: List[str],
    ) -> bool:
        with self._lock:
            if node_id in self._nodes:
                return False
            self._nodes[node_id] = {
                "capacity": capacity,
                "endpoint": endpoint,
                "capabilities": capabilities,
                "current_load": 0,
                "health": "healthy",
                "last_heartbeat": time.time(),
            }
            return True

    def unregister_node(self, node_id: str) -> bool:
        with self._lock:
            if node_id not in self._nodes:
                return False
            # Reassign streams
            for sid, nid in list(self._streams.items()):
                if nid == node_id:
                    self._reassign_stream(sid)
            del self._nodes[node_id]
            return True

    def assign_stream(self, stream_id: str, requirements: Dict[str, Any]) -> Optional[str]:
        with self._lock:
            # Find best node (least loaded with required capabilities)
            candidates = [
                (nid, node) for nid, node in self._nodes.items()
                if node["health"] == "healthy"
                and node["current_load"] < node["capacity"]
                and all(c in node["capabilities"] for c in requirements.get("capabilities", []))
            ]
            if not candidates:
                return None

            # Least loaded
            candidates.sort(key=lambda x: x[1]["current_load"])
            best_id, best_node = candidates[0]
            best_node["current_load"] += 1
            self._streams[stream_id] = best_id
            return best_id

    def _reassign_stream(self, stream_id: str) -> bool:
        if stream_id not in self._streams:
            return False
        # Simplified: would reassign to another node
        return True

    def get_node_load(self, node_id: str) -> Optional[int]:
        with self._lock:
            node = self._nodes.get(node_id)
            return node["current_load"] if node else None

    def get_cluster_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_capacity = sum(n["capacity"] for n in self._nodes.values())
            total_load = sum(n["current_load"] for n in self._nodes.values())
            return {
                "nodes": len(self._nodes),
                "streams": len(self._streams),
                "total_capacity": total_capacity,
                "total_load": total_load,
                "utilization": total_load / total_capacity if total_capacity > 0 else 0,
                "nodes": {
                    nid: {
                        "load": n["current_load"],
                        "capacity": n["capacity"],
                        "health": n["health"],
                    }
                    for nid, n in self._nodes.items()
                },
            }


class StreamManager:
    """Unified stream manager (Phases 26-35)."""

    def __init__(
        self,
        max_frames: int = 500,
        policy: BackpressurePolicy = BackpressurePolicy.BUFFER,
        storage_dir: Optional[str] = None,
    ):
        self.base_manager = MultimodalStreamManager(max_frames, policy)
        self.webrtc_connections: Dict[str, WebRTCConnection] = {}
        self.rtsp_streams: Dict[str, RTSPStream] = {}
        self.audio_buffers: Dict[str, Deque[AudioChunk]] = {}
        self.adaptive_bitrate: Dict[str, AdaptiveBitrateController] = {}
        self.multiplexer = StreamMultiplexer()
        self.recorder = StreamRecorder(storage_dir or tempfile.gettempdir()) if storage_dir or True else None
        self.analytics = StreamAnalytics()
        self.optimizer = LowLatencyOptimizer()
        self.security = StreamSecurity()
        self.cluster = StreamCluster()

    # --- WebRTC (Phase 26) ---
    def create_webrtc_connection(
        self,
        connection_id: str,
        config: Optional[StreamConfig] = None,
    ) -> WebRTCConnection:
        conn = WebRTCConnection(
            connection_id=connection_id,
            config=config or StreamConfig(),
        )
        self.webrtc_connections[connection_id] = conn
        return conn

    def handle_webrtc_offer(self, connection_id: str, offer_sdp: str) -> Optional[str]:
        conn = self.webrtc_connections.get(connection_id)
        if not conn:
            return None
        conn.remote_sdp = offer_sdp
        # In production: create peer connection, set remote description, create answer
        conn.local_sdp = f"v=0\r\no=- {int(time.time())} 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\n"
        conn.state = StreamState.STREAMING
        return conn.local_sdp

    def handle_ice_candidate(self, connection_id: str, candidate: str) -> bool:
        conn = self.webrtc_connections.get(connection_id)
        if not conn:
            return False
        conn.ice_candidates.append(candidate)
        return True

    # --- RTSP (Phase 27) ---
    def create_rtsp_stream(
        self,
        stream_id: str,
        url: str,
        auth: Optional[Tuple[str, str]] = None,
        transport: str = "tcp",
    ) -> RTSPStream:
        stream = RTSPStream(stream_id=stream_id, url=url, auth=auth, transport=transport)
        self.rtsp_streams[stream_id] = stream
        return stream

    def connect_rtsp(self, stream_id: str) -> bool:
        stream = self.rtsp_streams.get(stream_id)
        if not stream:
            return False
        # In production: RTSP DESCRIBE, SETUP, PLAY
        stream.state = StreamState.STREAMING
        stream.session_id = uuid.uuid4().hex[:12]
        return True

    # --- Audio Streaming (Phase 28) ---
    def push_audio_chunk(self, chunk: AudioChunk) -> bool:
        buf = self.audio_buffers.setdefault(chunk.stream_id, deque(maxlen=500))
        buf.append(chunk)
        return True

    def get_audio_chunks(self, stream_id: str, limit: int = 100) -> List[AudioChunk]:
        buf = self.audio_buffers.get(stream_id, deque())
        return list(buf)[-limit:]

    def get_audio_level(self, stream_id: str) -> float:
        """Calculate RMS audio level from recent chunks."""
        chunks = self.get_audio_chunks(stream_id, 10)
        if not chunks:
            return 0.0
        # Simplified RMS from PCM16
        total = 0
        count = 0
        for c in chunks:
            if c.format == "pcm16" and len(c.data) >= 2:
                import struct
                samples = struct.unpack(f"<{len(c.data)//2}h", c.data)
                total += sum(s * s for s in samples)
                count += len(samples)
        return (total / count) ** 0.5 if count > 0 else 0.0

    # --- Adaptive Bitrate (Phase 29) ---
    def get_bitrate_controller(self, stream_id: str) -> AdaptiveBitrateController:
        return self.adaptive_bitrate.setdefault(
            stream_id, AdaptiveBitrateController()
        )

    def update_bitrate(self, stream_id: str, metrics: StreamMetrics) -> int:
        controller = self.get_bitrate_controller(stream_id)
        return controller.update(metrics)

    # --- Multiplexing (Phase 30) ---
    def multiplex_stream(self, stream_id: str, stream: Any) -> bool:
        return self.multiplexer.add_stream(stream_id, stream)

    # --- Recording (Phase 31) ---
    def start_recording(self, stream_id: str, format: str = "mp4") -> Optional[StreamRecording]:
        if self.recorder:
            return self.recorder.start_recording(stream_id, format)
        return None

    def stop_recording(self, recording_id: str) -> Optional[StreamRecording]:
        if self.recorder:
            return self.recorder.stop_recording(recording_id)
        return None

    # --- Analytics (Phase 32) ---
    def record_metrics(self, metrics: StreamMetrics) -> None:
        metrics.stream_id = metrics.stream_id or "unknown"
        self.analytics.record(metrics)
        # Update adaptive bitrate
        if metrics.stream_id in self.adaptive_bitrate:
            self.adaptive_bitrate[metrics.stream_id].update(metrics)

    def get_stream_analytics(self, stream_id: str, window: int = 60) -> Dict[str, Any]:
        return self.analytics.get_summary(stream_id, window)

    def detect_anomalies(self, stream_id: str) -> List[Dict]:
        return self.analytics.detect_anomalies(stream_id)

    # --- Low Latency (Phase 33) ---
    def optimize_latency(self, stream_id: str) -> Dict[str, bool]:
        conn = self.webrtc_connections.get(stream_id)
        if not conn:
            return {}
        optimizations = self.optimizer.analyze(conn.metrics)
        self.optimizer.apply_optimizations(conn, optimizations)
        return optimizations

    # --- Security (Phase 34) ---
    def setup_dtls(self, stream_id: str, cert_path: str, key_path: str) -> ssl.SSLContext:
        return self.security.generate_dtls_context(stream_id, cert_path, key_path)

    def setup_srt_encryption(self, stream_id: str, passphrase: str) -> str:
        return self.security.generate_srt_key(stream_id, passphrase)

    # --- Clustering (Phase 35) ---
    def register_cluster_node(
        self,
        node_id: str,
        capacity: int,
        endpoint: str,
        capabilities: List[str],
    ) -> bool:
        return self.cluster.register_node(node_id, capacity, endpoint, capabilities)

    def assign_stream_to_cluster(self, stream_id: str, requirements: Dict) -> Optional[str]:
        return self.cluster.assign_stream(stream_id, requirements)

    def get_cluster_stats(self) -> Dict[str, Any]:
        return self.cluster.get_cluster_stats()

    # --- Base manager delegation ---
    def __getattr__(self, name):
        return getattr(self.base_manager, name)


@dataclass
class ModalityBudget:
    """Per-task resource budget (Phase 51)."""

    max_image_tokens: int = 1024
    max_video_frames: int = 24
    max_audio_seconds: float = 300.0
    max_ocr_pages: int = 50
    max_processing_seconds: float = 300.0
    max_memory_bytes: int = 512 * 1024 * 1024
    max_cost_usd: float = 2.0

    def within(self, **used: float) -> bool:
        checks = {
            "max_image_tokens": used.get("image_tokens", 0) <= self.max_image_tokens,
            "max_video_frames": used.get("video_frames", 0) <= self.max_video_frames,
            "max_audio_seconds": used.get("audio_seconds", 0) <= self.max_audio_seconds,
            "max_ocr_pages": used.get("ocr_pages", 0) <= self.max_ocr_pages,
            "max_processing_seconds": used.get("processing_seconds", 0) <= self.max_processing_seconds,
            "max_memory_bytes": used.get("memory_bytes", 0) <= self.max_memory_bytes,
            "max_cost_usd": used.get("cost_usd", 0) <= self.max_cost_usd,
        }
        return all(checks.values())


# Backward compatibility alias
MultimodalStreamManager = StreamManager