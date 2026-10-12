"""Package format + local/test registry publishing (Master 62 §57-58, §85-86).

Kinds map to extensions (honest, minimal): agent -> .aether-agent, skill ->
.aether-skill, tool -> .aether-tool, extension -> .aether-extension, mcp ->
.aether-mcp. Package = zip with manifest/metadata/schemas/permissions/
dependencies/artifacts/provenance/version/compatibility. Install never
executes code; provenance recorded, never fabricated (source commit only
when inside a git checkout, else 'unknown').
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_constants import get_aetheros_home
from aetheros_platform.errors import err
from aetheros_platform.schemas import validate

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-_]{0,63}$")
_VER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def _check_identity(manifest: Dict[str, Any], where: str) -> None:
    """Strict package identity: no path separators, no traversal, no SQL/quote
    payloads. The JSON-Schema Package.name is intentionally loose (compat),
    so this is the enforcement point for build/publish/install."""
    name = manifest.get("name", "")
    version = manifest.get("version", "")
    kind = manifest.get("kind", "")
    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise err("INVALID_SCHEMA",
                  f"{where}: illegal package name {name!r:.80}",
                  remediation="use lowercase alphanumerics, '-' or '_'")
    if not isinstance(version, str) or not _VER_RE.match(version):
        raise err("INVALID_SCHEMA",
                  f"{where}: illegal package version {version!r:.40}",
                  remediation="use semver X.Y.Z")
    if kind not in KIND_EXT:
        raise err("INVALID_SCHEMA", f"{where}: unknown kind {kind!r:.40}")

KIND_EXT = {"agent": ".aether-agent", "skill": ".aether-skill",
            "tool": ".aether-tool", "extension": ".aether-extension",
            "mcp": ".aether-mcp"}


def _registry_dir() -> Path:
    d = get_aetheros_home() / "dev-registry"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _source_commit() -> str:
    try:
        import subprocess
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, timeout=10).stdout.strip()
        return out if len(out) == 40 else "unknown"
    except Exception:
        return "unknown"


def build_package(project_dir: Path, out_dir: Optional[Path] = None) -> Dict[str, Any]:
    project_dir = Path(project_dir)
    manifest_path = project_dir / "manifest.json"
    if not manifest_path.exists():
        raise err("INVALID_REQUEST", "project has no manifest.json")
    manifest = json.loads(manifest_path.read_text())
    errors = validate("Package", manifest)
    if errors:
        raise err("INVALID_SCHEMA", f"package manifest invalid: {errors[0]}")
    _check_identity(manifest, "build_package")
    kind = manifest["kind"]
    ext = KIND_EXT[kind]
    out_dir = Path(out_dir) if out_dir else project_dir / "dist"
    out_dir.mkdir(parents=True, exist_ok=True)
    pkg_path = out_dir / f"{manifest['name']}-{manifest['version']}{ext}"
    files = []
    with zipfile.ZipFile(pkg_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(project_dir.rglob("*")):
            if f.is_file() and "dist" not in f.parts:
                arc = f.relative_to(project_dir).as_posix()
                z.write(f, arc)
                files.append(arc)
    digest = "sha256:" + hashlib.sha256(pkg_path.read_bytes()).hexdigest()
    provenance = {"built_at": time.time(), "source_commit": _source_commit(),
                  "files": files}
    (out_dir / (pkg_path.name + ".provenance.json")).write_text(
        json.dumps(provenance, indent=2))
    return {"path": str(pkg_path), "sha256": digest, "kind": kind,
            "manifest": manifest, "provenance": provenance}


def publish(pkg_path: Path, registry: Optional[Path] = None) -> Dict[str, Any]:
    """Publish to the LOCAL/TEST registry (real installable record)."""
    reg = Path(registry) if registry else _registry_dir()
    reg.mkdir(parents=True, exist_ok=True)
    pkg_path = Path(pkg_path)
    try:
        with zipfile.ZipFile(pkg_path) as z:
            manifest = json.loads(z.read("manifest.json"))
    except (zipfile.BadZipFile, KeyError, ValueError) as exc:
        raise err("INVALID_SCHEMA",
                  f"publish: unreadable package: {exc}"[:200]) from exc
    _check_identity(manifest, "publish")
    entry = {"name": manifest["name"], "version": manifest["version"],
             "kind": manifest["kind"], "file": pkg_path.name,
             "sha256": "sha256:" + hashlib.sha256(pkg_path.read_bytes()).hexdigest(),
             "published_at": time.time(), "publisher": "local",
             "security": {"signature": "none-available",
                          "warning": "NOT audited: listing never implies safety"}}
    dest = reg / pkg_path.name
    dest.write_bytes(pkg_path.read_bytes())
    index_path = reg / "index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else []
    index = [e for e in index
             if not (e["name"] == entry["name"] and e["version"] == entry["version"])]
    index.append(entry)
    index_path.write_text(json.dumps(index, indent=2))
    return entry


def install(name: str, version: str, dest: Path,
            registry: Optional[Path] = None) -> Dict[str, Any]:
    """Install from the local registry with hash verification + rollback record."""
    if not _NAME_RE.match(name or "") or not _VER_RE.match(version or ""):
        raise err("INVALID_SCHEMA", "install: illegal package name/version",
                  remediation="use safe package identifiers")
    reg = Path(registry) if registry else _registry_dir()
    index = json.loads((reg / "index.json").read_text())
    matches = [e for e in index if e["name"] == name and e["version"] == version]
    if not matches:
        raise err("RESOURCE_UNAVAILABLE", f"package {name}@{version} not in registry")
    entry = matches[0]
    _check_identity({"name": entry["name"], "version": entry["version"],
                     "kind": entry["kind"]}, "install")
    data = (reg / entry["file"]).read_bytes()
    if "sha256:" + hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise err("SECURITY_VIOLATION", "package hash mismatch: refusing install")
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="aether-install-"))
    with zipfile.ZipFile(reg / entry["file"]) as z:
        for arc in z.namelist():
            # Zip-slip guard: reject absolute paths and parent traversal.
            if arc.startswith(("/", "\\")) or ".." in arc.split("/"):
                raise err("SECURITY_VIOLATION",
                          f"package contains unsafe path {arc!r:.100}: refusing install")
        z.extractall(tmp)
    rollback = dest / ".rollback.json"
    rollback.write_text(json.dumps({"package": entry, "at": time.time()}))
    target = dest / f"{name}-{version}"
    if target.exists():
        import shutil
        shutil.rmtree(target)
    (tmp / ".").rename(target) if False else None
    import shutil
    shutil.copytree(tmp, target, dirs_exist_ok=True)
    shutil.rmtree(tmp, ignore_errors=True)
    # Never execute on install — record only.
    return {"installed": str(target), "package": entry,
            "note": "code was NOT executed; review before enabling"}
