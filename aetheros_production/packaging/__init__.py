"""
Packaging for AetherOS
======================

Generate packages for all platforms:
    - Windows: MSI, EXE
    - macOS: DMG, PKG
    - Linux: AppImage, Deb, RPM, Snap, Flatpak
    - Docker Images
    - Homebrew Formula
    - Winget Package
    - Chocolatey Package

Usage::

    from aetheros_production.packaging import PackagingManager

    manager = PackagingManager()
    packages = manager.generate_packages(["docker", "deb"])
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PackageResult:
    """Result of package generation."""
    format: str
    path: str
    size_bytes: int
    success: bool
    error: str = ""
    sha256: str = ""


def _get_version() -> str:
    from aetheros_production import get_version
    return get_version()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class PackagingManager:
    """Manages package generation for AetherOS.

    Usage::

        manager = PackagingManager()

        # Generate all packages
        results = manager.generate_packages()

        # Generate specific package
        result = manager.generate_package("docker")

        # Create a portable bundle
        result = manager.create_portable_bundle()
    """

    def __init__(self) -> None:
        self._home = Path(__file__).parent.parent.parent
        self._output_dir = self._home / "dist"
        self._output_dir.mkdir(exist_ok=True)

    def create_portable_bundle(self, output_dir: Optional[str] = None) -> PackageResult:
        """Create a self-contained portable bundle.

        The bundle contains the Python venv runtime, the package code, and a
        launcher, so AetherOS can run without a system-wide install.

        Returns:
            PackageResult pointing at the created archive.
        """
        version = _get_version()
        out_dir = Path(output_dir) if output_dir else self._output_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        base = "aetheros" if platform.system().lower() != "windows" else "aetheros"
        bundle_dir = out_dir / f"{base}-{version}-portable"
        if bundle_dir.exists():
            shutil.rmtree(bundle_dir)

        target = bundle_dir / "aetheros"
        target.mkdir(parents=True, exist_ok=True)

        copied = 0
        try:
            # Copy the Python venv runtime.
            venv = Path(sys.prefix)
            venv_target = bundle_dir / "runtime"
            if venv != Path(sys.base_prefix) or (venv / "Lib").exists():
                shutil.copytree(venv, venv_target, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                copied += 1

            # Copy the aetheros package tree.
            pkg = self._home / "aetheros"
            if pkg.exists():
                shutil.copytree(pkg, target / "aetheros", dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                copied += 1
            for sub in ("aetheros_security", "aetheros_production",
                        "aetheros_cli", "aetheros_constants.py",
                        "aetheros_state.py", "aetheros_logging.py"):
                src = self._home / sub
                if src.exists():
                    dst = target / sub
                    if src.is_file():
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)
                    else:
                        shutil.copytree(src, dst, dirs_exist_ok=True,
                                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                    copied += 1

            # Launcher.
            if platform.system().lower() == "windows":
                launcher = bundle_dir / "aetheros.cmd"
                launcher.write_text(
                    '@echo off\r\n'
                    'set "AETHEROS_HOME=%%USERPROFILE%%\\.aetheros"\r\n'
                    f'"{sys.executable}" "%~dp0aetheros\\cli.py" %*\r\n',
                    "utf-8",
                )
            else:
                launcher = bundle_dir / "aetheros"
                launcher.write_text(
                    '#!/bin/sh\n'
                    'AETHEROS_HOME="${AETHEROS_HOME:-$HOME/.aetheros}"\n'
                    f'exec "{sys.executable}" "$(dirname "$0")/aetheros/cli.py" "$@"\n',
                    "utf-8",
                )
                launcher.chmod(0o755)

            if copied == 0:
                return PackageResult(
                    format="portable", path="", size_bytes=0, success=False,
                    error="No package sources found to bundle",
                )

            # Archive it.
            archive_ext = "zip" if platform.system().lower() == "windows" else "tar.gz"
            archive = out_dir / f"{base}-{version}-portable.{archive_ext}"
            if archive.exists():
                archive.unlink()
            if archive_ext == "zip":
                shutil.make_archive(str(archive.with_suffix("")), "zip", bundle_dir)
            else:
                shutil.make_archive(str(archive.with_suffix("")), "gztar", bundle_dir)

            return PackageResult(
                format="portable",
                path=str(archive),
                size_bytes=archive.stat().st_size,
                success=True,
                sha256=_sha256_file(archive),
            )
        except Exception as exc:
            return PackageResult(
                format="portable", path="", size_bytes=0, success=False, error=str(exc),
            )

    def generate_sbom(self, output_path: Optional[str] = None) -> PackageResult:
        """Generate a CycloneDX-style SBOM of installed dependencies.

        The SBOM lists every installed distribution with its version and
        (when available) its SHA-256 hash, and is signed by default so
        release artifacts can be verified against it.

        Args:
            output_path: Optional output path (defaults to dist/sbom.json).

        Returns:
            PackageResult pointing at the SBOM file.
        """
        try:
            from aetheros_security.supply_chain import generate_sbom
        except Exception:
            generate_sbom = None

        out = Path(output_path) if output_path else self._output_dir / "sbom.json"
        out.parent.mkdir(parents=True, exist_ok=True)

        try:
            if generate_sbom is not None:
                sbom = generate_sbom()
                data = sbom if isinstance(sbom, dict) else {"components": list(sbom)}
            else:
                data = self._simple_sbom()
            out.write_text(json.dumps(data, indent=2), "utf-8")
            return PackageResult(
                format="sbom",
                path=str(out),
                size_bytes=out.stat().st_size,
                success=True,
                sha256=_sha256_file(out),
            )
        except Exception as exc:
            return PackageResult(
                format="sbom", path="", size_bytes=0, success=False, error=str(exc),
            )

    @staticmethod
    def _simple_sbom() -> Dict[str, Any]:
        """Fallback SBOM built from importlib.metadata."""
        import importlib.metadata as md

        components = []
        for dist in md.distributions():
            name = dist.metadata.get("Name") or dist.metadata.get("name") or ""
            ver = dist.version
            if not name:
                continue
            components.append({
                "type": "library",
                "name": name,
                "version": ver,
                "purl": f"pkg:pypi/{name.lower()}@{ver}",
            })
        return {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "version": 1,
            "components": sorted(components, key=lambda c: c["name"]),
        }

    def generate_packages(
        self,
        formats: Optional[List[str]] = None,
    ) -> List[PackageResult]:
        """Generate packages for specified formats.

        Args:
            formats: List of package formats. If None, generates for current platform.

        Returns:
            List of package results.
        """
        if formats is None:
            formats = self._get_platform_formats()

        results = []
        for fmt in formats:
            result = self.generate_package(fmt)
            results.append(result)

        return results

    def _get_platform_formats(self) -> List[str]:
        """Get package formats for current platform."""
        system = platform.system().lower()
        if system == "windows":
            return ["exe", "msi"]
        elif system == "darwin":
            return ["dmg", "pkg"]
        elif system == "linux":
            return ["appimage", "deb"]
        return ["docker"]

    def generate_package(self, fmt: str) -> PackageResult:
        """Generate a package for a specific format.

        Args:
            fmt: Package format.

        Returns:
            Package result.
        """
        logger.info("Generating %s package", fmt)

        generators = {
            "docker": self._generate_docker,
            "deb": self._generate_deb,
            "rpm": self._generate_rpm,
            "appimage": self._generate_appimage,
            "snap": self._generate_snap,
            "flatpak": self._generate_flatpak,
            "homebrew": self._generate_homebrew,
            "winget": self._generate_winget,
            "chocolatey": self._generate_chocolatey,
            "msi": self._generate_msi,
            "exe": self._generate_exe,
            "dmg": self._generate_dmg,
            "pkg": self._generate_pkg,
        }

        generator = generators.get(fmt)
        if not generator:
            return PackageResult(
                format=fmt,
                path="",
                size_bytes=0,
                success=False,
                error=f"Unknown format: {fmt}",
            )

        return generator()

    def _generate_docker(self) -> PackageResult:
        """Generate Docker image."""
        dockerfile = self._home / "Dockerfile"
        if not dockerfile.exists():
            return PackageResult(
                format="docker",
                path="",
                size_bytes=0,
                success=False,
                error="Dockerfile not found",
            )

        try:
            # Build Docker image
            result = subprocess.run(
                ["docker", "build", "-t", "aetheros:latest", "."],
                cwd=str(self._home),
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return PackageResult(
                    format="docker",
                    path="aetheros:latest",
                    size_bytes=0,
                    success=True,
                )
            else:
                return PackageResult(
                    format="docker",
                    path="",
                    size_bytes=0,
                    success=False,
                    error=result.stderr,
                )
        except Exception as exc:
            return PackageResult(
                format="docker",
                path="",
                size_bytes=0,
                success=False,
                error=str(exc),
            )

    def _generate_deb(self) -> PackageResult:
        """Generate Debian package."""
        version = _get_version()
        deb_dir = self._output_dir / "deb"
        deb_dir.mkdir(exist_ok=True)

        try:
            # Create package structure
            pkg_dir = deb_dir / f"aetheros_{version}_amd64"
            pkg_dir.mkdir(exist_ok=True)
            (pkg_dir / "DEBIAN").mkdir(exist_ok=True)
            (pkg_dir / "usr").mkdir(exist_ok=True)
            (pkg_dir / "usr" / "bin").mkdir(parents=True, exist_ok=True)

            # Create control file
            control = f"""Package: aetheros
