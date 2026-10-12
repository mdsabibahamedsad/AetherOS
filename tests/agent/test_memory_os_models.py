"""Memory OS models: P15 field completeness, hashing, versioning, validity."""

from agent.memory_os.models import (
    Confidence,
    MemoryItem,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    PreferenceKind,
    RelationshipType,
    Sensitivity,
    SourceType,
)


def _required_p15_fields():
    return {
        "memory_id", "type", "content", "summary", "source_type", "source_id",
        "scope", "owner", "project_id", "task_id", "entity_ids",
        "relationship_ids", "confidence", "importance", "sensitivity",
        "created_at", "updated_at", "last_accessed_at", "expires_at",
        "status", "version", "content_hash",
    }


def test_memory_item_has_every_p15_field():
    item = MemoryItem(content="x")
    row = item.to_row()
    assert _required_p15_fields().issubset(row.keys())


def test_content_hash_is_deterministic_and_short():
    a = MemoryItem(content="hello world")
    b = MemoryItem(content="hello world")
    c = MemoryItem(content="hello worlds")
    assert a.content_hash == b.content_hash and len(a.content_hash) == 16
    assert a.content_hash != c.content_hash


def test_versioning_preserves_identity_and_provenance():
    v1 = MemoryItem(content="pref: verbose", type=MemoryType.PREFERENCE,
                    preference_kind=PreferenceKind.EXPLICIT)
    v1.provenance.actor = "user"
    v2 = v1.with_content("pref: concise")
    assert v2.memory_id == v1.memory_id
    assert v2.version == 2
    assert v2.content_hash != v1.content_hash
    assert v2.provenance.actor == "user"


def test_validity_window_and_expiry():
    item = MemoryItem(content="old architecture was X", valid_until=1000.0)
    assert not item.temporally_valid(at=2000.0)      # historically true only
    assert item.temporally_valid(at=500.0)
    exp = MemoryItem(content="cache entry", expires_at=1.0)
    assert exp.is_expired()


def test_all_17_types_present():
    values = {t.value for t in MemoryType}
    expected = {"working", "episodic", "semantic", "procedural", "preference",
                "project", "task", "entity", "relationship", "research",
                "tool", "workflow", "ui_pattern", "computer_use", "temporal",
                "source", "system"}
    assert values == expected


def test_scopes_confidence_sensitivity_enums():
    assert {s.value for s in MemoryScope} == {
        "session", "task", "project", "user", "organization", "system"}
    assert [c.value for c in Confidence] == [
        "confirmed", "high", "medium", "low", "unknown"]
    assert {s.value for s in Sensitivity} == {"public", "internal", "sensitive"}


def test_relationship_types_match_spec():
    expected = {"owns", "uses", "depends_on", "created_by", "authored_by",
                "related_to", "part_of", "located_in", "built_with",
                "replaced_by", "contradicts", "supports", "mentions",
                "derived_from"}
    assert {r.value for r in RelationshipType} == expected


def test_source_taxonomy_distinguishes_inference_from_user():
    assert SourceType.MODEL_INFERENCE is not SourceType.USER_EXPLICIT


def test_status_lifecycle_states_exist():
    assert {s.value for s in MemoryStatus} >= {
        "candidate", "active", "superseded", "archived", "expired",
        "quarantined", "merged", "forgotten"}
