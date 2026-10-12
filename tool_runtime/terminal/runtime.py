"""Terminal Runtime — real multi-shell command execution.

Supports: PowerShell, Command Prompt, Bash, Zsh, Fish.
All execution is real — no fake output, no simulation.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
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


def _detect_shells() -> Dict[str, str]:
    """Detect available shells on the current system."""
    shells: Dict[str, str] = {}
    is_windows = platform.system() == "Windows"

    if is_windows:
        shells["powershell"] = "powershell.exe"
        shells["pwsh"] = "pwsh.exe"
        shells["cmd"] = "cmd.exe"
    else:
        for shell, path in [
            ("bash", "/bin/bash"),
            ("zsh", "/bin/zsh"),
            ("fish", "/usr/local/bin/fish"),
            ("sh", "/bin/sh"),
        ]:
            if os.path.exists(path):
                shells[shell] = path
        if not shells:
            shells["sh"] = "/bin/sh"

    return shells


class TerminalRuntime(ToolInterface):
    """Multi-shell terminal runtime.

    Executes commands in real subprocesses with:
    - Streaming output
    - Timeout handling
    - Cancellation support
    - Exit code capture
    - History tracking
    """

    def __init__(self):
        meta = ToolMetadata(
            id="terminal",
            name="Terminal Runtime",
            description="Execute shell commands in PowerShell, CMD, Bash, Zsh, or Fish",
            category=ToolCategory.TERMINAL,
            risk_level=ToolRiskLevel.EXECUTE,
            version="2.0.0",
            tags=["shell", "terminal", "execution"],
            requires_approval=False,
            timeout_seconds=120.0,
        )
        super().__init__(meta)
        self._available_shells = _detect_shells()
        self._processes: Dict[str, subprocess.Popen] = {}
        self._proc_lock = threading.Lock()
        self._history: List[Dict[str, Any]] = []

    def schema(self) -> Dict[str, Any]:
        return {
            "name": "terminal",
            "description": self.description(),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to execute"},
                    "shell": {
                        "type": "string",
                        "enum": list(self._available_shells.keys()) + ["auto"],
                        "description": "Shell to use (auto = detect best available)",
                    },
                    "workdir": {"type": "string", "description": "Working directory"},
                    "timeout": {
                        "type": "number",
                        "description": "Timeout in seconds (default 120)",
                    },
                    "env": {
                        "type": "object",
                        "description": "Additional environment variables",
                    },
                    "capture_output": {
                        "type": "boolean",
                        "description": "Capture stdout/stderr (default true)",
                    },
                    "stream": {
                        "type": "boolean",
                        "description": "Enable streaming output (default false)",
                    },
                },
                "required": ["command"],
            },
        }

    def validate(self, params: Dict[str, Any]) -> List[str]:
        errors = []
        if "command" not in params:
            errors.append("Missing required parameter: command")
        shell = params.get("shell", "auto")
        if shell != "auto" and shell not in self._available_shells:
            avail = ", ".join(self._available_shells.keys())
            errors.append(f"Shell '{shell}' not available. Available: {avail}")
        return errors

    def authorize(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        if self._cancelled:
            return ToolResult.fail("Execution cancelled")

        command = params["command"]
        shell_name = params.get("shell", "auto")
        workdir = params.get("workdir")
        timeout = params.get("timeout", self._metadata.timeout_seconds)
        env_add = params.get("env", {})
        capture = params.get("capture_output", True)

        if shell_name == "auto":
            shell_name = self._detect_best_shell()

        shell_path = self._available_shells.get(shell_name)
        if not shell_path:
            return ToolResult.fail(f"Shell '{shell_name}' not detected on this system")

        cwd = None
        if workdir:
            cwd = Path(workdir).resolve()
            if not cwd.exists():
                return ToolResult.fail(f"Working directory does not exist: {cwd}")

        env = os.environ.copy()
        env.update(env_add)

        exec_id = f"term_{int(time.time() * 1000)}"
        proc = self._launch_process(shell_name, shell_path, command, cwd, env)
        if not proc:
            return ToolResult.fail(f"Failed to launch shell: {shell_name}")

        with self._proc_lock:
            self._processes[exec_id] = proc

        stdout_data = []
        stderr_data = []
        start = time.time()

        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            elapsed = (time.time() - start) * 1000

            if stdout:
                stdout_data.append(stdout.decode("utf-8", errors="replace"))
            if stderr:
                stderr_data.append(stderr.decode("utf-8", errors="replace"))

            exit_code = proc.returncode
            stdout_str = "".join(stdout_data)
            stderr_str = "".join(stderr_data)

            result_data = {
                "exit_code": exit_code,
                "stdout": stdout_str if capture else f"[{len(stdout_str)} chars captured]",
                "stderr": stderr_str if capture else f"[{len(stderr_str)} chars captured]",
                "shell": shell_name,
                "command": command,
            }

            history_entry = {
                "exec_id": exec_id,
                "command": command[:200],
                "shell": shell_name,
                "exit_code": exit_code,
                "duration_ms": elapsed,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._history.append(history_entry)

            if exit_code == 0:
                return ToolResult.ok(result_data, duration_ms=elapsed)
            else:
                return ToolResult(
                    success=False,
                    output=result_data,
                    error=f"Command exited with code {exit_code}",
                    duration_ms=elapsed,
                    status=ToolStatus.FAILED,
                )

        except subprocess.TimeoutExpired:
            with self._proc_lock:
                if exec_id in self._processes:
                    self._kill_process(proc)
            elapsed = (time.time() - start) * 1000
            return ToolResult(
                success=False,
                output={"command": command, "shell": shell_name, "timeout": timeout},
                error=f"Command timed out after {timeout}s",
                duration_ms=elapsed,
                status=ToolStatus.TIMEOUT,
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return ToolResult.fail(f"Execution error: {type(e).__name__}: {e}", duration_ms=elapsed)
        finally:
            with self._proc_lock:
                self._processes.pop(exec_id, None)

    def cancel(self) -> bool:
        self._cancelled = True
        with self._proc_lock:
            for exec_id, proc in list(self._processes.items()):
                self._kill_process(proc)
            self._processes.clear()
        return True

    def _detect_best_shell(self) -> str:
        if "powershell" in self._available_shells:
            return "powershell"
        if "pwsh" in self._available_shells:
            return "pwsh"
        if "bash" in self._available_shells:
            return "bash"
        if "zsh" in self._available_shells:
            return "zsh"
        if "cmd" in self._available_shells:
            return "cmd"
        if "sh" in self._available_shells:
            return "sh"
        return "powershell"

    def _launch_process(
        self,
        shell_name: str,
        shell_path: str,
        command: str,
        cwd: Optional[Path],
        env: Dict[str, str],
    ) -> Optional[subprocess.Popen]:
        try:
            if shell_name in ("powershell", "pwsh"):
                cmd = [shell_path, "-NoProfile", "-Command", command]
            elif shell_name == "cmd":
                cmd = [shell_path, "/C", command]
            elif shell_name in ("bash", "zsh", "sh", "fish"):
                cmd = [shell_path, "-c", command]
            else:
                cmd = [shell_path, "-c", command]

            return subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                cwd=str(cwd) if cwd else None,
                env=env,
                shell=False,
            )
        except Exception as e:
            logger.error("Failed to launch process: %s", e)
            return None

    def _kill_process(self, proc: subprocess.Popen) -> None:
        try:
            if platform.system() == "Windows":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True, timeout=5,
                )
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            proc.kill()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def health(self) -> Dict[str, Any]:
        base = super().health()
        base["available_shells"] = list(self._available_shells.keys())
        base["active_processes"] = len(self._processes)
        base["history_count"] = len(self._history)
        return base

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._history)
