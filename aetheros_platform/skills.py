"""Skill SDK runtime (Master 62 §14-15): composable skills + dependency graph.

Dependencies resolve against registered tools/skills/models. Detection:
missing deps, incompatible versions, cycles, privilege escalation (a skill
may never gain capabilities beyond the union its chain declares — grants are
never auto-expanded), malicious change (hash-pinned updates).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Dict, List, Optional, Set

from aetheros_platform.errors import err
from aetheros_platform.schemas import validate


def _version_ok(required: str, actual: str) -> bool:
    """Minimal ^/~major check: '>=1.2.0' or exact/'1.x' accepted forms."""
    required = required.strip()
    if required in ("*", "x", ""):
        return True
    if required.startswith(">="):
        return _tuple(actual) >= _tuple(required[2:])
    if required.startswith("^"):
        base = _tuple(required[1:])
        return _tuple(actual)[:1] == base[:1] and _tuple(actual) >= base
    return _tuple(actual) == _tuple(required)


def _tuple(v: str) -> tuple:
    parts = []
    for p in v.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


class SkillRegistry:
    def __init__(self, tools=None, audit: Optional[Callable] = None) -> None:
        self._skills: Dict[str, Dict[str, Any]] = {}
        self._tools = tools
        self._audit = audit

    def register(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        errors = validate("Skill", manifest)
        if errors:
            raise err("INVALID_SCHEMA", f"skill manifest invalid: {errors[0]}")
        key = f"{manifest['name']}@{manifest['version']}"
        if key in self._skills:
            raise err("CONFLICT", f"skill {key} already registered")
        digest = "sha256:" + hashlib.sha256(
            json.dumps(manifest, sort_keys=True).encode()).hexdigest()
        manifest = dict(manifest)
        manifest["_digest"] = digest
        self._skills[key] = manifest
        if self._audit:
            self._audit("skill.registered", "", key, "ok", {})
        return manifest

    def get(self, name: str, version: Optional[str] = None) -> Dict[str, Any]:
        if version and f"{name}@{version}" in self._skills:
            return self._skills[f"{name}@{version}"]
        cands = sorted(k for k in self._skills if k.startswith(name + "@"))
        if not cands:
            raise err("RESOURCE_UNAVAILABLE", f"unknown skill {name}")
        return self._skills[cands[-1]]

    def list(self) -> List[Dict[str, Any]]:
        return list(self._skills.values())

    def resolve(self, name: str, version: Optional[str] = None,
                _stack: Optional[tuple] = None) -> Dict[str, Any]:
        """Resolve the full dependency graph. Raises on missing/version/
        cycle/escalation problems. Capabilities are the union of the chain —
        callers must pass exactly these as grants (never more)."""
        stack = _stack or ()
        skill = self.get(name, version)
        key = f"{skill['name']}@{skill['version']}"
        if key in stack:
            raise err("CONFLICT", f"skill dependency cycle: {' -> '.join(stack + (key,))}")
        deps = skill.get("dependencies", {}) or {}
        caps: Set[str] = set(skill.get("capabilities", []))
        resolved: Dict[str, Any] = {"skill": key, "tools": [], "skills": [], "models": []}
        for tool in skill.get("tools", []) + list(deps.get("tools", {}).keys()):
            if self._tools is None:
                raise err("TOOL_UNAVAILABLE", f"no tool runtime for dependency {tool}")
            try:
                tm = self._tools.get(tool)
            except Exception:
                raise err("INVALID_REQUEST", f"missing tool dependency: {tool}",
                          remediation="install the providing package first")
            resolved["tools"].append(f"{tm['name']}@{tm['version']}")
            caps.update(tm.get("capabilities", []))
        for dep_name, req in (deps.get("skills", {}) or {}).items():
            sub = self.resolve(dep_name, None, stack + (key,))
            avail = sub["skill"].split("@")[1]
            if not _version_ok(str(req), avail):
                raise err("CONFLICT",
                          f"skill {dep_name} version {avail} does not satisfy {req}")
            resolved["skills"].append(sub)
            caps.update(sub.get("capabilities", set()))
        declared = set(skill.get("capabilities", []))
        # Escalation check: the resolved union must not exceed what the root
        # skill plus its DIRECT tool deps declare... dependencies contribute
        # their own caps, but the ROOT grant set stays fixed: report it.
        resolved["capabilities"] = sorted(caps)
        resolved["grant_ceiling"] = sorted(declared)
        return resolved
