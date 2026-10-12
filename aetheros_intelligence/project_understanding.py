"""
Project Understanding for AetherOS Intelligence Engine.

Analyzes repositories to understand:
    - Architecture
    - Dependencies
    - Frameworks
    - Code Quality
    - Security Risks
    - Performance Issues
    - Technical Debt

Provides automated insights for any project on the filesystem.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ProjectUnderstanding:
    """Analyzes and understands project structures.

    Provides deep understanding of any repository including its
    architecture, dependencies, code quality, and potential issues.

    Usage::

        analyzer = ProjectUnderstanding()

        # Full project analysis
        analysis = analyzer.analyze("/path/to/project")

        # Single file understanding
        file_info = analyzer.understand_file("/path/to/file.py")
    """

    # File patterns for common ecosystems
    ECOSYSTEM_PATTERNS = {
        "python": ["*.py", "requirements.txt", "setup.py", "pyproject.toml", "Pipfile"],
        "node": ["*.js", "*.ts", "*.jsx", "*.tsx", "package.json"],
        "java": ["*.java", "pom.xml", "build.gradle"],
        "go": ["*.go", "go.mod"],
        "rust": ["*.rs", "Cargo.toml"],
        "ruby": ["*.rb", "Gemfile"],
    }

    # File types to check for quality analysis
    QUALITY_FILE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".rb"}

    def __init__(self) -> None:
        self._projects: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Main analysis methods
    # ------------------------------------------------------------------

    def analyze(self, path: str) -> Dict[str, Any]:
        """Perform a comprehensive project analysis.

        Args:
            path: Path to the project root directory

        Returns:
            Dict with architecture, dependencies, quality, and issues.
        """
        root = Path(path).resolve()
        if not root.is_dir():
            return {"error": f"Directory not found: {path}"}

        # Check for cached analysis
        cache_key = str(root)
        if cache_key in self._projects:
            return self._projects[cache_key]

        # Run all analyses
        analysis = {
            "path": str(root),
            "name": root.name,
            "ecosystem": self._detect_ecosystem(root),
            "architecture": self._analyze_architecture(root),
            "dependencies": self._analyze_dependencies(root),
            "frameworks": self._detect_frameworks(root),
            "code_quality": self._analyze_code_quality(root),
            "security_risks": self._detect_security_risks(root),
            "performance": self._analyze_performance(root),
            "technical_debt": self._estimate_technical_debt(root),
            "file_summary": self._summarize_files(root),
            "stats": self._compute_stats(root),
        }

        self._projects[cache_key] = analysis
        return analysis

    def understand_file(self, path: str) -> Dict[str, Any]:
        """Analyze a single file in depth.

        Args:
            path: Path to the file

        Returns:
            Dict with file purpose, dependencies, patterns, and metrics.
        """
        file_path = Path(path).resolve()
        if not file_path.is_file():
            return {"error": f"File not found: {path}"}

        content = file_path.read_text(encoding="utf-8", errors="replace")
        ext = file_path.suffix.lower()

        return {
            "path": str(file_path),
            "name": file_path.name,
            "extension": ext,
            "size": file_path.stat().st_size,
            "lines": len(content.splitlines()),
            "purpose": self._classify_file_purpose(file_path.name, content),
            "imports": self._extract_imports(content, ext),
            "exports": self._extract_exports(content, ext),
            "classes": self._extract_classes(content, ext),
            "functions": self._extract_functions(content, ext),
            "patterns": self._detect_patterns(content),
        }

    # ------------------------------------------------------------------
    # Ecosystem detection
    # ------------------------------------------------------------------

    def _detect_ecosystem(self, root: Path) -> Dict[str, Any]:
        """Detect the primary ecosystem(s) of a project."""
        ecosystems = {}
        for eco, patterns in self.ECOSYSTEM_PATTERNS.items():
            matches = []
            for pattern in patterns:
                found = list(root.rglob(pattern))
                # Don't go too deep for common patterns
                if pattern.startswith("*."):
                    found = [f for f in found if len(f.relative_to(root).parts) <= 3]
                matches.extend(str(f.relative_to(root)) for f in found[:20])
            if matches:
                ecosystems[eco] = {
                    "detected": True,
                    "file_count": len(matches),
                    "key_files": matches[:5],
                }

        # Determine primary
        counts = {eco: info["file_count"] for eco, info in ecosystems.items()}
        primary = max(counts, key=counts.get) if counts else "unknown"

        return {
            "ecosystems": ecosystems,
            "primary": primary,
            "has_package_manager": bool(ecosystems),
        }

    def _detect_frameworks(self, root: Path) -> Dict[str, Any]:
        """Detect frameworks used in the project."""
        frameworks = []

        # Check for common config files
        framework_indicators = {
            "React": ["react", "jsx", "tsx"],
            "Vue": ["vue.config.js", "nuxt.config"],
            "Angular": ["angular.json"],
            "Next.js": ["next.config.js", "next.config.mjs"],
            "Django": ["manage.py", "django"],
            "Flask": ["flask"],
            "FastAPI": ["fastapi"],
            "Spring": ["pom.xml", "build.gradle"],
            "Express": ["express"],
            "PyTorch": ["pytorch", "torch"],
            "TensorFlow": ["tensorflow", "tf"],
        }

        # Quick scan of key files
        for ext in ["*.py", "*.js", "*.ts", "*.json", "*.yaml", "*.yml", "*.xml"]:
            for f in root.rglob(ext):
                if len(f.relative_to(root).parts) > 4:  # Don't go too deep
                    continue
                try:
                    content = f.read_text(encoding="utf-8", errors="replace").lower()
                    for framework, indicators in framework_indicators.items():
                        if any(ind in content for ind in indicators):
                            if framework not in frameworks:
                                frameworks.append(framework)
                except Exception:
                    continue

        return {"frameworks": frameworks[:10], "count": len(frameworks)}

    # ------------------------------------------------------------------
    # Architecture analysis
    # ------------------------------------------------------------------

    def _analyze_architecture(self, root: Path) -> Dict[str, Any]:
        """Analyze the project architecture."""
        structure = self._map_directory_structure(root, max_depth=3)
        patterns = self._detect_architecture_patterns(root)
        return {
            "structure": structure,
            "patterns": patterns,
        }

    def _map_directory_structure(self, root: Path, max_depth: int = 3) -> List[Dict[str, Any]]:
        """Map the directory structure up to max_depth."""
        entries = []
        try:
            for entry in sorted(root.iterdir()):
                if entry.name.startswith((".", "__pycache__", "node_modules", "venv", ".git")):
                    continue

                if entry.is_dir():
                    depth = max_depth - 1
                    children = self._map_directory_structure(entry, depth) if depth > 0 else []
                    entries.append({
                        "name": entry.name,
                        "type": "directory",
                        "children": children,
                        "file_count": len(children),
                    })
                else:
                    if entry.suffix.lower() in self.QUALITY_FILE_EXTENSIONS:
                        entries.append({
                            "name": entry.name,
                            "type": "file",
                            "extension": entry.suffix.lower(),
                            "size": entry.stat().st_size,
                        })
        except PermissionError:
            pass

        return entries[:50]  # Limit to 50 entries

    def _detect_architecture_patterns(self, root: Path) -> List[str]:
        """Detect common architecture patterns."""
        patterns = []
        structure_str = str(root)

        # Check for common patterns
        checks = [
            ("Monolithic", ["src", "app", "lib"]),
            ("Modular", ["modules", "components", "features"]),
            ("Microservices", ["services", "api", "gateway"]),
            ("Clean Architecture", ["domain", "application", "infrastructure", "presentation"]),
            ("MVC", ["models", "views", "controllers", "routes"]),
            ("Event-Driven", ["events", "handlers", "queues", "events"]),
            ("Plugin Architecture", ["plugins", "extensions", "providers"]),
            ("Hexagonal", ["ports", "adapters", "core"]),
        ]

        for pattern, dirs in checks:
            if any((root / d).is_dir() for d in dirs):
                patterns.append(pattern)

        return patterns

    # ------------------------------------------------------------------
    # Dependency analysis
    # ------------------------------------------------------------------

    def _analyze_dependencies(self, root: Path) -> Dict[str, Any]:
        """Analyze project dependencies."""
        deps = {
            "internal": [],
            "external": [],
            "dev": [],
        }

        # Python: requirements.txt, pyproject.toml
        req_txt = root / "requirements.txt"
        if req_txt.exists():
            for line in req_txt.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith(("#", "-")):
                    deps["external"].append(line)

        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            try:
                import tomllib
                data = tomllib.loads(pyproject.read_text())
                project = data.get("project", {})
                for dep in project.get("dependencies", []):
                    if dep not in deps["external"]:
                        deps["external"].append(dep)
            except Exception:
                pass

        # Node: package.json
        pkg_json = root / "package.json"
        if pkg_json.exists():
            try:
                pkg = json.loads(pkg_json.read_text())
                deps["external"].extend(pkg.get("dependencies", {}).keys())
                deps["dev"].extend(pkg.get("devDependencies", {}).keys())
            except Exception:
                pass

        # Internal modules
        for ext in self.QUALITY_FILE_EXTENSIONS:
            for f in root.rglob(f"*{ext}"):
                if len(f.relative_to(root).parts) <= 3:
                    try:
                        imports = self._extract_imports(
                            f.read_text(encoding="utf-8", errors="replace"),
                            ext,
                        )
                        for imp in imports:
                            if imp not in deps["internal"]:
                                deps["internal"].append(imp)
                    except Exception:
                        pass

        return {
            "external_count": len(deps["external"]),
            "external": deps["external"][:20],
            "dev_count": len(deps["dev"]),
            "dev": deps["dev"][:10],
            "internal_count": len(set(deps["internal"])),
        }

    # ------------------------------------------------------------------
    # Code quality analysis
    # ------------------------------------------------------------------

    def _analyze_code_quality(self, root: Path) -> Dict[str, Any]:
        """Analyze code quality metrics."""
        total_lines = 0
        total_files = 0
        long_lines = 0
        todo_count = 0
        fixme_count = 0
        no_docstring_count = 0

        for ext in self.QUALITY_FILE_EXTENSIONS:
            for f in root.rglob(f"*{ext}"):
                if len(f.relative_to(root).parts) > 4:
                    continue
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                    lines = content.splitlines()
                    total_lines += len(lines)
                    total_files += 1

                    # Long lines
                    for line in lines:
                        if len(line) > 100:
                            long_lines += 1

                    # TODOs and FIXMEs
                    todo_count += content.count("TODO") + content.count("todo")
                    fixme_count += content.count("FIXME") + content.count("fixme")

                    # Missing docstrings (Python)
                    if ext == ".py":
                        if '"""' not in content and "'''" not in content:
                            no_docstring_count += 1

                except Exception:
                    continue

        quality_score = 1.0
        if total_files > 0:
            # Penalize for long lines
            if total_lines > 0:
                long_line_ratio = long_lines / total_lines
                quality_score -= long_line_ratio * 0.3

            # Penalize for TODOs
            if todo_count > 5:
                quality_score -= min(0.1, todo_count * 0.01)

            # Penalize for missing docstrings
            if no_docstring_count > 0 and total_files > 0:
                docstring_ratio = no_docstring_count / total_files
                quality_score -= docstring_ratio * 0.2

        quality_score = max(0.1, min(1.0, quality_score))

        return {
            "total_files": total_files,
            "total_lines": total_lines,
            "long_lines": long_lines,
            "todos": todo_count,
            "fixmes": fixme_count,
            "files_without_docstrings": no_docstring_count,
            "quality_score": round(quality_score, 2),
        }

    def _detect_security_risks(self, root: Path) -> List[Dict[str, Any]]:
        """Detect potential security risks."""
        risks = []
        risk_patterns = {
            "hardcoded_api_key": r"(?:api[_-]?key|apikey|secret|token)\s*[=:]\s*['\"][a-zA-Z0-9_\-]{20,}['\"]",
            "sql_injection": r"execute\s*\(\s*f['\"]|\.format\(.*\buser\b|f-string.*execute",
            "eval_usage": r"\beval\s*\(",
            "exec_usage": r"\bexec\s*\(",
            "insecure_crypto": r"(?:md5|sha1)\s*\(",
            "debug_enabled": r"debug\s*=\s*True",
            "password_hardcoded": r"password\s*[=:]\s*['\"][^'\"]+['\"]",
        }

        for ext in self.QUALITY_FILE_EXTENSIONS:
            for f in root.rglob(f"*{ext}"):
                if len(f.relative_to(root).parts) > 4:
                    continue
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                    rel_path = str(f.relative_to(root))

                    for risk_name, pattern in risk_patterns.items():
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for match in matches:
                            risks.append({
                                "type": risk_name,
                                "file": rel_path,
                                "line": content[:match.start()].count("\n") + 1,
                                "severity": "high" if risk_name in (
                                    "hardcoded_api_key", "sql_injection",
                                ) else "medium",
                            })
                except Exception:
                    continue

        return risks[:20]

    def _analyze_performance(self, root: Path) -> Dict[str, Any]:
        """Analyze for potential performance issues."""
        issues = []

        for ext in self.QUALITY_FILE_EXTENSIONS:
            for f in root.rglob(f"*{ext}"):
                if len(f.relative_to(root).parts) > 4:
                    continue
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                    rel_path = str(f.relative_to(root))

                    # Check for common anti-patterns
                    if "for " in content and "range(len(" in content:
                        issues.append({
                            "type": "inefficient_loop",
                            "file": rel_path,
                            "description": "Consider using enumerate() instead of range(len())",
                            "severity": "low",
                        })
                    if "import *" in content:
                        issues.append({
                            "type": "wildcard_import",
                            "file": rel_path,
                            "description": "Wildcard imports can cause namespace pollution",
                            "severity": "low",
                        })
                    if content.count("nested for") > 2:
                        issues.append({
                            "type": "deep_nesting",
                            "file": rel_path,
                            "description": "Deeply nested loops may impact performance",
                            "severity": "medium",
                        })
                except Exception:
                    continue

        return {"issues": issues[:10], "count": len(issues)}

    def _estimate_technical_debt(self, root: Path) -> Dict[str, Any]:
        """Estimate technical debt based on code quality signals."""
        todo_count = 0
        fixme_count = 0
        xxx_count = 0
        hack_count = 0

        for ext in self.QUALITY_FILE_EXTENSIONS:
            for f in root.rglob(f"*{ext}"):
                if len(f.relative_to(root).parts) > 4:
                    continue
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                    todo_count += content.count("TODO") + content.count("todo")
                    fixme_count += content.count("FIXME") + content.count("fixme")
                    xxx_count += content.count("XXX")
                    hack_count += content.count("HACK") + content.count("hack")
                except Exception:
                    continue

        total_markers = todo_count + fixme_count + xxx_count + hack_count

        # Estimate remediation effort
        if total_markers == 0:
            effort = "low"
        elif total_markers < 10:
            effort = "low"
        elif total_markers < 30:
            effort = "medium"
        else:
            effort = "high"

        return {
            "todo_count": todo_count,
            "fixme_count": fixme_count,
            "total_markers": total_markers,
            "estimated_effort": effort,
            "recommendation": "Address TODO/FIXME markers" if total_markers > 0 else "No significant debt markers found",
        }

    # ------------------------------------------------------------------
    # File-level analysis helpers
    # ------------------------------------------------------------------

    def _classify_file_purpose(self, name: str, content: str) -> str:
        """Classify a file's purpose based on name and content."""
        name_lower = name.lower()

        # Common naming patterns
        if "test" in name_lower or name_lower.startswith("test_"):
            return "Test file"
        if "model" in name_lower:
            return "Data model"
        if "view" in name_lower:
            return "View/UI component"
        if "controller" in name_lower:
            return "Controller"
        if "service" in name_lower:
            return "Service"
        if "config" in name_lower:
            return "Configuration"
        if "util" in name_lower or "helper" in name_lower:
            return "Utility"
        if "api" in name_lower:
            return "API endpoint"
        if "plugin" in name_lower:
            return "Plugin"
        if "schema" in name_lower:
            return "Schema definition"
        if "migration" in name_lower:
            return "Database migration"
        if "middleware" in name_lower:
            return "Middleware"
        if "factory" in name_lower:
            return "Factory"
        if "provider" in name_lower:
            return "Provider"
        if "adapter" in name_lower:
            return "Adapter"

        # Check for class definitions
        if "class " in content:
            return "Class definition"

        # Check for main entry point
        if 'if __name__ == "__main__"' in content or "def main(" in content:
            return "Entry point"

        return "Module"

    def _extract_imports(self, content: str, ext: str) -> List[str]:
        """Extract import statements from code."""
        imports = []

        if ext in (".py",):
            # Python imports
            for match in re.finditer(
                r"^(?:from\s+(\S+)\s+import|import\s+(\S+))",
                content,
                re.MULTILINE,
            ):
                imp = match.group(1) or match.group(2)
                if imp:
                    imports.append(imp.split(".")[0])

        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            # JS/TS imports
            for match in re.finditer(
                r"(?:import|require)\s*\(?\s*['\"]([^'\"]+)['\"]",
                content,
            ):
                imp = match.group(1)
                # Skip relative imports
                if imp and not imp.startswith((".", "/")):
                    imports.append(imp.split("/")[0])

        return list(set(imports))

    def _extract_exports(self, content: str, ext: str) -> List[str]:
        """Extract exported symbols."""
        exports = []

        if ext in (".py",):
            for match in re.finditer(r"^def (\w+)", content, re.MULTILINE):
                exports.append(match.group(1))
            for match in re.finditer(r"^class (\w+)", content, re.MULTILINE):
                exports.append(match.group(1))

        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            for match in re.finditer(r"export (?:default |const |function |class )?(\w+)", content):
                exports.append(match.group(1))

        return exports

    def _extract_classes(self, content: str, ext: str) -> List[str]:
        """Extract class definitions."""
        classes = []
        if ext in (".py",):
            for match in re.finditer(r"^class (\w+)", content, re.MULTILINE):
                classes.append(match.group(1))
        elif ext in (".java",):
            for match in re.finditer(r"(?:public |private )?(?:class |interface |enum )(\w+)", content):
                classes.append(match.group(1))
        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            for match in re.finditer(r"(?:export )?(?:default )?(?:class )(\w+)", content):
                classes.append(match.group(1))
        return classes

    def _extract_functions(self, content: str, ext: str) -> List[str]:
        """Extract function/method definitions."""
        functions = []
        if ext in (".py",):
            for match in re.finditer(r"^async def (\w+)|^def (\w+)", content, re.MULTILINE):
                functions.append(match.group(1) or match.group(2))
        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            for match in re.finditer(r"(?:async )?(?:function )?(?:(\w+)\s*=\s*(?:async\s*)?\(|(\w+)\s*\([^)]*\)\s*\{)", content):
                functions.append(match.group(1) or match.group(2))
        return functions

    def _detect_patterns(self, content: str) -> List[str]:
        """Detect common code patterns."""
        patterns = []
        if "class " in content:
            patterns.append("Object-oriented")
        if "def " in content and " -> " in content:
            patterns.append("Type hints")
        if "async " in content:
            patterns.append("Async/await")
        if "lambda " in content:
            patterns.append("Lambda/functions")
        if "decorator" in content or content.startswith("@"):
            patterns.append("Decorators")
        if "try:" in content or "try {" in content:
            patterns.append("Error handling")
        if import_patterns := re.findall(r"^(?:import |from )", content, re.MULTILINE):
            patterns.append("External dependencies")
        return patterns

    # ------------------------------------------------------------------
    # Summary and stats
    # ------------------------------------------------------------------

    def _summarize_files(self, root: Path) -> Dict[str, Any]:
        """Summarize the files in the project."""
        by_extension: Counter = Counter()
        by_purpose: Counter = Counter()
        total = 0

        for f in root.rglob("*"):
            if f.is_file() and not f.name.startswith("."):
                total += 1
                ext = f.suffix.lower()
                if ext:
                    by_extension[ext] += 1

                if ext in self.QUALITY_FILE_EXTENSIONS:
                    try:
                        content = f.read_text(encoding="utf-8", errors="replace")[:500]
                        purpose = self._classify_file_purpose(f.name, content)
                        by_purpose[purpose] += 1
                    except Exception:
                        by_purpose["Unknown"] += 1

        return {
            "total_files": total,
            "by_extension": dict(by_extension.most_common(10)),
            "by_purpose": dict(by_purpose.most_common(10)),
        }

    def _compute_stats(self, root: Path) -> Dict[str, Any]:
        """Compute basic project statistics."""
        total_files = 0
        total_dirs = 0
        total_size = 0

        for entry in root.rglob("*"):
            if entry.is_dir() and not entry.name.startswith((".", "__pycache__", "node_modules")):
                total_dirs += 1
            elif entry.is_file():
                total_files += 1
                total_size += entry.stat().st_size

        return {
            "total_directories": total_dirs,
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_human": self._format_size(total_size),
            "root_name": root.name,
        }

    @staticmethod
    def _format_size(size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_analyzed_projects(self) -> List[Dict[str, Any]]:
        """Get list of all analyzed projects."""
        return [
            {
                "path": info["path"],
                "name": info["name"],
                "ecosystem": info.get("ecosystem", {}).get("primary", "unknown"),
            }
            for info in self._projects.values()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get analysis statistics."""
        return {
            "total_projects_analyzed": len(self._projects),
            "recent_projects": list(self._projects.keys())[-3:],
        }
