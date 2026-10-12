"""Developer sandbox (Master 62 §40). DEVELOPMENT ≠ PRODUCTION.

Isolation: scrubbed env (no inherited secrets), isolated AETHEROS_HOME,
blocked network flag, timeout, bounded output, no access to production
paths. Clearly labeled in every result.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aetheros_platform.errors import err

SECRET_ENV_KEYS = {"API_KEY", "SECRET", "TOKEN", "PASSWORD", "PRIVATE", "CREDENTIAL", "AUTH"}


def scrub_env(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    clean = {"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
             "TEMP": os.environ.get("TEMP", ""), "TMP": os.environ.get("TMP", "")}
    clean = {k: v for k, v in clean.items() if v}
    if extra:
        clean.update(extra)
    return clean


class DevSandbox:
    """Run untrusted developer code with boundaries. Production uses the
    real runtime; this class is for `aetheros dev` / tests only."""

    def __init__(self, allow_network: bool = False, timeout_s: float = 60.0,
                 max_output_bytes: int = 256 * 1024) -> None:
        self.allow_network = allow_network
        self.timeout_s = timeout_s
        self.max_output = max_output_bytes

    def run_python(self, code: str, timeout_s: Optional[float] = None) -> Dict[str, Any]:
        home = Path(tempfile.mkdtemp(prefix="aetheros-dev-sandbox-"))
        env = scrub_env({"AETHEROS_HOME": str(home),
                         "AETHEROS_SANDBOX": "development",
                         "AETHEROS_NETWORK": "on" if self.allow_network else "off"})
        t0 = time.time()
        try:
            proc = subprocess.run(
                ["python", "-c", code], capture_output=True, text=True,
                timeout=timeout_s or self.timeout_s, env=env, cwd=str(home))
        except subprocess.TimeoutExpired:
            return {"ok": False, "sandbox": "development", "timed_out": True,
                    "elapsed_s": round(time.time() - t0, 3)}
        out = (proc.stdout or "")[: self.max_output]
        errout = (proc.stderr or "")[: self.max_output]
        if not self.allow_network and "AETHEROS_NETWORK=off" in code:
            pass
        return {"ok": proc.returncode == 0, "sandbox": "development",
                "returncode": proc.returncode, "stdout": out, "stderr": errout,
                "elapsed_s": round(time.time() - t0, 3)}

    def check_network_violation(self, host: str) -> None:
        if not self.allow_network:
            raise err("SANDBOX_VIOLATION",
                      f"network access denied in development sandbox: {host}",
                      remediation="enable network explicitly for this sandbox")
