"""
Repository Intelligence — understands repository structure and characteristics.

Analyzes:
  - Repository structure and file organization
  - Languages used
  - Frameworks detected
  - Build system configuration
  - Test frameworks and coverage
  - Dependency graph
  - Existing architecture patterns

Avoids duplicate implementations by understanding existing code.
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from kernel.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class LanguageInfo:
    """Information about a programming language in the repository.

    Attributes:
        name: Language name
        version: Detected version (if applicable)
        file_count: Number of files in this language
        line_count: Estimated lines of code
        main_files: Key entry point files
    """
    name: str = ""
    version: str = ""
    file_count: int = 0
    line_count: int = 0
    main_files: List[str] = field(default_factory=list)


@dataclass
class FrameworkInfo:
    """Information about a detected framework.

    Attributes:
        name: Framework name
        version: Detected version
        category: Framework category (web, test, ORM, etc.)
        config_files: Configuration files associated with this framework
    """
    name: str = ""
    version: str = ""
    category: str = ""
    config_files: List[str] = field(default_factory=list)


@dataclass
class BuildSystemInfo:
    """Information about the build system.

    Attributes:
        name: Build system name
        config_files: Build configuration files
        build_commands: Common build commands
        test_commands: Common test commands
    """
    name: str = ""
    config_files: List[str] = field(default_factory=list)
    build_commands: List[str] = field(default_factory=list)
    test_commands: List[str] = field(default_factory=list)


@dataclass
class DependencyGraph:
    """A dependency graph for the repository.

    Attributes:
        nodes: Dependency name -> version mapping
        edges: (source, target, type) dependency relationships
        vulnerabilities: Known vulnerability information
    """
    nodes: Dict[str, str] = field(default_factory=dict)
    edges: List[tuple[str, str, str]] = field(default_factory=list)
    vulnerabilities: List[str] = field(default_factory=list)


@dataclass
class RepositoryProfile:
    """Complete profile of a repository.

    Attributes:
        root_path: Repository root path
        name: Repository name
        description: Repository description
        languages: Detected languages
        frameworks: Detected frameworks
        build_system: Build system information
        test_patterns: Patterns for test files
        dependency_graph: Dependency information
        directory_structure: High-level directory structure
        entry_points: Main entry point files
        config_files: Configuration files found
        has_docker: Whether Docker configuration exists
        has_ci: Whether CI configuration exists
        total_files: Total file count
        total_dirs: Total directory count
        analyzed_at: When the analysis was performed
    """
    root_path: str = ""
    name: str = ""
    description: str = ""
    languages: List[LanguageInfo] = field(default_factory=list)
    frameworks: List[FrameworkInfo] = field(default_factory=list)
    build_system: Optional[BuildSystemInfo] = None
    test_patterns: List[str] = field(default_factory=list)
    dependency_graph: Optional[DependencyGraph] = None
    directory_structure: Dict[str, Any] = field(default_factory=dict)
    entry_points: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    has_docker: bool = False
    has_ci: bool = False
    total_files: int = 0
    total_dirs: int = 0
    analyzed_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RepositoryIntelligence:
    """Analyzes repositories to understand their structure, languages, and patterns.

    Provides intelligence about a repository to guide engineering decisions,
    avoid duplicate implementations, and generate context-aware plans.

    Usage:
        ri = RepositoryIntelligence(event_bus)
        profile = ri.analyze("/path/to/repo")
        print(f"Languages: {[l.name for l in profile.languages]}")
    """

    # Language detection patterns
    LANGUAGE_PATTERNS: Dict[str, Dict[str, Any]] = {
        ".py": {"name": "Python", "version_file": "pyproject.toml"},
        ".js": {"name": "JavaScript", "version_file": "package.json"},
        ".ts": {"name": "TypeScript", "version_file": "package.json"},
        ".tsx": {"name": "TypeScript (React)", "version_file": "package.json"},
        ".jsx": {"name": "JavaScript (React)", "version_file": "package.json"},
        ".go": {"name": "Go", "version_file": "go.mod"},
        ".rs": {"name": "Rust", "version_file": "Cargo.toml"},
        ".java": {"name": "Java", "version_file": "pom.xml"},
        ".rb": {"name": "Ruby", "version_file": "Gemfile"},
        ".c": {"name": "C", "version_file": ""},
        ".cpp": {"name": "C++", "version_file": ""},
        ".cs": {"name": "C#", "version_file": ".csproj"},
        ".swift": {"name": "Swift", "version_file": "Package.swift"},
        ".kt": {"name": "Kotlin", "version_file": "build.gradle.kts"},
        ".rs": {"name": "Rust", "version_file": "Cargo.toml"},
        ".sh": {"name": "Shell", "version_file": ""},
        ".yaml": {"name": "YAML", "version_file": ""},
        ".yml": {"name": "YAML", "version_file": ""},
        ".json": {"name": "JSON", "version_file": ""},
        ".md": {"name": "Markdown", "version_file": ""},
        ".html": {"name": "HTML", "version_file": ""},
        ".css": {"name": "CSS", "version_file": ""},
    }

    # Framework detection patterns
    FRAMEWORK_PATTERNS: Dict[str, Dict[str, Any]] = {
        "pyproject.toml": {"name": "Python project", "version_key": None},
        "package.json": {"name": "Node.js project", "version_key": None},
        "Cargo.toml": {"name": "Rust project", "version_key": None},
        "go.mod": {"name": "Go module", "version_key": None},
        "requirements.txt": {"name": "Python dependencies", "version_key": None},
        "Dockerfile": {"name": "Docker", "version_key": None},
        "docker-compose.yml": {"name": "Docker Compose", "version_key": None},
        ".github/workflows": {"name": "GitHub Actions CI", "version_key": None},
        "pytest.ini": {"name": "Pytest", "version_key": None},
        ".pylintrc": {"name": "Pylint", "version_key": None},
        ".eslintrc.js": {"name": "ESLint", "version_key": None},
        "tsconfig.json": {"name": "TypeScript config", "version_key": None},
        "jest.config.js": {"name": "Jest", "version_key": None},
        "vitest.config.ts": {"name": "Vitest", "version_key": None},
        "setup.py": {"name": "Python setup", "version_key": None},
        "Makefile": {"name": "Make build system", "version_key": None},
        "mvnw": {"name": "Maven Wrapper", "version_key": None},
        "gradlew": {"name": "Gradle Wrapper", "version_key": None},
    }

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._cache: Dict[str, RepositoryProfile] = {}

    def analyze(self, repo_path: str, force: bool = False) -> RepositoryProfile:
        """Analyze a repository and return its profile.

        Results are cached; use force=True to re-analyze.

        Args:
            repo_path: Path to the repository root
            force: If True, re-analyze even if cached

        Returns:
            RepositoryProfile with analysis results
        """
        abs_path = str(Path(repo_path).resolve())

        # Check cache
        if not force and abs_path in self._cache:
            return self._cache[abs_path]

        root = Path(abs_path)
        if not root.is_dir():
            logger.warning("RepositoryIntelligence: path not found: %s", repo_path)
            return RepositoryProfile(root_path=abs_path, name=root.name)

        profile = RepositoryProfile(
            root_path=abs_path,
            name=root.name,
        )

        # Walk the repository
        self._analyze_structure(root, profile)
        self._detect_languages(root, profile)
        self._detect_frameworks(root, profile)
        self._detect_build_system(root, profile)
        self._detect_tests(root, profile)
        self._detect_config_files(root, profile)
        self._generate_directory_structure(root, profile)

        profile.analyzed_at = time.time()

        # Cache the result
        self._cache[abs_path] = profile

        logger.info(
            "RepositoryIntelligence: analyzed %s: %d files, %d languages, %d frameworks",
            profile.name, profile.total_files, len(profile.languages),
            len(profile.frameworks),
        )

        if self._event_bus:
            self._event_bus.emit_async("engineering.repo_analyzed", {
                "repo": profile.name,
                "files": profile.total_files,
                "languages": [l.name for l in profile.languages],
                "frameworks": [f.name for f in profile.frameworks],
            })

        return profile

    def _analyze_structure(self, root: Path, profile: RepositoryProfile) -> None:
        """Count files and directories."""
        file_count = 0
        dir_count = 0
        exclude_dirs = {
            ".git", "__pycache__", "node_modules", ".venv", "venv",
            ".tox", "build", "dist", ".eggs", "*.egg-info",
            ".mypy_cache", ".pytest_cache", ".ruff_cache",
            ".aetheros", "target", ".next",
        }

        try:
            for dirpath, dirnames, filenames in os.walk(root):
                # Skip excluded directories
                dirnames[:] = [d for d in dirnames if d not in exclude_dirs
                              and not d.startswith(".")]

                dir_count += 1
                file_count += len(filenames)

            profile.total_files = file_count
            profile.total_dirs = dir_count
        except (PermissionError, OSError) as exc:
            logger.warning("RepositoryIntelligence: walk error: %s", exc)

    def _detect_languages(self, root: Path, profile: RepositoryProfile) -> None:
        """Detect programming languages used in the repository."""
        extension_counts: Dict[str, int] = {}
        extension_lines: Dict[str, int] = {}
        exclude_dirs = {
            ".git", "__pycache__", "node_modules", ".venv", "venv",
            ".tox", "build", "dist", ".eggs",
        }

        try:
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if d not in exclude_dirs
                              and not d.startswith(".")]

                for filename in filenames:
                    ext = Path(filename).suffix.lower()
                    if ext in self.LANGUAGE_PATTERNS:
                        extension_counts[ext] = extension_counts.get(ext, 0) + 1
                        # Estimate lines of code
                        try:
                            filepath = Path(dirpath) / filename
                            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                                line_count = sum(1 for _ in f)
                            extension_lines[ext] = extension_lines.get(ext, 0) + line_count
                        except Exception:
                            pass
        except (PermissionError, OSError) as exc:
            logger.warning("RepositoryIntelligence: language detection error: %s", exc)

        # Build language info objects
        for ext, count in sorted(
            extension_counts.items(), key=lambda x: x[1], reverse=True
        ):
            info = self.LANGUAGE_PATTERNS[ext]
            lang = LanguageInfo(
                name=info["name"],
                file_count=count,
                line_count=extension_lines.get(ext, 0),
            )

            # Check for version info
            if info.get("version_file"):
                version_file = root / info["version_file"]
                if version_file.exists():
                    try:
                        content = version_file.read_text(encoding="utf-8", errors="ignore")
                        # Simple version extraction patterns
                        version_match = re.search(
                            r'version\s*=\s*["\']([^"\']+)["\']', content
                        ) or re.search(
                            r'"version":\s*"([^"]+)"', content
                        )
                        if version_match:
                            lang.version = version_match.group(1)
                    except Exception:
                        pass

            profile.languages.append(lang)

    def _detect_frameworks(self, root: Path, profile: RepositoryProfile) -> None:
        """Detect frameworks and tools used in the repository."""
        for filename, framework_info in self.FRAMEWORK_PATTERNS.items():
            # Handle directory-based configs
            if "/" in filename:
                path = root / filename
            else:
                # Search recursively
                path = self._find_file(root, filename)

            if path and path.exists():
                profile.frameworks.append(FrameworkInfo(
                    name=framework_info["name"],
                    category=self._categorize_framework(framework_info["name"]),
                    config_files=[str(path.relative_to(root))],
                ))

                # Detect specific versions from package.json if available
                if filename == "package.json" and path.exists():
                    self._detect_node_packages(path, profile)

    def _detect_node_packages(self, package_json: Path,
                              profile: RepositoryProfile) -> None:
        """Extract framework info from package.json dependencies."""
        try:
            import json
            data = json.loads(package_json.read_text(encoding="utf-8", errors="ignore"))

            deps = {
                **data.get("dependencies", {}),
                **data.get("devDependencies", {}),
            }

            framework_keywords = {
                "react": "Web Framework",
                "express": "Web Framework",
                "fastapi": "Web Framework",
                "flask": "Web Framework",
                "django": "Web Framework",
                "vue": "Web Framework",
                "angular": "Web Framework",
                "svelte": "Web Framework",
                "next": "Web Framework",
                "jest": "Test Framework",
                "vitest": "Test Framework",
                "mocha": "Test Framework",
                "pytest": "Test Framework",
                "cypress": "Test Framework",
                "playwright": "Test Framework",
                "eslint": "Linting",
                "prettier": "Formatting",
                "typescript": "Language",
                "tailwindcss": "CSS Framework",
                "bootstrap": "CSS Framework",
            }

            for dep_name, dep_version in deps.items():
                for keyword, category in framework_keywords.items():
                    if keyword in dep_name.lower():
                        is_new = True
                        for fw in profile.frameworks:
                            if fw.name == dep_name:
                                is_new = False
                                break
                        if is_new:
                            profile.frameworks.append(FrameworkInfo(
                                name=dep_name,
                                version=str(dep_version).replace("^", ""),
                                category=category,
                                config_files=[str(package_json.relative_to(
                                    package_json.parent.parent))],
                            ))
                        break
        except Exception:
            pass

    def _detect_build_system(self, root: Path, profile: RepositoryProfile) -> None:
        """Detect the build system."""
        build_system = None

        if (root / "Makefile").exists():
            build_system = BuildSystemInfo(
                name="Make",
                config_files=["Makefile"],
                build_commands=["make", "make build"],
                test_commands=["make test"],
            )
        elif (root / "pyproject.toml").exists():
            # Check for specific build backends
            content = (root / "pyproject.toml").read_text(encoding="utf-8", errors="ignore")
            if "hatchling" in content:
                build_system = BuildSystemInfo(
                    name="Hatchling",
                    config_files=["pyproject.toml"],
                    build_commands=["hatch build", "pip install -e ."],
                    test_commands=["hatch run test", "pytest"],
                )
            elif "setuptools" in content:
                build_system = BuildSystemInfo(
                    name="Setuptools",
                    config_files=["pyproject.toml"],
                    build_commands=["pip install -e ."],
                    test_commands=["pytest"],
                )
            elif "poetry" in content:
                build_system = BuildSystemInfo(
                    name="Poetry",
                    config_files=["pyproject.toml"],
                    build_commands=["poetry build"],
                    test_commands=["poetry run pytest"],
                )
            else:
                build_system = BuildSystemInfo(
                    name="Python (pyproject.toml)",
                    config_files=["pyproject.toml"],
                    build_commands=["pip install -e ."],
                    test_commands=["pytest"],
                )
        elif (root / "package.json").exists():
            build_system = BuildSystemInfo(
                name="npm",
                config_files=["package.json"],
                build_commands=["npm run build"],
                test_commands=["npm test", "npm run test"],
            )
        elif (root / "Cargo.toml").exists():
            build_system = BuildSystemInfo(
                name="Cargo",
                config_files=["Cargo.toml"],
                build_commands=["cargo build"],
                test_commands=["cargo test"],
            )
        elif (root / "go.mod").exists():
            build_system = BuildSystemInfo(
                name="Go modules",
                config_files=["go.mod"],
                build_commands=["go build ./..."],
                test_commands=["go test ./..."],
            )
        elif (root / "setup.py").exists():
            build_system = BuildSystemInfo(
                name="Setuptools",
                config_files=["setup.py"],
                build_commands=["pip install -e ."],
                test_commands=["pytest"],
            )
        elif (root / "build.gradle").exists():
            build_system = BuildSystemInfo(
                name="Gradle",
                config_files=["build.gradle", "build.gradle.kts"],
                build_commands=["./gradlew build"],
                test_commands=["./gradlew test"],
            )
        elif (root / "pom.xml").exists():
            build_system = BuildSystemInfo(
                name="Maven",
                config_files=["pom.xml"],
                build_commands=["mvn package"],
                test_commands=["mvn test"],
            )

        if build_system:
            profile.build_system = build_system

    def _detect_tests(self, root: Path, profile: RepositoryProfile) -> None:
        """Detect test patterns and frameworks."""
        test_patterns = [
            "test_*.py",
            "*_test.py",
            "*_test.go",
            "*_test.rs",
            "*.test.js",
            "*.test.ts",
            "*.spec.js",
            "*.spec.ts",
            "test_*",
            "*Test.java",
        ]

        profile.test_patterns = test_patterns

        # Count test files
        test_count = 0
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                if ".git" in dirpath or "node_modules" in dirpath:
                    continue
                for filename in filenames:
                    for pattern in test_patterns:
                        import fnmatch
                        if fnmatch.fnmatch(filename, pattern):
                            test_count += 1
                            break
        except (PermissionError, OSError):
            pass

        profile.metadata["test_file_count"] = test_count

    def _detect_config_files(self, root: Path, profile: RepositoryProfile) -> None:
        """Detect common configuration files."""
        config_patterns = [
            ".env.example", ".envrc", ".gitignore", ".gitattributes",
            ".editorconfig", ".pre-commit-config.yaml", "Dockerfile",
            "docker-compose.yml", ".github/workflows", ".gitlab-ci.yml",
            "Jenkinsfile", ".travis.yml", "Makefile",
        ]

        for pattern in config_patterns:
            path = root / pattern
            if path.exists():
                profile.config_files.append(pattern)

        profile.has_docker = (root / "Dockerfile").exists()
        profile.has_ci = (root / ".github" / "workflows").exists()

        # Detect entry points
        entry_candidates = [
            "main.py", "app.py", "cli.py", "run.py", "server.py",
            "index.js", "index.ts", "main.ts", "main.go", "main.rs",
            "src/main.py", "src/app.py", "src/index.ts",
        ]
        for candidate in entry_candidates:
            if (root / candidate).exists():
                profile.entry_points.append(candidate)

    def _generate_directory_structure(self, root: Path,
                                      profile: RepositoryProfile) -> None:
        """Generate a high-level directory structure."""
        structure: Dict[str, Any] = {}
        exclude_dirs = {
            ".git", "__pycache__", "node_modules", ".venv", "venv",
            ".tox", "build", "dist", ".eggs", ".mypy_cache",
        }

        try:
            for entry in sorted(root.iterdir()):
                if entry.name.startswith(".") and entry.name not in (".github", ".env.example"):
                    continue
                if entry.name in exclude_dirs:
                    continue

                if entry.is_dir():
                    subdirs = [
                        d.name for d in entry.iterdir()
                        if d.is_dir() and d.name not in exclude_dirs
                    ]
                    structure[entry.name] = {
                        "type": "directory",
                        "subdirectories": subdirs[:10],  # Limit to keep output manageable
                        "description": self._guess_dir_purpose(entry.name),
                    }
                elif entry.is_file():
                    structure[entry.name] = {
                        "type": "file",
                        "description": self._guess_file_purpose(entry.name),
                    }
        except (PermissionError, OSError) as exc:
            logger.warning("RepositoryIntelligence: structure error: %s", exc)

        profile.directory_structure = structure

    def _categorize_framework(self, name: str) -> str:
        """Categorize a framework by name."""
        name_lower = name.lower()
        if "test" in name_lower or "pytest" in name_lower or "jest" in name_lower:
            return "testing"
        if "lint" in name_lower or "eslint" in name_lower or "pylint" in name_lower:
            return "linting"
        if "docker" in name_lower:
            return "containerization"
        if "ci" in name_lower or "github action" in name_lower:
            return "ci"
        if "type" in name_lower:
            return "type_checking"
        if "build" in name_lower or "make" in name_lower:
            return "build"
        return "development"

    def _guess_dir_purpose(self, name: str) -> str:
        """Guess the purpose of a directory based on its name."""
        name_lower = name.lower()
        if name_lower in ("src", "source"):
            return "Source code root"
        if name_lower in ("test", "tests"):
            return "Test files"
        if name_lower in ("docs", "documentation"):
            return "Documentation"
        if name_lower in ("config", "configuration"):
            return "Configuration files"
        if name_lower in ("scripts", "bin"):
            return "Build/utility scripts"
        if name_lower in ("lib", "library"):
            return "Library code"
        if name_lower in ("plugins", "extensions"):
            return "Plugin/extensions directory"
        if name_lower in ("static", "assets", "public"):
            return "Static assets"
        if name_lower in ("templates"):
            return "Template files"
        if name_lower in ("migrations"):
            return "Database migrations"
        if name_lower in ("api"):
            return "API layer"
        if name_lower in ("db", "database"):
            return "Database related"
        if name_lower in ("docker"):
            return "Docker configuration"
        if name_lower == "ui" or "frontend" in name_lower:
            return "Frontend/UI code"
        return "Project directory"

    def _guess_file_purpose(self, name: str) -> str:
        """Guess the purpose of a file based on its name."""
        name_lower = name.lower()
        if name_lower == "readme.md":
            return "Project documentation"
        if name_lower == "license":
            return "License file"
        if name_lower == "contributing.md":
            return "Contribution guidelines"
        if name_lower == "changelog.md":
            return "Changelog"
        if name_lower == "dockerfile":
            return "Docker build configuration"
        if name_lower in ("makefile",):
            return "Build automation"
        if name_lower == "pyproject.toml":
            return "Python project configuration"
        if name_lower == "package.json":
            return "Node.js project configuration"
        if name_lower == "requirements.txt":
            return "Python dependencies"
        if name_lower == "setup.py":
            return "Python package setup"
        return "Project file"

    def _find_file(self, root: Path, filename: str, max_depth: int = 3) -> Optional[Path]:
        """Find a file in the repository, searching up to max_depth levels."""
        try:
            for i, (dirpath, dirnames, filenames) in enumerate(os.walk(root)):
                if i >= max_depth:
                    break
                if filename in filenames:
                    return Path(dirpath) / filename
                # Skip excluded directories
                dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        except (PermissionError, OSError):
            pass
        return None

    def clear_cache(self, repo_path: Optional[str] = None) -> None:
        """Clear the analysis cache.

        Args:
            repo_path: If provided, only clear this repo's cache
        """
        if repo_path:
            abs_path = str(Path(repo_path).resolve())
            self._cache.pop(abs_path, None)
        else:
            self._cache.clear()

    def get_profile(self, repo_path: str) -> Optional[RepositoryProfile]:
        """Get a cached profile, or None if not analyzed yet."""
        abs_path = str(Path(repo_path).resolve())
        return self._cache.get(abs_path)

    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return {
            "cached_repos": len(self._cache),
            "total_files_analyzed": sum(
                p.total_files for p in self._cache.values()
            ),
        }