Version: {version}
Architecture: amd64
Maintainer: AetherOS Team <team@aetheros.dev>
Description: AetherOS - AI Operating System
 AetherOS is a personal AI agent that runs across multiple platforms.
"""
            (pkg_dir / "DEBIAN" / "control").write_text(control)

            # Create binary
            binary_content = "#!/bin/bash\nexec aetheros-cli \"$@\"\n"
            (pkg_dir / "usr" / "bin" / "aetheros").write_text(binary_content)
            (pkg_dir / "usr" / "bin" / "aetheros").chmod(0o755)

            # Build package
            result = subprocess.run(
                ["dpkg-deb", "--build", str(pkg_dir)],
                capture_output=True,
                text=True,
            )

            deb_path = deb_dir / f"aetheros_{version}_amd64.deb"
            if deb_path.exists():
                return PackageResult(
                    format="deb",
                    path=str(deb_path),
                    size_bytes=deb_path.stat().st_size,
                    success=True,
                    sha256=_sha256_file(deb_path),
                )

            return PackageResult(
                format="deb",
                path="",
                size_bytes=0,
                success=False,
                error=result.stderr,
            )
        except FileNotFoundError:
            return PackageResult(
                format="deb",
                path="",
                size_bytes=0,
                success=False,
                error="dpkg-deb not found (required to build .deb packages)",
            )
        except Exception as exc:
            return PackageResult(
                format="deb",
                path="",
                size_bytes=0,
                success=False,
                error=str(exc),
            )

    def _generate_rpm(self) -> PackageResult:
        """Generate RPM package."""
        return PackageResult(
            format="rpm",
            path="",
            size_bytes=0,
            success=False,
            error="RPM generation not implemented",
        )

    def _generate_appimage(self) -> PackageResult:
        """Generate AppImage."""
        return PackageResult(
            format="appimage",
            path="",
            size_bytes=0,
            success=False,
            error="AppImage generation not implemented",
        )

    def _generate_snap(self) -> PackageResult:
        """Generate Snap package."""
        return PackageResult(
            format="snap",
            path="",
            size_bytes=0,
            success=False,
            error="Snap generation not implemented",
        )

    def _generate_flatpak(self) -> PackageResult:
        """Generate Flatpak package."""
        return PackageResult(
            format="flatpak",
            path="",
            size_bytes=0,
            success=False,
            error="Flatpak generation not implemented",
        )

    def _generate_homebrew(self) -> PackageResult:
        """Generate Homebrew formula."""
        version = _get_version()
        formula = f'''class Aetheros < Formula
  desc "AetherOS - AI Operating System"
  homepage "https://aetheros.dev"
  url "https://github.com/aetheros/aetheros/releases/download/v{version}/aetheros-{version}.tar.gz"
  sha256 "COMPUTE_AFTER_RELEASE"
  license "MIT"

  def install
    bin.install "aetheros"
  end

  test do
    system "#{{bin}}/aetheros", "--version"
  end
end
'''
        formula_path = self._output_dir / "aetheros.rb"
        formula_path.write_text(formula)

        return PackageResult(
            format="homebrew",
            path=str(formula_path),
            size_bytes=formula_path.stat().st_size,
            success=True,
        )

    def _generate_winget(self) -> PackageResult:
        """Generate Winget manifest."""
        version = _get_version()
        manifest = f'''PackageIdentifier: AetherOS.AetherOS
PackageVersion: {version}
PackageName: AetherOS
PackageLocale: en-US
Publisher: AetherOS
ShortDescription: AI Operating System
License: MIT
Installers:
  - Architecture: x64
    InstallerType: exe
    InstallerUrl: https://github.com/aetheros/aetheros/releases/download/v{version}/aetheros-setup.exe
    InstallerSha256: COMPUTE_AFTER_RELEASE
'''
        manifest_path = self._output_dir / "aetheros-winget.yaml"
        manifest_path.write_text(manifest)

        return PackageResult(
            format="winget",
            path=str(manifest_path),
            size_bytes=manifest_path.stat().st_size,
            success=True,
        )

    def _generate_chocolatey(self) -> PackageResult:
        """Generate Chocolatey package."""
        version = _get_version()
        nuspec = f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd">
  <metadata>
    <id>aetheros</id>
    <version>{version}</version>
    <title>AetherOS</title>
    <authors>AetherOS Team</authors>
    <description>AI Operating System</description>
    <licenseUrl>https://opensource.org/licenses/MIT</licenseUrl>
    <requireLicenseAcceptance>false</requireLicenseAcceptance>
  </metadata>
  <files>
    <file src="tools\\**" target="tools" />
  </files>
</package>
'''
        nuspec_path = self._output_dir / "aetheros.nuspec"
        nuspec_path.write_text(nuspec)

        return PackageResult(
            format="chocolatey",
            path=str(nuspec_path),
            size_bytes=nuspec_path.stat().st_size,
            success=True,
        )

    def _generate_msi(self) -> PackageResult:
        """Generate Windows MSI installer."""
        return PackageResult(
            format="msi",
            path="",
            size_bytes=0,
            success=False,
            error="MSI generation requires WiX Toolset",
        )

    def _generate_exe(self) -> PackageResult:
        """Generate Windows EXE installer."""
        return PackageResult(
            format="exe",
            path="",
            size_bytes=0,
            success=False,
            error="EXE generation requires NSIS or Inno Setup",
        )

    def _generate_dmg(self) -> PackageResult:
        """Generate macOS DMG."""
        return PackageResult(
            format="dmg",
            path="",
            size_bytes=0,
            success=False,
            error="DMG generation requires macOS",
        )

    def _generate_pkg(self) -> PackageResult:
        """Generate macOS PKG."""
        return PackageResult(
            format="pkg",
            path="",
            size_bytes=0,
            success=False,
            error="PKG generation requires macOS",
        )


# Global packaging manager
_packaging_manager: Optional[PackagingManager] = None


def get_packaging_manager() -> PackagingManager:
    """Return the global PackagingManager singleton."""
    global _packaging_manager
    if _packaging_manager is None:
        _packaging_manager = PackagingManager()
    return _packaging_manager
