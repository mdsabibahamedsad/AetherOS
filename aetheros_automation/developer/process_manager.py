from __future__ import annotations
import asyncio, logging, os, signal, time, uuid
from typing import Any

logger = logging.getLogger(__name__)

class ProcessManager:
    def __init__(self):
        self._processes: dict[str, dict[str, Any]] = {}
        self._max_processes = 50

    async def start_process(self, command: list[str], cwd: str = "", env: dict[str, str] | None = None, name: str = "", sandbox_key: str = "") -> str:
        process_id = uuid.uuid4().hex[:12]
        actual_cwd = cwd or os.getcwd()
        merged_env = {**os.environ, **(env or {})}
        try:
            proc = await asyncio.create_subprocess_exec(*command, cwd=actual_cwd, env=merged_env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            entry = {"id": process_id, "name": name or command[0], "command": " ".join(command), "cwd": actual_cwd, "proc": proc, "pid": proc.pid, "status": "running", "started_at": time.time(), "cpu": 0.0, "memory": 0, "output_lines": [], "sandbox_key": sandbox_key}
            self._processes[process_id] = entry
            asyncio.create_task(self._collect_output(process_id, proc))
            logger.info("Started process %s: %s (PID %s)", process_id, command[0], proc.pid)
            return process_id
        except Exception as e:
            logger.error("Failed to start process: %s", e)
            raise

    async def _collect_output(self, process_id: str, proc: asyncio.subprocess.Process):
        entry = self._processes.get(process_id)
        if not entry:
            return
        async def read_stream(stream, key):
            async for line in stream:
                entry["output_lines"].append({"stream": key, "text": line.decode("utf-8", errors="replace").rstrip(), "time": time.time()})
                if len(entry["output_lines"]) > 10000:
                    entry["output_lines"] = entry["output_lines"][-5000:]
        await asyncio.gather(read_stream(proc.stdout, "stdout"), read_stream(proc.stderr, "stderr"))
        if entry["status"] == "running":
            entry["status"] = "exited"
            entry["exit_code"] = proc.returncode

    def stop_process(self, process_id: str, force: bool = False) -> bool:
        entry = self._processes.get(process_id)
        if not entry or entry["status"] != "running":
            return False
        proc = entry.get("proc")
        if proc:
            try:
                if force:
                    proc.kill()
                else:
                    proc.terminate()
                entry["status"] = "stopped"
                return True
            except Exception:
                pass
        return False

    def get_process(self, process_id: str) -> dict[str, Any] | None:
        entry = self._processes.get(process_id)
        if not entry:
            return None
        return {k: v for k, v in entry.items() if k != "proc"}

    def list_processes(self) -> list[dict[str, Any]]:
        return [{k: v for k, v in p.items() if k != "proc"} for p in self._processes.values()]

    def get_process_output(self, process_id: str, tail: int = 100) -> list[dict[str, Any]]:
        entry = self._processes.get(process_id)
        if not entry:
            return []
        return entry["output_lines"][-tail:]

    def cleanup_completed(self):
        to_remove = [pid for pid, p in self._processes.items() if p.get("status") in ("exited", "stopped", "failed")]
        for pid in to_remove:
            self._processes.pop(pid, None)
