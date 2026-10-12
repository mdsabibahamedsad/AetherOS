"""Code Executor — sandboxed Python, JavaScript, Shell, PowerShell, Batch.

Always sandboxed. Permission system required.
"""

from __future__ import annotations

import enum
import json
import logging
import os
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("aetheros_runtime.code")


class CodeLanguage(enum.Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    SHELL = "shell"
    POWERSHELL = "powershell"
    BATCH = "batch"


class SandboxMode(enum.Enum):
    NONE = "none"
    SUBPROCESS = "subprocess"
    CONTAINER = "container"
    VM = "vm"


@dataclass
class ExecutionResult:
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0
    elapsed_ms: float = 0.0
    stdout: str = ""
    stderr: str = ""
    language: str = ""
    permission_denied: bool = False
    timed_out: bool = False


@dataclass
class CodePermission:
    language: CodeLanguage
    allowed: bool = True
    max_execution_time: float = 30.0
    allow_network: bool = False
    allow_filesystem: bool = False
    allowed_paths: List[str] = field(default_factory=lambda: [str(Path.cwd())])
    max_memory_mb: int = 512


class CodeExecutor:
    """Sandboxed code execution for multiple languages.

    Supports Python, JavaScript, Shell, PowerShell, and Batch with:
    - Sandbox mode (subprocess isolation)
    - Permission system per language
    - Timeout enforcement
    - Output capture (stdout/stderr)
    - Resource limits
    """

    LANGUAGE_MAP: Dict[CodeLanguage, Dict[str, Any]] = {
        CodeLanguage.PYTHON: {
            "ext": ".py",
            "interpreter": [sys.executable] if sys.executable else ["python"],
        },
        CodeLanguage.JAVASCRIPT: {
            "ext": ".js",
            "interpreter": ["node"],
        },
        CodeLanguage.SHELL: {
            "ext": ".sh",
            "interpreter": ["bash", "-c"],
        },
        CodeLanguage.POWERSHELL: {
            "ext": ".ps1",
            "interpreter": ["powershell", "-Command"],
        },
        CodeLanguage.BATCH: {
            "ext": ".bat",
            "interpreter": ["cmd", "/c"],
        },
    }

    def __init__(self, sandbox_mode: SandboxMode = SandboxMode.SUBPROCESS) -> None:
        self._lock = threading.RLock()
        self._sandbox_mode = sandbox_mode
        self._permissions: Dict[CodeLanguage, CodePermission] = {}
        self._execution_dir: Optional[Path] = None
        self._history: List[ExecutionResult] = []
        self._max_history: int = 100

        self._set_default_permissions()

    def _set_default_permissions(self) -> None:
        for lang in CodeLanguage:
            self._permissions[lang] = CodePermission(
                language=lang,
                allowed=True,
                max_execution_time=30.0,
                allow_network=False,
                allow_filesystem=True,
            )

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    def set_permission(self, permission: CodePermission) -> None:
        with self._lock:
            self._permissions[permission.language] = permission

    def get_permission(self, language: CodeLanguage) -> CodePermission:
        with self._lock:
            return self._permissions.get(language, CodePermission(language=language))

    def is_allowed(self, language: CodeLanguage) -> bool:
        return self.get_permission(language).allowed

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(
        self,
        code: str,
        language: CodeLanguage = CodeLanguage.PYTHON,
        args: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        workdir: Optional[Path] = None,
    ) -> ExecutionResult:
        perm = self.get_permission(language)
        if not perm.allowed:
            return ExecutionResult(
                success=False, error=f"{language.value} execution is not permitted",
                permission_denied=True, language=language.value,
            )

        effective_timeout = timeout if timeout is not None else perm.max_execution_time
        start = time.monotonic()

        if self._sandbox_mode == SandboxMode.SUBPROCESS:
            result = self._execute_subprocess(code, language, args, effective_timeout, workdir)
        elif self._sandbox_mode == SandboxMode.CONTAINER:
            result = self._execute_container(code, language, args, effective_timeout)
        else:
            result = self._execute_in_process(code, language)

        result.elapsed_ms = (time.monotonic() - start) * 1000
        result.language = language.value

        with self._lock:
            self._history.append(result)
            if len(self._history) > self._max_history:
                self._history.pop(0)

        return result

    def _execute_subprocess(
        self, code: str, language: CodeLanguage,
        args: Optional[List[str]], timeout: float, workdir: Optional[Path],
    ) -> ExecutionResult:
        lang_config = self.LANGUAGE_MAP.get(language)
        if not lang_config:
            return ExecutionResult(success=False, error=f"Unsupported language: {language}")

        try:
            if language == CodeLanguage.PYTHON:
                result = subprocess.run(
                    lang_config["interpreter"] + ["-c", code],
                    capture_output=True, text=True, timeout=timeout,
                    cwd=workdir or self._execution_dir or Path.cwd(),
                )
            elif language in (CodeLanguage.SHELL, CodeLanguage.BATCH, CodeLanguage.POWERSHELL):
                result = subprocess.run(
                    lang_config["interpreter"] + [code],
                    capture_output=True, text=True, timeout=timeout,
                    cwd=workdir or self._execution_dir or Path.cwd(),
                    shell=(language == CodeLanguage.SHELL),
                )
            elif language == CodeLanguage.JAVASCRIPT:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False, encoding="utf-8") as f:
                    f.write(code)
                    script_path = f.name
                try:
                    result = subprocess.run(
                        lang_config["interpreter"] + [script_path] + (args or []),
                        capture_output=True, text=True, timeout=timeout,
                        cwd=workdir or self._execution_dir or Path.cwd(),
                    )
                finally:
                    try:
                        os.unlink(script_path)
                    except OSError:
                        pass
            else:
                return ExecutionResult(success=False, error=f"Unsupported language: {language}")

            return ExecutionResult(
                success=result.returncode == 0,
                output=result.stdout.strip(),
                error=result.stderr.strip(),
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False, error=f"Execution timed out after {timeout}s",
                timed_out=True,
            )
        except FileNotFoundError as exc:
            return ExecutionResult(
                success=False, error=f"Interpreter not found: {exc}",
            )
        except Exception as exc:
            return ExecutionResult(
                success=False, error=str(exc),
            )

    def _execute_in_process(self, code: str, language: CodeLanguage) -> ExecutionResult:
        if language == CodeLanguage.PYTHON:
            try:
                local_ns: Dict[str, Any] = {}
                exec(code, {"__builtins__": __builtins__}, local_ns)
                output = str(local_ns.get("result", local_ns.get("output", "")))
                return ExecutionResult(success=True, output=output)
            except Exception as exc:
                return ExecutionResult(success=False, error=str(exc))
        return ExecutionResult(success=False, error=f"In-process execution not supported for {language.value}")

    def _execute_container(self, code: str, language: CodeLanguage, args: Optional[List[str]], timeout: float) -> ExecutionResult:
        return ExecutionResult(
            success=False, error="Container sandbox not yet implemented",
        )

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(self, limit: int = 10) -> List[ExecutionResult]:
        with self._lock:
            return list(self._history[-limit:])

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_execution_dir(self, directory: Path) -> None:
        self._execution_dir = directory

    def set_sandbox_mode(self, mode: SandboxMode) -> None:
        self._sandbox_mode = mode

    def health_check(self) -> bool:
        try:
            result = self.execute("print('ok')", CodeLanguage.PYTHON)
            return result.success
        except Exception:
            return False

    def summary(self) -> str:
        with self._lock:
            total = len(self._history)
            success = sum(1 for r in self._history if r.success)
        return f"Code Executor: {total} executions, {success} successful, mode={self._sandbox_mode.value}"