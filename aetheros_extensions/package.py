"""Extension package format (.aetherext) + integrity (sections 8-9).

Deterministic zip: manifest.json + extension/ + assets/ + schemas/ +
README.md + LICENSE + integrity.json (+ signature/ when signed).
Protections: normalized paths, no traversal, no absolute paths, symlink
policy (stored, never followed on extract), size/file-count limits,
archive-bomb ratio guard, duplicate detection, manifest/package
consistency. SHA-256 per file + manifest digest + package digest.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

MAX_PACKAGE_BYTES = 50 * 1024 * 1024
MAX_FILES = 2000
MAX_RATIO = 100  # uncompressed / compressed bomb guard
MAX_SINGLE_FILE = 10 * 1024 * 1024

REQUIRED = ("manifest.json",)
ALLOWED_TOP = ("manifest.json", "extension", "assets", "schemas",
               "README.md", "LICENSE", "integrity.json", "signature",
               "provenance")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _norm(name: str) -> str:
    # Normalize separators; reject absolute/traversal/odd entries.
    p = name.replace("\\", "/")
    if p.startswith("/") or p.startswith("~"):
        raise ValueError(f"absolute path: {name!r}")
    parts = [seg for seg in p.split("/") if seg not in ("", ".")]
    if any(seg == ".." for seg in parts):
        raise ValueError(f"path traversal: {name!r}")
    if not parts:
        raise ValueError(f"empty path: {name!r}")
    return "/".join(parts)


@dataclass
class PackageReport:
    ok: bool = False
    reason: str = ""
    files: List[str] = field(default_factory=list)
    digests: Dict[str, str] = field(default_factory=dict)
    manifest_digest: str = ""
    package_digest: str = ""
    manifest: Dict[str, Any] = field(default_factory=dict)


def build_package(src_dir: Path, dest: Optional[Path] = None) -> Path:
    """Deterministic build: sorted entries, fixed timestamps, no extras."""
    src = Path(src_dir)
    manifest_path = src / "manifest.json"
    if not manifest_path.exists():
        raise ValueError("src_dir must contain manifest.json")
    files: List[Tuple[str, bytes]] = []
    for path in sorted(src.rglob("*")):
        if path.is_dir() or path.is_symlink():
            continue
        rel = _norm(path.relative_to(src).as_posix())
        data = path.read_bytes()
        if len(data) > MAX_SINGLE_FILE:
            raise ValueError(f"file too large: {rel}")
        files.append((rel, data))
    if len(files) > MAX_FILES:
        raise ValueError("too many files")
    digests = {rel: sha256_bytes(data) for rel, data in files if rel != "integrity.json"}
    manifest_raw = (src / "manifest.json").read_bytes()
    integrity = {"created_at": 0, "files": digests,
                 "manifest_sha256": sha256_bytes(manifest_raw)}
    integrity_raw = json.dumps(integrity, sort_keys=True,
                               ensure_ascii=False).encode()
    files.append(("integrity.json", integrity_raw))
    files.sort(key=lambda kv: kv[0])
    dest = dest or (src.parent / (src.name + ".aetherext"))
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel, data in files:
            info = zipfile.ZipInfo(rel, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 0
            zf.writestr(info, data)
    return dest


def verify_package(pkg: Path, *, extract_to: Optional[Path] = None) -> PackageReport:
    rep = PackageReport()
    try:
        size = pkg.stat().st_size
    except OSError as exc:
        return PackageReport(ok=False, reason=f"unreadable: {exc}")
    if size > MAX_PACKAGE_BYTES:
        return PackageReport(ok=False, reason="package exceeds size limit")
    try:
        zf = zipfile.ZipFile(pkg)
    except zipfile.BadZipFile:
        return PackageReport(ok=False, reason="not a valid zip")
    with zf:
        infos = zf.infolist()
        if len(infos) > MAX_FILES + 1:
            return PackageReport(ok=False, reason="too many files")
        total_comp = sum(i.compress_size for i in infos)
        total_uncomp = sum(i.file_size for i in infos)
        if total_comp > 0 and total_uncomp / max(1, total_comp) > MAX_RATIO:
            return PackageReport(ok=False, reason="archive bomb ratio exceeded")
        seen: set = set()
        entries: Dict[str, bytes] = {}
        for info in infos:
            if info.is_dir():
                continue
            try:
                rel = _norm(info.filename)
            except ValueError as exc:
                return PackageReport(ok=False, reason=str(exc))
            if rel in seen:
                return PackageReport(ok=False, reason=f"duplicate entry: {rel}")
            seen.add(rel)
            top = rel.split("/")[0]
            if top not in ALLOWED_TOP and "/" not in rel and rel not in ALLOWED_TOP:
                return PackageReport(ok=False, reason=f"unexpected top-level: {rel}")
            if info.file_size > MAX_SINGLE_FILE:
                return PackageReport(ok=False, reason=f"file too large: {rel}")
            entries[rel] = zf.read(info.filename)
        for req in REQUIRED:
            if req not in entries:
                return PackageReport(ok=False, reason=f"missing {req}")
        try:
            manifest = json.loads(entries["manifest.json"].decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return PackageReport(ok=False, reason="manifest.json is not valid JSON")
        # Manifest/package consistency: integrity.json must match files.
        if "integrity.json" in entries:
            try:
                integrity = json.loads(entries["integrity.json"].decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return PackageReport(ok=False, reason="integrity.json is not valid JSON")
            for rel, claimed in (integrity.get("files") or {}).items():
                if rel == "integrity.json":
                    continue
                actual = entries.get(rel)
                if actual is None:
                    return PackageReport(ok=False, reason=f"integrity lists missing file: {rel}")
                if sha256_bytes(actual) != claimed:
                    return PackageReport(ok=False, reason=f"hash mismatch: {rel}")
            if integrity.get("manifest_sha256") != sha256_bytes(entries["manifest.json"]):
                return PackageReport(ok=False, reason="manifest digest mismatch")
        digests = {rel: sha256_bytes(data) for rel, data in entries.items()}
        # Package digest excludes signature/ (sign-then-embed flow: the
        # signature covers content, and is itself verified cryptographically).
        h = hashlib.sha256()
        for rel in sorted(entries):
            if rel == "signature/signature.json" or rel.startswith("signature/"):
                continue
            h.update(rel.encode())
            h.update(entries[rel])
        rep = PackageReport(ok=True, files=sorted(entries), digests=digests,
                            manifest_digest=sha256_bytes(entries["manifest.json"]),
                            package_digest=h.hexdigest(), manifest=manifest)
        if extract_to is not None:
            dest = Path(extract_to)
            dest.mkdir(parents=True, exist_ok=True)
            for rel, data in entries.items():
                target = dest / PurePosixPath(rel)
                # Belt-and-suspenders: resolved target must stay inside dest.
                if dest not in target.resolve().parents and target.resolve() != dest.resolve():
                    return PackageReport(ok=False, reason=f"escape on extract: {rel}")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
    return rep
