"""Plugin sandbox — isolated execution environments for Python, Node.js, Rust, Go, WASM."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from hub.models import SandboxRuntime, Permission

logger = logging.getLogger(__name__)


class SandboxError(Exception):
    pass


@dataclass
class SandboxResult:
    success: bool = True
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    output: Any = None
    error: str = ""
    duration: float = 0.0


class Sandbox:
    def __init__(self, work_dir: Optional[str] = None):
        self.work_dir = Path(work_dir or tempfile.mkdtemp(prefix="aetheros_sandbox_"))
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self._allowed_paths: list[str] = [str(self.work_dir)]
        self._allowed_networks: list[str] = []
        self._timeout: int = 30

    def restrict_paths(self, paths: list[str]) -> None:
        self._allowed_paths = paths

    def restrict_networks(self, networks: list[str]) -> None:
        self._allowed_networks = networks

    def set_timeout(self, seconds: int) -> None:
        self._timeout = seconds

    def write_file(self, path: str, content: str) -> str:
        full_path = self.work_dir / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        return str(full_path)

    def read_file(self, path: str) -> str:
        full_path = self._resolve_path(path)
        return full_path.read_text()

    def _resolve_path(self, path: str) -> Path:
        p = Path(path)
        if not p.is_absolute():
            p = self.work_dir / p
        p = p.resolve()
        for allowed in self._allowed_paths:
            if str(p).startswith(os.path.normpath(allowed)):
                return p
        raise SandboxError(f"Path not allowed: {path}")

    def clean(self) -> None:
        shutil.rmtree(self.work_dir, ignore_errors=True)


class PythonSandbox(Sandbox):
    async def execute(self, code: str, env: dict = None) -> SandboxResult:
        import time
        start = time.time()
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-c", code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **(env or {}),
                     "PYTHONPATH": str(self.work_dir)},
                cwd=str(self.work_dir),
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout)
            elapsed = time.time() - start
            return SandboxResult(
                success=proc.returncode == 0, stdout=stdout.decode(),
                stderr=stderr.decode(), returncode=proc.returncode or 0,
                duration=elapsed)
        except asyncio.TimeoutError:
            return SandboxResult(success=False, error="Timed out",
                                 duration=time.time() - start)
        except Exception as e:
            return SandboxResult(success=False, error=str(e),
                                 duration=time.time() - start)

    async def execute_file(self, file_path: str, args: list = None) -> SandboxResult:
        import time
        start = time.time()
        full_path = self._resolve_path(file_path)
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, str(full_path), *(args or []),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.work_dir),
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout)
            elapsed = time.time() - start
            return SandboxResult(
                success=proc.returncode == 0, stdout=stdout.decode(),
                stderr=stderr.decode(), returncode=proc.returncode or 0,
                duration=elapsed)
        except asyncio.TimeoutError:
            return SandboxResult(success=False, error="Timed out",
                                 duration=time.time() - start)


class NodeSandbox(Sandbox):
    async def execute(self, code: str, env: dict = None) -> SandboxResult:
        import time
        start = time.time()
        try:
            proc = await asyncio.create_subprocess_exec(
                "node", "-e", code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **(env or {})},
                cwd=str(self.work_dir),
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout)
            elapsed = time.time() - start
            return SandboxResult(
                success=proc.returncode == 0, stdout=stdout.decode(),
                stderr=stderr.decode(), returncode=proc.returncode or 0,
                duration=elapsed)
        except FileNotFoundError:
            return SandboxResult(success=False, error="Node.js not found")
        except asyncio.TimeoutError:
            return SandboxResult(success=False, error="Timed out",
                                 duration=time.time() - start)

    async def execute_file(self, file_path: str, args: list = None,
                           env: dict = None) -> SandboxResult:
        import time
        start = time.time()
        full_path = self._resolve_path(file_path)
        try:
            proc = await asyncio.create_subprocess_exec(
                "node", str(full_path), *(args or []),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **(env or {})},
                cwd=str(self.work_dir),
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout)
            elapsed = time.time() - start
            return SandboxResult(
                success=proc.returncode == 0, stdout=stdout.decode(),
                stderr=stderr.decode(), returncode=proc.returncode or 0,
                duration=elapsed)
        except FileNotFoundError:
            return SandboxResult(success=False, error="Node.js not found")
        except asyncio.TimeoutError:
            return SandboxResult(success=False, error="Timed out",
                                 duration=time.time() - start)


class RustSandbox(Sandbox):
    async def execute(self, code: str, env: dict = None) -> SandboxResult:
        src_file = self.write_file("main.rs", code)
        import time, tempfile
        out_file = str(self.work_dir / "program")
        start = time.time()
        try:
            compile_proc = await asyncio.create_subprocess_exec(
                "rustc", src_file, "-o", out_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.work_dir),
            )
            _, stderr = await asyncio.wait_for(
                compile_proc.communicate(), timeout=self._timeout)
            if compile_proc.returncode != 0:
                return SandboxResult(success=False, stderr=stderr.decode(),
                                     error="Compilation failed")
            proc = await asyncio.create_subprocess_exec(
                out_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **(env or {})},
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout)
            elapsed = time.time() - start
            return SandboxResult(success=proc.returncode == 0,
                                 stdout=stdout.decode(), stderr=stderr.decode(),
                                 returncode=proc.returncode or 0, duration=elapsed)
        except FileNotFoundError:
            return SandboxResult(success=False, error="rustc not found")
        except asyncio.TimeoutError:
            return SandboxResult(success=False, error="Timed out",
                                 duration=time.time() - start)


class GoSandbox(Sandbox):
    async def execute(self, code: str, env: dict = None) -> SandboxResult:
        src_file = self.write_file("main.go", code)
        import time
        start = time.time()
        try:
            proc = await asyncio.create_subprocess_exec(
                "go", "run", src_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **(env or {})},
                cwd=str(self.work_dir),
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout)
            elapsed = time.time() - start
            return SandboxResult(success=proc.returncode == 0,
                                 stdout=stdout.decode(), stderr=stderr.decode(),
                                 returncode=proc.returncode or 0, duration=elapsed)
        except FileNotFoundError:
            return SandboxResult(success=False, error="Go not found")
        except asyncio.TimeoutError:
            return SandboxResult(success=False, error="Timed out",
                                 duration=time.time() - start)


class WASMSandbox(Sandbox):
    async def execute(self, wasm_bytes: bytes, env: dict = None) -> SandboxResult:
        import time
        start = time.time()
        try:
            proc = await asyncio.create_subprocess_exec(
                "wasmtime", "run", "--dir", str(self.work_dir), "-",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **(env or {})},
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=wasm_bytes), timeout=self._timeout)
            elapsed = time.time() - start
            return SandboxResult(success=proc.returncode == 0,
                                 stdout=stdout.decode(), stderr=stderr.decode(),
                                 returncode=proc.returncode or 0, duration=elapsed)
        except FileNotFoundError:
            return SandboxResult(success=False, error="wasmtime not found")
        except asyncio.TimeoutError:
            return SandboxResult(success=False, error="Timed out",
                                 duration=time.time() - start)


class SandboxManager:
    _runtimes: dict[str, type[Sandbox]] = {
        "python": PythonSandbox,
        "node": NodeSandbox,
        "rust": RustSandbox,
        "go": GoSandbox,
        "wasm": WASMSandbox,
    }

    @classmethod
    def create(cls, runtime: str, **kwargs) -> Sandbox:
        runtime_cls = cls._runtimes.get(runtime)
        if not runtime_cls:
            runtime_cls = PythonSandbox
        return runtime_cls(**kwargs)

    @classmethod
    async def execute_in_sandbox(cls, runtime: str, code: str,
                                  permissions: list[Permission] = None,
                                  env: dict = None,
                                  timeout: int = 30) -> SandboxResult:
        sandbox = cls.create(runtime)
        sandbox.set_timeout(timeout)
        try:
            return await sandbox.execute(code, env)
        finally:
            sandbox.clean()
