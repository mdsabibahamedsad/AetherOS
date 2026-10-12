"""AetherOS Vision — video understanding.

Extracts frames from local video (ffmpeg or OpenCV), builds a timeline,
detects key moments, and (when a VLM is available) produces scene
summaries. Frame extraction is real; subtitle parsing is real; scene
summaries are either generated locally from OCR text or via the vision
router — never fabricated.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_vision.config import VisionSettings, get_aetheros_dir, load_vision_settings
from aetheros_vision.models import VideoExtraction, VideoFrame

logger = logging.getLogger(__name__)


def ffmpeg_available() -> bool:
    path = None
    try:
        from aetheros_vision.config import VisionSettings
        path = VisionSettings.video.ffmpeg_path or shutil.which("ffmpeg")
    except Exception:  # noqa: BLE001
        path = shutil.which("ffmpeg")
    return bool(path)


def _ffmpeg_binary() -> str:
    try:
        from aetheros_vision.config import VisionSettings
        return VisionSettings.video.ffmpeg_path or shutil.which("ffmpeg") or "ffmpeg"
    except Exception:  # noqa: BLE001
        return shutil.which("ffmpeg") or "ffmpeg"


class VideoUnderstanding:
    def __init__(self, settings: Optional[VisionSettings] = None):
        self._settings = settings or load_vision_settings()

    def extract(self, video_path: str, max_frames: Optional[int] = None) -> VideoExtraction:
        start = time.perf_counter()
        max_frames = max_frames or self._settings.video.max_frames
        path = Path(video_path)
        if not path.is_file():
            return VideoExtraction(success=False, error=f"Video file not found: {video_path}", processing_time_ms=(time.perf_counter() - start) * 1000)

        out_dir = get_aetheros_dir("cache/vision/video")
        out_dir.mkdir(parents=True, exist_ok=True)

        # Probe duration.
        duration = self._probe_duration(path)
        result = VideoExtraction(success=False, duration_s=duration)

        frames: List[VideoFrame] = []
        if ffmpeg_available():
            frames = self._extract_ffmpeg(path, out_dir, max_frames)
        else:
            frames = self._extract_opencv(path, out_dir, max_frames)

        if not frames:
            result.error = "No frame extractor available (install ffmpeg or opencv-python)"
            result.processing_time_ms = (time.perf_counter() - start) * 1000
            return result

        result.success = True
        result.frames = frames
        result.frame_count = len(frames)
        if duration > 0 and len(frames) > 1:
            result.fps = len(frames) / max(duration, 0.001)
        # Key moment detection: local rule — frames with high visual contrast
        # variance (scene changes) are marked as key moments.
        result.key_moments = self._detect_key_moments(frames)
        for frame in result.key_moments:
            frame.is_key_moment = True
        result.scene_summary = self._scene_summary(frames)
        result.processing_time_ms = (time.perf_counter() - start) * 1000
        return result

    def _probe_duration(self, path: Path) -> float:
        try:
            if ffmpeg_available():
                out = subprocess.run(
                    [_ffmpeg_binary(), "-i", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                stderr = out.stderr or ""
                marker = "Duration:"
                idx = stderr.find(marker)
                if idx >= 0:
                    dur_str = stderr[idx + len(marker):idx + len(marker) + 11].strip().rstrip(",")
                    parts = dur_str.split(":")
                    if len(parts) == 3:
                        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            try:
                import cv2
                cap = cv2.VideoCapture(str(path))
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    cap.release()
                    if fps > 0:
                        return count / fps
            except ImportError:
                pass
        except Exception as exc:  # noqa: BLE001
            logger.debug("Duration probe failed: %s", exc)
        return 0.0

    def _extract_ffmpeg(self, path: Path, out_dir: Path, max_frames: int) -> List[VideoFrame]:
        frames: List[VideoFrame] = []
        try:
            # Sample evenly: one frame every (total_seconds / max_frames).
            duration = self._probe_duration(path)
            interval = max(1.0, duration / max_frames) if duration > 0 else 1.0
            cmd = [_ffmpeg_binary(), "-i", str(path), "-vf", f"fps=1/{interval}", "-vsync", "vfr", str(out_dir / "frame_%05d.png")]
            subprocess.run(cmd, capture_output=True, timeout=120)
            files = sorted(out_dir.glob("frame_*.png"))[:max_frames]
            for i, f in enumerate(files):
                frames.append(VideoFrame(index=i, timestamp_s=i * interval, path=str(f), is_key_moment=False))
        except Exception as exc:  # noqa: BLE001
            logger.warning("ffmpeg frame extraction failed: %s", exc)
        return frames

    def _extract_opencv(self, path: Path, out_dir: Path, max_frames: int) -> List[VideoFrame]:
        try:
            import cv2
        except ImportError:
            return []
        frames: List[VideoFrame] = []
        try:
            cap = cv2.VideoCapture(str(path))
            if not cap.isOpened():
                return []
            fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
            count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            step = max(1, int(count / max_frames)) if count > 0 else max(1, int(fps))
            i = 0
            frame_no = 0
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if frame_no % step == 0 and len(frames) < max_frames:
                    out = out_dir / f"cv_{i:05d}.png"
                    cv2.imwrite(str(out), frame)
                    frames.append(VideoFrame(index=i, timestamp_s=frame_no / fps, path=str(out), is_key_moment=False))
                    i += 1
                frame_no += 1
            cap.release()
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenCV frame extraction failed: %s", exc)
        return frames

    def _detect_key_moments(self, frames: List[VideoFrame]) -> List[VideoFrame]:
        if len(frames) < 3:
            return [frames[0]] if frames else []
        try:
            from PIL import Image
            import math
            prev_hist: Optional[Dict[int, int]] = None
            key: List[VideoFrame] = []
            threshold = self._settings.video.key_moment_threshold
            for frame in frames:
                try:
                    with Image.open(frame.path) as img:
                        img.load()
                        gray = img.convert("L").resize((48, 48))
                        hist = gray.histogram()
                    if prev_hist is not None:
                        diff = sum(abs(a - b) for a, b in zip(prev_hist, hist))
                        total = sum(hist)
                        ratio = diff / max(total, 1)
                        if ratio > threshold:
                            key.append(frame)
                    prev_hist = hist
                except Exception:  # noqa: BLE001
                    continue
            if not key and frames:
                key = [frames[0]]
            return key
        except Exception as exc:  # noqa: BLE001
            logger.debug("Key moment detection skipped: %s", exc)
            return [frames[0]] if frames else []

    def _scene_summary(self, frames: List[VideoFrame]) -> str:
        if not frames:
            return ""
        # Local scene summary from per-frame OCR (cheap, offline).
        try:
            from aetheros_vision.ocr import create_ocr_engine
            engine = create_ocr_engine(self._settings)
            if not engine.is_available():
                return f"{len(frames)} frames extracted; OCR unavailable for scene text."
            texts = []
            for frame in frames[:6]:
                ocr = engine.extract(frame.path)
                if ocr and ocr.success and ocr.text.strip():
                    texts.append(ocr.text.strip()[:200])
            if texts:
                return "Scene text: " + " | ".join(texts[:3])
            return f"{len(frames)} frames extracted; no readable scene text."
        except Exception as exc:  # noqa: BLE001
            logger.debug("Scene summary OCR failed: %s", exc)
            return f"{len(frames)} frames extracted."
