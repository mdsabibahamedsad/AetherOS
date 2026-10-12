"""AetherOS Vision Runtime.

Lifecycle owner for the multimodal engine: initialization, health checks,
GPU detection, backend fallback, diagnostics, and recovery. Every subsystem
(OCR, capture, document, video) is registered as a provider so health and
recovery can be driven uniformly.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from aetheros_vision.config import VisionSettings, load_vision_settings
from aetheros_vision.gpu import detect_gpu
from aetheros_vision.models import RuntimeState, VisionDiagnostics

logger = logging.getLogger(__name__)


@dataclass
class HealthCheck:
    name: str
    ok: bool
    detail: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "ok": self.ok, "detail": self.detail, "latency_ms": round(self.latency_ms, 3)}


class Subsystem:
    """Protocol surface for a registered vision subsystem."""

    name = "subsystem"

    def health(self) -> Dict[str, Any]:
        return {"ok": True}

    def shutdown(self) -> None:
        pass


class VisionRuntime:
    """Central multimodal runtime.

    Owns the lifecycle state machine, the subsystem registry, GPU/backend
    resolution, health checks, diagnostics, and recovery. Thread-safe.
    """

    def __init__(self, settings: Optional[VisionSettings] = None):
        self._lock = threading.RLock()
        self._settings = settings or load_vision_settings()
        self._state = RuntimeState.UNINITIALIZED
        self._subsystems: Dict[str, Subsystem] = {}
        self._gpu_available = False
        self._gpu_name = ""
        self._backend = self._settings.backend or "hybrid"
        self._started_at = time.time()
        self._total_requests = 0
        self._failures = 0
        self._last_error: Optional[str] = None
        self._ocr_health: Dict[str, Any] = {"ok": False, "provider": "", "languages": []}
        self._vision_health: Dict[str, Any] = {"ok": False, "provider": "", "model": ""}
        self._capture_health: Dict[str, Any] = {"ok": False}
        self._recovery_attempts = 0

    # -- lifecycle ----------------------------------------------------------

    def initialize(self) -> None:
        with self._lock:
            if self._state in (RuntimeState.READY, RuntimeState.DEGRADED):
                return
            self._state = RuntimeState.INITIALIZING
        self._gpu_available, self._gpu_name = detect_gpu()
        self._probe_ocr()
        self._probe_vision()
        self._probe_capture()
        with self._lock:
            degraded = not (self._ocr_health["ok"] or self._vision_health["ok"])
            self._state = RuntimeState.DEGRADED if degraded else RuntimeState.READY

    def shutdown(self) -> None:
        with self._lock:
            if self._state == RuntimeState.SHUTDOWN:
                return
            for subsystem in list(self._subsystems.values()):
                try:
                    subsystem.shutdown()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Subsystem %s shutdown error: %s", subsystem.name, exc)
            self._state = RuntimeState.SHUTDOWN

    # -- registration -------------------------------------------------------

    def register(self, subsystem: Subsystem) -> None:
        with self._lock:
            self._subsystems[subsystem.name] = subsystem

    def get(self, name: str) -> Optional[Subsystem]:
        with self._lock:
            return self._subsystems.get(name)

    # -- health probes ------------------------------------------------------

    def _probe_ocr(self) -> None:
        try:
            from aetheros_vision.ocr import create_ocr_engine
            engine = create_ocr_engine(self._settings)
            available = engine.is_available()
            languages = engine.list_languages()
            provider = engine.provider_name()
            self._ocr_health = {
                "ok": available,
                "provider": provider,
                "languages": languages,
            }
            if available:
                self.register(engine)
        except Exception as exc:  # noqa: BLE001
            logger.warning("OCR probe failed: %s", exc)
            self._ocr_health = {"ok": False, "provider": "", "languages": [], "error": str(exc)}

    def _probe_vision(self) -> None:
        provider, model = "", ""
        ok = False
        try:
            from agent.auxiliary_client import resolve_vision_provider_client
            try:
                provider, client, model = resolve_vision_provider_client()
                ok = client is not None
            except Exception:  # noqa: BLE001
                provider, client, model = resolve_vision_provider_client(provider="auto")
                ok = client is not None
        except Exception as exc:  # noqa: BLE001
            logger.debug("Vision provider probe unavailable: %s", exc)
        self._vision_health = {"ok": ok, "provider": provider or "", "model": model or ""}

    def _probe_capture(self) -> None:
        try:
            from aetheros_vision.capture import ScreenCaptureRuntime
            probe = ScreenCaptureRuntime(self._settings)
            self._capture_health = {"ok": probe.is_available()}
        except Exception as exc:  # noqa: BLE001
            logger.debug("Capture probe failed: %s", exc)
            self._capture_health = {"ok": False, "error": str(exc)}

    # -- public API ---------------------------------------------------------

    @property
    def state(self) -> RuntimeState:
        with self._lock:
            return self._state

    @property
    def settings(self) -> VisionSettings:
        return self._settings

    @property
    def gpu_available(self) -> bool:
        return self._gpu_available

    @property
    def gpu_name(self) -> str:
        return self._gpu_name

    @property
    def backend(self) -> str:
        return self._backend

    def record_request(self, ok: bool, error: Optional[str] = None) -> None:
        with self._lock:
            self._total_requests += 1
            if not ok:
                self._failures += 1
                self._last_error = error

    def health_check(self) -> List[HealthCheck]:
        checks = [
            HealthCheck("runtime", self.state in (RuntimeState.READY, RuntimeState.DEGRADED), self.state.value),
            HealthCheck("gpu", self._gpu_available or True, self._gpu_name or "CPU fallback"),
            HealthCheck("ocr", self._ocr_health.get("ok", False), self._ocr_health.get("provider", "")),
            HealthCheck("vision", self._vision_health.get("ok", False), f"{self._vision_health.get('provider')} {self._vision_health.get('model')}".strip()),
            HealthCheck("capture", self._capture_health.get("ok", False), ""),
        ]
        for name, subsystem in list(self._subsystems.items()):
            start = time.perf_counter()
            try:
                detail = subsystem.health()
                ok = bool(detail.get("ok", True))
            except Exception as exc:  # noqa: BLE001
                ok, detail = False, {"error": str(exc)}
            checks.append(HealthCheck(name, ok, str(detail.get("detail", detail)), (time.perf_counter() - start) * 1000))
        return checks

    def diagnostics(self) -> VisionDiagnostics:
        return VisionDiagnostics(
            state=self.state,
            gpu_available=self._gpu_available,
            gpu_name=self._gpu_name,
            backend=self._backend,
            model_loaded=self._vision_health.get("ok", False),
            ocr_available=self._ocr_health.get("ok", False),
            ocr_provider=self._ocr_health.get("provider", ""),
            ocr_languages=self._ocr_health.get("languages", []),
            vision_provider=self._vision_health.get("provider", ""),
            vision_model=self._vision_health.get("model", ""),
            capture_available=self._capture_health.get("ok", False),
            uptime_s=time.time() - self._started_at,
            total_requests=self._total_requests,
            failures=self._failures,
            last_error=self._last_error,
            checks=[c.to_dict() for c in self.health_check()],
        )

    def recover(self) -> bool:
        """Attempt to recover from a degraded/failed state. Returns success."""
        with self._lock:
            self._recovery_attempts += 1
            self._state = RuntimeState.RECOVERING
        self._probe_ocr()
        self._probe_vision()
        self._probe_capture()
        with self._lock:
            degraded = not (self._ocr_health["ok"] or self._vision_health["ok"])
            self._state = RuntimeState.DEGRADED if degraded else RuntimeState.READY
            return not degraded

    def is_ready(self) -> bool:
        return self.state in (RuntimeState.READY, RuntimeState.DEGRADED)
