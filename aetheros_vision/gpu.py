"""AetherOS Vision — GPU detection.

Cheap, dependency-free GPU detection with explicit probe ordering and
honest "unknown" results. Never guesses; every probe failure reports the
reason so callers can fall back to CPU with a real diagnostic.
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def detect_gpu() -> Tuple[bool, str]:
    """Detect whether a usable GPU is present and return (available, label).

    Probe order:
      1. NVIDIA ``nvidia-smi`` (fast, reliable on Windows/Linux/macOS).
      2. CUDA-capable torch when installed.
      3. Metal (Apple Silicon) when ``torch.backends.mps`` is available.

    Returns ``(False, "reason")`` when nothing is found so the runtime can
    report a truthful CPU fallback.
    """
    env_override = os.environ.get("AETHEROS_VISION_FORCE_BACKEND", "").strip().lower()
    if env_override == "cpu":
        return False, "forced cpu via AETHEROS_VISION_FORCE_BACKEND"
    if env_override == "gpu":
        if _detect_nvidia() is not None:
            return True, _detect_nvidia()
        return False, "forced gpu but no GPU found via AETHEROS_VISION_FORCE_BACKEND"

    nvidia = _detect_nvidia()
    if nvidia is not None:
        return True, nvidia

    torch_gpu = _detect_torch()
    if torch_gpu is not None:
        return True, torch_gpu

    metal = _detect_metal()
    if metal is not None:
        return True, metal

    return False, "no GPU detected (nvidia-smi, torch-cuda, and MPS unavailable)"


def _detect_nvidia() -> Optional[str]:
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return None
    try:
        out = subprocess.run(
            [nvidia_smi, "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip().splitlines()[0].strip()
    except Exception as exc:  # noqa: BLE001
        logger.debug("nvidia-smi probe failed: %s", exc)
    return None


def _detect_torch() -> Optional[str]:
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            return f"CUDA ({name})"
    except Exception as exc:  # noqa: BLE001
        logger.debug("torch CUDA probe failed: %s", exc)
    return None


def _detect_metal() -> Optional[str]:
    if platform.system() != "Darwin":
        return None
    try:
        import torch
        if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
            return "Metal (Apple Silicon)"
    except Exception as exc:  # noqa: BLE001
        logger.debug("MPS probe failed: %s", exc)
    return None
