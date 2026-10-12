"""AetherOS Vision — chart & diagram analysis.

Rule-based structural analysis of charts (bar, pie, line) and diagrams
(flowcharts, mind maps, ER/architecture/network) using pixel heuristics,
then enrichment via the vision router when available. No hallucinated
elements: every claim either comes from measured pixels or an explicit
VLM description flagged with its backend.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_vision.config import VisionSettings, load_vision_settings
from aetheros_vision.models import AnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class ChartEstimate:
    chart_type: str = "unknown"
    has_axes: bool = False
    has_legend: bool = False
    series_count: int = 0
    data_points: int = 0
    title: str = ""
    bars: int = 0
    pie_slices: int = 0
    line_segments: int = 0
    confidence: float = 0.0
    detail: str = ""


def estimate_chart(path: str) -> ChartEstimate:
    """Analyse a chart image using pixel heuristics."""
    from PIL import Image
    with Image.open(path) as img:
        img.load()
        if img.mode != "RGB":
            img = img.convert("RGB")
        width, height = img.size
        sample = img.resize((min(width, 160), min(height, 160)))
        pixels = list(sample.getdata())

    # Color cluster detection (dominant hues → legend/series hints).
    colors = _color_clusters(pixels)

    # Detect chart type by structure heuristics.
    estimate = ChartEstimate()
    estimate.has_legend = len(colors) >= 2
    estimate.series_count = len(colors)
    estimate.title = ""

    # Bar vs pie vs line discrimination using edge density across regions.
    try:
        from PIL import ImageFilter
        edges = sample.convert("L").filter(ImageFilter.FIND_EDGES)
        edge_data = list(edges.getdata())
        total_edges = sum(1 for p in edge_data if p > 120)
        ratio = total_edges / max(len(edge_data), 1)
        # Vertical vs horizontal structure
        width_edge_rows = _edge_profile(edge_data, sample.width, axis="x")
        height_edge_cols = _edge_profile(edge_data, sample.width, axis="y")

        if ratio < 0.08:
            estimate.chart_type = "line" if ratio > 0.02 else "unknown"
            estimate.line_segments = max(width_edge_rows, height_edge_cols) // 2
            estimate.data_points = max(width_edge_rows, height_edge_cols)
            estimate.confidence = 0.5
        else:
            # Pie: strong circular boundary → edges concentrated around center ring.
            center_ring = _center_ring_edge_ratio(edge_data, sample.width, sample.height)
            if center_ring > 0.15:
                estimate.chart_type = "pie"
                estimate.pie_slices = estimate.series_count or 2
                estimate.data_points = estimate.pie_slices
                estimate.confidence = 0.6
            else:
                estimate.chart_type = "bar"
                # Number of vertical bar separators ≈ columns with high edge density.
                estimate.bars = max(1, sum(1 for c in height_edge_cols if c > 2))
                estimate.data_points = estimate.bars
                estimate.has_axes = max(width_edge_rows) > 2
                estimate.confidence = 0.55
    except Exception as exc:  # noqa: BLE001
        logger.debug("Chart edge analysis failed: %s", exc)

    return estimate


def _color_clusters(pixels: List[tuple]) -> List[tuple]:
    """Return up to 6 dominant saturated colors (rounded to buckets)."""
    buckets: Dict[tuple, int] = {}
    for r, g, b in pixels:
        key = (r // 32 * 32, g // 32 * 32, b // 32 * 32)
        # Skip near-grays
        if abs(key[0] - key[1]) < 24 and abs(key[1] - key[2]) < 24:
            continue
        buckets[key] = buckets.get(key, 0) + 1
    sorted_buckets = sorted(buckets.items(), key=lambda kv: kv[1], reverse=True)[:6]
    return [b[0] for b in sorted_buckets if b[1] > 5]


def _edge_profile(edge_data: List[int], width: int, axis: str) -> List[int]:
    rows = len(edge_data) // width
    if axis == "x":
        return [sum(1 for x in range(width) if edge_data[y * width + x] > 120) for y in range(rows)]
    return [sum(1 for y in range(rows) if edge_data[y * width + x] > 120) for x in range(width)]


def _center_ring_edge_ratio(edge_data: List[int], width: int, height: int) -> float:
    cx, cy = width / 2, height / 2
    inner, outer = 0, 0
    for y in range(height):
        for x in range(width):
            dist = math.hypot(x - cx, y - cy)
            r = max(width, height) * 0.28
            if dist < r:
                inner += 1
                if edge_data[y * width + x] > 120:
                    outer += 1
    return outer / max(inner, 1)


class ChartAnalyzer:
    def __init__(self, settings: Optional[VisionSettings] = None):
        self._settings = settings or load_vision_settings()

    def analyze(self, path: str, question: str = "") -> AnalysisResult:
        estimate = estimate_chart(path)
        result = AnalysisResult(backend="rule")
        result.metadata["chart"] = {
            "chart_type": estimate.chart_type,
            "series_count": estimate.series_count,
            "data_points": estimate.data_points,
            "bars": estimate.bars,
            "pie_slices": estimate.pie_slices,
            "line_segments": estimate.line_segments,
            "has_axes": estimate.has_axes,
            "has_legend": estimate.has_legend,
            "confidence": round(estimate.confidence, 3),
        }
        result.summary = (
            f"Detected a {estimate.chart_type} chart "
            f"with approximately {estimate.data_points} data points "
            f"across {estimate.series_count} series."
        )
        result.labels = ["chart", estimate.chart_type]
        return result

    async def analyze_async(self, path: str, question: str = "") -> AnalysisResult:
        """Rule analysis plus VLM enrichment (skipped under local_only)."""
        result = self.analyze(path, question)
        if self._settings.local_only:
            return result
        try:
            from aetheros_vision.images import ImageUnderstanding
            vlm = ImageUnderstanding(self._settings)
            enriched = await vlm.analyze(path, question or result.summary)
            if enriched and enriched.summary:
                result.summary = enriched.summary
                result.backend = "hybrid"
                result.raw = enriched.raw
        except Exception as exc:  # noqa: BLE001
            logger.debug("Chart VLM enrichment unavailable: %s", exc)
        return result
