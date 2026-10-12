"""Local inference: hardware probe + runtime discovery + fit analysis.

Reuses aetheros_providers.local_model_manager for runtime detection
(no duplicate detectors). Hardware via psutil (CPU/RAM) + nvidia-smi /
torch best-effort (GPU/VRAM); anything unavailable is reported
NOT_INSTALLED/unknown, never fabricated. Locality verified by loopback
check on the endpoint. Fit analysis refuses models that cannot
realistically fit (with explicit reason).
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse


@dataclass
class HardwareInfo:
    cpu_count: int = 0
    ram_gb: float = 0.0
    gpu_name: str = ""
    vram_gb: float = 0.0
    gpu_available: bool = False
    os: str = ""
    arch: str = ""
    accelerators: List[str] = field(default_factory=list)
    at: float = field(default_factory=time.time)


def probe_hardware() -> HardwareInfo:
    import platform
    info = HardwareInfo(os=platform.system().lower(),
                        arch=platform.machine().lower())
    try:
        import psutil
        info.cpu_count = psutil.cpu_count(logical=True) or 0
        info.ram_gb = round(psutil.virtual_memory().total / 1e9, 1)
    except ImportError:
        pass
    # NVIDIA via nvidia-smi (best effort; absent => not claimed).
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10)
            if out.returncode == 0 and out.stdout.strip():
                name, mem = out.stdout.strip().splitlines()[0].split(",")
                info.gpu_name = name.strip()
                info.vram_gb = round(float(mem.strip()) / 1024, 1)
                info.gpu_available = True
                info.accelerators.append("cuda")
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    if not info.gpu_available:
        try:
            import torch
            if torch.cuda.is_available():
                info.gpu_name = torch.cuda.get_device_name(0)
                info.vram_gb = round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1)
                info.gpu_available = True
                info.accelerators.append("cuda")
        except (ImportError, Exception):
            pass
    return info


def fit_check(model_gb: float, hw: HardwareInfo, *,
              reserve_gb: float = 2.0) -> Dict[str, Any]:
    """Can this model realistically fit? Explicit reason either way."""
    if model_gb <= 0:
        return {"fit": False, "reason": "model memory requirement unknown"}
    pool = (hw.vram_gb if hw.gpu_available else 0.0) + hw.ram_gb
    usable = max(0.0, pool - reserve_gb)
    if model_gb <= usable:
        return {"fit": True, "reason": f"{model_gb}GB <= {usable:.1f}GB usable"}
    return {"fit": False,
            "reason": f"{model_gb}GB exceeds {usable:.1f}GB usable "
                      f"(RAM {hw.ram_gb}GB, VRAM {hw.vram_gb}GB)"}


class LocalInferenceManager:
    """Detect/discover/health-check local runtimes (real APIs only)."""

    def __init__(self, fetch: Optional[Callable[[str], Dict[str, Any]]] = None) -> None:
        self._fetch = fetch or self._http_get
        self._runtimes: List[Dict[str, Any]] = []

    @staticmethod
    def _http_get(url: str, timeout_s: float = 5.0) -> Dict[str, Any]:
        import httpx
        resp = httpx.get(url, timeout=timeout_s)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {"data": data}

    def detect(self) -> List[Dict[str, Any]]:
        """Reuse existing detectors; fall back to endpoint probes."""
        found: List[Dict[str, Any]] = []
        try:
            from aetheros_providers import local_model_manager as lmm
            for attr in ("detect_providers", "detect_local_providers",
                         "discover", "list_providers"):
                fn = getattr(lmm, attr, None)
                if callable(fn):
                    try:
                        res = fn()
                        if res:
                            found = [{"runtime": str(getattr(r, "name", r)),
                                      "via": f"local_model_manager.{attr}",
                                      "status": "detected"} for r in (
                                          res if isinstance(res, list) else [res])]
                            break
                    except Exception:
                        continue
        except ImportError:
            pass
        # Direct endpoint probes (ground truth): Ollama/LM Studio/llama.cpp.
        probes = [("ollama", "http://localhost:11434/api/tags"),
                  ("lm_studio", "http://localhost:1234/v1/models"),
                  ("llama_cpp", "http://localhost:8080/health")]
        for name, url in probes:
            if any(f.get("runtime") == name for f in found):
                continue
            try:
                self._fetch(url)
                found.append({"runtime": name, "url": url,
                              "via": "endpoint_probe", "status": "detected"})
            except Exception:
                found.append({"runtime": name, "via": "endpoint_probe",
                              "status": "not_installed"})
        self._runtimes = found
        return found

    def discover_models(self, base_url: str) -> List[Dict[str, Any]]:
        """List models from a live local endpoint (raises when absent)."""
        host = (urlparse(base_url).hostname or "").lower()
        if host not in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("local discovery requires loopback endpoint")
        if "11434" in base_url:
            data = self._fetch(base_url.rstrip("/") + "/api/tags")
            models = data.get("models", []) if isinstance(data, dict) else []
            return [{"id": m.get("name", ""), "size_gb": round(
                float(m.get("size", 0)) / 1e9, 2)} for m in models if m.get("name")]
        data = self._fetch(base_url.rstrip("/") + "/v1/models")
        items = data.get("data", []) if isinstance(data, dict) else []
        return [{"id": str(m.get("id", ""))} for m in items if m.get("id")]

    def health(self, base_url: str) -> Dict[str, Any]:
        t0 = time.time()
        try:
            self.discover_models(base_url)
            return {"ok": True,
                    "latency_ms": round((time.time() - t0) * 1000, 1),
                    "reason": "local endpoint responded"}
        except Exception as exc:
            return {"ok": False,
                    "latency_ms": round((time.time() - t0) * 1000, 1),
                    "reason": str(exc)[:300]}
