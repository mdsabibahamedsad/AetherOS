"""
Extension SDK — development toolkit for building AetherOS extensions.
Supports plugin scaffolding, hot reload, packaging, and validation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from aetheros_constants import get_aetheros_home

logger = logging.getLogger(__name__)


PLUGIN_API_ACCESS_PATTERNS: Set[str] = {
    "providers", "models", "agents", "memory", "knowledge",
    "automation", "communication", "filesystem", "browser",
    "database", "notifications", "workspace", "UI", "components",
    "commands", "settings", "MCP", "terminal", "clipboard",
    "secrets", "hooks", "middleware", "scheduler", "events",
    "search", "vision", "audio", "embedding",
}


class ExtensionType(str, Enum):
    PLUGIN = "plugin"
    TOOL = "tool"
    SKILL = "skill"
    MCP_SERVER = "mcp_server"
    PROVIDER = "provider"
    HOOK = "hook"
    UI_WIDGET = "ui_widget"
    THEME = "theme"
    LANGUAGE = "language"


@dataclass
class ExtensionTemplate:
    name: str
    description: str
    type: ExtensionType
    files: Dict[str, str] = field(default_factory=dict)

    @property
    def file_count(self) -> int:
        return len(self.files)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "type": self.type.value,
            "file_count": self.file_count,
        }


@dataclass
class ExtensionProject:
    path: Path
    manifest: Dict[str, Any] = field(default_factory=dict)
    type: ExtensionType = ExtensionType.PLUGIN
    dev_mode: bool = False
    hot_reload: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": str(self.path),
            "manifest": self.manifest,
            "type": self.type.value,
            "dev_mode": self.dev_mode,
            "hot_reload": self.hot_reload,
        }

    @property
    def manifest_path(self) -> Path:
        for name in ("manifest.json", "manifest.yaml", "plugin.json", "plugin.yaml"):
            p = self.path / name
            if p.exists():
                return p
        return self.path / "manifest.json"


@dataclass
class BuildResult:
    success: bool
    path: Optional[Path] = None
    size: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    checksum: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "path": str(self.path) if self.path else None,
            "size": self.size,
            "errors": self.errors,
            "warnings": self.warnings,
            "checksum": self.checksum,
        }


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    hints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "hints": self.hints,
        }


PLUGIN_MANIFEST_JSON = """{{
    "name": "{name}",
    "version": "0.1.0",
    "description": "{description}",
    "author": "{author}",
    "license": "MIT",
    "type": "{type}",
    "min_engine_version": "0.16.0",
    "entry_point": "plugin.py",
    "categories": [],
    "tags": [],
    "permissions": []
}}"""

PLUGIN_INIT_PY = '''"""
{description}
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register(ctx) -> None:
    """Register this plugin with the AetherOS plugin system."""
    logger.info("Loaded plugin: {name}")
'''

PLUGIN_MANIFEST_YAML = """# {name}
name: {name}
version: 0.1.0
description: "{description}"
author: "{author}"
license: MIT
type: {type}
min_engine_version: "0.16.0"
entry_point: plugin.py

categories: []
tags: []
permissions: []
"""

TOOL_PLUGIN_PY = '''"""
{description}
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def register(ctx) -> None:
    """Register the {name} tool."""
    ctx.register_tool(
        name="{name}",
        toolset="custom",
        schema={{
            "name": "{name}",
            "description": "{description}",
            "input_schema": {{
                "type": "object",
                "properties": {{
                    "input": {{
                        "type": "string",
                        "description": "Input parameter",
                    }}
                }},
                "required": ["input"],
            }},
        }},
        handler=lambda args, **kw: {name}_handler(args, **kw),
    )


def {name}_handler(args: dict, **kw: Any) -> str:
    """Handle the {name} tool call."""
    input_value = args.get("input", "")
    return json.dumps({{"result": f"Processed: {{input_value}}"}})
'''

MCP_SERVER_PY = '''"""
{name} — MCP server generated by AetherOS SDK
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)


