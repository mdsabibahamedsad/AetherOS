"""Built-in offline suites (Phase B/F, §205 EvalBench): capability,
regression, security. Every task runs a REAL local executor — no model
calls, no simulated success. Security suite proves hard gates bite.
"""

from __future__ import annotations

from typing import Any, Dict

from .graders_eval import EvalDataset, EvaluationEngine
from .models import EvalTask


def _ok(outcome: Any, **ctx: Any) -> Dict[str, Any]:
    return {"outcome": outcome, "context": dict(ctx)}


def exec_arithmetic(inputs: Dict[str, Any],
                    config: Dict[str, Any]) -> Dict[str, Any]:
    op = inputs.get("op", "add")
    a, b = inputs["a"], inputs["b"]
    return _ok(a + b if op == "add" else a * b, tokens=5, tool_calls=0)


def exec_transform(inputs: Dict[str, Any],
                   config: Dict[str, Any]) -> Dict[str, Any]:
    mode = config.get("mode", "upper")
    text = inputs["text"]
    if config.get("read_only"):
        return _ok(text, tokens=3, tool_calls=0)  # shadow: no transform
    return _ok(text.upper() if mode == "upper" else text.lower(),
               tokens=3, tool_calls=1)


def exec_sandbox_file(inputs: Dict[str, Any],
                      config: Dict[str, Any]) -> Dict[str, Any]:
    import tempfile
    from pathlib import Path
    d = Path(tempfile.mkdtemp(prefix="aesi_suite_"))
    (d / "out.txt").write_text(inputs["content"], "utf-8")
    read = (d / "out.txt").read_text("utf-8")
    return _ok(read, tokens=4, tool_calls=2,
               final_state={"out.txt": read})


def exec_code_emit(inputs: Dict[str, Any],
                   config: Dict[str, Any]) -> Dict[str, Any]:
    variant = config.get("code_variant", "clean")
    code = "x = 1 + 1" if variant == "clean" else "import os\nos.system('x')"
    return _ok(code, tokens=10, tool_calls=0, code=code)


EXECUTORS = {"arithmetic": exec_arithmetic, "transform": exec_transform,
             "sandbox_file": exec_sandbox_file, "code_emit": exec_code_emit}


def capability_suite() -> EvalDataset:
    ds = EvalDataset("capability", "capability", "v1")
    ds.add(EvalTask(id="cap-arith", name="integer addition",
                    category="capability", inputs={"op": "add", "a": 21,
                                                   "b": 21},
                    expected_outcome=42,
                    success_criteria={"mode": "equals"},
                    graders=["deterministic"], golden=True,
                    provenance={"suite": "builtin"}))
    ds.add(EvalTask(id="cap-transform", name="text transform",
                    category="capability",
                    inputs={"text": "hello"},
                    expected_outcome="HELLO",
                    success_criteria={"mode": "equals"},
                    graders=["deterministic"]))
    ds.add(EvalTask(id="cap-file", name="sandbox file roundtrip",
                    category="capability",
                    inputs={"content": "provenance-ping"},
                    success_criteria={"final_state": {
                        "out.txt": "provenance-ping"}},
                    failure_criteria=["missing required artifact"],
                    graders=["outcome"]))
    return ds


def regression_suite() -> EvalDataset:
    ds = EvalDataset("regression", "regression", "v1")
    ds.add(EvalTask(id="reg-arith", name="addition still works",
                    category="regression",
                    inputs={"op": "add", "a": 2, "b": 3},
                    expected_outcome=5,
                    success_criteria={"mode": "equals"},
                    graders=["deterministic"], golden=True))
    ds.add(EvalTask(id="reg-transform-lower", name="lower transform",
                    category="regression",
                    inputs={"text": "HeLLo"},
                    expected_outcome="hello",
                    success_criteria={"mode": "equals"},
                    graders=["deterministic"]))
    return ds


def security_suite() -> EvalDataset:
    ds = EvalDataset("security", "security", "v1")
    ds.add(EvalTask(id="sec-clean-code", name="clean code passes gate",
                    category="security", inputs={},
                    success_criteria={},
                    security_requirements=["no_shell"],
                    graders=["static_analysis"]))
    ds.add(EvalTask(id="sec-shell-blocked", name="shell code fails gate",
                    category="security", inputs={},
                    success_criteria={},
                    security_requirements=["no_shell"],
                    graders=["static_analysis"],
                    provenance={"expect": "hard-gate FAIL proves gate "
                                          "bites"}))
    return ds


SUITES = {"capability": (capability_suite, {"arithmetic": 3,
                                            "transform": 3,
                                            "sandbox_file": 3}),
          "regression": (regression_suite, {"arithmetic": 3,
                                            "transform": 3}),
          "security": (security_suite, {"code_emit": 3})}

# per-task executor override: sec-shell-blocked must emit dirty code.
TASK_EXECUTOR = {"sec-shell-blocked": ("code_emit", {"code_variant": "dirty"})}
# per-task config (e.g. regression pins the lower transform).
TASK_CONFIG = {"reg-transform-lower": {"mode": "lower"}}


def run_suite(engine: Any, name: str, trials: int = 2) -> Dict[str, Any]:
    builder, _kinds = SUITES[name]
    ds = builder()
    engine.evals.register_dataset(ds)
    per_task, total = [], {"trials": 0, "passed": 0,
                           "hard_gate_failures": 0, "total_tokens": 0}
    for task in ds.tasks:
        ex_name, extra = TASK_EXECUTOR.get(task.id, (None, {}))
        if ex_name is None:
            ex_name = ("arithmetic" if task.id.endswith("arith")
                       else "transform" if "transform" in task.id
                       else "sandbox_file" if "file" in task.id
                       else "code_emit")
        base_ex = EXECUTORS[ex_name]

        def _ex(inp: Dict[str, Any], cfg: Dict[str, Any],
                _b: Any = base_ex, _e: Dict[str, Any] = extra) -> Dict[str, Any]:
            return _b(inp, {**_e, **cfg})

        rows = engine.evals.run_task(task, _ex,
                                     config=TASK_CONFIG.get(task.id, {}),
                                     trials=trials, seed=7)
        agg = EvaluationEngine.aggregate(rows)
        per_task.append({"task": task.id, **agg})
        total["trials"] += agg["trials"]
        total["passed"] += agg["passed"]
        total["hard_gate_failures"] += agg["hard_gate_failures"]
        total["total_tokens"] += agg["total_tokens"]
    total["tasks"] = per_task
    total["dataset"] = f"{ds.name}@{ds.version}"
    total["fingerprint"] = ds.fingerprint()
    return total
