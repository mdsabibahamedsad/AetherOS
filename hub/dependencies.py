"""Dependency manager — resolve plugin dependencies, version conflicts, and missing packages."""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from hub.store import HubStore

logger = logging.getLogger(__name__)


class DependencyResolver:
    def __init__(self, store: Optional[HubStore] = None):
        self.store = store or HubStore()

    def parse_version(self, version: str) -> tuple:
        parts = re.split(r"[.+]", version)
        return tuple(int(p) if p.isdigit() else 0 for p in parts[:3])

    def satisfies(self, version: str, constraint: str) -> bool:
        if constraint == "*" or not constraint:
            return True
        if constraint.startswith(">="):
            return self.parse_version(version) >= self.parse_version(constraint[2:])
        if constraint.startswith("<="):
            return self.parse_version(version) <= self.parse_version(constraint[1:])
        if constraint.startswith(">"):
            return self.parse_version(version) > self.parse_version(constraint[1:])
        if constraint.startswith("<"):
            return self.parse_version(version) < self.parse_version(constraint[1:])
        if constraint.startswith("=="):
            return self.parse_version(version) == self.parse_version(constraint[2:])
        if constraint.startswith("~="):
            ver = self.parse_version(version)
            req = self.parse_version(constraint[2:])
            return ver >= req and ver[0] == req[0]
        if constraint.startswith("^"):
            ver = self.parse_version(version)
            req = self.parse_version(constraint[1:])
            return ver >= req and ver[0] == req[0]
        return version == constraint or version.startswith(constraint)

    def check_dependencies(self, plugin_id: str,
                            dependencies: list[dict]) -> dict:
        """Check if all dependencies are satisfied for a plugin."""
        results = {"satisfied": True, "missing": [], "conflicts": [],
                   "updates_needed": []}
        installed = {i["id"]: i for i in self.store.get_installed()}
        for dep in dependencies:
            dep_id = dep.get("package_id", dep if isinstance(dep, str) else "")
            dep_version = dep.get("version", "*")
            optional = dep.get("optional", False)
            if dep_id in installed:
                installed_ver = installed[dep_id].get("version", "0.0.0")
                if not self.satisfies(installed_ver, dep_version):
                    results["conflicts"].append({
                        "package": dep_id,
                        "required": dep_version,
                        "installed": installed_ver,
                    })
                    results["satisfied"] = False
            elif not optional:
                results["missing"].append({
                    "package": dep_id,
                    "version": dep_version,
                    "optional": False,
                })
                results["satisfied"] = False
        return results

    def resolve_conflicts(self, plugin_id: str) -> list[dict]:
        """Find and suggest resolutions for version conflicts."""
        item = self.store.get_installed_item(plugin_id)
        if not item:
            return []
        deps = item.get("dependencies", [])
        if isinstance(deps, str):
            deps = json.loads(deps)
        result = self.check_dependencies(plugin_id, deps)
        resolutions = []
        for conflict in result.get("conflicts", []):
            resolutions.append({
                "package": conflict["package"],
                "issue": f"Version conflict: need {conflict['required']}, "
                         f"have {conflict['installed']}",
                "suggestion": f"Update {conflict['package']} to satisfy "
                              f"{conflict['required']}",
            })
        for missing in result.get("missing", []):
            resolutions.append({
                "package": missing["package"],
                "issue": f"Missing dependency: {missing['package']}",
                "suggestion": f"Install {missing['package']}=={missing['version']}",
            })
        return resolutions

    def install_missing(self, plugin_id: str) -> dict:
        """Auto-install missing dependencies for a plugin."""
        item = self.store.get_installed_item(plugin_id)
        if not item:
            return {"success": False, "error": "Plugin not installed"}
        deps = item.get("dependencies", [])
        if isinstance(deps, str):
            deps = json.loads(deps)
        result = self.check_dependencies(plugin_id, deps)
        if result["satisfied"]:
            return {"success": True, "message": "All dependencies satisfied"}
        installed = []
        for missing in result["missing"]:
            try:
                from hub.marketplace import HubMarketplace
                mp = HubMarketplace()
                mp_item = mp.get_item(missing["package"])
                if mp_item:
                    mp.install(missing["package"])
                    installed.append(missing["package"])
            except Exception as e:
                logger.error("Failed to install %s: %s", missing["package"], e)
        return {"success": True, "installed": installed,
                "remaining": result["missing"]}

    def get_dependency_tree(self, plugin_id: str, depth: int = 0,
                             max_depth: int = 3) -> dict:
        if depth > max_depth:
            return {"name": plugin_id, "truncated": True}
        item = self.store.get_installed_item(plugin_id)
        if not item:
            return {"name": plugin_id, "status": "not_installed"}
        deps = item.get("dependencies", [])
        if isinstance(deps, str):
            deps = json.loads(deps)
        children = []
        for dep in deps:
            dep_id = dep.get("package_id", dep if isinstance(dep, str) else "")
            child = self.get_dependency_tree(dep_id, depth + 1, max_depth)
            child["version_required"] = dep.get("version", "*")
            children.append(child)
        return {"name": plugin_id, "version": item.get("version", ""),
                "children": children}
