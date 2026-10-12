"""
Developer AI for AetherOS Intelligence Engine.

Understands entire repositories with:
    - Cross-file reasoning
    - Architecture understanding
    - Automatic documentation generation
    - Code explanation
    - Test generation
    - Refactoring suggestions

Integrates with the project understanding module for deep analysis.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CodeSymbol:
    name: str
    kind: str
    file_path: str
    line_start: int
    line_end: int
    docstring: str = ""
    dependencies: List[str] = field(default_factory=list)


@dataclass
class ArchitectureInsight:
    title: str
    description: str
    category: str
    severity: str
    file_paths: List[str] = field(default_factory=list)


@dataclass
class RefactoringSuggestion:
    title: str
    description: str
    category: str
    effort: str
    benefit: str
    file_path: str
    line_start: int = 0
    line_end: int = 0


class DeveloperAI:
    """AI-powered developer assistance for repository understanding.

    Provides cross-file reasoning, architecture analysis,
    documentation generation, code explanation, test generation,
    and refactoring suggestions.

    Usage::

        dev = DeveloperAI()
        analysis = dev.analyze_repository("/path/to/repo")
        docs = dev.generate_documentation("/path/to/repo")
        tests = dev.generate_tests("/path/to/file.py")
        suggestions = dev.suggest_refactoring("/path/to/repo")
    """

    def __init__(self) -> None:
        self._repos: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Repository analysis
    # ------------------------------------------------------------------

    def analyze_repository(self, path: str) -> Dict[str, Any]:
        """Comprehensive analysis of a repository."""
        root = Path(path).resolve()
        if not root.is_dir():
            return {"error": f"Directory not found: {path}"}

        cache_key = str(root)
        if cache_key in self._repos:
            return self._repos[cache_key]

        symbols = self._extract_symbols(root)
        architecture = self._analyze_architecture(root, symbols)
        dependencies = self._analyze_dependencies(symbols)
        insights = self._generate_insights(root, symbols)

        analysis = {
            "path": str(root),
            "name": root.name,
            "symbols": symbols,
            "architecture": architecture,
            "dependencies": dependencies,
            "insights": insights,
            "file_count": self._count_files(root),
        }

        self._repos[cache_key] = analysis
        return analysis

    def _extract_symbols(self, root: Path) -> List[Dict[str, Any]]:
        """Extract code symbols from all files in the repo."""
        symbols = []
        for ext in (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".rb"):
            for f in root.rglob(f"*{ext}"):
                if any(p.startswith(".") for p in f.relative_to(root).parts):
                    continue
                if len(f.relative_to(root).parts) > 5:
                    continue
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                    rel_path = str(f.relative_to(root))

                    if ext == ".py":
                        for m in re.finditer(
                            r"^(?:async\s+)?def\s+(\w+)\s*\(", content, re.MULTILINE
                        ):
                            symbols.append({
                                "name": m.group(1), "kind": "function",
                                "file": rel_path, "line": content[:m.start()].count("\n") + 1,
                            })
                        for m in re.finditer(r"^class\s+(\w+)", content, re.MULTILINE):
                            symbols.append({
                                "name": m.group(1), "kind": "class",
                                "file": rel_path, "line": content[:m.start()].count("\n") + 1,
                            })

                    elif ext in (".js", ".ts", ".jsx", ".tsx"):
                        for m in re.finditer(
                            r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", content
                        ):
                            symbols.append({
                                "name": m.group(1), "kind": "function",
                                "file": rel_path, "line": content[:m.start()].count("\n") + 1,
                            })
                        for m in re.finditer(r"class\s+(\w+)", content):
                            symbols.append({
                                "name": m.group(1), "kind": "class",
                                "file": rel_path, "line": content[:m.start()].count("\n") + 1,
                            })

                except Exception:
                    continue

        return symbols[:200]

    def _analyze_architecture(self, root: Path,
                              symbols: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze the architecture based on symbols and directory structure."""
        patterns = []

        dirs = [d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")]
        if "src" in dirs or "lib" in dirs:
            patterns.append({"type": "standard_layout", "detail": "src/ or lib/ layout"})
        if "services" in dirs or "api" in dirs:
            patterns.append({"type": "service_oriented", "detail": "API/services directory"})
        if "models" in dirs:
            patterns.append({"type": "model_centric", "detail": "Has models/ directory"})
        if "tests" in dirs or "test" in dirs:
            patterns.append({"type": "has_tests", "detail": "Has test directory"})

        symbol_files = set(s["file"] for s in symbols)
        if symbol_files:
            patterns.append({
                "type": "symbol_count",
                "detail": f"{len(symbols)} symbols across {len(symbol_files)} files",
            })

        return patterns

    def _analyze_dependencies(self, symbols: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze dependencies between symbols."""
        return {
            "total_symbols": len(symbols),
            "functions": len([s for s in symbols if s["kind"] == "function"]),
            "classes": len([s for s in symbols if s["kind"] == "class"]),
        }

    def _generate_insights(self, root: Path,
                           symbols: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate architecture and code insights."""
        insights = []

        if symbols:
            files_by_symbol = {}
            for s in symbols:
                files_by_symbol.setdefault(s["file"], []).append(s)
            high_symbol_files = sorted(
                files_by_symbol.items(), key=lambda x: len(x[1]), reverse=True
            )[:3]
            for file_path, file_symbols in high_symbol_files:
                insights.append({
                    "title": f"Hotspot: {file_path}",
                    "description": f"{len(file_symbols)} symbols defined here",
                    "category": "complexity",
                    "severity": "info",
                })

        test_count = sum(1 for s in symbols if "test" in s["name"].lower())
        if test_count == 0 and len(symbols) > 10:
            insights.append({
                "title": "Missing tests",
                "description": "No test symbols found in the codebase",
                "category": "testing",
                "severity": "warning",
            })

        return insights

    def _count_files(self, root: Path) -> Dict[str, int]:
        counts = {}
        for f in root.rglob("*"):
            if f.is_file() and not f.name.startswith("."):
                ext = f.suffix.lower()
                if ext:
                    counts[ext] = counts.get(ext, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10])

    # ------------------------------------------------------------------
    # Documentation generation
    # ------------------------------------------------------------------

    def generate_documentation(self, path: str) -> Dict[str, Any]:
        """Generate documentation for a repository or file."""
        root = Path(path).resolve()
        if root.is_file():
            return self._document_file(root)
        elif root.is_dir():
            return self._document_repo(root)
        return {"error": f"Path not found: {path}"}

    def _document_repo(self, root: Path) -> Dict[str, Any]:
        """Generate repository-level documentation."""
        analysis = self.analyze_repository(str(root))
        file_extensions = analysis.get("file_count", {})

        sections = []
        sections.append({
            "title": "Overview",
            "content": f"# {root.name}\n\nRepository with {analysis.get('symbols', [])} "
                       f"symbols across {analysis.get('file_count', {})}.",
        })
        sections.append({
            "title": "Architecture",
            "content": "\n".join(
                f"- {p.get('detail', p.get('type', ''))}"
                for p in analysis.get("architecture", [])
            ),
        })
        sections.append({
            "title": "File Types",
            "content": "\n".join(
                f"- {ext}: {count} files" for ext, count in file_extensions.items()
            ),
        })

        return {
            "name": root.name,
            "sections": sections,
            "total_files": sum(file_extensions.values()),
        }

    def _document_file(self, file_path: Path) -> Dict[str, Any]:
        """Generate documentation for a single file."""
        content = file_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        ext = file_path.suffix.lower()

        symbols = []
        if ext == ".py":
            for m in re.finditer(r"^(?:async\s+)?def\s+(\w+)", content, re.MULTILINE):
                symbols.append({"name": m.group(1), "kind": "function",
                                "line": content[:m.start()].count("\n") + 1})
            for m in re.finditer(r"^class\s+(\w+)", content, re.MULTILINE):
                symbols.append({"name": m.group(1), "kind": "class",
                                "line": content[:m.start()].count("\n") + 1})

        return {
            "file": file_path.name,
            "path": str(file_path),
            "lines": len(lines),
            "symbols": symbols,
            "documentation": f"# {file_path.name}\n\n{len(symbols)} symbols defined.",
        }

    # ------------------------------------------------------------------
    # Code explanation
    # ------------------------------------------------------------------

    def explain_code(self, path: str, function_name: str = "",
                     line_start: int = 0, line_end: int = 0) -> Dict[str, Any]:
        """Explain a specific piece of code."""
        file_path = Path(path)
        if not file_path.is_file():
            return {"error": f"File not found: {path}"}

        content = file_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()

        if function_name:
            func_lines = self._extract_function_lines(content, function_name)
            if func_lines:
                line_start, line_end = func_lines
                code_snippet = "\n".join(lines[line_start - 1:line_end])
            else:
                code_snippet = f"Function '{function_name}' not found"
        elif line_start and line_end:
            code_snippet = "\n".join(lines[line_start - 1:line_end])
        else:
            code_snippet = "\n".join(lines[:30])

        return {
            "file": file_path.name,
            "function": function_name or "entire file",
            "code_snippet": code_snippet,
            "line_count": line_end - line_start if line_end else 0,
        }

    def _extract_function_lines(self, content: str,
                                function_name: str) -> Optional[tuple]:
        """Find the line range of a function definition."""
        pattern = rf"^(?:async\s+)?def\s+{re.escape(function_name)}\s*\("
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if re.match(pattern, line):
                start = i + 1
                end = start
                for j in range(i + 1, len(lines)):
                    if lines[j] and not lines[j].startswith((" ", "\t", ")")):
                        end = j
                        break
                else:
                    end = len(lines)
                return (start, end)
        return None

    # ------------------------------------------------------------------
    # Test generation
    # ------------------------------------------------------------------

    def generate_tests(self, path: str, framework: str = "pytest") -> Dict[str, Any]:
        """Analyze a file and generate test scaffolding."""
        file_path = Path(path)
        if not file_path.is_file():
            return {"error": f"File not found: {path}"}

        content = file_path.read_text(encoding="utf-8", errors="replace")
        functions = []

        ext = file_path.suffix.lower()
        if ext == ".py":
            for m in re.finditer(r"^def (\w+)", content, re.MULTILINE):
                name = m.group(1)
                if not name.startswith("_"):
                    functions.append(name)

        if framework == "pytest":
            test_templates = [
                f"def test_{fn}():\n    \"\"\"Test {fn}.\"\"\"\n    pass\n"
                for fn in functions
            ]

        return {
            "file": file_path.name,
            "function_count": len(functions),
            "functions": functions,
            "framework": framework,
            "test_templates": test_templates,
        }

    # ------------------------------------------------------------------
    # Refactoring suggestions
    # ------------------------------------------------------------------

    def suggest_refactoring(self, path: str) -> List[Dict[str, Any]]:
        """Analyze code for refactoring opportunities."""
        root = Path(path).resolve()
        suggestions = []

        if root.is_file():
            files_to_check = [root]
        elif root.is_dir():
            files_to_check = []
            for ext in (".py", ".js", ".ts", ".jsx", ".tsx"):
                files_to_check.extend(root.rglob(f"*{ext}"))
        else:
            return [{"error": f"Path not found: {path}"}]

        for f in files_to_check:
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                lines = content.splitlines()
                rel_path = str(f.relative_to(root)) if root.is_dir() else f.name

                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if len(stripped) > 120:
                        suggestions.append({
                            "title": f"Long line at {rel_path}:{i+1}",
                            "description": f"Line is {len(stripped)} characters (max 120)",
                            "category": "readability",
                            "effort": "low",
                            "benefit": "medium",
                            "file_path": rel_path,
                            "line_start": i + 1,
                            "line_end": i + 1,
                        })

                if content.count("\n") > 500:
                    suggestions.append({
                        "title": f"Large file: {rel_path}",
                        "description": f"File has {content.count(chr(10)) + 1} lines",
                        "category": "modularity",
                        "effort": "medium",
                        "benefit": "high",
                        "file_path": rel_path,
                    })

                if "TODO" in content or "FIXME" in content:
                    suggestions.append({
                        "title": f"TODO/FIXME markers in {rel_path}",
                        "description": f"File contains unaddressed TODO/FIXME markers",
                        "category": "maintenance",
                        "effort": "varies",
                        "benefit": "high",
                        "file_path": rel_path,
                    })

                if ext == ".py" and "class " in content:
                    class_count = len(re.findall(r"^class ", content, re.MULTILINE))
                    if class_count > 10:
                        suggestions.append({
                            "title": f"Many classes in {rel_path}",
                            "description": f"File has {class_count} classes",
                            "category": "modularity",
                            "effort": "high",
                            "benefit": "high",
                            "file_path": rel_path,
                        })

            except Exception:
                continue

        return suggestions[:20]

    # ------------------------------------------------------------------
    # Cross-file reasoning
    # ------------------------------------------------------------------

    def cross_file_reference(self, path: str, symbol: str) -> List[Dict[str, Any]]:
        """Find all references to a symbol across the repository."""
        root = Path(path).resolve()
        if not root.is_dir():
            root = root.parent

        references = []
        for ext in (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go"):
            for f in root.rglob(f"*{ext}"):
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                    for i, line in enumerate(content.splitlines(), 1):
                        if symbol in line and not line.strip().startswith(("#", "//")):
                            references.append({
                                "file": str(f.relative_to(root)),
                                "line": i,
                                "content": line.strip()[:120],
                            })
                except Exception:
                    continue

        return references[:50]

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        return {
            "repos_analyzed": len(self._repos),
            "recent_repos": list(self._repos.keys())[-3:],
        }
