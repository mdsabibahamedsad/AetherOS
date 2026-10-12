"""AetherOS Vision — code screenshot intelligence.

Recognises programming languages from code-screenshot text (via OCR),
detects errors / stack traces / terminal output / IDE chrome, and proposes
fixes. Everything is derived from the OCR'd text plus deterministic
heuristics; no hallucinated syntax.
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
class CodeInsight:
    language: str = "unknown"
    confidence: float = 0.0
    error_messages: List[str] = field(default_factory=list)
    stack_traces: List[str] = field(default_factory=list)
    is_terminal: bool = False
    has_syntax_highlighting: bool = False
    ide_name: str = ""
    suggested_fixes: List[str] = field(default_factory=list)
    code: str = ""


# Language signature matchers: (pattern, language)
_LANGUAGE_SIGNATURES = [
    (r"\bdef\s+\w+\s*\(.*\)\s*:|^\s*import\s+\w+$|^\s*from\s+\w+\s+import\b", "python"),
    (r"\bfunction\s+\w+\s*\(|=>\s*\{|const\s+\w+\s*=\s*[\(|\[]|console\.log\(", "javascript"),
    (r"\bpublic\s+(static\s+)?void\s+main|System\.out\.println|^\s*package\s+[\w.]+;", "java"),
    (r"#include\s*<\w+>|std::|\bint\s+main\s*\(", "cpp"),
    (r"\buse\s+strict\b|#!/usr/bin/perl", "perl"),
    (r"^\s*package\s+\w+;|^\s*import\s+\w+\.\*;", "java"),
    (r"using\s+System;|namespace\s+\w+|\bConsole\.WriteLine\(", "csharp"),
    (r"func\s+\w+\s*\(|\bgo\s+mod\b|package\s+main\b", "go"),
    (r"\blet\s+\w+\s*=\s*\d+;|fn\s+\w+\s*\(", "rust"),
    (r"SELECT\s+.*\s+FROM\s+.*\s+WHERE|INSERT\s+INTO\b", "sql"),
    (r"^\s*<!DOCTYPE html>|<html|</div>|class=\"", "html"),
    (r"^\s*#!/bin/bash|^\s*\$\{|fi\s*$|^\s*for\s+\w+\s+in\s+.*;", "bash"),
]

# Error signatures that indicate a real error/stack trace.
_ERROR_SIGNATURES = [
    r"(?i)error\s*:|exception\s+in|traceback \(most recent call last\)",
    r"(?i)fatal\s*error|unhandled\s+exception|cannot\s+find\s+symbol",
    r"(?i)typeerror|valueerror|keyerror|attributeerror|syntaxerror|indexerror",
    r"(?i)undefined is not a function|is not defined|referenceerror",
    r"(?i)at\s+[\w.$]+\s*\([\w./:()\-. ]+:\d+:\d+\)",  # JS/TS stack frame
    r"File\s+\".*?\",\s+line\s+\d+",                    # Python stack frame
]

_FIX_SUGGESTIONS = {
    "python": "Check the referenced variable/function for a typo or missing definition.",
    "javascript": "Check for undefined variables, missing imports, or null values before access.",
    "java": "Verify the symbol exists in the current class or an imported package.",
    "cpp": "Check that all referenced headers are included and symbols are in scope.",
    "bash": "Check that referenced files/commands exist and are executable.",
}


def analyze_code_screenshot(text: str) -> CodeInsight:
    """Analyse OCR'd screenshot text for language, errors, and terminal output."""
    insight = CodeInsight()
    if not text:
        return insight
    insight.code = text.strip()

    # Terminal detection: prompt markers + terse output lines.
    if re.search(r"(?m)^[\w@./:~ -]+\$ |PS [A-Z]:\\|C:\\>|> ", text):
        insight.is_terminal = True
        insight.language = "terminal"

    # Language detection.
    best_lang, best_conf = "unknown", 0.0
    for pattern, lang in _LANGUAGE_SIGNATURES:
        matches = re.findall(pattern, text)
        if matches:
            conf = min(0.95, 0.5 + 0.08 * len(matches))
            if conf > best_conf:
                best_lang, best_conf = lang, conf
    if insight.is_terminal:
        best_lang = "terminal"
    insight.language = best_lang
    insight.confidence = best_conf if best_lang != "unknown" else 0.2

    # Syntax highlighting heuristic: ANSI escape sequences or common IDE colors.
    insight.has_syntax_highlighting = bool(re.search(r"\x1b\[|\033\[", text))

    # IDE chrome detection.
    ide_names = ["Visual Studio Code", "Visual Studio", "IntelliJ", "PyCharm", "CLion", "WebStorm", "Eclipse", "Xcode"]
    for name in ide_names:
        if name.lower() in text.lower():
            insight.ide_name = name
            break

    # Errors and stack traces.
    for signature in _ERROR_SIGNATURES:
        for m in re.finditer(signature, text):
            snippet = _capture_error_line(text, m.start())
            if snippet and snippet not in insight.error_messages:
                insight.error_messages.append(snippet)
    if "stack trace" in text.lower() or "at " in text or re.search(r'File\s+".*?",\s+line\s+\d+', text):
        # Best-effort stack frame capture (JS/TS "at ..." frames and
        # Python "File ..., line N" frames).
        frames = re.findall(r"at\s+[\w.$]+.*?:\d+:\d+", text) or re.findall(r'File\s+".*?",\s+line\s+\d+', text)
        insight.stack_traces = frames[:10]

    if insight.error_messages:
        suggestion = _FIX_SUGGESTIONS.get(insight.language)
        if suggestion:
            insight.suggested_fixes.append(suggestion)
    return insight


def _capture_error_line(text: str, start: int) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", start)
    if line_end == -1:
        line_end = len(text)
    return text[line_start:line_end].strip()[:300]


class CodeScreenshotAnalyzer:
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
                insight = analyze_code_screenshot(ocr.text)
                result.metadata["code"] = {
                    "language": insight.language,
                    "confidence": round(insight.confidence, 3),
                    "errors": insight.error_messages,
                    "stack_traces": insight.stack_traces,
                    "is_terminal": insight.is_terminal,
                    "ide": insight.ide_name,
                    "syntax_highlighting": insight.has_syntax_highlighting,
                    "suggested_fixes": insight.suggested_fixes,
                }
                result.labels = ["code", insight.language]
                error_summary = f"Detected {len(insight.error_messages)} error(s)." if insight.error_messages else "No obvious errors detected."
                result.summary = f"Code screenshot in {insight.language} ({insight.confidence:.0%} confidence). {error_summary}"
            else:
                result.success = False
                result.error = ocr.error if ocr else "OCR unavailable"
        else:
            result.success = False
            result.error = "OCR engine unavailable for code screenshot analysis"
        return result
