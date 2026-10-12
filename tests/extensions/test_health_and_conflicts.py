"""Behavior contracts for the facade health surface (Phases 19-20, 77)
and the skill requirement conflict checker (Phase 49-lite)."""

from extensions.facade import (
    CapabilityType,
    health_report,
    resolve_capability,
    skill_requirement_conflicts,
)


def test_health_report_shape_and_internal_consistency():
    report = health_report()
    assert report["total"] == len(report["capabilities"])
    assert report["total"] >= 10, "registry+skills+plugins project many rows"
    assert sum(report["counts"].values()) == report["total"]
    for row in report["capabilities"]:
        assert set(row) == {
            "capability_id",
            "type",
            "availability",
            "health",
            "reachability",
            "trust_state",
        }
        assert row["reachability"] in {"LOCAL", "REMOTE", "OFFLINE", "DEGRADED"}


def test_health_report_is_pure_projection():
    """No probes / no execution: consecutive reports agree on membership."""
    ids_a = {r["capability_id"] for r in health_report()["capabilities"]}
    ids_b = {r["capability_id"] for r in health_report()["capabilities"]}
    assert ids_a == ids_b


def test_reachability_labels_for_known_families():
    report = health_report()
    tools = [r for r in report["capabilities"] if r["type"] == "tool"]
    assert tools and all(r["reachability"] in {"LOCAL", "REMOTE", "DEGRADED"} for r in tools)
    local_core = [r for r in tools if r["capability_id"].startswith("aetheros.tool.")]
    assert local_core, "core tools projected under stable namespace"


def test_skill_requirement_conflicts_detects_missing_tool():
    problems = skill_requirement_conflicts(
        {"requires_tools": ["read_file", "nope_xyz_9"]}
    )
    assert any("nope_xyz_9" in p for p in problems)
    assert not any(p.endswith("read_file") for p in problems)


def test_skill_requirement_conflicts_detects_missing_toolset():
    problems = skill_requirement_conflicts(
        {"requires_toolsets": ["file", "not_a_real_set"]}
    )
    assert any("missing toolset: not_a_real_set" in p for p in problems)
    assert not any(p.endswith(": file") for p in problems)


def test_skill_requirement_conflicts_empty_meta_is_clean():
    assert skill_requirement_conflicts({}) == []


def test_facade_exposes_schema_contract_flag():
    rec = resolve_capability("read_file")
    assert rec is not None
    assert rec.type is CapabilityType.TOOL
    assert isinstance(rec.metadata.get("schema_valid"), bool)
