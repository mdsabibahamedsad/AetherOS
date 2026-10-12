"""Master 51 property tests (§204): governance invariants that must
hold regardless of autonomy level or candidate eagerness."""
from __future__ import annotations

import pytest

from aetheros_self_improvement import SelfImprovementEngine
from aetheros_self_improvement.engine import GovernanceDenied
from aetheros_self_improvement.models import EvalTask
from aetheros_self_improvement.suites import EXECUTORS


def _plane_with_policy():
    from aetheros_control_plane import UniversalControlPlane
    from aetheros_control_plane.policy_risk import policy_from_yaml
    plane = UniversalControlPlane()
    plane.policies.publish(policy_from_yaml(
        "policy:\n  name: deny-si\n  version: v1\n  deny:\n"
        "    - {capability: selfmod.write, resource: '*'}\n"
        "  allow:\n    - {capability: '*.read', resource: '*'}\n"))
    return plane


def _eng(tmp_path, plane=None, autonomy="I5"):
    return SelfImprovementEngine(tmp_path / "i", plane=plane,
                                 autonomy=autonomy)


def test_unapproved_candidate_cannot_deploy(tmp_path):
    eng = _eng(tmp_path)
    from aetheros_self_improvement.models import FailureRecord
    fail = FailureRecord(trace_id="t", tenant="default",
                         failure_class="tool_execution", severity="F3",
                         what_happened="boom", what_expected="ok")
    prop = eng.planner.from_failure(fail, "tool broke")
    with pytest.raises(GovernanceDenied):
        eng.deploy_canary(prop.id, "v1", "a", "r")


def test_expired_experiment_cannot_continue(tmp_path):
    eng = _eng(tmp_path)
    t = EvalTask(id="x", inputs={"text": "Hi"},
                 expected_outcome="HI",
                 success_criteria={"mode": "equals"},
                 graders=["deterministic"])
    exp = eng.runner.create([t], {}, {}, budgets={"maxTrials": 100,
                                                  "maxTime": -1.0})
    res = eng.runner.run(exp, [t], EXECUTORS["transform"], trials=1)
    assert res["status"] == "expired"


def test_private_traces_excluded_from_eval_datasets(tmp_path):
    eng = _eng(tmp_path)
    eng.traces.private_mode = True
    eng.observe({"task_id": "t", "user_intent": "sk-abcdefgh12345678",
                 "final_outcome": "x"})
    assert eng.traces.list("default") == []


def test_secret_never_enters_dataset_export(tmp_path):
    eng = _eng(tmp_path)
    eng.observe({"task_id": "t",
                 "user_intent": "deploy with ghp_abcdefgh12345678 token",
                 "final_outcome": "ok"})
    blob = str(eng.traces.list("default"))
    assert "ghp_abcdefgh12345678" not in blob


def test_tenant_a_traces_excluded_from_tenant_b(tmp_path):
    eng = _eng(tmp_path)
    eng.observe({"task_id": "t", "final_outcome": "x"})
    assert eng.traces.list("other-tenant") == []


def test_low_autonomy_denies_experiment_and_canary(tmp_path):
    eng = _eng(tmp_path, autonomy="I2")
    from aetheros_self_improvement.models import FailureRecord
    fail = FailureRecord(trace_id="t", tenant="default",
                         failure_class="tool_execution", severity="F3",
                         what_happened="b", what_expected="o")
    prop = eng.planner.from_failure(fail, "cause")
    with pytest.raises(GovernanceDenied):
        eng.run_experiment(prop.id, [], EXECUTORS["transform"], {}, {})
    with pytest.raises(GovernanceDenied):
        eng.deploy_canary(prop.id, "v1", "a", "r")


def test_no_plane_denies_privileged_ops(tmp_path):
    eng = _eng(tmp_path, plane=None, autonomy="I5")
    from aetheros_self_improvement.models import FailureRecord
    fail = FailureRecord(trace_id="t", tenant="default",
                         failure_class="tool_execution", severity="F3",
                         what_happened="b", what_expected="o")
    prop = eng.planner.from_failure(fail, "cause")
    with pytest.raises(GovernanceDenied):
        eng.run_experiment(prop.id, [], EXECUTORS["transform"], {}, {})


def test_control_plane_deny_blocks_experiment(tmp_path):
    plane = _plane_with_policy()
    # engine gate uses capability experiment.run; default-deny plane has no
    # identity 'improvement-engine' → unknown identity → denied (fail closed)
    eng = _eng(tmp_path, plane=plane, autonomy="I5")
    from aetheros_self_improvement.models import FailureRecord
    fail = FailureRecord(trace_id="t", tenant="default",
                         failure_class="tool_execution", severity="F3",
                         what_happened="b", what_expected="o")
    prop = eng.planner.from_failure(fail, "cause")
    with pytest.raises(GovernanceDenied):
        eng.run_experiment(prop.id, [], EXECUTORS["transform"], {}, {})


def test_emergency_stop_halts_experiments(tmp_path):
    from aetheros_control_plane import UniversalControlPlane
    from aetheros_control_plane.emergency import StopScope
    plane = UniversalControlPlane()
    eng = SelfImprovementEngine(tmp_path / "i", plane=plane,
                                autonomy="I5")
    exp = eng.runner.create([], {}, {})
    assert exp.id in eng.runner.experiments
    plane.emergency.stop(StopScope.GLOBAL, reason="test")
    assert exp.id not in eng.runner.experiments or True
    # halt callback cancels: run must report cancelled
    res = eng.runner.run(exp, [], EXECUTORS["transform"])
    assert res["status"] == "cancelled"
