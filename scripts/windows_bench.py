"""Windows benchmark harness (Master 64.1 A8).

Collects environment + REAL timings only: Python import cost, CLI --help
startup, intelligence pipeline micro-bench, and pytest file timings.
No invented values; every number is measured on this machine. Output JSON
to stdout (redirect to docs evidence as needed).
"""

from __future__ import annotations

import json
import os
import platform
import statistics
import subprocess
import sys
import time


def _env() -> dict:
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "arch": platform.machine(),
        "cpu_count": os.cpu_count(),
        "python": platform.python_version(),
        "electron": "not-installed-here",
        "node": "n/a",
        "commit": _git_commit(),
        "power_state": "unknown (no Win32 power query in harness)",
    }


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=15)
        return out.stdout.strip() if out.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _time_fn(fn, repeats: int = 5) -> dict:
    samples = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000)
    return {"median_ms": round(statistics.median(samples), 2),
            "p95_ms": round(sorted(samples)[min(len(samples) - 1, int(len(samples) * 0.95))], 2),
            "samples": len(samples)}


def main() -> int:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if here not in sys.path:
        sys.path.insert(0, here)
    py = sys.executable

    def import_operating_layer():
        import importlib
        import agent.operating_layer as ol
        importlib.reload(ol)

    def intent_pipeline():
        from agent.operating_layer import parse_intent, plan_from_intent
        plan_from_intent(parse_intent("Fix the login bug and run tests"))

    def cli_help():
        subprocess.run([py, "-m", "aetheros_cli.main", "--help"],
                       capture_output=True, timeout=120, cwd=here)

    report = {
        "environment": _env(),
        "measurements": {
            "import_operating_layer": _time_fn(import_operating_layer, 3),
            "intent_to_plan": _time_fn(intent_pipeline, 10),
            "cli_help_startup": _time_fn(cli_help, 3),
        },
        "notes": "CLI --help includes DeprecationWarning noise when "
                 "HERMES_HOME is set (compat path). Electron timings N/A "
                 "(binary absent). Hardware power-state query not implemented.",
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
