"""Browser/Computer automation benchmarks (PERF-BROWSER-*, PERF-COMPUTER-*)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Dict, Optional

from benchmarks.core.measure import (
    BenchmarkHarness,
    BenchmarkResult,
    EnvironmentInfo,
    PrecisionTimer,
    run_benchmark,
)
from benchmarks.core.runner import register_benchmark


@register_benchmark("browser", "PERF-BROWSER-001")
class BrowserColdStartBenchmark(BenchmarkHarness):
    """PERF-BROWSER-001: Cold browser launch time."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-BROWSER-001",
            name="Browser Cold Start",
            category="browser",
            warmup_iterations=0,
            measurement_iterations=5,
            environment=environment,
        )
        self._playwright = None

    def setup(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
        except ImportError:
            self._playwright = None

    def teardown(self) -> None:
        if self._playwright:
            self._playwright.stop()

    def measure_once(self) -> Dict[str, float]:
        if not self._playwright:
            return {"blocked": 1.0, "reason": "Playwright not installed"}

        timer = PrecisionTimer()
        timer.start()

        browser = self._playwright.chromium.launch(headless=True)
        launch_ms = timer.stop()

        timer.start()
        context = browser.new_context()
        context_ms = timer.stop()

        timer.start()
        page = context.new_page()
        page_ms = timer.stop()

        timer.start()
        page.goto("about:blank", wait_until="domcontentloaded")
        nav_ms = timer.stop()

        browser.close()

        return {
            "launch_ms": launch_ms,
            "context_ms": context_ms,
            "page_ms": page_ms,
            "navigation_ms": nav_ms,
            "total_ms": launch_ms + context_ms + page_ms + nav_ms,
        }

    def get_metric_units(self) -> Dict[str, str]:
        return {k: "ms" for k in ["launch_ms", "context_ms", "page_ms", "navigation_ms", "total_ms"]}


@register_benchmark("browser", "PERF-BROWSER-002")
class BrowserWarmStartBenchmark(BenchmarkHarness):
    """PERF-BROWSER-002: Warm browser (reused context) page creation."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-BROWSER-002",
            name="Browser Warm Start (Context Reuse)",
            category="browser",
            warmup_iterations=1,
            measurement_iterations=20,
            environment=environment,
        )
        self._playwright = None
        self._browser = None
        self._context = None

    def setup(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
            self._context = self._browser.new_context()
        except ImportError:
            self._playwright = None

    def teardown(self) -> None:
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def warmup(self) -> None:
        if self._context:
            page = self._context.new_page()
            page.goto("about:blank")
            page.close()

    def measure_once(self) -> Dict[str, float]:
        if not self._context:
            return {"blocked": 1.0, "reason": "Playwright not available"}

        timer = PrecisionTimer()
        timer.start()

        page = self._context.new_page()
        page_ms = timer.stop()

        timer.start()
        page.goto("about:blank", wait_until="domcontentloaded")
        nav_ms = timer.stop()

        page.close()

        return {"page_ms": page_ms, "navigation_ms": nav_ms, "total_ms": page_ms + nav_ms}

    def get_metric_units(self) -> Dict[str, str]:
        return {"page_ms": "ms", "navigation_ms": "ms", "total_ms": "ms"}


@register_benchmark("browser", "PERF-BROWSER-003")
class BrowserAutomationActionsBenchmark(BenchmarkHarness):
    """PERF-BROWSER-003: Common browser automation action latencies."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-BROWSER-003",
            name="Browser Automation Actions",
            category="browser",
            warmup_iterations=2,
            measurement_iterations=50,
            environment=environment,
        )
        self._playwright = None
        self._page = None

    def setup(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            browser = self._playwright.chromium.launch(headless=True)
            context = browser.new_context()
            self._page = context.new_page()
            self._page.goto("data:text/html,<button id=btn>Click</button><input id=inp>")
        except ImportError:
            self._playwright = None

    def teardown(self) -> None:
        if self._playwright:
            self._playwright.stop()

    def measure_once(self) -> Dict[str, float]:
        if not self._page:
            return {"blocked": 1.0, "reason": "Playwright not available"}

        results = {}

        # Click
        timer = PrecisionTimer()
        timer.start()
        self._page.click("#btn")
        results["click_ms"] = timer.stop()

        # Type
        timer.start()
        self._page.fill("#inp", "test input")
        results["type_ms"] = timer.stop()

        # Screenshot
        timer.start()
        self._page.screenshot()
        results["screenshot_ms"] = timer.stop()

        # DOM query
        timer.start()
        self._page.query_selector("#btn")
        results["query_selector_ms"] = timer.stop()

        # Wait for selector
        timer.start()
        self._page.wait_for_selector("#btn")
        results["wait_selector_ms"] = timer.stop()

        return results

    def get_metric_units(self) -> Dict[str, str]:
        return {k: "ms" for k in ["click_ms", "type_ms", "screenshot_ms", "query_selector_ms", "wait_selector_ms"]}


@register_benchmark("browser", "PERF-BROWSER-004")
class BrowserNavigationBenchmark(BenchmarkHarness):
    """PERF-BROWSER-004: Page navigation performance."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-BROWSER-004",
            name="Browser Navigation",
            category="browser",
            warmup_iterations=1,
            measurement_iterations=10,
            environment=environment,
        )
        self._playwright = None
        self._page = None
        self.test_urls = [
            "https://example.com",
            "https://httpbin.org/html",
            "data:text/html," + "<div>" * 1000 + "content" + "</div>" * 1000,
        ]

    def setup(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            browser = self._playwright.chromium.launch(headless=True)
            context = browser.new_context()
            self._page = context.new_page()
        except ImportError:
            self._playwright = None

    def teardown(self) -> None:
        if self._playwright:
            self._playwright.stop()

    def measure_once(self) -> Dict[str, float]:
        if not self._page:
            return {"blocked": 1.0, "reason": "Playwright not available"}

        results = {}
        for i, url in enumerate(self.test_urls):
            timer = PrecisionTimer()
            timer.start()
            self._page.goto(url, wait_until="domcontentloaded")
            results[f"nav_{i}_ms"] = timer.stop()

        return results

    def get_metric_units(self) -> Dict[str, str]:
        return {f"nav_{i}_ms": "ms" for i in range(3)}


@register_benchmark("computer", "PERF-COMPUTER-001")
class ComputerUseObservationLoopBenchmark(BenchmarkHarness):
    """PERF-COMPUTER-001: Computer-use observation→action loop."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-COMPUTER-001",
            name="Computer-Use Observation Loop",
            category="computer",
            warmup_iterations=0,
            measurement_iterations=10,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        # Requires computer-use environment (VM, VNC, etc.)
        return {
            "blocked": 1.0,
            "reason": "Requires computer-use environment (VM/VNC)",
        }

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "screenshot_ms": "ms",
            "model_inference_ms": "ms",
            "action_execution_ms": "ms",
            "full_loop_ms": "ms",
        }


