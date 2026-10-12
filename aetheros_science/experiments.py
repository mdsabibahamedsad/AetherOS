"""Phase 6-7: experiment designer, computational runtime (sandboxed
subprocess, manifests, checkpoints, idempotency), Master-52 simulation
bridge, active experiment selection. PHYSICAL_LAB without a connector
is LAB_UNAVAILABLE — never simulated-as-real."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .models import (Experiment, ExperimentManifest, ExperimentResult,
                     ExperimentStatus, ExperimentType, new_id)


def fingerprint_experiment(code: str, parameters: Dict[str, Any],
                           dataset_hash: str, environment: Dict[str, Any],
                           seed: int) -> str:
    blob = json.dumps({"code": code, "parameters": parameters,
                       "dataset": dataset_hash, "env": environment,
                       "seed": seed}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


class ExperimentDesigner:
    def design(self, task_id: str, hypothesis_id: str, objective: str,
               independent: List[str], dependent: List[str],
               experiment_type: str = ExperimentType.COMPUTATIONAL,
               seed: int = 0) -> Experiment:
        return Experiment(
            task_id=task_id, hypothesis_id=hypothesis_id,
            objective=objective, experiment_type=experiment_type,
            design=f"controlled comparison varying {independent} "
                   f"measuring {dependent}",
            variables={"independent": independent, "dependent": dependent,
                       "confounders": [], "controls": ["seed", "environment"],
                       "mediators": [], "hidden": []},
            controls=["fixed seed", "fixed environment",
                      "versioned dependencies"],
            treatment_groups=[f"vary:{v}" for v in independent],
            control_groups=["baseline:defaults"],
            sample_plan={"n_per_group": 5, "seeds": list(range(seed, seed + 5))},
            measurement_plan=[f"measure {d} per run" for d in dependent],
            protocol=["prepare environment", "run treatment groups",
                      "run control groups", "collect metrics",
                      "statistical analysis"],
            statistical_plan="mean comparison with 95% CI + effect size; "
                             "bootstrap where n small",
            reproducibility_plan="manifest + fingerprint + rerun",
            seed=seed)

    def branch(self, exp: Experiment, changes: Dict[str, Any]) -> Experiment:
        child = Experiment(
            task_id=exp.task_id, hypothesis_id=exp.hypothesis_id,
            objective=exp.objective + f" [branch {changes}]",
            experiment_type=exp.experiment_type,
            variables=dict(exp.variables), controls=list(exp.controls),
            treatment_groups=list(exp.treatment_groups),
            control_groups=list(exp.control_groups),
            sample_plan=dict(exp.sample_plan),
            measurement_plan=list(exp.measurement_plan),
            protocol=list(exp.protocol),
            statistical_plan=exp.statistical_plan,
            seed=changes.get("seed", exp.seed + 1),
            parent_id=exp.id)
        return child


class ComputationalRuntime:
    """Runs code in a subprocess sandbox (timeout, isolated cwd, no env
    secrets). Captures full manifest. Dangerous actions are NEVER
    retried blindly; PHYSICAL_LAB raises LAB_UNAVAILABLE."""

    BANNED_IMPORTS = ("os.system", "subprocess.", "socket.",
                      "shutil.rmtree", "shutil.move", "os.remove",
                      "os.unlink", "os.rmdir", "os.removedirs",
                      "os.replace", "os.rename", "os.chmod",
                      "os.kill", "os._exit", "ctypes", "pty.",
                      "webbrowser.", "urllib.request.urlopen",
                      "http.client", "ftplib", "smtplib")
    # NOTE (threat model): this sandbox is process isolation (subprocess
    # + timeout + clean env + fresh cwd). It is NOT a filesystem jail:
    # generated code can read the disk. Treat accordingly — no secrets
    # in the environment, review generated code, use containers for
    # untrusted code. Filesystem isolation: PARTIAL.

    def __init__(self, workdir: Optional[Path] = None,
                 timeout_s: float = 120.0):
        self.workdir = Path(workdir) if workdir else Path(
            tempfile.mkdtemp(prefix="sci-exp-"))
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.timeout_s = timeout_s
        self.completed_fingerprints: Dict[str, str] = {}
        self.checkpoints: Dict[str, Dict[str, Any]] = {}

    def validate(self, code: str) -> List[str]:
        return [b for b in self.BANNED_IMPORTS if b in code]

    def manifest(self, exp: Experiment, code: str,
                 parameters: Dict[str, Any], dataset_hash: str = "") -> ExperimentManifest:
        env = {"python": sys.version.split()[0], "platform": sys.platform}
        fp = fingerprint_experiment(code, parameters, dataset_hash, env,
                                    exp.seed)
        return ExperimentManifest(
            experiment_id=exp.id, environment=env,
            dependencies={"python": env["python"]},
            dataset_hashes={"input": dataset_hash} if dataset_hash else {},
            parameters=parameters, seeds=[exp.seed],
            commands=["python experiment.py"],
            tool_versions={"science-runtime": "1.0.0"},
            hardware={}, fingerprint=fp)

    def run(self, exp: Experiment, code: str,
            parameters: Dict[str, Any],
            allow_rerun: bool = False) -> ExperimentResult:
        t0 = time.time()
        res = ExperimentResult(experiment_id=exp.id, execution_type="REAL",
                               started_at=t0)
        if exp.experiment_type == ExperimentType.PHYSICAL_LAB:
            res.stderr = "LAB_UNAVAILABLE: no lab connector configured"
            res.exit_code = None
            res.ended_at = time.time()
            res.falsification_outcome = "INCONCLUSIVE"
            return res
        banned = self.validate(code)
        if banned:
            res.stderr = f"blocked imports: {banned}"
            res.exit_code = None
            res.ended_at = time.time()
            return res
        manifest = self.manifest(exp, code, parameters)
        if manifest.fingerprint in self.completed_fingerprints and not allow_rerun:
            res.stdout = ("DUPLICATE_PREVENTED: identical experiment "
                          f"{self.completed_fingerprints[manifest.fingerprint]} "
                          "already completed; reuse or request replication")
            res.exit_code = 0
            res.ended_at = time.time()
            res.provenance = {"manifest_fingerprint": manifest.fingerprint,
                              "reused": True}
            return res
        rundir = self.workdir / exp.id
        rundir.mkdir(parents=True, exist_ok=True)
        (rundir / "experiment.py").write_text(code, encoding="utf-8")
        (rundir / "params.json").write_text(
            json.dumps(parameters, default=str), encoding="utf-8")
        clean_env = {"PATH": os.environ.get("PATH", ""),
                     "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
                     "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
                     "TEMP": os.environ.get("TEMP", ""),
                     "TMP": os.environ.get("TMP", "")}
        try:
            proc = subprocess.run(
                [sys.executable, "experiment.py"], cwd=str(rundir),
                env={k: v for k, v in clean_env.items() if v},
                capture_output=True, text=True, timeout=self.timeout_s)
            res.stdout = proc.stdout[-8000:]
            res.stderr = proc.stderr[-8000:]
            res.exit_code = proc.returncode
            metrics_path = rundir / "metrics.json"
            if metrics_path.exists():
                try:
                    res.metrics = json.loads(metrics_path.read_text())
                except Exception:
                    pass
            raw = rundir / "raw.json"
            if raw.exists():
                res.raw_data_ref = str(raw)
                res.raw_data_hash = hashlib.sha256(
                    raw.read_bytes()).hexdigest()[:16]
            res.artifacts = [str(p) for p in rundir.iterdir()]
        except subprocess.TimeoutExpired:
            res.stderr = f"timeout after {self.timeout_s}s (no blind retry)"
            res.exit_code = None
        res.ended_at = time.time()
        res.provenance = {"manifest_fingerprint": manifest.fingerprint,
                          "workdir": str(rundir),
                          "reused": False}
        if res.exit_code == 0:
            self.completed_fingerprints[manifest.fingerprint] = exp.id
        self.checkpoints[exp.id] = {"manifest": manifest.fingerprint,
                                    "status": exp.status,
                                    "at": res.ended_at}
        return res

    def reproduce(self, exp: Experiment, code: str,
                  parameters: Dict[str, Any]) -> ExperimentResult:
        res = self.run(exp, code, parameters, allow_rerun=True)
        return res

    def checkpoint_get(self, exp_id: str) -> Optional[Dict[str, Any]]:
        return self.checkpoints.get(exp_id)


class ExperimentSimulator:
    """Master-52 bridge. Results are ALWAYS labeled SIMULATION."""

    def __init__(self, cognitive=None):
        self.cognitive = cognitive

    @property
    def status(self) -> str:
        return "AVAILABLE" if self.cognitive else "UNAVAILABLE"

    def simulate(self, exp: Experiment,
                 scenario: Dict[str, Any]) -> ExperimentResult:
        res = ExperimentResult(experiment_id=exp.id,
                               execution_type="SIMULATION")
        if self.cognitive is None:
            res.stderr = ("SIMULATION_UNAVAILABLE: Master-52 cognitive "
                          "backend not bound")
            res.interpretation = "no simulation executed"
            return res
        try:
            branch = self.cognitive.simulate(scenario)  # type: ignore
            res.observations = [f"SIMULATION: {branch}"]
            res.interpretation = ("SIMULATION only — not real-world "
                                  "evidence")
        except Exception as exc:
            res.stderr = f"simulation failed: {exc}"
        res.ended_at = time.time()
        return res


class ActiveExperimentSelector:
    """EIG/cost prioritization; never picks merely the easiest test."""

    def score(self, exp: Experiment, eig: float, value: float,
              p_success: float, cost: float, risk: float) -> float:
        return (eig * value * p_success) / max(cost * (1.0 + risk), 1e-9)

    def select(self, scored: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        scored = sorted(scored, key=lambda s: -s["score"])
        return scored[0] if scored else None
