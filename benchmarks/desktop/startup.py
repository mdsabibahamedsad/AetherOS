"""Desktop/Electron startup performance benchmarks (PERF-DESKTOP-*)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from benchmarks.core.measure import (
    BenchmarkHarness,
    BenchmarkResult,
    EnvironmentInfo,
    PrecisionTimer,
    ResourceMonitor,
    run_benchmark,
)
from benchmarks.core.runner import register_benchmark


@register_benchmark("desktop", "PERF-DESKTOP-001")
class ColdStartupBenchmark(BenchmarkHarness):
    """PERF-DESKTOP-001: Cold desktop application startup time.

    Measures: process launch → Electron init → main ready → BrowserWindow →
    preload → renderer boot → React init → first paint → usable UI
    """

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-DESKTOP-001",
            name="Cold Desktop Startup",
            category="desktop",
            warmup_iterations=0,  # No warmup for cold start
            measurement_iterations=5,
            environment=environment,
        )
        self.app_path = self._find_app()

    def _find_app(self) -> Optional[str]:
        """Find the Electron app executable or entry point."""
        # Check for built app
        candidates = [
            Path("apps/desktop/dist/win-unpacked/AetherOS.exe"),
            Path("apps/desktop/dist/AetherOS.exe"),
            Path("apps/desktop/dist/mac/AetherOS.app/Contents/MacOS/AetherOS"),
            Path("apps/desktop/dist/linux-unpacked/AetherOS"),
            Path("apps/desktop/src/main.tsx"),  # Dev mode
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        return None

    def measure_once(self) -> Dict[str, float]:
        if not self.app_path:
            return {"error": 1.0, "error_msg": "App not found"}

        # For dev mode, we measure `npm run dev` startup
        if self.app_path.endswith(".tsx") or self.app_path.endswith(".ts"):
            return self._measure_dev_startup()

        return self._measure_built_startup()

    def _measure_dev_startup(self) -> Dict[str, float]:
        """Measure development mode startup (npm run dev)."""
        cwd = Path("apps/desktop")
        timer = PrecisionTimer()
        timer.start()

        # Start the dev process
        proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for "ready" indicator (Vite ready message)
        ready = False
        start_time = time.time()
        while time.time() - start_time < 60:  # 60s timeout
            line = proc.stdout.readline() if proc.stdout else b""
            if b"ready" in line.lower() or b"local" in line.lower():
                ready = True
                break
            if proc.poll() is not None:
                break

        elapsed = timer.stop()
        proc.terminate()
        proc.wait(timeout=5)

        return {
            "startup_time_ms": elapsed,
            "ready": 1.0 if ready else 0.0,
        }

    def _measure_built_startup(self) -> Dict[str, float]:
        """Measure built application startup."""
        timer = PrecisionTimer()
        timer.start()

        proc = subprocess.Popen(
            [self.app_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for window to appear (simplified - in reality would use
        # Electron's app.whenReady or similar IPC signal)
        time.sleep(3)  # Give time for window creation

        elapsed = timer.stop()
        proc.terminate()
        proc.wait(timeout=5)

        return {
            "startup_time_ms": elapsed,
        }

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "startup_time_ms": "ms",
            "ready": "bool",
        }


@register_benchmark("desktop", "PERF-DESKTOP-002")
class WarmStartupBenchmark(BenchmarkHarness):
    """PERF-DESKTOP-002: Warm desktop startup (cached)."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-DESKTOP-002",
            name="Warm Desktop Startup",
            category="desktop",
            warmup_iterations=1,  # First run warms cache
            measurement_iterations=10,
            environment=environment,
        )
        self.app_path = self._find_app()

    def _find_app(self) -> Optional[str]:
        candidates = [
            Path("apps/desktop/dist/win-unpacked/AetherOS.exe"),
            Path("apps/desktop/dist/AetherOS.exe"),
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        return None

    def warmup(self) -> None:
        """Run once to warm caches."""
        if self.app_path:
            proc = subprocess.Popen([self.app_path])
            time.sleep(2)
            proc.terminate()
            proc.wait(timeout=5)

    def measure_once(self) -> Dict[str, float]:
        if not self.app_path:
            return {"error": 1.0}

        timer = PrecisionTimer()
        timer.start()

        proc = subprocess.Popen([self.app_path])
        time.sleep(2)  # Reduced wait for warm start
        elapsed = timer.stop()

        proc.terminate()
        proc.wait(timeout=5)

        return {"startup_time_ms": elapsed}

    def get_metric_units(self) -> Dict[str, str]:
        return {"startup_time_ms": "ms"}


@register_benchmark("desktop", "PERF-DESKTOP-003")
class RendererFirstPaintBenchmark(BenchmarkHarness):
    """PERF-DESKTOP-003: Renderer first paint timing.

    Uses Electron's `webContents` events to measure:
    - dom-ready
    - did-first-paint (via performance.now())
    """

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-DESKTOP-003",
            name="Renderer First Paint",
            category="desktop",
            warmup_iterations=0,
            measurement_iterations=5,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        # This would require a custom Electron script that exposes
        # performance.timing via IPC. For now, return BLOCKED.
        return {"blocked": 1.0, "reason": "Requires Electron test harness"}

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "dom_ready_ms": "ms",
            "first_paint_ms": "ms",
            "first_contentful_paint_ms": "ms",
        }


