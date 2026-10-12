"""Environment normalization (P3) — every run records where it happened.

Also owns the fairness fingerprint used by the P44 check: same model,
provider, reasoning config, tool profile, dataset version, benchmark
version, timeout policy.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional

from benchmark.schema import BENCHMARK_VERSION


def snapshot() -> Dict[str, Any]:
    def first_line(cmd: List[str]) -> str:
        try:
            out = subprocess.run(cmd, capture_output=True, text=True,
                                 timeout=10)
            return (out.stdout or out.stderr).strip().splitlines()[0][:120] \
                if (out.stdout or out.stderr).strip() else ""
        except Exception:
            return ""

    return {
        "benchmark_version": BENCHMARK_VERSION,
        "os": f"{platform.system()} {platform.release()}",
        "os_platform": platform.platform(),
        "cpu": platform.processor() or platform.machine(),
        "cpu_count": os.cpu_count(),
        "ram_gb": _ram_gb(),
        "gpu": _gpu(),
        "python": sys.version.split()[0],
        "node": first_line(["node", "--version"]),
        "docker": first_line(["docker", "--version"]),
        "network": {"online_probe": False},   # filled by controller when probed
        "locale": os.environ.get("LANG", ""),
        "tz": os.environ.get("TZ", ""),
    }


def _ram_gb() -> Optional[float]:
    try:
        if hasattr(os, "sysconf"):
            return round(os.sysconf("SC_PAGE_SIZE") *
                         os.sysconf("SC_PHYS_PAGES") / 1024 ** 3, 1)
    except (ValueError, OSError, AttributeError):
        pass
    try:
        import ctypes
        class _MEM(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong)]
        m = _MEM()
        m.dwLength = ctypes.sizeof(_MEM)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return round(m.ullTotalPhys / 1024 ** 3, 1)
    except Exception:
        return None


def _gpu() -> str:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip().splitlines()[0]
    except Exception:
        pass
    return "none-detected"


def env_fingerprint(env: Dict[str, Any]) -> str:
    payload = json.dumps(env, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


FAIRNESS_DIMENSIONS = (
    "model", "model_version", "provider", "reasoning_config",
    "task_id", "tools_profile", "timeout_s", "dataset_version",
    "benchmark_version", "environment_class",
)


def fairness_check(a_env: Dict[str, Any], b_env: Dict[str, Any]) -> List[str]:
    """P44 — returns FAIRNESS_WARNING entries for materially differing
    dimensions; empty list means directly comparable."""
    warnings: List[str] = []
    for dim in FAIRNESS_DIMENSIONS:
        va, vb = a_env.get(dim), b_env.get(dim)
        if va != vb:
            warnings.append(f"FAIRNESS_WARNING:{dim}:{va!r}!={vb!r}")
    return warnings


def tool_available(binary: str) -> bool:
    return shutil.which(binary) is not None
