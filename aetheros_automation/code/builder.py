from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from aetheros_automation.terminal.runner import TerminalRunner

logger = logging.getLogger(__name__)

_PACKAGE_MANAGERS: dict[str, dict[str, Any]] = {
    "pip": {
        "files": ["requirements.txt", "setup.py", "setup.cfg", "pyproject.toml"],
        "install_cmd": ["pip", "install", "-r", "requirements.txt"],
        "install_fallback": ["pip", "install", "-e", "."],
    },
    "npm": {
        "files": ["package.json"],
        "install_cmd": ["npm", "install"],
    },
    "yarn": {
        "files": ["yarn.lock"],
        "install_cmd": ["yarn", "install"],
    },
    "cargo": {
        "files": ["Cargo.toml"],
        "install_cmd": ["cargo", "build"],
    },
    "go": {
        "files": ["go.mod"],
        "install_cmd": ["go", "mod", "download"],
    },
    "mvn": {
        "files": ["pom.xml"],
        "install_cmd": ["mvn", "install", "-DskipTests"],
    },
    "gradle": {
        "files": ["build.gradle", "build.gradle.kts"],
        "install_cmd": ["gradle", "build", "-x", "test"],
    },
    "gem": {
        "files": ["Gemfile", "Gemfile.lock"],
        "install_cmd": ["bundle", "install"],
    },
    "mix": {
        "files": ["mix.exs"],
        "install_cmd": ["mix", "deps.get"],
    },
}


class CodeBuilder:
    """Detect project type, install dependencies, run tests, and build."""

    @staticmethod
    async def detect_package_manager(path: str) -> str | None:
        p = Path(path).resolve()
        for name, config in _PACKAGE_MANAGERS.items():
            for marker in config["files"]:
                if (p / marker).is_file():
                    return name
        return None

    @staticmethod
    async def install_deps(path: str, manager: str = "auto") -> dict[str, Any]:
        path_obj = Path(path).resolve()
        if manager == "auto":
            detected = await CodeBuilder.detect_package_manager(str(path_obj))
            if not detected:
                return {
                    "success": False,
                    "output": "No recognised package manager detected",
                    "manager": None,
                }
            manager = detected

        config = _PACKAGE_MANAGERS.get(manager)
        if not config:
            return {
                "success": False,
                "output": f"Unknown package manager: {manager}",
                "manager": manager,
            }

        install_cmds: list[list[str]] = [config["install_cmd"]]
        if manager == "pip" and not (path_obj / "requirements.txt").is_file():
            install_cmds = [config.get("install_fallback", config["install_cmd"])]

        outputs: list[str] = []
        exit_code = 0
        for cmd_parts in install_cmds:
            cmd_str = " ".join(cmd_parts)
            result = await TerminalRunner.run(cmd_str, cwd=str(path_obj))
            outputs.append(result["stdout"])
            outputs.append(result["stderr"])
            if result["exit_code"] != 0:
                exit_code = result["exit_code"]
                break

        return {
            "success": exit_code == 0,
            "output": "\n".join(outputs),
            "manager": manager,
            "exit_code": exit_code,
        }

    @staticmethod
    async def run_tests(
        path: str, test_command: str | None = None
    ) -> dict[str, Any]:
        if test_command:
            cmd = test_command
        else:
            manager = await CodeBuilder.detect_package_manager(path)
            cmd = _test_command_for(manager, path)

        result = await TerminalRunner.run(cmd, cwd=path)
        stdout = result["stdout"]
        stderr = result["stderr"]

        passed = "FAILED" not in stdout and "FAILED" not in stderr
        return {
            "passed": passed,
            "failed": not passed,
            "output": stdout + "\n" + stderr,
            "exit_code": result["exit_code"],
            "command": cmd,
        }

    @staticmethod
    async def fix_errors(path: str, errors: list[str]) -> dict[str, Any]:
        """Attempt auto-fixes for common error patterns."""
        fixes: list[str] = []
        combined_errors = "\n".join(errors).lower()

        for pattern, fix_cmd in _FIX_PATTERNS:
            if any(p in combined_errors for p in pattern):
                logger.info("Applying fix: %s", fix_cmd)
                result = await TerminalRunner.run(fix_cmd, cwd=path)
                fixes.append(fix_cmd)
                if result["exit_code"] != 0:
                    logger.warning("Fix failed: %s", result["stderr"])

        if not fixes:
            return {
                "fixed": False,
                "applied_fixes": [],
                "message": "No known auto-fix matched the provided errors",
            }

        return {
            "fixed": True,
            "applied_fixes": fixes,
            "message": f"Applied {len(fixes)} fix(es)",
        }

    @staticmethod
    async def build(
        path: str, build_command: str | None = None
    ) -> dict[str, Any]:
        if build_command:
            cmd = build_command
        else:
            manager = await CodeBuilder.detect_package_manager(path)
            cmd = _build_command_for(manager, path)

        result = await TerminalRunner.run(cmd, cwd=path)
        return {
            "success": result["exit_code"] == 0,
            "output": result["stdout"],
            "errors": result["stderr"],
            "exit_code": result["exit_code"],
            "command": cmd,
        }


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------

_FIX_PATTERNS: list[tuple[list[str], str]] = [
    (["module not found", "modulenotfounderror", "import error"], "pip install -e ."),
    (["cannot find package", "enoent"], "npm install"),
    (["lockfile", "out of date"], "npm install"),
    (["eslint", "prettier"], "npx eslint --fix ."),
    (["black", "formatting"], "black ."),
    (["ruff"], "ruff check --fix ."),
]


def _test_command_for(manager: str | None, path: str) -> str:
    if manager is None:
        if (Path(path) / "pyproject.toml").is_file():
            return "pytest"
        if (Path(path) / "package.json").is_file():
            return "npm test"
        return "python -m pytest"
    commands: dict[str, str] = {
        "pip": "python -m pytest",
        "npm": "npm test",
        "yarn": "yarn test",
        "cargo": "cargo test",
        "go": "go test ./...",
        "mvn": "mvn test",
        "gradle": "gradle test",
        "gem": "bundle exec rspec",
        "mix": "mix test",
    }
    return commands.get(manager, "pytest")


def _build_command_for(manager: str | None, path: str) -> str:
    if manager is None:
        if (Path(path) / "pyproject.toml").is_file():
            return "python -m build"
        if (Path(path) / "package.json").is_file():
            return "npm run build"
        return "echo 'no build command detected'"

    commands: dict[str, str] = {
        "pip": "python -m build",
        "npm": "npm run build",
        "yarn": "yarn build",
        "cargo": "cargo build --release",
        "go": "go build ./...",
        "mvn": "mvn package -DskipTests",
        "gradle": "gradle build -x test",
        "gem": "gem build *.gemspec",
        "mix": "mix compile",
    }
    return commands.get(manager, "echo 'no build command detected'")
