"""QA results collector (Master 70).

Runs the locally-executable QA battery and writes machine-readable
`docs/AETHEROS_MASTER_70_TEST_MATRIX.json` (schema: id/name/platform/
environment/version/started/duration/status/error/evidence). Anything
not executable here is recorded BLOCKED with cause — never PASS.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable

SUITES = [
    {"id": "QA-SMOKE", "cmd": [PY, "-m", "pytest", "tests/qa/test_smoke_security.py",
                               "-q", "-p", "no:cacheprovider", "-o", "addopts="]},
    {"id": "QA-WEB-CONTRACT", "cmd": [PY, "-m", "pytest",
                                      "tests/aetheros_platform/test_web_contract.py",
                                      "-q", "-p", "no:cacheprovider", "-o", "addopts="]},
    {"id": "QA-MOBILE-CONTRACT", "cmd": [PY, "-m", "pytest",
                                         "tests/aetheros_platform/test_mobile_contract.py",
                                         "-q", "-p", "no:cacheprovider", "-o", "addopts="]},
    {"id": "QA-ANDROID-CONTRACT", "cmd": [PY, "-m", "pytest",
                                          "tests/aetheros_platform/test_android_contract.py",
                                          "-q", "-p", "no:cacheprovider", "-o", "addopts="]},
    {"id": "QA-PLATFORM-CONTRACTS", "cmd": [PY, "-m", "pytest",
                                            "tests/aetheros_platform/test_linux_platform.py",
                                            "tests/aetheros_platform/test_macos_platform.py",
                                            "tests/aetheros_platform/test_windows_capabilities.py",
                                            "tests/aetheros_platform/test_toast_actions.py",
                                            "tests/aetheros_platform/test_windows_native.py",
                                            "-q", "-p", "no:cacheprovider", "-o", "addopts="]},
    {"id": "QA-INTEL", "cmd": [PY, "-m", "pytest",
                               "tests/agent/test_operating_layer.py",
                               "tests/agent_network/test_cli_parsers.py",
                               "-q", "-p", "no:cacheprovider", "-o", "addopts="]},
]

BLOCKED_SUITES = [
    {"id": "QA-XCODE", "reason": "no macOS/Xcode", "need": "macos-runner"},
    {"id": "QA-GRADLE", "reason": "no Java/Android SDK", "need": "linux-runner+sdk"},
    {"id": "QA-DOCKER", "reason": "no Docker daemon", "need": "linux-runner+docker"},
    {"id": "QA-BROWSER", "reason": "no Playwright browsers installed", "need": "ci-playwright"},
    {"id": "QA-DEVICE", "reason": "no phones/tablets/VMs", "need": "device-lab"},
    {"id": "QA-E2E-LIVE", "reason": "no runnable clients/servers", "need": "staging-env"},
]


def _version() -> str:
    try:
        import tomllib
        return tomllib.load(open(REPO / "pyproject.toml", "rb"))["project"]["version"]
    except Exception:
        return "unknown"


def main() -> int:
    started = datetime.now(timezone.utc).isoformat()
    records = []
    for suite in SUITES:
        t0 = time.perf_counter()
        try:
            r = subprocess.run(suite["cmd"], capture_output=True, text=True,
                               timeout=600, cwd=REPO)
            tail = (r.stdout or "").strip().splitlines()[-1] if r.stdout else ""
            status = "PASSED" if r.returncode == 0 else "FAILED"
            error = "" if r.returncode == 0 else tail
        except Exception as exc:
            status, error = "FAILED", str(exc)
            tail = ""
        records.append({
            "id": suite["id"], "name": suite["id"], "platform": "windows-x64",
            "environment": f"python {sys.version.split()[0]}",
            "version": _version(), "started": started,
            "duration": round(time.perf_counter() - t0, 2),
            "status": status, "error": error,
            "artifact": "", "evidence": tail,
        })
    for b in BLOCKED_SUITES:
        records.append({
            "id": b["id"], "name": b["id"], "platform": "n/a",
            "environment": "unavailable", "version": _version(),
            "started": started, "duration": 0.0, "status": "BLOCKED",
            "error": b["reason"], "artifact": "",
            "evidence": f"next action: {b['need']}",
        })
    out = REPO / "docs" / "AETHEROS_MASTER_70_TEST_MATRIX.json"
    out.write_text(json.dumps({"generated": started, "results": records}, indent=2))
    passed = sum(1 for r in records if r["status"] == "PASSED")
    failed = sum(1 for r in records if r["status"] == "FAILED")
    blocked = sum(1 for r in records if r["status"] == "BLOCKED")
    print(f"PASSED={passed} FAILED={failed} BLOCKED={blocked} -> {out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
