from __future__ import annotations

import asyncio
import logging
import os
import shlex
import subprocess
import time
from typing import Any

logger = logging.getLogger(__name__)


class Sandbox:
    """Execute shell commands in a restricted sandbox.

    Uses :class:`asyncio.subprocess` under the hood and rejects a
    hard-coded set of destructive commands before they reach the shell.
    """

    _BLOCKED_COMMANDS: list[str] = [
        "rm -rf /",
        "rm -rf /*",
        "format",
        "dd if=",
        "mkfs",
        ":(){ :|:& };:",
        "shutdown -h now",
        "reboot",
        "shutdown -r now",
        "poweroff",
        "halt",
        "init 0",
        "init 6",
        "mkfs.ext4",
        "mkfs.ntfs",
        "fdisk",
        "parted",
        "mkswap",
        "dd if=/dev/zero",
        "dd if=/dev/urandom",
        "> /dev/sda",
        "> /dev/sdb",
        "chmod -R 000 /",
        "chown -R root:root /",
    ]

    def __init__(self) -> None:
        self._running_processes: dict[str, asyncio.subprocess.Process] = {}
        self._executor = None

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    async def execute_in_sandbox(
        self,
        command: str,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Execute *command* inside the sandbox with a *timeout*.

        Returns a dict with keys ``returncode``, ``stdout``, ``stderr``,
        ``timed_out``, and ``duration``.
        """
        safe = await self.check_command_safety(command)
        if not safe:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"Command blocked by sandbox: {command}",
                "timed_out": False,
                "duration": 0.0,
            }

        start = time.monotonic()
        process_id = f"sandbox_{int(start)}_{id(command)}"

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
            )
            self._running_processes[process_id] = proc

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout,
                )
                timed_out = False
            except asyncio.TimeoutError:
                proc.kill()
                stdout, stderr = await proc.communicate()
                timed_out = True

            duration = time.monotonic() - start
            return {
                "returncode": proc.returncode or -1 if timed_out else proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace") if stdout else "",
                "stderr": stderr.decode("utf-8", errors="replace") if stderr else "",
                "timed_out": timed_out,
                "duration": round(duration, 3),
            }
        except Exception as exc:
            logger.exception("Sandbox execution failed for command: %s", command)
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(exc),
                "timed_out": False,
                "duration": time.monotonic() - start,
            }
        finally:
            self._running_processes.pop(process_id, None)

    async def check_command_safety(self, command: str) -> bool:
        """Return ``False`` if *command* matches a blocked pattern."""
        cmd_lower = command.lower().strip()

        for blocked in self._BLOCKED_COMMANDS:
            if blocked in cmd_lower:
                logger.warning("Blocked dangerous command pattern: %s", blocked)
                return False

        destructive_patterns = [
            "rm -rf",
            "rm -r /",
            "rm --recursive /",
        ]
        for pat in destructive_patterns:
            if pat in cmd_lower:
                words = shlex.split(command)
                for i, w in enumerate(words):
                    if w in ("rm",):
                        flags = words[i + 1] if i + 1 < len(words) else ""
                        if "r" in flags and "f" in flags:
                            target = words[i + 2] if i + 2 < len(words) else ""
                            if target in ("/", "/*", "/.", "/.."):
                                logger.warning("Blocked destructive rm: %s", command)
                                return False

        return True

    async def run_safe(
        self,
        command: str,
        cwd: str | None = None,
    ) -> dict[str, Any]:
        """Convenience wrapper – passes through to :meth:`execute_in_sandbox`."""
        return await self.execute_in_sandbox(command, timeout=30.0)
