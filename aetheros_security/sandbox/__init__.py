"""
Secure Sandbox for AetherOS
===========================

Run plugins, MCP servers, agents, and automation tasks in isolated sandboxes.

Supported sandbox backends:
    - Firejail (Linux, when installed)
    - Docker / Podman (when available)
    - Resource limits (memory, CPU, execution time) on every platform
    - Filesystem isolation (allow/deny path lists + restricted temp dir)
    - Network policy (allow/deny host lists)

Usage::

    from aetheros_security.sandbox import SandboxManager, SandboxConfig

    manager = SandboxManager()
    config = SandboxConfig(name="my-plugin", max_memory_mb=256)
    with manager.create_sandbox(config) as sandbox:
        result = sandbox.execute("python script.py")
        print(result.output)
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:  # POSIX-only module; resource limits there, psutil fallback elsewhere
    import resource  # type: ignore
except ImportError:  # pragma: no cover - Windows
    resource = None  # type: ignore


class SandboxBackend(Enum):
    """Sandbox backend types."""
    FIREJAIL = "firejail"
    DOCKER = "docker"
    PODMAN = "podman"
    WINDOWS_SANDBOX = "windows_sandbox"
    MACOS_SANDBOX = "macos_sandbox"
    RESTRICTED_PYTHON = "restricted_python"
    NONE = "none"


class SandboxMode(Enum):
    """Sandbox isolation levels."""
    FULL = "full"           # Maximum isolation
    STANDARD = "standard"   # Balanced isolation
    RELAXED = "relaxed"     # Minimal isolation
    NONE = "none"           # No isolation (trusted code only)


@dataclass
class SandboxConfig:
    """Sandbox configuration."""
    name: str
    backend: SandboxBackend = SandboxBackend.RESTRICTED_PYTHON
    mode: SandboxMode = SandboxMode.STANDARD
    max_memory_mb: int = 512
    max_cpu_percent: float = 50.0
    max_execution_time: int = 300  # seconds
    allowed_paths: List[str] = field(default_factory=list)
    denied_paths: List[str] = field(default_factory=list)
    allowed_hosts: List[str] = field(default_factory=list)
    denied_hosts: List[str] = field(default_factory=list)
    network_access: bool = False
    filesystem_access: bool = True
    env_vars: Dict[str, str] = field(default_factory=dict)
    read_only: bool = False


@dataclass
class SandboxResult:
    """Result of sandbox execution."""
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0
    execution_time: float = 0.0
    memory_used: int = 0
    violations: List[str] = field(default_factory=list)


class Sandbox:
    """Isolated execution sandbox."""

    def __init__(self, config: SandboxConfig) -> None:
        self._config = config
        self._temp_dir: Optional[tempfile.TemporaryDirectory] = None
        self._active = False
        self._start_time: float = 0

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def config(self) -> SandboxConfig:
        return self._config

    def enter(self) -> None:
        """Enter the sandbox."""
        self._temp_dir = tempfile.TemporaryDirectory(
            prefix=f"aetheros-sandbox-{self._config.name}-",
        )
        self._active = True
        self._start_time = time.time()
        logger.info("Sandbox entered: %s", self._config.name)

    def exit(self) -> None:
        """Exit the sandbox."""
        self._active = False
        if self._temp_dir:
            self._temp_dir.cleanup()
            self._temp_dir = None
        logger.info("Sandbox exited: %s", self._config.name)

    def __enter__(self) -> "Sandbox":
        self.enter()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.exit()

    def check_path_allowed(self, path: str) -> bool:
        """Check if a path is allowed in the sandbox."""
        resolved = str(Path(path).resolve())

        # Deny takes precedence
        for denied in self._config.denied_paths:
            denied_resolved = str(Path(denied).resolve())
            if resolved == denied_resolved or resolved.startswith(denied_resolved + os.sep):
                return False

        # Allow list, when present, is exclusive
        if self._config.allowed_paths:
            for allowed in self._config.allowed_paths:
                allowed_resolved = str(Path(allowed).resolve())
                if resolved == allowed_resolved or resolved.startswith(allowed_resolved + os.sep):
                    return True
            return False

        return True

    def check_host_allowed(self, host: str) -> bool:
        """Check if a host is allowed."""
        if not self._config.network_access:
            return False
        if host in self._config.denied_hosts:
            return False
        if not self._config.allowed_hosts:
            return True
        return host in self._config.allowed_hosts

    def execute(
        self,
        command: str,
        *,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> SandboxResult:
        """Execute a command in the sandbox.

        Args:
            command: Command to execute.
            timeout: Execution timeout in seconds.
            env: Additional environment variables.

        Returns:
            Execution result.
        """
        if not self._active:
            return SandboxResult(success=False, error="Sandbox not active")

        timeout = timeout or self._config.max_execution_time
        start_time = time.time()

        # Check time limit
        if time.time() - self._start_time > self._config.max_execution_time:
            return SandboxResult(
                success=False,
                error="Sandbox time limit exceeded",
                violations=["time_limit_exceeded"],
            )

        # Prepare environment
        exec_env = os.environ.copy()
        exec_env.update(self._config.env_vars)
        if env:
            exec_env.update(env)
        if self._temp_dir:
            exec_env["SANDBOX_TEMP"] = self._temp_dir.name
            exec_env["SANDBOX_HOME"] = self._temp_dir.name
            if self._config.mode != SandboxMode.NONE:
                exec_env["HOME"] = self._temp_dir.name
                exec_env["TMPDIR"] = self._temp_dir.name
                exec_env["TEMP"] = self._temp_dir.name
                exec_env["TMP"] = self._temp_dir.name

        if self._config.mode == SandboxMode.NONE:
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=exec_env,
                )
            except subprocess.TimeoutExpired:
                return SandboxResult(
                    success=False,
                    error=f"Execution timed out after {timeout} seconds",
                    execution_time=float(timeout),
                    violations=["timeout"],
                )
            execution_time = time.time() - start_time
            return SandboxResult(
                success=result.returncode == 0,
                output=result.stdout or "",
                error=result.stderr or "",
                exit_code=result.returncode,
                execution_time=execution_time,
            )

        try:
            return self._restricted_execute(command, exec_env, timeout, start_time)
        except subprocess.TimeoutExpired:
            return SandboxResult(
                success=False,
                error=f"Execution timed out after {timeout} seconds",
                execution_time=float(timeout),
                violations=["timeout"],
            )
        except Exception as exc:
            return SandboxResult(
                success=False,
                error=str(exc),
                execution_time=time.time() - start_time,
            )

    # ------------------------------------------------------------------
    # Restricted execution
    # ------------------------------------------------------------------

    def _build_prefix(self) -> List[str]:
        """Build the OS-level sandbox command prefix if available."""
        if self._config.mode == SandboxMode.NONE:
            return []

        # Firejail (Linux) — best-effort namespace isolation
        if shutil.which("firejail") and self._config.backend in (
            SandboxBackend.FIREJAIL, SandboxBackend.RESTRICTED_PYTHON,
        ):
            prefix = ["firejail", "--quiet", "--net=none" if not self._config.network_access else "--net=eth0"]
            if self._config.allowed_hosts:
                prefix.append("--allow={}".format(",".join(self._config.allowed_hosts)))
            if self._config.max_memory_mb:
                prefix.append(f"--rlimit-as={self._config.max_memory_mb * 1024 * 1024}")
            if self._config.read_only:
                prefix.append("--private")
            if self._temp_dir:
                prefix.append(f"--private={self._temp_dir.name}")
            return prefix

        # Docker — full isolation when the daemon is available
        if shutil.which("docker") and self._config.backend in (
            SandboxBackend.DOCKER, SandboxBackend.RESTRICTED_PYTHON,
        ):
            prefix = ["docker", "run", "--rm", "-i"]
            prefix.append("--network=none" if not self._config.network_access else "--network=bridge")
            if self._config.max_memory_mb:
                prefix.append(f"--memory={self._config.max_memory_mb}m")
            if self._config.max_cpu_percent:
                prefix.append(f"--cpus={max(0.1, self._config.max_cpu_percent / 100.0):.2f}")
            if self._temp_dir:
                prefix.extend(["-v", f"{self._temp_dir.name}:/sandbox:rw"])
            prefix.append("alpine:latest")
            return prefix

        return []

    def _restricted_execute(
        self,
        command: str,
        env: Dict[str, str],
        timeout: int,
        start_time: float,
    ) -> SandboxResult:
        """Execute with resource limits and environment scrubbing.

        Cross-platform enforcement:
          - Sensitive env vars are stripped
          - Memory usage is monitored with psutil and the process is killed
            when it exceeds ``max_memory_mb``
          - POSIX rlimits are applied where available
          - A hard wall-clock timeout kills the process tree
        """
        restricted_env = {
            k: v for k, v in env.items()
            if not self._is_sensitive_env(k)
        }
        # Never let the child inherit AetherOS's own secrets
        restricted_env.pop("AETHEROS_API_KEY", None)
        restricted_env.pop("OPENAI_API_KEY", None)

        prefix = self._build_prefix()

        if prefix:
            full_cmd = prefix + [command]
            process = subprocess.Popen(
                full_cmd,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=restricted_env,
            )
        else:
            # Keep shell=True only for the unfirejailed path so existing
            # command strings (pipelines, env subs) keep working.
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=restricted_env,
                **self._posix_preexec(),
            )

        violations: List[str] = []
        max_mem_bytes = self._config.max_memory_mb * 1024 * 1024
        try:
            import psutil
        except ImportError:
            psutil = None  # type: ignore

        while True:
            ret = process.poll()
            if ret is not None:
                break
            if time.time() - start_time > timeout:
                violations.append("timeout")
                self._kill_tree(process)
                break
            if psutil is not None and max_mem_bytes > 0:
                try:
                    proc = psutil.Process(process.pid)
                    used = proc.memory_info().rss
                    # Account for children too
                    for child in proc.children(recursive=True):
                        used += child.memory_info().rss
                    if used > max_mem_bytes:
                        violations.append("memory_limit_exceeded")
                        self._kill_tree(process)
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            time.sleep(0.05)

        out, err = process.communicate(timeout=5)
        execution_time = time.time() - start_time
        memory_used = 0
        if psutil is not None:
            try:
                memory_used = psutil.Process(process.pid).memory_info().rss
            except Exception:
                pass

        return SandboxResult(
            success=process.returncode == 0 and not violations,
            output=out or "",
            error=err or "",
            exit_code=process.returncode or 0,
            execution_time=execution_time,
            memory_used=memory_used,
            violations=violations,
        )

    def _posix_preexec(self) -> Dict[str, Any]:
        """POSIX-only rlimit enforcement; no-op elsewhere."""
        if resource is None:
            return {}

        max_mem = self._config.max_memory_mb * 1024 * 1024

        def _limits() -> None:
            try:
                if max_mem > 0:
                    resource.setrlimit(resource.RLIMIT_AS, (max_mem, max_mem))
                resource.setrlimit(
                    resource.RLIMIT_CPU,
                    (max(1, self._config.max_execution_time), max(1, self._config.max_execution_time)),
                )
            except (ValueError, OSError):
                pass

        return {"preexec_fn": _limits}

    @staticmethod
    def _is_sensitive_env(name: str) -> bool:
        upper = name.upper()
        if any(tok in upper for tok in ("SECRET", "TOKEN", "API_KEY", "PASSWORD", "CREDENTIAL", "AUTH")):
            return True
        return upper.endswith("_KEY")

    @staticmethod
    def _kill_tree(process: subprocess.Popen) -> None:
        """Best-effort process-tree kill, cross-platform."""
        try:
            import psutil
            proc = psutil.Process(process.pid)
            children = proc.children(recursive=True)
            for child in children:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            proc.kill()
        except Exception:
            try:
                process.kill()
            except Exception:
                pass
        process.wait(timeout=5)


class SandboxManager:
    """Manages sandboxes for AetherOS.

    Usage::

        manager = SandboxManager()

        # Create a sandbox
        config = SandboxConfig(name="my-plugin", max_memory_mb=256)
        with manager.create_sandbox(config) as sandbox:
            result = sandbox.execute("python script.py")
            print(result.output)
    """

    def __init__(self) -> None:
        self._sandboxes: Dict[str, Sandbox] = {}
        self._active_sandbox: Optional[Sandbox] = None
        self._backend = self._detect_backend()

    def _detect_backend(self) -> SandboxBackend:
        """Detect available sandbox backend."""
        if sys.platform == "linux":
            if shutil.which("firejail"):
                return SandboxBackend.FIREJAIL
        if shutil.which("docker"):
            return SandboxBackend.DOCKER
        return SandboxBackend.RESTRICTED_PYTHON

    def create_sandbox(self, config: SandboxConfig) -> Sandbox:
        """Create a new sandbox."""
        if config.backend == SandboxBackend.NONE:
            pass
        elif self._backend in (SandboxBackend.FIREJAIL, SandboxBackend.DOCKER):
            # Use the strongest available backend unless overridden
            config.backend = self._backend
        sandbox = Sandbox(config)
        self._sandboxes[config.name] = sandbox
        return sandbox

    def get_sandbox(self, name: str) -> Optional[Sandbox]:
        """Get a sandbox by name."""
        return self._sandboxes.get(name)

    def destroy_sandbox(self, name: str) -> bool:
        """Destroy a sandbox."""
        sandbox = self._sandboxes.get(name)
        if sandbox:
            if sandbox.is_active:
                sandbox.exit()
            del self._sandboxes[name]
            return True
        return False

    def get_active_sandbox(self) -> Optional[Sandbox]:
        """Get the currently active sandbox."""
        return self._active_sandbox

    def list_sandboxes(self) -> List[Dict[str, Any]]:
        """List all sandboxes."""
        return [
            {
                "name": s.name,
                "active": s.is_active,
                "backend": s.config.backend.value,
                "mode": s.config.mode.value,
            }
            for s in self._sandboxes.values()
        ]

    def get_backend(self) -> str:
        """Get the current sandbox backend."""
        return self._backend.value

    def get_stats(self) -> Dict[str, Any]:
        """Get sandbox statistics."""
        return {
            "total_sandboxes": len(self._sandboxes),
            "active_sandboxes": sum(1 for s in self._sandboxes.values() if s.is_active),
            "backend": self._backend.value,
        }


# Global sandbox manager
_sandbox_manager: SandboxManager | None = None


def get_sandbox_manager() -> SandboxManager:
    """Return the global SandboxManager singleton."""
    global _sandbox_manager
    if _sandbox_manager is None:
        _sandbox_manager = SandboxManager()
    return _sandbox_manager
