"""Python Runtime — isolated Python code execution.

Real execution with:
- Subprocess isolation
- pip package management
- Virtual environment support
- Timeout enforcement
- Streaming output capture
"""

from __future__ import annotations

import ast
import io
import json
import logging
import os
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import venv as venv_module
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tool_runtime.interface import (
    ToolInterface,
    ToolMetadata,
    ToolResult,
    ToolRiskLevel,
    ToolCategory,
    ToolStatus,
)

logger = logging.getLogger(__name__)


class PythonRuntime(ToolInterface):
    """Isolated Python execution environment.

    Features:
    - Execute Python code strings in isolated subprocess
    - Package installation with pip
    - Virtual environment creation and management
    - Timeout enforcement
    - Output capture and streaming
    """

    def __init__(self):
        meta = ToolMetadata(
            id="python",
            name="Python Runtime",
            description="Execute isolated Python code, manage packages and virtual environments",
            category=ToolCategory.PYTHON,
            risk_level=ToolRiskLevel.EXECUTE,
            version="2.0.0",
            tags=["python", "code", "execution", "venv"],
            requires_approval=False,
            timeout_seconds=60.0,
        )
        super().__init__(meta)
        self._venv_base = Path(tempfile.gettempdir()) / "aetheros_venvs"
        self._venv_base.mkdir(parents=True, exist_ok=True)

    def schema(self) -> Dict[str, Any]:
        return {
            "name": "python",
            "description": self.description(),
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["exec", "eval", "install", "create_venv", "list_packages"],
                    },
                    "code": {"type": "string", "description": "Python code to execute"},
                    "expression": {"type": "string", "description": "Python expression to evaluate"},
                    "packages": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Packages to install",
                    },
                    "venv_name": {"type": "string", "description": "Virtual environment name"},
                    "python_path": {"type": "string", "description": "Python executable path"},
                    "timeout": {"type": "number", "description": "Timeout in seconds"},
                },
                "required": ["operation"],
            },
        }

    def validate(self, params: Dict[str, Any]) -> List[str]:
        errors = []
        op = params.get("operation")
        if not op:
            errors.append("Missing required parameter: operation")
        elif op not in ("exec", "eval", "install", "create_venv", "list_packages"):
            errors.append(f"Unknown operation: {op}")

        if op in ("exec",) and "code" not in params:
            errors.append("Operation 'exec' requires 'code' parameter")

        if op == "install" and "packages" not in params:
            errors.append("Operation 'install' requires 'packages' parameter")

        if op in ("exec",) and params.get("code"):
            try:
                ast.parse(params["code"])
            except SyntaxError as e:
                errors.append(f"Python syntax error: {e}")

        return errors

    def authorize(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        if self._cancelled:
            return ToolResult.fail("Execution cancelled")

        operation = params.get("operation")
        op_map = {
            "exec": self._exec_code,
            "eval": self._eval_expression,
            "install": self._install_packages,
            "create_venv": self._create_venv,
            "list_packages": self._list_packages,
        }

        handler = op_map.get(operation)
        if not handler:
            return ToolResult.fail(f"Unknown operation: {operation}")

        try:
            return handler(params)
        except Exception as e:
            logger.error("Python operation '%s' failed: %s", operation, e)
            return ToolResult.fail(f"{type(e).__name__}: {e}")

    def _get_python_path(self, params: Dict[str, Any]) -> str:
        venv_name = params.get("venv_name")
        if venv_name:
            venv_path = self._venv_base / venv_name
            if venv_path.exists():
                if sys.platform == "win32":
                    candidate = str(venv_path / "Scripts" / "python.exe")
                else:
                    candidate = str(venv_path / "bin" / "python")
                if os.path.exists(candidate):
                    return candidate
        return params.get("python_path", sys.executable)

    def _exec_code(self, params: Dict[str, Any]) -> ToolResult:
        code = params["code"]
        python_path = self._get_python_path(params)
        timeout = params.get("timeout", 30)

        wrapped = textwrap.dedent(f"""\
        import sys, json, traceback
        try:
            exec_loc = {{}}
            exec(compile({json.dumps(code)}, '<exec>', 'exec'), exec_loc)
            output = {{
                "success": True,
                "result": str(exec_loc.get("result", None)),
                "locals": {{k: str(v) for k, v in exec_loc.items() if not k.startswith("_")}}
            }}
        except Exception:
            output = {{
                "success": False,
                "error": traceback.format_exc()
            }}
        json.dump(output, sys.stdout)
        """)

        try:
            result = subprocess.run(
                [python_path, "-c", wrapped],
                capture_output=True, text=True,
                timeout=timeout,
            )
            stdout = result.stdout
            stderr = result.stderr

            try:
                output = json.loads(stdout)
            except json.JSONDecodeError:
                output = {"stdout": stdout[:500], "stderr": stderr[:500]}

            if output.get("success", False):
                return ToolResult.ok(output)
            return ToolResult.fail(output.get("error", "Execution failed"), output=output)

        except subprocess.TimeoutExpired:
            return ToolResult.timeout(f"Python execution timed out after {timeout}s")
        except Exception as e:
            return ToolResult.fail(f"Execution error: {e}")

    def _eval_expression(self, params: Dict[str, Any]) -> ToolResult:
        expression = params.get("expression", "")
        python_path = self._get_python_path(params)
        timeout = params.get("timeout", 15)

        wrapped = textwrap.dedent(f"""\
        import sys, json, traceback
        try:
            result = eval({json.dumps(expression)})
            print(json.dumps({{"success": True, "result": str(result), "type": type(result).__name__}}))
        except Exception:
            print(json.dumps({{"success": False, "error": traceback.format_exc()}}))
        """)

        try:
            result = subprocess.run(
                [python_path, "-c", wrapped],
                capture_output=True, text=True,
                timeout=timeout,
            )
            output = json.loads(result.stdout.strip())
            if output.get("success", False):
                return ToolResult.ok(output)
            return ToolResult.fail(output.get("error", "Eval failed"), output=output)
        except Exception as e:
            return ToolResult.fail(f"Eval error: {e}")

    def _install_packages(self, params: Dict[str, Any]) -> ToolResult:
        packages = params.get("packages", [])
        python_path = self._get_python_path(params)
        timeout = params.get("timeout", 120)

        if not packages:
            return ToolResult.fail("No packages specified")

        cmd = [python_path, "-m", "pip", "install"] + packages
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
            )
            if result.returncode == 0:
                return ToolResult.ok({
                    "installed": packages,
                    "stdout": result.stdout[:500],
                })
            return ToolResult.fail(
                f"pip install failed (code {result.returncode}): {result.stderr[:500]}",
            )
        except subprocess.TimeoutExpired:
            return ToolResult.timeout(f"Package installation timed out after {timeout}s")
        except Exception as e:
            return ToolResult.fail(f"Install error: {e}")

    def _create_venv(self, params: Dict[str, Any]) -> ToolResult:
        venv_name = params.get("venv_name", f"venv_{int(time.time())}")
        venv_path = self._venv_base / venv_name

        try:
            venv_module.create(str(venv_path), with_pip=True)
            return ToolResult.ok({
                "venv_name": venv_name,
                "path": str(venv_path),
                "python": str(venv_path / ("Scripts" if sys.platform == "win32" else "bin") / "python"),
            })
        except Exception as e:
            return ToolResult.fail(f"Virtual environment creation failed: {e}")

    def _list_packages(self, params: Dict[str, Any]) -> ToolResult:
        python_path = self._get_python_path(params)
        try:
            result = subprocess.run(
                [python_path, "-m", "pip", "list", "--format=json"],
                capture_output=True, text=True, timeout=30,
            )
            packages = json.loads(result.stdout)
            return ToolResult.ok({
                "packages": packages,
                "count": len(packages),
                "python": python_path,
            })
        except Exception as e:
            return ToolResult.fail(f"Failed to list packages: {e}")

    def health(self) -> Dict[str, Any]:
        base = super().health()
        base["python_version"] = sys.version
        base["venv_base"] = str(self._venv_base)
        return base