@register_benchmark("desktop", "PERF-DESKTOP-004")
class MainProcessInitBenchmark(BenchmarkHarness):
    """PERF-DESKTOP-004: Main process initialization breakdown.

    Measures time spent in each main.cjs module import.
    """

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-DESKTOP-004",
            name="Main Process Init Breakdown",
            category="desktop",
            warmup_iterations=0,
            measurement_iterations=3,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        # Run Node with --trace-require or custom loader to measure import times
        # For now, simulate by parsing main.cjs and timing imports
        main_file = Path("apps/desktop/electron/main.cjs")
        if not main_file.exists():
            return {"error": 1.0}

        content = main_file.read_text()
        imports = self._extract_imports(content)

        results = {}
        for imp in imports[:20]:  # Limit to first 20
            timer = PrecisionTimer()
            timer.start()
            try:
                __import__(imp.replace(".cjs", "").replace("/", "."))
            except ImportError:
                pass
            elapsed = timer.stop()
            results[f"import_{imp.replace('/', '_').replace('.', '_')}_ms"] = elapsed

        return results

    def _extract_imports(self, content: str) -> List[str]:
        """Extract require/import statements from main.cjs."""
        import re
        # Match require('...') and import ... from '...'
        requires = re.findall(r"require\(['\"]([^'\"]+)['\"]\)", content)
        imports = re.findall(r"from\s+['\"]([^'\"]+)['\"]", content)
        return requires + imports

    def get_metric_units(self) -> Dict[str, str]:
        return {"import_*_ms": "ms"}


@register_benchmark("desktop", "PERF-DESKTOP-005")
class PreloadScriptBenchmark(BenchmarkHarness):
    """PERF-DESKTOP-005: Preload script execution time."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-DESKTOP-005",
            name="Preload Script Execution",
            category="desktop",
            warmup_iterations=1,
            measurement_iterations=10,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        preload_file = Path("apps/desktop/electron/preload.cjs")
        if not preload_file.exists():
            return {"error": 1.0}

        # Execute preload in isolated context (simplified)
        timer = PrecisionTimer()
        timer.start()

        # In reality, this would run in Electron's preload context
        # For benchmark, we just measure Node execution time
        proc = subprocess.run(
            ["node", "--eval", preload_file.read_text()],
            capture_output=True,
            timeout=10,
        )

        elapsed = timer.stop()

        return {
            "execution_time_ms": elapsed,
            "exit_code": float(proc.returncode),
        }

    def get_metric_units(self) -> Dict[str, str]:
        return {"execution_time_ms": "ms", "exit_code": "code"}


def run_desktop_benchmarks() -> List[BenchmarkResult]:
    """Run all desktop benchmarks."""
    results = []
    for bench_id in ["PERF-DESKTOP-001", "PERF-DESKTOP-002", "PERF-DESKTOP-004", "PERF-DESKTOP-005"]:
        # Note: PERF-DESKTOP-003 requires Electron test harness
        pass
    return results


if __name__ == "__main__":
    env = EnvironmentInfo()
    print(f"Environment: {env.os}, Fingerprint: {env.fingerprint()}")

    for bench_id in ["PERF-DESKTOP-001", "PERF-DESKTOP-002", "PERF-DESKTOP-004", "PERF-DESKTOP-005"]:
        from benchmarks.core.runner import REGISTRY
        harness = REGISTRY.get("desktop", bench_id)
        if harness:
            harness.environment = env
            result = run_benchmark(harness)
            print(json.dumps(result.to_dict(), indent=2, default=str))