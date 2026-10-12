"""Self-repair, path verification, and health check utilities for AetherOS."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


def get_aetheros_bin_dir() -> Path:
    """Return the platform-appropriate directory for the aetheros binary."""
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "AetherOS" / "bin"
    return Path.home() / ".local" / "bin"


def get_aetheros_config_dir() -> Path:
    """Return the AetherOS configuration directory."""
    env_home = os.environ.get("AETHEROS_HOME")
    if env_home:
        return Path(env_home)
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "AetherOS"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "AetherOS"
    return Path.home() / ".aetheros"


def get_aetheros_venv_dir() -> Path:
    """Return the expected virtual environment directory."""
    return get_aetheros_config_dir() / "venv"


def find_aetheros_on_path() -> Optional[Path]:
    """Locate the 'aetheros' or 'AetherOS' command on PATH."""
    for name in ("aetheros", "AetherOS", "aetheros.exe", "AetherOS.exe", "aetheros.cmd", "AetherOS.cmd"):
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def find_python() -> Optional[Path]:
    """Find a suitable Python 3.11+ interpreter."""
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found:
            try:
                v = subprocess.run(
                    [found, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                    capture_output=True, text=True, timeout=10,
                )
                ver_str = v.stdout.strip()
                major, minor = ver_str.split(".")
                if int(major) >= 3 and int(minor) >= 11:
                    return Path(found)
            except Exception:
                continue
    return None


def verify_installation() -> dict:
    """Run comprehensive installation verification.
    
    Returns a dict with status for each check.
    """
    results = {
        "aetheros_on_path": False,
        "aetheros_version": None,
        "aetheros_executable": None,
        "venv_exists": False,
        "venv_has_aetheros": False,
        "config_dir_exists": False,
        "path_contains_bin": False,
        "import_works": False,
        "errors": [],
    }
    
    # Check PATH
    bin_dir = get_aetheros_bin_dir()
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    results["path_contains_bin"] = str(bin_dir) in path_dirs
    
    # Check executable on PATH
    exe = find_aetheros_on_path()
    if exe:
        results["aetheros_on_path"] = True
        results["aetheros_executable"] = str(exe)
    
    # Check version
    try:
        from aetheros_cli import __version__
        results["aetheros_version"] = __version__
        results["import_works"] = True
    except Exception as e:
        results["errors"].append(f"Import failed: {e}")
    
    # Check venv
    venv_dir = get_aetheros_venv_dir()
    results["venv_exists"] = venv_dir.exists()
    if venv_dir.exists():
        if sys.platform == "win32":
            scripts_dir = venv_dir / "Scripts"
        else:
            scripts_dir = venv_dir / "bin"
        results["venv_has_aetheros"] = (scripts_dir / "aetheros").exists() or (scripts_dir / "aetheros.exe").exists()
    
    # Check config dir
    config_dir = get_aetheros_config_dir()
    results["config_dir_exists"] = config_dir.exists()
    
    return results


def repair_path() -> bool:
    """Ensure the AetherOS bin directory is on PATH.
    
    Returns True if repair was needed and applied.
    """
    bin_dir = get_aetheros_bin_dir()
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    if str(bin_dir) in path_dirs:
        return False
    
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            
            # Add to User PATH via registry
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                "Environment",
                0,
                winreg.KEY_READ | winreg.KEY_WRITE,
            )
            current_path, _ = winreg.QueryValueEx(key, "PATH")
            new_path = f"{bin_dir};{current_path}" if current_path else str(bin_dir)
            winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
            winreg.CloseKey(key)
            
            # Broadcast WM_SETTINGCHANGE
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment")
            return True
        except Exception:
            return False
    
    # Linux/macOS - update shell config
    shell_configs = []
    for rc in (".zshrc", ".bashrc", ".bash_profile", ".profile"):
        p = Path.home() / rc
        if p.exists():
            shell_configs.append(p)
    
    if not shell_configs:
        shell_configs = [Path.home() / ".bashrc"]
    
    export_line = f'\nexport PATH="{bin_dir}:$PATH"\n'
    for cfg in shell_configs:
        try:
            content = cfg.read_text(encoding="utf-8")
            if str(bin_dir) in content:
                continue
            with open(cfg, "a", encoding="utf-8") as f:
                f.write(f'\n# AetherOS\nexport PATH="{bin_dir}:$PATH"\n')
        except Exception:
            continue
    
    return True


def repair_launcher() -> bool:
    """Repair the aetheros launcher if missing or broken.
    
    Returns True if repair was applied.
    """
    bin_dir = get_aetheros_bin_dir()
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    launcher_path = bin_dir / ("aetheros" if sys.platform != "win32" else "aetheros.cmd")
    if launcher_path.exists():
        try:
            if sys.platform != "win32":
                result = subprocess.run([str(launcher_path), "--version"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return False
            else:
                return False
        except Exception:
            pass
    
    # Create launcher
    if sys.platform == "win32":
        launcher_path = bin_dir / "aetheros.cmd"
        launcher_path.write_text(
            f'@echo off\n'
            f'"{sys.executable}" -m aetheros_cli %*\n',
            encoding="utf-8",
        )
        # Also create AetherOS.cmd
        (bin_dir / "AetherOS.cmd").write_text(
            f'@echo off\n'
            f'"{sys.executable}" -m aetheros_cli %*\n',
            encoding="utf-8",
        )
    else:
        launcher_path = bin_dir / "aetheros"
        launcher_path.write_text(
            f'#!/bin/sh\n'
            f'exec "{sys.executable}" -m aetheros_cli "$@"\n',
            encoding="utf-8",
        )
        launcher_path.chmod(launcher_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        
        # Also create AetherOS
        aether_path = bin_dir / "AetherOS"
        aether_path.write_text(launcher_path.read_text(encoding="utf-8"), encoding="utf-8")
        aether_path.chmod(aether_path.stat().st_mode)
    
    return True


def repair_venv() -> bool:
    """Reinstall the package into the venv if broken.
    
    Returns True if repair was applied.
    """
    venv_dir = get_aetheros_venv_dir()
    project_root = Path(__file__).parent.parent.resolve()
    
    if not venv_dir.exists():
        venv_dir.mkdir(parents=True, exist_ok=True)
    
    if sys.platform == "win32":
        python_path = venv_dir / "Scripts" / "python.exe"
    else:
        python_path = venv_dir / "bin" / "python"
    
    if not python_path.exists():
        import venv
        try:
            venv.create(str(venv_dir), with_pip=True)
        except Exception:
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    
    result = subprocess.run(
        [str(python_path), "-m", "pip", "install", "-e", str(project_root)],
        capture_output=True, text=True, timeout=120,
    )
    return result.returncode == 0


def run_self_diagnostic() -> dict:
    """Run full self-diagnostic and return structured results."""
    results = {
        "timestamp": time.time(),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "executable": sys.executable,
        "checks": {},
        "repairs_needed": [],
        "repairs_applied": [],
    }
    
    checks = {
        "launcher_on_path": lambda: find_aetheros_on_path() is not None,
        "both_names_on_path": lambda: shutil.which("AetherOS") is not None and shutil.which("aetheros") is not None,
        "import_works": lambda: _check_import(),
        "config_dir_exists": lambda: get_aetheros_config_dir().exists(),
        "venv_exists": lambda: get_aetheros_venv_dir().exists(),
        "version_accessible": lambda: _check_version(),
    }
    
    for name, check_fn in checks.items():
        try:
            results["checks"][name] = check_fn()
        except Exception as e:
            results["checks"][name] = False
            results.setdefault("check_errors", {})[name] = str(e)
    
    # Determine repairs needed
    if not results["checks"].get("launcher_on_path", False):
        results["repairs_needed"].append("launcher")
        if repair_launcher():
            results["repairs_applied"].append("launcher_created")
    
    if not results["checks"].get("both_names_on_path", False):
        if repair_launcher():
            if "launcher_created" not in results["repairs_applied"]:
                results["repairs_applied"].append("launcher_alias_created")
    
    if not results["checks"].get("config_dir_exists", False):
        get_aetheros_config_dir().mkdir(parents=True, exist_ok=True)
        results["repairs_applied"].append("config_dir_created")
    
    return results


def _check_import() -> bool:
    try:
        import aetheros_cli
        return True
    except Exception:
        return False


def _check_version() -> bool:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "aetheros_cli", "--version"],
            capture_output=True, text=True, timeout=15,
        )
        return result.returncode == 0
    except Exception:
        return False


def print_diagnostic(results: dict) -> None:
    """Pretty-print self-diagnostic results."""
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    
    console = Console()
    
    table = Table(title="AetherOS Diagnostic Report")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="bold")
    
    for name, passed in results.get("checks", {}).items():
        status = "✓ Pass" if passed else "✗ Fail"
        style = "green" if passed else "red"
        table.add_row(name.replace("_", " ").title(), f"[{style}]{status}[/]")
    
    console.print(table)
    
    if results.get("repairs_needed"):
        console.print(f"\n[yellow]Repairs needed: {', '.join(results['repairs_needed'])}[/]")
    if results.get("repairs_applied"):
        console.print(f"[green]Repairs applied: {', '.join(results['repairs_applied'])}[/]")
    
    console.print(f"\nPython: {results['python']}")
    console.print(f"Platform: {results['platform']}")
    console.print(f"Executable: {results['executable']}")


if __name__ == "__main__":
    results = run_self_diagnostic()
    try:
        print_diagnostic(results)
    except ImportError:
        print(json.dumps(results, indent=2))
