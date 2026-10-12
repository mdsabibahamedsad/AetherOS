from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class TerminalRunner:
    """Run shell commands asynchronously with output capture, streaming, and retry support."""

    @staticmethod
    async def run(
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float = 300.0,
        shell: bool | None = None,
    ) -> dict[str, Any]:
        if shell is None:
            shell = sys.platform == "win32"
        resolved_env = {**os.environ, **(env or {})}
        logger.debug("run: %s (cwd=%s, timeout=%s)", command, cwd, timeout)

        if shell:
            args = command if sys.platform == "win32" else ["sh", "-c", command]
            if sys.platform == "win32":
                proc = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=resolved_env,
                )
            else:
                proc = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=resolved_env,
                )
        else:
            parts = _parse_command(command)
            proc = await asyncio.create_subprocess_exec(
                *parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=resolved_env,
            )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "exit_code": -1,
                "timed_out": True,
            }

        return {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "exit_code": proc.returncode or 0,
            "timed_out": False,
        }

    @staticmethod
    async def run_stream(
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        on_output: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        shell = sys.platform == "win32"
        resolved_env = {**os.environ, **(env or {})}
        logger.debug("run_stream: %s", command)

        if shell:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=resolved_env,
            )
        else:
            parts = _parse_command(command)
            proc = await asyncio.create_subprocess_exec(
                *parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=resolved_env,
            )

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        async def _read_stream(
            stream: asyncio.StreamReader,
            lines: list[str],
            label: str,
        ) -> None:
            while True:
                line_bytes = await stream.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="replace").rstrip()
                lines.append(line)
                if on_output:
                    on_output(line)

        await asyncio.gather(
            _read_stream(proc.stdout, stdout_lines, "stdout"),
            _read_stream(proc.stderr, stderr_lines, "stderr"),
        )
        await proc.wait()

        return {
            "stdout": "\n".join(stdout_lines),
            "stderr": "\n".join(stderr_lines),
            "exit_code": proc.returncode or 0,
        }

    @staticmethod
    async def retry(
        command: str,
        max_retries: int = 3,
        delay: float = 1.0,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float = 300.0,
    ) -> dict[str, Any]:
        last_result: dict[str, Any] = {}
        for attempt in range(1, max_retries + 1):
            logger.debug("retry attempt %d/%d: %s", attempt, max_retries, command)
            result = await TerminalRunner.run(command, cwd=cwd, env=env, timeout=timeout)
            last_result = result
            if result["exit_code"] == 0:
                return result
            if attempt < max_retries:
                wait = delay * attempt
                logger.debug("retry waiting %.1fs before attempt %d", wait, attempt + 1)
                await asyncio.sleep(wait)

        last_result["retries"] = max_retries
        return last_result

    @staticmethod
    async def run_with_rollback(
        command: str,
        rollback_command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float = 300.0,
    ) -> dict[str, Any]:
        logger.debug("run_with_rollback: %s | rollback: %s", command, rollback_command)
        result = await TerminalRunner.run(command, cwd=cwd, env=env, timeout=timeout)

        if result["exit_code"] != 0:
            logger.info("Command failed; executing rollback: %s", rollback_command)
            rollback_result = await TerminalRunner.run(
                rollback_command, cwd=cwd, env=env, timeout=timeout
            )
            result["rollback_executed"] = True
            result["rollback_result"] = rollback_result
        else:
            result["rollback_executed"] = False

        return result

    @staticmethod
    async def capture_live_logs(
        command: str,
        callback: Callable[[str], None],
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Run a command and stream each output line to a callback in real time."""
        return await TerminalRunner.run_stream(
            command, cwd=cwd, env=env, on_output=callback
        )


def _parse_command(cmd: str) -> list[str]:
    """Split a command string into parts respecting quoted substrings."""
    import shlex
    return shlex.split(cmd)