@register_benchmark("computer", "PERF-COMPUTER-002")
class ScreenshotLatencyBenchmark(BenchmarkHarness):
    """PERF-COMPUTER-002: Screenshot capture latency."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-COMPUTER-002",
            name="Screenshot Capture",
            category="computer",
            warmup_iterations=5,
            measurement_iterations=50,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        # Use PIL/mss for screenshot benchmark
        try:
            import mss
            with mss.mss() as sct:
                timer = PrecisionTimer()
                timer.start()
                sct.shot()
                return {"screenshot_ms": timer.stop()}
        except ImportError:
            return {"blocked": 1.0, "reason": "mss not installed"}

    def get_metric_units(self) -> Dict[str, str]:
        return {"screenshot_ms": "ms"}


if __name__ == "__main__":
    env = EnvironmentInfo()
    print(f"Environment: {env.os}, Fingerprint: {env.fingerprint()}")

    from benchmarks.core.runner import REGISTRY

    for bench_id in ["PERF-BROWSER-001", "PERF-BROWSER-002", "PERF-BROWSER-003", "PERF-BROWSER-004", "PERF-COMPUTER-002"]:
        harness = REGISTRY.get("browser" if "BROWSER" in bench_id else "computer", bench_id)
        if harness:
            harness.environment = env
            result = run_benchmark(harness)
            print(json.dumps(result.to_dict(), indent=2, default=str))