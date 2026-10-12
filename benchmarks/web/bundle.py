"""Bundle size analysis benchmark (PERF-BUNDLE-*)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

from benchmarks.core.measure import (
    BenchmarkHarness,
    BenchmarkResult,
    EnvironmentInfo,
    run_benchmark,
)
from benchmarks.core.runner import register_benchmark


@register_benchmark("web", "PERF-BUNDLE-001")
class DesktopBundleSizeBenchmark(BenchmarkHarness):
    """PERF-BUNDLE-001: Desktop app bundle size analysis."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-BUNDLE-001",
            name="Desktop Bundle Size",
            category="web",
            warmup_iterations=0,
            measurement_iterations=1,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        # Run Vite build with analysis
        desktop_dir = Path("apps/desktop")
        if not desktop_dir.exists():
            return {"blocked": 1.0, "reason": "Desktop app not found"}

        # Check if dist exists
        dist_dir = desktop_dir / "dist"
        if not dist_dir.exists():
            return {"blocked": 1.0, "reason": "Dist not built. Run build first."}

        results = {}

        # Total JS size
        js_files = list(dist_dir.rglob("*.js"))
        total_js = sum(f.stat().st_size for f in js_files)
        results["total_js_bytes"] = float(total_js)

        # CSS size
        css_files = list(dist_dir.rglob("*.css"))
        total_css = sum(f.stat().st_size for f in css_files)
        results["total_css_bytes"] = float(total_css)

        # HTML size
        html_files = list(dist_dir.rglob("*.html"))
        total_html = sum(f.stat().st_size for f in html_files)
        results["total_html_bytes"] = float(total_html)

        # Asset size
        asset_extensions = [".woff", ".woff2", ".ttf", ".eot", ".png", ".jpg", ".svg", ".ico"]
        asset_files = []
        for ext in asset_extensions:
            asset_files.extend(dist_dir.rglob(f"*{ext}"))
        total_assets = sum(f.stat().st_size for f in asset_files)
        results["total_assets_bytes"] = float(total_assets)

        # Largest JS files
        js_sizes = [(f, f.stat().st_size) for f in js_files]
        js_sizes.sort(key=lambda x: x[1], reverse=True)
        for i, (f, size) in enumerate(js_sizes[:10]):
            results[f"top_js_{i}_bytes"] = float(size)

        return results

    def get_metric_units(self) -> Dict[str, str]:
        units = {
            "total_js_bytes": "bytes",
            "total_css_bytes": "bytes",
            "total_html_bytes": "bytes",
            "total_assets_bytes": "bytes",
        }
        for i in range(10):
            units[f"top_js_{i}_bytes"] = "bytes"
        return units


@register_benchmark("web", "PERF-BUNDLE-002")
class BundleAnalysisBenchmark(BenchmarkHarness):
    """PERF-BUNDLE-002: Detailed bundle analysis with rollup-plugin-visualizer."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-BUNDLE-002",
            name="Bundle Analysis",
            category="web",
            warmup_iterations=0,
            measurement_iterations=1,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        desktop_dir = Path("apps/desktop")
        if not desktop_dir.exists():
            return {"blocked": 1.0, "reason": "Desktop app not found"}

        # Try to run build with analysis
        try:
            result = subprocess.run(
                ["npm", "run", "build", "--", "--mode", "analyze"],
                cwd=desktop_dir,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                return {"blocked": 1.0, "reason": f"Build failed: {result.stderr[:200]}"}

            # Parse visualizer output if available
            stats_file = desktop_dir / "dist" / "stats.html"
            if stats_file.exists():
                # Could parse the stats.html for detailed metrics
                return {"analysis_complete": 1.0, "stats_size_bytes": float(stats_file.stat().st_size)}

            return {"analysis_complete": 1.0}

        except subprocess.TimeoutExpired:
            return {"blocked": 1.0, "reason": "Build timeout"}
        except Exception as e:
            return {"blocked": 1.0, "reason": str(e)}

    def get_metric_units(self) -> Dict[str, str]:
        return {"analysis_complete": "bool", "stats_size_bytes": "bytes"}


@register_benchmark("web", "PERF-BUNDLE-003")
class DuplicateDependenciesBenchmark(BenchmarkHarness):
    """PERF-BUNDLE-003: Detect duplicate dependencies in bundle."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-BUNDLE-003",
            name="Duplicate Dependencies",
            category="web",
            warmup_iterations=0,
            measurement_iterations=1,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        desktop_dir = Path("apps/desktop")
        package_lock = desktop_dir / "package-lock.json"

        if not package_lock.exists():
            return {"blocked": 1.0, "reason": "package-lock.json not found"}

        try:
            data = json.loads(package_lock.read_text())
            packages = data.get("packages", {})

            # Count duplicate package names at different versions
            versions: Dict[str, set] = {}
            for pkg_path, pkg_info in packages.items():
                if pkg_path == "":
                    continue
                name = pkg_path.split("/")[-1] if "node_modules" in pkg_path else pkg_path
                version = pkg_info.get("version", "unknown")
                versions.setdefault(name, set()).add(version)

            duplicates = {name: vers for name, vers in versions.items() if len(vers) > 1}

            return {
                "total_packages": float(len(packages)),
                "unique_names": float(len(versions)),
                "duplicates_count": float(len(duplicates)),
                "duplicate_details": len(duplicates),  # For display
            }

        except Exception as e:
            return {"blocked": 1.0, "reason": str(e)}

    def get_metric_units(self) -> Dict[str, str]:
        return {
            "total_packages": "count",
            "unique_names": "count",
            "duplicates_count": "count",
        }


@register_benchmark("web", "PERF-BUNDLE-004")
class TreeShakingEffectivenessBenchmark(BenchmarkHarness):
    """PERF-BUNDLE-004: Tree shaking effectiveness check."""

    def __init__(self, environment: Optional[EnvironmentInfo] = None):
        super().__init__(
            benchmark_id="PERF-BUNDLE-004",
            name="Tree Shaking Effectiveness",
            category="web",
            warmup_iterations=0,
            measurement_iterations=1,
            environment=environment,
        )

    def measure_once(self) -> Dict[str, float]:
        # Check for common non-tree-shakeable patterns in built JS
        dist_dir = Path("apps/desktop/dist")
        if not dist_dir.exists():
            return {"blocked": 1.0, "reason": "Dist not built"}

        js_files = list(dist_dir.rglob("*.js"))
        patterns = {
            "lodash_whole": "lodash.js",
            "moment_whole": "moment.js",
            "jquery": "jquery",
            "rxjs_whole": "rxjs.js",
        }

        results = {}
        for pattern_name, pattern in patterns.items():
            found = any(pattern in f.read_text()[:10000] for f in js_files[:5])  # Check first 5 files
            results[f"contains_{pattern_name}"] = 1.0 if found else 0.0

        return results

    def get_metric_units(self) -> Dict[str, str]:
        return {k: "bool" for k in ["contains_lodash_whole", "contains_moment_whole", "contains_jquery", "contains_rxjs_whole"]}


if __name__ == "__main__":
    env = EnvironmentInfo()
    print(f"Environment: {env.os}, Fingerprint: {env.fingerprint()}")

    from benchmarks.core.runner import REGISTRY

    for bench_id in ["PERF-BUNDLE-001", "PERF-BUNDLE-003"]:
        harness = REGISTRY.get("web", bench_id)
        if harness:
            harness.environment = env
            result = run_benchmark(harness)
            print(json.dumps(result.to_dict(), indent=2, default=str))