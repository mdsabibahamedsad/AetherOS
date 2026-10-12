"""Master-13 slice 3: workflow spec, DAG mechanics and error classification."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from automation.errors import classify, is_retryable


class TestClassify:
    @pytest.mark.parametrize("text,expected", [
        ("HTTP 401 Unauthorized: bad api key", "auth"),
        ("permission denied while writing", "permission"),
        ("connection reset by peer during request", "network"),
        ("429 rate limit exceeded, try again", "transient"),
        ("context length exceeded for model", "model"),
        ("No space left on device", "resource"),
        ("config.yaml missing required field", "configuration"),
        ("tool call failed schema validation", "tool"),
        ("operation cancelled by user", "user"),
        ("prompt injection blocked by security policy", "security"),
    ])
    def test_known_categories(self, text, expected):
        assert classify(text) == expected

    def test_unknown_falls_back(self):
        assert classify("weird gibberish") == "unknown"

    def test_retryable_defaults(self):
        assert is_retryable("connection timed out")
        assert is_retryable("429 slow down")
        assert not is_retryable("401 invalid api key")       # never hammer auth
        assert not is_retryable("permission denied")


def _wf(steps, **extra):
    base = {"steps": steps}
    base.update(extra)
    return base


def _step(sid, prompt="p", deps=None, **kw):
    step = {"id": sid, "prompt": prompt, "depends_on": deps or []}
    step.update(kw)
    return step


class TestNormalizeWorkflow:
    def test_valid_spec_orders_topologically(self):
        from automation.workflow import normalize_workflow

        spec = normalize_workflow(_wf([
            _step("report", deps=["research", "verify"]),
            _step("research"),
            _step("verify", deps=["research"]),
        ]))
        assert spec["order"] == ["research", "verify", "report"]
        assert spec["on_failure"] == "stop"

    def test_cycle_detected(self):
        from automation.workflow import normalize_workflow

        with pytest.raises(ValueError):
            normalize_workflow(_wf([
                _step("a", deps=["b"]),
                _step("b", deps=["a"]),
            ]))

    def test_unknown_dependency_rejected(self):
        from automation.workflow import normalize_workflow

        with pytest.raises(ValueError):
            normalize_workflow(_wf([_step("a", deps=["ghost"])]))

    def test_duplicate_ids_rejected(self):
        from automation.workflow import normalize_workflow

        with pytest.raises(ValueError):
            normalize_workflow(_wf([_step("a"), _step("a")]))

    def test_self_dependency_rejected(self):
        from automation.workflow import normalize_workflow

        with pytest.raises(ValueError):
            normalize_workflow(_wf([_step("a", deps=["a"])]))

    def test_step_needs_prompt_or_script(self):
        from automation.workflow import normalize_workflow

        with pytest.raises(ValueError):
            normalize_workflow(_wf([{"id": "empty"}]))

    def test_bad_on_failure_rejected(self):
        from automation.workflow import normalize_workflow

        with pytest.raises(ValueError):
            normalize_workflow(_wf([_step("a")], on_failure="explode"))

    def test_attempts_bounded(self):
        from automation.workflow import normalize_workflow

        with pytest.raises(ValueError):
            normalize_workflow(_wf([_step("a", attempts=99)]))


class TestReadyStepsAndConditions:
    def _run_states(self, statuses):
        return {
            sid: {"status": st, "output": "", "error": "", "attempts": 0}
            for sid, st in statuses.items()
        }

    def test_deps_gate_execution(self):
        from automation.workflow import normalize_workflow, ready_steps

        spec = normalize_workflow(_wf([
            _step("a"),
            _step("b", deps=["a"]),
        ]))
        run_steps = self._run_states({"a": "pending", "b": "pending"})
        assert ready_steps(run_steps, spec) == ["a"]

        run_steps["a"]["status"] = "done"
        assert ready_steps(run_steps, spec) == ["b"]

    def test_condition_false_skips_branch(self):
        from automation.workflow import normalize_workflow, ready_steps

        spec = normalize_workflow(_wf([
            _step("build"),
            _step(
                "deploy",
                deps=["build"],
                condition=[{"path": "steps.build.status", "op": "eq", "value": "done"}],
            ),
        ]))
        run_steps = self._run_states({"build": "done", "deploy": "pending"})
        run_steps["build"]["status"] = "failed"
        # build failed → deploy's dep isn't done anyway; use done-with-false-cond:
        run_steps["build"]["status"] = "done"
        run_steps["build"]["status"] = "done"
        spec2 = normalize_workflow(_wf([
            _step("build"),
            _step(
                "deploy",
                deps=["build"],
                condition=[{"path": "steps.build.status", "op": "eq", "value": "failed"}],
            ),
        ]))
        ready = ready_steps(run_steps, spec2)
        assert ready == []
        assert run_steps["deploy"]["status"] == "skipped"

    def test_parallel_ready_batch(self):
        from automation.workflow import normalize_workflow, ready_steps

        spec = normalize_workflow(_wf([
            _step("root"),
            _step("left", deps=["root"]),
            _step("right", deps=["root"]),
        ], concurrency=2))
        run_steps = self._run_states({"root": "done", "left": "pending", "right": "pending"})
        assert ready_steps(run_steps, spec) == ["left", "right"]


class TestStepPromptContext:
    def test_upstream_output_injected_and_truncated(self):
        from automation.workflow import build_step_prompt, normalize_workflow

        spec = normalize_workflow(_wf([
            _step("a"),
            _step("b", deps=["a"]),
        ]))
        run_steps = {
            "a": {"status": "done", "output": "FINDINGS" * 5000, "error": "", "attempts": 1},
            "b": {"status": "pending", "output": "", "error": "", "attempts": 0},
        }
        prompt = build_step_prompt(spec["steps"][1], run_steps)
        assert "Output from step 'a'" in prompt
        assert "[... truncated ...]" in prompt


class TestDescribeWorkflow:
    def test_description_mentions_approval(self):
        from automation.workflow import describe_workflow, normalize_workflow

        spec = normalize_workflow(_wf([
            _step("publish", approval_required=True),
        ]))
        text = describe_workflow(spec)
        assert "approval" in text
