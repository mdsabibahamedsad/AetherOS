"""Remote artifacts: integrity, quarantine, provenance (Master 46 sections 38-41, 108-109).

Downloaded artifacts are untrusted: quarantine -> validate -> scan ->
verify -> release. Never auto-execute. Never trust the filename.
"""

from __future__ import annotations

import hashlib
import time
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

ALLOWED_ARTIFACT_TYPES = {
    "file", "document", "image", "json", "report", "code_patch", "evidence",
}
BLOCKED_SUFFIXES = {
    ".exe", ".dll", ".so", ".dylib", ".bat", ".cmd", ".ps1", ".scr",
    ".msi", ".dmg", ".pkg", ".jar", ".apk",
}
MACRO_SUFFIXES = {".docm", ".xlsm", ".pptm"}
MAX_ARTIFACT_BYTES = 100 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 1000
MAX_ARCHIVE_RATIO = 100  # uncompressed / compressed bomb heuristic


@dataclass
class Artifact:
    artifact_id: str
    type: str
    size: int
    sha256: str
    source_agent: str
    task_id: str
    created_at: float = field(default_factory=time.time)
    filename: str = ""
    permissions: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
    quarantine: str = "quarantined"  # quarantined | released | rejected

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_filename(name: str) -> str:
    """Strip directories, control chars, and traversal — never trust filename."""
    base = Path(name.replace("\\", "/")).name.strip()
    base = "".join(c for c in base if c.isprintable() and c not in '<>:"|?*')
    return base[:128] or "artifact"


def examine_artifact(path: Path, filename: str = "") -> Dict[str, Any]:
    """Return verdict dict: {ok, reasons[], sanitized_name, size, sha256}."""
    reasons: List[str] = []
    name = safe_filename(filename or path.name)
    suffix = Path(name).suffix.lower()
    try:
        size = path.stat().st_size
    except OSError as e:
        return {"ok": False, "reasons": [f"unreadable: {e}"], "sanitized_name": name,
                "size": -1, "sha256": ""}
    if size > MAX_ARTIFACT_BYTES:
        reasons.append(f"size {size} exceeds {MAX_ARTIFACT_BYTES} cap")
    if suffix in BLOCKED_SUFFIXES:
        reasons.append(f"executable type {suffix} blocked — release requires explicit approval")
    if suffix in MACRO_SUFFIXES:
        reasons.append(f"macro-enabled document {suffix} blocked pending review")
    digest = sha256_file(path) if not reasons or size <= MAX_ARTIFACT_BYTES else ""
    if suffix == ".zip" and path.exists() and size <= MAX_ARTIFACT_BYTES:
        try:
            with zipfile.ZipFile(path) as zf:
                members = zf.infolist()
                if len(members) > MAX_ARCHIVE_MEMBERS:
                    reasons.append(f"archive has {len(members)} members (cap {MAX_ARCHIVE_MEMBERS})")
                total = sum(m.file_size for m in members)
                if zf.comment is None and total > size * MAX_ARCHIVE_RATIO and size > 1024:
                    reasons.append("suspected archive bomb (compression ratio)")
                for m in members:
                    if m.filename.startswith("/") or ".." in m.filename:
                        reasons.append(f"archive path traversal: {m.filename[:80]}")
                        break
        except zipfile.BadZipFile:
            reasons.append("corrupt zip archive")
    return {"ok": not reasons, "reasons": reasons, "sanitized_name": name,
            "size": size, "sha256": digest}


def release_path(quarantine_dir: Path, name: str) -> Path:
    """Destination inside quarantine dir using the sanitized name only."""
    return Path(quarantine_dir) / safe_filename(name)
