"""Repository, GitHub, academic, and news research support (P36-40).

Pure builders and analyzers: local repo summarization (files, symbols,
dependencies, git history), candidate-URL construction for GitHub/arXiv
research, and news language classification (reported/confirmed/alleged/
opinion). No network calls happen here.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

_LANG_BY_EXT = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".tsx": "typescript", ".jsx": "javascript", ".go": "go", ".rs": "rust",
    ".java": "java", ".rb": "ruby", ".php": "php", ".c": "c", ".cpp": "cpp",
    ".cs": "csharp", ".swift": "swift", ".kt": "kotlin", ".sh": "shell",
}


@dataclass
class RepoSummary:
    path: str
    name: str
    languages: Dict[str, int] = field(default_factory=dict)
    file_count: int = 0
    readme_excerpt: str = ""
    dependencies: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    recent_commits: List[str] = field(default_factory=list)
    license: str = ""
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return dict(self.__dict__)


_SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache",
    "dist", "build", ".tox", ".idea", ".vscode",
}
_MAX_SCAN_FILES = 4000
_MAX_README_CHARS = 1200


def summarize_repository(path: str, include_git_history: bool = True) -> RepoSummary:
    """P36/P37: analyze an authorized local checkout (files, deps, commits)."""
    root = Path(path)
    if not root.exists():
        raise FileNotFoundError(f"repository not found: {path}")
    summary = RepoSummary(path=str(root), name=root.name)

    scanned = 0
    for item in sorted(root.rglob("*")):
        if scanned > _MAX_SCAN_FILES:
            summary.warnings.append("file_scan_truncated")
            break
        if any(part in _SKIP_DIRS for part in item.parts):
            continue
        if item.is_file():
            scanned += 1
            summary.file_count += 1
            lang = _LANG_BY_EXT.get(item.suffix.lower())
            if lang:
                summary.languages[lang] = summary.languages.get(lang, 0) + 1
                if summary.file_count <= _MAX_SCAN_FILES:
                    try:
                        text = item.read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        text = ""
                    for sym in re.findall(
                        r"^(?:def|class|function|export (?:async )?function)"
                        r"\s+([A-Za-z_][A-Za-z0-9_]*)",
                        text, re.M,
                    ):
                        if sym not in summary.entry_points[:50]:
                            summary.entry_points.append(sym)
            lowered = item.name.lower()
            if lowered == "license":
                try:
                    head = item.read_text(encoding="utf-8", errors="replace")[:200]
                except OSError:
                    head = ""
                match = re.search(r"(?i)\b(mit|apache[- ]2(?:\.0)?|gpl|bsd|mpl|isc)\b", head)
                summary.license = match.group(1) if match else "custom"
    summary.languages = dict(sorted(summary.languages.items(), key=lambda kv: -kv[1]))

    for readme_name in ("README.md", "readme.md", "README.rst", "README.txt", "README"):
        candidate = root / readme_name
        if candidate.exists():
            try:
                summary.readme_excerpt = candidate.read_text(
                    encoding="utf-8", errors="replace"
                )[:_MAX_README_CHARS]
            except OSError:
                pass
            break

    summary.dependencies.extend(_deps_from_pyproject(root))
    summary.dependencies.extend(_deps_from_requirements(root))
    summary.dependencies.extend(_deps_from_package_json(root))

    if include_git_history and (root / ".git").exists():
        try:
            out = subprocess.run(
                ["git", "-C", str(root), "log", "-5", "--oneline"],
                capture_output=True, text=True, timeout=15,
            )
            if out.returncode == 0 and out.stdout.strip():
                summary.recent_commits = out.stdout.strip().splitlines()[:5]
        except (OSError, subprocess.TimeoutExpired):
            summary.warnings.append("git_unavailable")
    return summary


def _deps_from_pyproject(root: Path) -> List[str]:
    pp = root / "pyproject.toml"
    if not pp.exists():
        return []
    try:
        text = pp.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    deps: List[str] = []
    in_deps = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("dependencies") and "=" in stripped and "[" in stripped:
            in_deps = True
            continue
        if in_deps:
            if stripped.startswith("]"):
                in_deps = False
                continue
            match = re.match(r"[\"']([A-Za-z0-9_.\-]+)", stripped)
            if match:
                deps.append(match.group(1))
    return deps


def _deps_from_requirements(root: Path) -> List[str]:
    req = root / "requirements.txt"
    if not req.exists():
        return []
    try:
        lines = req.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith(("#", "-")):
            out.append(re.split(r"[<>=~\[;]", line)[0])
    return out


def _deps_from_package_json(root: Path) -> List[str]:
    pj = root / "package.json"
    if not pj.exists():
        return []
    try:
        data = json.loads(pj.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return []
    deps = list((data.get("dependencies") or {}).keys())
    deps += list((data.get("devDependencies") or {}).keys())
    return deps


# ---------------------------------------------------------------------------
# Candidate URL builders for remote research (P37-39)
# ---------------------------------------------------------------------------


def github_research_urls(repo: str) -> Dict[str, str]:
    """Candidate URLs for one 'owner/name' repo; provenance preserved."""
    repo = repo.strip().strip("/")
    base = f"https://github.com/{repo}"
    return {
        "overview": base,
        "issues": f"{base}/issues",
        "releases": f"{base}/releases",
        "readme_main": f"https://raw.githubusercontent.com/{repo}/main/README.md",
        "readme_master": f"https://raw.githubusercontent.com/{repo}/master/README.md",
    }


def arxiv_research_urls(query_terms: List[str]) -> List[str]:
    """P39: primary academic surface — abs pages track version + date."""
    slug = "+".join(re.sub(r"[^a-z0-9]+", "", t.lower()) for t in query_terms[:4] if t)
    return [f"https://arxiv.org/list/cs/recent"] if not slug else [
        f"http://export.arxiv.org/api/query?search_query=all:{slug}&max_results=10",
    ]


ARXIV_ABS_RE = re.compile(r"https?://arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5})(v\d+)?")


def parse_arxiv_ref(url: str) -> Optional[Dict[str, str]]:
    """Extract paper id + version from an arXiv URL (version tracking)."""
    match = ARXIV_ABS_RE.search(url or "")
    if not match:
        return None
    return {"arxiv_id": match.group(1), "version": match.group(2) or "v1"}


# ---------------------------------------------------------------------------
# News language classification (P40)
# ---------------------------------------------------------------------------

_NEWS_MARKERS = {
    "reported": ("reported", "according to", "is said to", "reportedly"),
    "confirmed": ("confirmed", "verified", "announced officially", "stated officially"),
    "alleged": ("alleged", "allegedly", "unverified claims", "accused", "claims without evidence"),
    "opinion": ("in my view", "opinion", "editorial", "argues that", "should be seen as"),
}


def classify_news_language(text: str) -> str:
    lowered = (text or "").lower()
    best = "reported"
    best_score = 0
    for label, markers in _NEWS_MARKERS.items():
        score = sum(1 for m in markers if m in lowered)
        if score > best_score:
            best, best_score = label, score
    return best


TECH_QUERY_HINTS = (
    "api", "sdk", "library", "framework", "spec", "protocol", "release",
    "version", "install", "configure", "error", "bug", "migration", "docs",
)


def is_technical_query(query: str) -> bool:
    lowered = (query or "").lower()
    return any(h in lowered for h in TECH_QUERY_HINTS)


ACADEMIC_QUERY_HINTS = (
    "paper", "study", "research", "benchmark", "dataset", "survey",
    "state of the art", "sota", "citation", "peer review",
)

NEWS_QUERY_HINTS = (
    "news", "announced", "launch", "acquisition", "lawsuit", "funding",
    "today", "yesterday", "this week", "breaking",
)


def bias_strategies_for_query(query: str) -> List[str]:
    """P38-40: extra subquestion purposes based on what the question is."""
    purposes = []
    if is_technical_query(query):
        purposes.append("technical")
    lowered = query.lower()
    if any(h in lowered for h in ACADEMIC_QUERY_HINTS):
        purposes.append("academic")
    if any(h in lowered for h in NEWS_QUERY_HINTS):
        purposes.append("news")
    return purposes
