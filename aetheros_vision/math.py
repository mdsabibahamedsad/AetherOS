"""AetherOS Vision — mathematical understanding.

Detects equations and math regions in images, extracts rendered math, and
attempts OCR-based equation recognition. Deterministic heuristics only —
formula symbols are reported as found with confidence, never fabricated.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aetheros_vision.config import VisionSettings, load_vision_settings
from aetheros_vision.models import AnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class MathInsight:
    equation_count: int = 0
    has_math_notation: bool = False
    notation_types: List[str] = field(default_factory=list)
    sample_equations: List[str] = field(default_factory=list)
    equations: List[str] = field(default_factory=list)
    is_graph: bool = False
    is_geometry: bool = False
    scientific_notation: bool = False
    confidence: float = 0.0


# Symbols that indicate math content in OCR text.
_MATH_INDICATORS = [
    r"[=≠≈≡]",
    r"[∑∏∫√∂]",
    r"[≤≥<>]",
    r"\^[0-9A-Za-z{}()+-]",
    r"_[0-9A-Za-z{}()]",
    r"[πθφλμσ]",
    r"sin|cos|tan|log|ln|sqrt|frac|lim|∑|∫",
    r"\b\d+[xX÷*/]\b",
    r"[（）]",
    r"[±∓×÷]",
]

_GRAPH_INDICATORS = [r"x-axis", r"y-axis", r"axis", r"origin", r"intercept", r"slope", r"plot", r"coordinate"]
_GEOMETRY_INDICATORS = [r"triangle", r"angle", r"circle", r"radius", r"diameter", r"parallel", r"perpendicular", r"polygon"]
_SCIENTIFIC_INDICATORS = [r"\d+\.\d+\s*[eE][+-]?\d+", r"\d+\s*[eE][+-]?\d+", r"[×x]\s*10\s*\^"]


def analyze_math_text(text: str) -> MathInsight:
    insight = MathInsight()
    if not text:
        return insight
    lines = text.splitlines()
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        hits = [i for i in _MATH_INDICATORS if re.search(i, stripped)]
        if hits:
            insight.equation_count += 1
            if len(insight.equations) < 20:
                insight.equations.append(stripped[:300])
            insight.has_math_notation = True
            if "∑" in stripped or "∫" in stripped or "∑" in stripped:
                insight.notation_types.append("calculus")
            if "=" in stripped or "≠" in stripped or "≈" in stripped or "≡" in stripped:
                insight.notation_types.append("equation")
            if re.search(r"[≤≥<>]", stripped):
                insight.notation_types.append("inequality")
            if re.search(r"\^[0-9A-Za-z{}()+-]", stripped):
                insight.notation_types.append("exponent")
    insight.sample_equations = insight.equations[:5]
    insight.notation_types = list(dict.fromkeys(insight.notation_types))

    if any(re.search(p, text, re.IGNORECASE) for p in _GRAPH_INDICATORS):
        insight.is_graph = True
    if any(re.search(p, text, re.IGNORECASE) for p in _GEOMETRY_INDICATORS):
        insight.is_geometry = True
    if any(re.search(p, text) for p in _SCIENTIFIC_INDICATORS):
        insight.scientific_notation = True

    score = insight.equation_count
    if insight.notation_types:
        score += len(insight.notation_types)
    insight.confidence = min(0.95, 0.3 + 0.1 * score)
    return insight


class MathAnalyzer:
    def __init__(self, settings: Optional[VisionSettings] = None):
        self._settings = settings or load_vision_settings()

    def analyze(self, path: str, question: str = "") -> AnalysisResult:
        from aetheros_vision.ocr import create_ocr_engine
        engine = create_ocr_engine(self._settings)
        result = AnalysisResult(backend="rule")
        if engine.is_available():
            ocr = engine.extract(path)
            if ocr and ocr.success:
                result.ocr = ocr
                result.text = ocr.text
                insight = analyze_math_text(ocr.text)
                result.metadata["math"] = {
                    "equation_count": insight.equation_count,
                    "has_math_notation": insight.has_math_notation,
                    "notation_types": insight.notation_types,
                    "sample_equations": insight.sample_equations,
                    "is_graph": insight.is_graph,
                    "is_geometry": insight.is_geometry,
                    "scientific_notation": insight.scientific_notation,
                    "confidence": round(insight.confidence, 3),
                }
                result.labels = ["math"]
                result.summary = (
                    f"Detected {insight.equation_count} mathematical region(s) "
                    f"({', '.join(insight.notation_types) or 'unknown types'})."
                )
            else:
                result.success = False
                result.error = ocr.error if ocr else "OCR unavailable"
        else:
            result.success = False
            result.error = "OCR engine unavailable for math analysis"
        return result
