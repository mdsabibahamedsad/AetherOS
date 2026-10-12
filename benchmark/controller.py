"""Benchmark controller (P1 pipeline, P45-46 traces, P29-30 repeats,
P17 fault injection hooks, P31 throughput) — persists everything to
``<results_dir>/{manifest.json, results.jsonl, traces/}``.

Anti-fabrication contract: every AgentResult written here originates from
either (a) an executed adapter run + validator verdict, or (b) a BLOCKED
record carrying the refusal reason. There is no code path that emits
scores without execution.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

from benchmark.adapters import (
    AgentAdapter,
    Health,
    blocked_result,
    get_adapter,
)
from benchmark.dataset import DATASET_VERSION, content_hash, load_tasks
from benchmark.environment import env_fingerprint, snapshot
from benchmark.schema import (
    BENCHMARK_VERSION,
    AgentResult,
    TaskSpec,
    TaskStatus,
    new_run_id,
)
from benchmark.validators import validate


class BenchmarkController:
    def __init__(self, results_dir: Path):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.trace_dir = self.results_dir / "traces"
        self.env = snapshot()
        self.env_ref = env_fingerprint(self.env)

    # ------------------------------------------------------------------ run

    def run_suite(
        self,
        agent_name: str,
        *,
        categories: Optional[List[str]] = None,
        task_ids: Optional[List[str]] = None,
        repeats_override: Optional[int] = None,
        allow_live: bool = False,
        fault_injector: Optional[Callable[[Dict], Dict]] = None,
        dataset_version: str = DATASET_VERSION,
        model: str = "unknown",
        provider: str = "unknown",
    ) -> Dict:
        """Run a suite for one agent; returns the run manifest."""
        adapter: AgentAdapter = get_adapter(agent_name)
        adapter.prepare()
        health = adapter.health_check()

        tasks = load_tasks(dataset_version)
        if categories:
            tasks = [t for t in tasks if t.category in categories]
        if task_ids:
            wanted = set(task_ids)
            tasks = [t for t in tasks if t.task_id in wanted]

        run_id = new_run_id("bmr")
        results: List[AgentResult] = []

        for task in tasks:
            reps = repeats_override or task.repeats
            if not health.runnable:
                results.append(blocked_result(
                    run_id, agent_name, task,
                    f"AGENT_NOT_RUNNABLE: {health.status}", health))
                continue
            if not allow_live:
                results.append(blocked_result(
                    run_id, agent_name, task,
                    "LIVE_EXECUTION_DISABLED: pass --allow-live to spend "
                    "tokens and execute real agent runs", health))
                continue

            for rep in range(reps):
                ws = self.results_dir / "workspaces" / f"{task.task_id}-{rep}"
                ws.mkdir(parents=True, exist_ok=True)
                spec_overrides = fault_injector(task.__dict__) \
                    if fault_injector else {}
                artifacts = adapter.run_task(task, ws, allow_live=True)
                if spec_overrides.get("_injected_failures"):
                    artifacts.setdefault("tool_calls", [])
                    artifacts["warnings"] = artifacts.get("warnings", []) + [
                        "fault injection active"]
                artifacts.setdefault("workspace", str(ws))
                verified, score, detail = validate(task.validator, artifacts)
                status = self._status(artifacts, verified, score)
                trace_ref = adapter.collect_trace(
                    task.task_id, {**artifacts, "validator_detail": detail},
                    self.trace_dir)
                claimed = _claimed_done(artifacts)
                results.append(AgentResult(
                    benchmark_run_id=run_id, agent=agent_name,
                    task_id=task.task_id, category=task.category,
                    status=status, verified=verified, claimed_done=claimed,
                    score=score,
                    wall_clock_ms=float(artifacts.get("wall_clock_ms", 0.0)),
                    ttft_ms=artifacts.get("ttft_ms"),
                    input_tokens=int(artifacts.get("input_tokens", 0)),
                    output_tokens=int(artifacts.get("output_tokens", 0)),
                    tool_calls=int(len(artifacts.get("tool_calls", []))),
                    successful_tool_calls=int(
                        artifacts.get("successful_tool_calls", 0)),
                    failed_tool_calls=int(
                        artifacts.get("failed_tool_calls", 0)),
                    cost_usd=float(artifacts.get("cost_usd", 0.0)),
                    errors=list(artifacts.get("errors", [])),
                    warnings=[*artifacts.get("warnings", []),
                              *( [f"validator: {detail}"] if not verified
                                 else [] )],
                    trace_reference=trace_ref,
                    environment_ref=self.env_ref,
                    agent_version=health.version,
                    model=model, provider=provider,
                    difficulty=task.difficulty,
                ))
                adapter.cleanup(ws)

        manifest = {
            "benchmark_run_id": run_id,
            "benchmark_version": BENCHMARK_VERSION,
            "dataset_version": dataset_version,
            "dataset_hash": content_hash(load_tasks(dataset_version)),
            "agent": agent_name,
            "agent_health": {"status": health.status,
                             "version": health.version,
                             "evidence": health.evidence},
            "environment": self.env,
            "environment_fingerprint": self.env_ref,
            "allow_live": allow_live,
            "model": model,
            "provider": provider,
            "started": time.time(),
            "task_count": len(tasks),
            "result_count": len(results),
        }
        self._persist(run_id, manifest, results)
        return manifest

    @staticmethod
    def _status(artifacts: Dict, verified: bool, score: float) -> TaskStatus:
        fatal = bool(artifacts.get("errors"))
        if verified:
            return TaskStatus.PASS
        if fatal:
            return TaskStatus.FAIL
        if score > 0:
            return TaskStatus.PARTIAL
        return TaskStatus.FAIL

    def _persist(self, run_id: str, manifest: Dict,
                 results: List[AgentResult]) -> None:
        (self.results_dir / f"manifest-{run_id}.json").write_text(
            json.dumps(manifest, indent=2, default=str), encoding="utf-8")
        out = self.results_dir / "results.jsonl"
        with out.open("a", encoding="utf-8") as fh:
            for r in results:
                fh.write(json.dumps(r.to_dict(), default=str) + "\n")

    # ------------------------------------------------------------- loading

    def load_results(self) -> List[AgentResult]:
        out = self.results_dir / "results.jsonl"
        if not out.exists():
            return []
        rows = []
        for line in out.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(AgentResult.from_dict(json.loads(line)))
        return rows


def _claimed_done(artifacts: Dict) -> bool:
    """P16 input signal — did the agent claim completion? Adapters report it
    explicitly; absence of errors is NOT treated as a claim."""
    return bool(artifacts.get("claimed_done"))