def handle_request(request: dict) -> dict:
    """Handle an MCP request."""
    method = request.get("method", "")

    if method == "initialize":
        return {{
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {{
                "protocolVersion": "2024-11-05",
                "capabilities": {{
                    "tools": {{}},
                }},
                "serverInfo": {{
                    "name": "{name}",
                    "version": "0.1.0",
                }},
            }},
        }}

    if method == "tools/list":
        return {{
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {{
                "tools": [],
            }},
        }}

    if method == "tools/call":
        return {{
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {{
                "code": -32601,
                "message": "Tool not found",
            }},
        }}

    return {{
        "jsonrpc": "2.0",
        "id": request.get("id"),
        "error": {{
            "code": -32601,
            "message": f"Unknown method: {{method}}",
        }},
    }}


def main() -> None:
    """Run the MCP server over stdio."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            sys.stdout.write(json.dumps(response) + "\\n")
            sys.stdout.flush()
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON: %s", e)


if __name__ == "__main__":
    main()
'''

TEST_PLUGIN_PY = '''"""Tests for {name} plugin."""

from __future__ import annotations

import pytest


def test_plugin_imports():
    """Verify the plugin can be imported."""
    import importlib
    spec = importlib.util.spec_from_file_location(
        "{name}", "plugin.py"
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert hasattr(module, "register")


def test_manifest_exists():
    """Verify manifest file exists."""
    import os
    for name in ("manifest.json", "manifest.yaml", "plugin.json", "plugin.yaml"):
        if os.path.exists(name):
            return
    pytest.fail("No manifest file found")
'''

README_MD = """# {name}

{description}

## Installation

```bash
aetheros plugin install {name}
```

## Development

```bash
aetheros sdk init {name} --type {type}
```

## License

{license}
"""


_BUILTIN_TEMPLATES: Dict[str, ExtensionTemplate] = {
    "plugin": ExtensionTemplate(
        name="plugin",
        description="A basic AetherOS plugin with register() entry point",
        type=ExtensionType.PLUGIN,
        files={
            "plugin.py": PLUGIN_INIT_PY,
            "manifest.json": PLUGIN_MANIFEST_JSON,
            "README.md": README_MD,
        },
    ),
    "tool": ExtensionTemplate(
        name="tool",
        description="A plugin that exposes a custom tool via ctx.register_tool()",
        type=ExtensionType.TOOL,
        files={
            "plugin.py": TOOL_PLUGIN_PY,
            "manifest.json": PLUGIN_MANIFEST_JSON,
            "README.md": README_MD,
        },
    ),
    "mcp_server": ExtensionTemplate(
        name="mcp_server",
        description="A Model Context Protocol server with stdio transport",
        type=ExtensionType.MCP_SERVER,
        files={
            "server.py": MCP_SERVER_PY,
            "manifest.json": PLUGIN_MANIFEST_JSON,
            "README.md": README_MD,
        },
    ),
    "skill": ExtensionTemplate(
        name="skill",
        description="A skill plugin with SKILL.md frontmatter and procedure",
        type=ExtensionType.SKILL,
        files={
            "SKILL.md": "# {name}\\n\\n{description}\\n",
            "manifest.json": PLUGIN_MANIFEST_JSON,
            "README.md": README_MD,
        },
    ),
    "provider": ExtensionTemplate(
        name="provider",
        description="A provider plugin implementing a storage or inference backend",
        type=ExtensionType.PROVIDER,
        files={
            "plugin.py": PLUGIN_INIT_PY,
            "provider.py": '''"""Provider implementation for {name}."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class {name_camel}Provider:
    """Provider implementation."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {{}}

    def initialize(self) -> None:
        """Initialize the provider."""
        logger.info("Initialized {name} provider")

    def shutdown(self) -> None:
        """Shutdown the provider."""
        logger.info("Shutdown {name} provider")
''',
            "manifest.json": PLUGIN_MANIFEST_JSON,
            "README.md": README_MD,
        },
    ),
    "hook": ExtensionTemplate(
        name="hook",
        description="A plugin that registers lifecycle hooks",
        type=ExtensionType.HOOK,
        files={
            "plugin.py": '''"""
{description}
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register(ctx) -> None:
    """Register lifecycle hooks."""
    ctx.register_hook("pre_tool_call", on_pre_tool_call)
    ctx.register_hook("post_tool_call", on_post_tool_call)
    ctx.register_hook("on_session_start", on_session_start)


