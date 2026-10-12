from __future__ import annotations
import json, logging, os, subprocess
from typing import Any

logger = logging.getLogger(__name__)

class DependencyManager:
    def __init__(self):
        self._managers = {
            "npm": {"files": ["package.json", "package-lock.json"], "lock": "package-lock.json", "install": ["npm", "install"], "add": ["npm", "install"], "remove": ["npm", "uninstall"], "update": ["npm", "update"], "audit": ["npm", "audit"]},
            "pip": {"files": ["requirements.txt", "pyproject.toml", "setup.py", "setup.cfg", "Pipfile"], "lock": "", "install": ["pip", "install"], "add": ["pip", "install"], "remove": ["pip", "uninstall"], "update": ["pip", "install", "--upgrade"], "audit": ["pip", "audit"] if self._has_pip_audit() else []},
            "cargo": {"files": ["Cargo.toml", "Cargo.lock"], "lock": "Cargo.lock", "install": ["cargo", "build"], "add": ["cargo", "add"], "remove": ["cargo", "remove"], "update": ["cargo", "update"], "audit": ["cargo", "audit"]},
            "go": {"files": ["go.mod", "go.sum"], "lock": "go.sum", "install": ["go", "mod", "download"], "add": ["go", "get"], "remove": ["go", "mod", "tidy"], "update": ["go", "get", "-u"], "audit": ["go", "vet"]},
        }

    def _has_pip_audit(self) -> bool:
        try:
            subprocess.run(["pip", "audit", "--version"], capture_output=True, timeout=10)
            return True
        except Exception:
            return False

    def detect_managers(self, project_path: str) -> list[dict[str, Any]]:
        detected = []
        for name, config in self._managers.items():
            for f in config["files"]:
                if os.path.isfile(os.path.join(project_path, f)):
                    info = {"name": name, "files": config["files"]}
                    if name == "npm" and os.path.isfile(os.path.join(project_path, "package.json")):
                        try:
                            with open(os.path.join(project_path, "package.json"), encoding="utf-8") as fh:
                                pkg = json.load(fh)
                            deps = pkg.get("dependencies", {})
                            dev_deps = pkg.get("devDependencies", {})
                            info["dependencies"] = len(deps) + len(dev_deps)
                            info["package_count"] = len(deps) + len(dev_deps)
                        except Exception:
                            pass
                    elif name == "pip":
                        req_file = os.path.join(project_path, "requirements.txt")
                        if os.path.isfile(req_file):
                            try:
                                with open(req_file, encoding="utf-8") as fh:
                                    info["dependencies"] = sum(1 for l in fh if l.strip() and not l.startswith("#") and "==" in l)
                            except Exception:
                                pass
                    detected.append(info)
                    break
        return detected

    def get_dependencies(self, project_path: str, manager: str) -> list[dict[str, Any]]:
        deps = []
        if manager == "npm":
            pkg_path = os.path.join(project_path, "package.json")
            if os.path.isfile(pkg_path):
                try:
                    with open(pkg_path, encoding="utf-8") as f:
                        pkg = json.load(f)
                    for name, ver in pkg.get("dependencies", {}).items():
                        deps.append({"name": name, "version": ver, "type": "production"})
                    for name, ver in pkg.get("devDependencies", {}).items():
                        deps.append({"name": name, "version": ver, "type": "development"})
                except Exception:
                    pass
        elif manager == "pip":
            req_path = os.path.join(project_path, "requirements.txt")
            if os.path.isfile(req_path):
                try:
                    with open(req_path, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#"):
                                parts = line.split("==", 1)
                                deps.append({"name": parts[0], "version": parts[1] if len(parts) > 1 else "*", "type": "production"})
                except Exception:
                    pass
        return deps

    def install_package(self, project_path: str, manager: str, package_name: str, dev: bool = False, version: str = "") -> dict[str, Any]:
        config = self._managers.get(manager)
        if not config:
            return {"success": False, "error": f"Unknown package manager: {manager}"}
        cmd = list(config["add"])
        if manager == "npm":
            if dev:
                cmd.append("--save-dev")
            cmd.append(f"{package_name}@{version}" if version else package_name)
        elif manager == "pip":
            cmd.append(f"{package_name}=={version}" if version else package_name)
        elif manager == "cargo":
            cmd.append(package_name)
        try:
            r = subprocess.run(cmd, cwd=project_path, capture_output=True, text=True, timeout=120)
            return {"success": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Package installation timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def remove_package(self, project_path: str, manager: str, package_name: str) -> dict[str, Any]:
        config = self._managers.get(manager)
        if not config:
            return {"success": False, "error": f"Unknown package manager: {manager}"}
        cmd = list(config["remove"])
        cmd.append(package_name)
        try:
            r = subprocess.run(cmd, cwd=project_path, capture_output=True, text=True, timeout=120)
            return {"success": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_audit(self, project_path: str, manager: str) -> dict[str, Any]:
        config = self._managers.get(manager)
        if not config or not config["audit"]:
            return {"success": False, "error": f"Audit not available for {manager}"}
        try:
            r = subprocess.run(config["audit"], cwd=project_path, capture_output=True, text=True, timeout=120)
            return {"success": r.returncode in (0, 1), "stdout": r.stdout, "stderr": r.stderr, "exit_code": r.returncode}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Audit timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
