from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

from aetheros_automation.agents.registry import AgentRegistry, BaseAgent
from aetheros_automation.models.models import AgentRole, Task

logger = logging.getLogger(__name__)


class QAAgent(BaseAgent):
    @property
    def role(self) -> AgentRole:
        return AgentRole.QA

    async def execute(self, task: Task, context: dict | None = None) -> str:
        ctx = context or {}
        logger.info("QA agent executing: %s", task.name)

        code_path = task.metadata.get("code_path", "")
        if code_path:
            result = await self.run_tests(code_path)
            return self._format_test_result(result)

        actual = task.metadata.get("actual", "")
        expected = task.metadata.get("expected", "")
        if actual and expected:
            match = await self.validate_output(actual, expected)
            return f"Validation result: {'PASS' if match else 'FAIL'}"

        return "No test path or validation data provided."

    async def run_tests(self, code_path: str) -> dict:
        logger.info("Running tests at: %s", code_path)
        path = Path(code_path)

        if not path.exists():
            return {"success": False, "error": f"Path not found: {code_path}"}

        if path.is_file():
            return await self._run_single_test(path)

        results: dict[str, dict] = {}
        for test_file in sorted(path.rglob("test_*.py")):
            results[test_file.name] = await self._run_single_test(test_file)
            if not results[test_file.name]["success"]:
                logger.warning("Test failed in %s", test_file.name)

        passed = sum(1 for r in results.values() if r["success"])
        total = len(results)
        return {
            "success": passed == total,
            "passed": passed,
            "failed": total - passed,
            "total": total,
            "results": results,
        }

    async def validate_output(self, actual: str, expected: str) -> bool:
        logger.info("Validating output")
        return actual.strip() == expected.strip()

    async def _run_single_test(self, path: Path) -> dict:
        logger.info("Running test file: %s", path.name)
        try:
            proc = await asyncio_create_subprocess(
                [sys.executable, "-m", "pytest", str(path), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout[-2000:] if proc.stdout else "",
                "stderr": proc.stderr[-2000:] if proc.stderr else "",
                "returncode": proc.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Test timed out after 120s"}
        except FileNotFoundError:
            try:
                result = subprocess.run(
                    [sys.executable, str(path)],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                return {
                    "success": result.returncode == 0,
                    "stdout": result.stdout[-2000:],
                    "stderr": result.stderr[-2000:],
                    "returncode": result.returncode,
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _format_test_result(self, result: dict) -> str:
        if "results" in result:
            lines = [f"# Test Results\nPassed: {result.get('passed', 0)}/{result.get('total', 0)}"]
            for name, r in result.get("results", {}).items():
                status = "PASS" if r["success"] else "FAIL"
                lines.append(f"\n{name}: {status}")
                if not r["success"]:
                    err = r.get("stderr") or r.get("error", "")
                    if err:
                        lines.append(f"  {err[:300]}")
            return "\n".join(lines)
        if result["success"]:
            return f"Tests passed.\n{result.get('stdout', '')[:500]}"
        return f"Tests failed.\n{result.get('stderr', '')[:500]}"


async def asyncio_create_subprocess(
    cmd: list[str],
    capture_output: bool = True,
    text: bool = True,
    timeout: float = 120,
) -> subprocess.CompletedProcess:
    import asyncio
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE if capture_output else None,
        stderr=asyncio.subprocess.PIPE if capture_output else None,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise subprocess.TimeoutExpired(cmd, timeout)
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=proc.returncode or 0,
        stdout=stdout.decode("utf-8", errors="replace") if text and stdout else stdout,
        stderr=stderr.decode("utf-8", errors="replace") if text and stderr else stderr,
    )


AgentRegistry.register(AgentRole.QA, QAAgent)