def on_pre_tool_call(tool_name: str, args: dict, **kw) -> None:
    logger.debug("Pre tool call: %s", tool_name)


def on_post_tool_call(tool_name: str, result: str, **kw) -> None:
    logger.debug("Post tool call: %s", tool_name)


def on_session_start(**kw) -> None:
    logger.info("Session started")
''',
            "manifest.json": PLUGIN_MANIFEST_JSON,
            "README.md": README_MD,
        },
    ),
}


class ExtensionSdk:
    def __init__(self):
        self._home = get_aetheros_home()
        self._sdk_dir = self._home / "sdk"
        self._projects_dir = self._home / "projects"
        self._templates: Dict[str, ExtensionTemplate] = dict(_BUILTIN_TEMPLATES)
        self._projects: Dict[str, ExtensionProject] = {}
        self._dev_mode: bool = False
        self._hot_reload: bool = False
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self._sdk_dir.mkdir(parents=True, exist_ok=True)
        self._projects_dir.mkdir(parents=True, exist_ok=True)

    def list_templates(self, type_filter: Optional[ExtensionType] = None) -> List[ExtensionTemplate]:
        if type_filter:
            return [t for t in self._templates.values() if t.type == type_filter]
        return list(self._templates.values())

    def get_template(self, name: str) -> Optional[ExtensionTemplate]:
        return self._templates.get(name)

    def register_template(self, template: ExtensionTemplate) -> None:
        self._templates[template.name] = template

    def scaffold_extension(
        self,
        template_name: str,
        output_dir: Path,
        name: str,
        description: str = "",
        author: str = "",
        license: str = "MIT",
    ) -> List[Path]:
        template = self._templates.get(template_name)
        if not template:
            raise ValueError(
                f"Unknown template '{template_name}'. "
                f"Available: {', '.join(self._templates)}"
            )

        project_dir = output_dir / name
        if project_dir.exists():
            raise FileExistsError(f"Directory already exists: {project_dir}")
        project_dir.mkdir(parents=True, exist_ok=True)

        name_camel = "".join(part.capitalize() for part in name.replace("-", "_").split("_"))

        created: List[Path] = []
        for filename, content in template.files.items():
            formatted = content.format(
                name=name,
                name_camel=name_camel,
                description=description or f"{name} plugin",
                author=author or "AetherOS Developer",
                license=license,
                type=template.type.value,
            )
            file_path = project_dir / filename
            file_path.write_text(formatted, encoding="utf-8")
            created.append(file_path)

        if template_name == "plugin" and "manifest.json" not in template.files:
            manifest = OrderedManifest(
                name=name,
                version="0.1.0",
                description=description or f"{name} plugin",
                author=author or "AetherOS Developer",
                license=license,
                type=template.type.value,
            )
            manifest_path = project_dir / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest.to_dict(), indent=2), encoding="utf-8"
            )
            created.append(manifest_path)

        project = ExtensionProject(
            path=project_dir,
            manifest=self._load_manifest(project_dir),
            type=template.type,
            dev_mode=self._dev_mode,
            hot_reload=self._hot_reload,
        )
        self._projects[name] = project

        logger.info(
            "Scaffolded %s extension '%s' at %s (%d files)",
            template.type.value, name, project_dir, len(created),
        )
        return created

    def _load_manifest(self, path: Path) -> Dict[str, Any]:
        for name in ("manifest.json", "manifest.yaml", "plugin.json", "plugin.yaml"):
            p = path / name
            if p.exists():
                if p.suffix == ".json":
                    return json.loads(p.read_text(encoding="utf-8"))
                elif p.suffix in (".yaml", ".yml"):
                    import yaml
                    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return {}

    def validate_manifest(self, path: Path) -> ValidationResult:
        errors: List[str] = []
        warnings: List[str] = []
        hints: List[str] = []

        manifest = self._load_manifest(path)
        if not manifest:
            return ValidationResult(
                valid=False,
                errors=["No manifest file found (manifest.json, manifest.yaml, plugin.json, or plugin.yaml)"],
            )

        if "name" not in manifest:
            errors.append("Missing required field: 'name'")
        elif not re.match(r"^[a-zA-Z_][a-zA-Z0-9_\-]*$", str(manifest["name"])):
            errors.append(
                "Field 'name' must match pattern: ^[a-zA-Z_][a-zA-Z0-9_\\-]*$"
            )

        if "version" not in manifest:
            errors.append("Missing required field: 'version'")
        else:
            ver = str(manifest["version"])
            if not re.match(r"^\d+\.\d+\.\d+", ver):
                warnings.append(
                    f"Field 'version' ('{ver}') does not follow semver"
                )

        if "description" not in manifest:
            warnings.append("Missing recommended field: 'description'")

        if "type" not in manifest:
            hints.append(
                "Consider adding 'type' field: plugin, tool, skill, mcp_server, provider, hook"
            )

        type_val = manifest.get("type", "plugin")
        if type_val not in {t.value for t in ExtensionType}:
            warnings.append(
                f"Unknown type '{type_val}'. "
                f"Supported: {', '.join(t.value for t in ExtensionType)}"
            )

        if "entry_point" not in manifest:
            for candidate in ("plugin.py", "main.py", "__init__.py"):
                if (path / candidate).exists():
                    hints.append(f"Add 'entry_point': '{candidate}' to manifest")
                    break
            else:
                warnings.append("Missing recommended field: 'entry_point'")

        permissions = manifest.get("permissions", [])
        if not isinstance(permissions, list):
            errors.append("Field 'permissions' must be a list")
        elif permissions:
            for p in permissions:
                if isinstance(p, dict) and "resource" not in p:
                    errors.append("Each permission entry must have a 'resource' field")

        dependencies = manifest.get("dependencies", {})
        if isinstance(dependencies, dict):
            for dep_name, dep_ver in dependencies.items():
                if not isinstance(dep_ver, str):
                    errors.append(
                        f"Dependency '{dep_name}' version must be a string"
                    )

        if "min_engine_version" not in manifest:
            hints.append(
                "Consider adding 'min_engine_version' for compatibility checking"
            )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            hints=hints,
        )

    def build_extension(
        self,
        source_dir: Path,
        output_path: Optional[Path] = None,
        include_patterns: Optional[List[str]] = None,
    ) -> BuildResult:
        errors: List[str] = []
        warnings: List[str] = []

        if not source_dir.exists():
            return BuildResult(
                success=False,
                errors=[f"Source directory not found: {source_dir}"],
            )

        validation = self.validate_manifest(source_dir)
        if not validation.valid:
            return BuildResult(
                success=False,
                errors=validation.errors,
                warnings=validation.warnings,
            )

        if output_path is None:
            manifest = self._load_manifest(source_dir)
            name = manifest.get("name", source_dir.name)
            version = manifest.get("version", "0.1.0")
            output_path = source_dir.parent / f"{name}-{version}.aep"

        try:
            tmp_dir = Path(tempfile.mkdtemp(prefix="aep_build_"))
            staging = tmp_dir / "plugin"
            shutil.copytree(source_dir, staging)

            exclude = {"__pycache__", ".git", ".DS_Store", "*.pyc", ".aep"}
            for item in list(staging.rglob("*")):
                for pattern in exclude:
                    if item.match(pattern):
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
                        break

            with zipfile.ZipFile(
                output_path, "w", zipfile.ZIP_DEFLATED
            ) as zf:
                for file_path in sorted(staging.rglob("*")):
                    if file_path.is_file():
                        arcname = str(file_path.relative_to(staging))
                        zf.write(file_path, arcname)

            file_size = output_path.stat().st_size
            checksum = hashlib.sha256(output_path.read_bytes()).hexdigest()

            shutil.rmtree(tmp_dir, ignore_errors=True)

            project_name = self._load_manifest(source_dir).get("name", source_dir.name)
            self._projects[project_name] = ExtensionProject(
                path=source_dir,
                manifest=self._load_manifest(source_dir),
                type=ExtensionType.PLUGIN,
                dev_mode=self._dev_mode,
                hot_reload=self._hot_reload,
            )

            logger.info(
                "Built extension: %s (%d bytes, sha256=%s)",
                output_path, file_size, checksum[:16],
            )

            return BuildResult(
                success=True,
                path=output_path,
                size=file_size,
                errors=errors,
                warnings=warnings,
                checksum=checksum,
            )

        except Exception as e:
            logger.exception("Build failed")
            return BuildResult(
                success=False,
                errors=[str(e)],
                warnings=warnings,
            )

    def hot_reload(self, project_name: str) -> bool:
        project = self._projects.get(project_name)
        if not project:
            logger.warning("Project '%s' not found", project_name)
            return False

        if not project.hot_reload:
            logger.info("Hot reload not enabled for '%s'", project_name)
            return False

        validation = self.validate_manifest(project.path)
        if not validation.valid:
            logger.error(
                "Hot reload blocked: validation failed for '%s'", project_name
            )
            return False

        logger.info("Hot reload triggered for '%s'", project_name)
        return True

    def enable_dev_mode(self) -> None:
        self._dev_mode = True
        marker = self._sdk_dir / ".dev_mode"
        marker.write_text(datetime.utcnow().isoformat(), encoding="utf-8")
        logger.info("Developer mode enabled")

    def disable_dev_mode(self) -> None:
        self._dev_mode = False
        marker = self._sdk_dir / ".dev_mode"
        if marker.exists():
            marker.unlink()
        logger.info("Developer mode disabled")

    @property
    def is_dev_mode(self) -> bool:
        return self._dev_mode or (self._sdk_dir / ".dev_mode").exists()

    def enable_hot_reload(self) -> None:
        self._hot_reload = True
        marker = self._sdk_dir / ".hot_reload"
        marker.write_text(datetime.utcnow().isoformat(), encoding="utf-8")
        logger.info("Hot reload enabled")

    def disable_hot_reload(self) -> None:
        self._hot_reload = False
        marker = self._sdk_dir / ".hot_reload"
        if marker.exists():
            marker.unlink()
        logger.info("Hot reload disabled")

    @property
    def is_hot_reload(self) -> bool:
        return self._hot_reload or (self._sdk_dir / ".hot_reload").exists()

    def run_tests(
        self,
        project_path: Path,
        test_path: Optional[str] = None,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        if not project_path.exists():
            return {"success": False, "error": "Project path not found"}

        validation = self.validate_manifest(project_path)
        test_dir = project_path / "tests"
        if not test_dir.exists():
            test_dir = project_path

        cmd = [sys.executable, "-m", "pytest", str(test_dir), "-x", "--tb=short"]
        if verbose:
            cmd.append("-v")
        if test_path:
            cmd.append(f"-k={test_path}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(project_path),
            )
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "valid_manifest": validation.valid,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Tests timed out (120s)"}
        except FileNotFoundError:
            return {"success": False, "error": "pytest not found"}

    def generate_docs(self, project_path: Path, output_path: Optional[Path] = None) -> Path:
        manifest = self._load_manifest(project_path)
        if not manifest:
            raise ValueError("No manifest found in project")

        name = manifest.get("name", project_path.name)
        description = manifest.get("description", "")
        version = manifest.get("version", "0.1.0")
        author = manifest.get("author", "")
        license_val = manifest.get("license", "MIT")

        if output_path is None:
            output_path = project_path / "docs" / "README.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        doc_lines = [
            f"# {name}",
            "",
            f"{description}",
            "",
            "## Overview",
            "",
            f"**Version:** {version}  ",
            f"**Author:** {author}  ",
            f"**License:** {license_val}",
            "",
            "## Installation",
            "",
            "```bash",
            f"aetheros plugin install {name}",
            "```",
            "",
            "## Development",
            "",
            "```bash",
            "aetheros sdk init --type plugin",
            "aetheros sdk build",
            "aetheros sdk validate",
            "```",
            "",
            "## Permissions",
            "",
        ]

        permissions = manifest.get("permissions", [])
        if permissions:
            doc_lines.append("| Resource | Actions | Effect |")
            doc_lines.append("|----------|---------|--------|")
            for p in permissions:
                resource = p.get("resource", "unknown")
                actions = ", ".join(p.get("actions", ["read"]))
                effect = p.get("effect", "allow")
                doc_lines.append(f"| {resource} | {actions} | {effect} |")
        else:
            doc_lines.append("No permissions declared.")

        dependencies = manifest.get("dependencies", {})
        if dependencies:
            doc_lines.extend(["", "## Dependencies", ""])
            for dep_name, dep_ver in dependencies.items():
                doc_lines.append(f"- **{dep_name}**: `{dep_ver}`")

        doc_lines.extend(["", "## API Access Patterns", ""])
        api_patterns = manifest.get("api_access", [])
        if api_patterns:
            for pattern in api_patterns:
                doc_lines.append(f"- `{pattern}`")
        else:
            doc_lines.append(
                "This plugin does not declare API access patterns."
            )

        output_path.write_text("\n".join(doc_lines) + "\n", encoding="utf-8")
        logger.info("Generated docs for '%s' at %s", name, output_path)
        return output_path

    def get_project(self, name: str) -> Optional[ExtensionProject]:
        return self._projects.get(name)

    def list_projects(self) -> List[ExtensionProject]:
        return list(self._projects.values())

    def load_projects(self) -> None:
        for item in self._projects_dir.iterdir():
            if item.is_dir():
                manifest = self._load_manifest(item)
                if manifest:
                    type_str = manifest.get("type", "plugin")
                    try:
                        ext_type = ExtensionType(type_str)
                    except ValueError:
                        ext_type = ExtensionType.PLUGIN
                    self._projects[item.name] = ExtensionProject(
                        path=item,
                        manifest=manifest,
                        type=ext_type,
                        dev_mode=self.is_dev_mode,
                        hot_reload=self.is_hot_reload,
                    )

    def get_api_access_patterns(self) -> Set[str]:
        return PLUGIN_API_ACCESS_PATTERNS

    def validate_extension_compatibility(
        self, manifest_path: Path, engine_version: str = "0.16.0"
    ) -> ValidationResult:
        result = self.validate_manifest(manifest_path)
        if not result.valid:
            return result

        manifest = self._load_manifest(manifest_path)
        min_ver = manifest.get("min_engine_version", "")

        if min_ver:
            try:
                manifest_parts = [int(x) for x in min_ver.split(".")]
                engine_parts = [int(x) for x in engine_version.split(".")]
                mp = manifest_parts[:3]
                ep = engine_parts[:3]
                while len(mp) < 3:
                    mp.append(0)
                while len(ep) < 3:
                    ep.append(0)
                if tuple(mp) > tuple(ep):
                    result.valid = False
                    result.errors.append(
                        f"Extension requires engine version {min_ver}, "
                        f"but current is {engine_version}"
                    )
            except (ValueError, IndexError):
                result.warnings.append(
                    f"Could not parse min_engine_version '{min_ver}'"
                )

        return result


class OrderedManifest:
    def __init__(
        self,
        name: str,
        version: str,
        description: str = "",
        author: str = "",
        license: str = "MIT",
        type: str = "plugin",
        entry_point: str = "plugin.py",
        min_engine_version: str = "0.16.0",
        categories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        permissions: Optional[List[Dict[str, Any]]] = None,
    ):
        self._data = {
            "name": name,
            "version": version,
            "description": description,
            "author": author,
            "license": license,
            "type": type,
            "min_engine_version": min_engine_version,
            "entry_point": entry_point,
            "categories": categories or [],
            "tags": tags or [],
            "permissions": permissions or [],
        }

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)
