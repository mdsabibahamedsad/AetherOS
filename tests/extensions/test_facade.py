"""Behavior contracts for the Master 12 capability facade."""

from extensions.facade import (
    CapabilityType,
    all_capabilities,
    capability_id_for,
    ecosystem_summary,
    find,
    resolve_capability,
)


def test_tool_projection_unique_ids_and_alias_resolution():
    tools = [r for r in all_capabilities() if r.type is CapabilityType.TOOL]
    # Behavioral floor: the core registry ships dozens of built-ins.
    assert len(tools) >= 10
    ids = {r.capability_id for r in tools}
    assert len(ids) == len(tools), "stable IDs must not collide"
    sample = tools[0]
    resolved = resolve_capability(sample.name)  # legacy raw-name alias
    assert resolved is not None
    assert resolved.capability_id == sample.capability_id


def test_stable_id_scheme():
    assert capability_id_for(CapabilityType.TOOL, "aetheros", "terminal") == (
        "aetheros.tool.terminal"
    )
    assert capability_id_for(CapabilityType.MCP_TOOL, "mcp", "gh_search") == (
        "mcp.mcp_tool.gh_search"
    )
    assert capability_id_for(CapabilityType.MCP_SERVER, "mcp", "github") == (
        "aetheros.mcp.github"
    )
    assert capability_id_for(CapabilityType.SKILL, "", "research") == (
        "aetheros.skill.research"
    )


def test_find_filters_by_type_and_text():
    hits = find(cap_type=CapabilityType.TOOL, query="read")
    assert hits, "read_file/web_extract family should match 'read'"
    for rec in hits:
        assert rec.type is CapabilityType.TOOL
        assert "read" in (rec.name + " " + rec.description).lower()


def test_find_name_glob():
    hits = find(cap_type=CapabilityType.TOOL, name_glob="read_*")
    assert any(r.name == "read_file" for r in hits)
    assert all(r.name.startswith("read_") for r in hits)


def test_skill_projection_from_bundled_tree():
    skills = find(cap_type=CapabilityType.SKILL)
    assert len(skills) >= 1, "repo ships ~73 bundled SKILL.md files"
    first = skills[0]
    assert first.capability_id.startswith("aetheros.skill.")
    assert resolve_capability(first.name) is not None


def test_plugin_projection_includes_bundled_plugins():
    plugins = find(cap_type=CapabilityType.PLUGIN)
    assert len(plugins) >= 3, "repo bundles many plugin.yaml manifests"
    assert all(p.capability_id.startswith("aetheros.plugin.") for p in plugins)
    bundled = [p for p in plugins if p.installation_source == "bundled"]
    assert bundled, "bundled source must be labeled for trust decisions"


def test_mcp_servers_absent_when_unconfigured():
    # Hermetic AETHEROS_HOME has no user config → no configured servers.
    assert find(cap_type=CapabilityType.MCP_SERVER) == []


def test_resolve_unknown_returns_none():
    assert resolve_capability("") is None
    assert resolve_capability("nope.not.a.thing") is None


def test_ecosystem_summary_counts_align_with_projection():
    summary = ecosystem_summary()
    total = sum(summary.values())
    assert total >= 10
    assert set(summary).issubset({t.value for t in CapabilityType})
