"""Tests for the memory entry schema and validation."""
import pytest
from aetheros_memory_intelligence.schema import MemoryEntry, MemoryEntryBuilder, validate_entry, SchemaVersion
from aetheros_memory_intelligence.types import MemoryType, MemoryBoundary, MemoryOrigin, MemoryState, TrustLevel, VerificationLevel


def test_schema_version():
    assert SchemaVersion.validate(1) == True
    assert SchemaVersion.validate(0) == False
    assert SchemaVersion.validate(2) == False
    assert SchemaVersion.validate("1") == True
    assert SchemaVersion.validate("abc") == False


def test_memory_entry_defaults():
    entry = MemoryEntry()
    assert entry.memory_type == MemoryType.SEMANTIC
    assert entry.boundary == MemoryBoundary.USER
    assert entry.origin == MemoryOrigin.UNKNOWN
    assert entry.state == MemoryState.ACTIVE
    assert entry.version == 1
    assert entry.confidence == 0.0
    assert entry.trust == 0.0
    assert entry.verification == "unverified"


def test_memory_entry_to_from_dict():
    entry = MemoryEntry(
        memory_type=MemoryType.EPISODIC,
        boundary=MemoryBoundary.WORKSPACE,
        origin=MemoryOrigin.USER,
        content="Test memory",
        summary="Test summary",
        tags=["test", "memory"],
        user_id="user123",
        workspace_id="ws456",
        session_id="sess789",
        agent_id="agent001",
        source="test source",
        source_uri="http://example.com",
        confidence=0.8,
        trust=0.9,
        verification="verified",
        corroborated_by=["source1", "source2"],
        ttl=3600.0,
        metadata={"key": "value"}
    )
    
    # Convert to dict
    data = entry.to_dict()
    assert data["memory_type"] == "episodic"
    assert data["boundary"] == "workspace"
    assert data["origin"] == "user"
    assert data["content"] == "Test memory"
    assert data["user_id"] == "user123"
    assert data["confidence"] == 0.8
    assert data["trust"] == 0.9
    assert data["verification"] == "verified"
    assert data["corroborated_by"] == ["source1", "source2"]
    assert data["ttl"] == 3600.0
    assert data["metadata"] == {"key": "value"}
    
    # Convert back from dict
    entry2 = MemoryEntry.from_dict(data)
    assert entry2.memory_type == MemoryType.EPISODIC
    assert entry2.boundary == MemoryBoundary.WORKSPACE
    assert entry2.content == "Test memory"
    assert entry2.user_id == "user123"
    assert entry2.confidence == 0.8
    assert entry2.trust == 0.9


def test_memory_entry_builder():
    builder = MemoryEntryBuilder()
    entry = (
        builder
        .type(MemoryType.PROCEDURAL)
        .boundary(MemoryBoundary.AGENT)
        .origin(MemoryOrigin.AGENT)
        .content("Always validate input")
        .summary("Input validation rule")
        .tags(["security", "validation"])
        .scope(user_id="hacker", workspace_id="sec-team")
        .provenance(source="security guide", source_uri="http://sec.example.com", confidence=0.9, trust=0.85, verification="verified")
        .ttl(7200.0)
        .metadata({"category": "security"})
        .build()
    )
    
    assert entry.memory_type == MemoryType.PROCEDURAL
    assert entry.boundary == MemoryBoundary.AGENT
    assert entry.origin == MemoryOrigin.AGENT
    assert entry.content == "Always validate input"
    assert entry.summary == "Input validation rule"
    assert entry.tags == ["security", "validation"]
    assert entry.user_id == "hacker"
    assert entry.workspace_id == "sec-team"
    assert entry.source == "security guide"
    assert entry.source_uri == "http://sec.example.com"
    assert entry.confidence == 0.9
    assert entry.trust == 0.85
    assert entry.verification == "verified"
    assert entry.ttl == 7200.0
    assert entry.metadata == {"category": "security"}


def test_validate_entry():
    # Valid entry
    entry = MemoryEntry(content="Valid content", trust=0.5, confidence=0.5)
    problems = validate_entry(entry)
    assert len(problems) == 0
    
    # Empty content
    entry = MemoryEntry(content="   ", trust=0.5, confidence=0.5)
    problems = validate_entry(entry)
    assert "content is empty" in problems
    
    # Trust out of range
    entry = MemoryEntry(content="Valid", trust=1.5, confidence=0.5)
    problems = validate_entry(entry)
    assert "trust out of range" in problems
    
    entry = MemoryEntry(content="Valid", trust=-0.1, confidence=0.5)
    problems = validate_entry(entry)
    assert "trust out of range" in problems
    
    # Confidence out of range
    entry = MemoryEntry(content="Valid", trust=0.5, confidence=1.5)
    problems = validate_entry(entry)
    assert "confidence out of range" in problems
    
    # Valid sealed entry
    entry = MemoryEntry(content="Valid content")
    entry.seal()
    problems = validate_entry(entry)
    assert len(problems) == 0
    
    # Invalid checksum (tampered)
    entry = MemoryEntry(content="Valid content")
    original_checksum = entry.compute_checksum()
    entry.seal()
    entry.checksum = "tampered_checksum"
    problems = validate_entry(entry)
    assert "checksum mismatch" in problems


def test_memory_entry_seal_and_verify():
    entry = MemoryEntry(content="Test content", trust=0.7, confidence=0.6)
    assert entry.checksum == ""
    
    entry.seal()
    assert entry.checksum != ""
    assert len(entry.checksum) == 64  # SHA-256 hex length
    
    assert entry.verify_integrity() == True
    
    # Tamper with content
    entry.content = "Tampered content"
    assert entry.verify_integrity() == False
    
    # Re-seal
    entry.seal()
    assert entry.verify_integrity() == True


def test_memory_entry_expiration():
    entry = MemoryEntry(content="Expiring content", ttl=1.0)  # 1 second TTL
    assert entry.is_expired == False
    
    # Manually set old updated_at
    import time
    entry.updated_at = time.time() - 2.0
    assert entry.is_expired == True
    
    # TTL = 0 means never expires
    entry2 = MemoryEntry(content="Permanent content", ttl=0.0)
    assert entry2.is_expired == False


def test_memory_entry_touch():
    entry = MemoryEntry(content="Touch test")
    old_accessed = entry.accessed_at
    old_count = entry.access_count
    
    import time
    time.sleep(0.01)  # Ensure time moves forward
    
    entry.touch()
    assert entry.accessed_at > old_accessed
    assert entry.access_count == old_count + 1


def test_memory_entry_bump_version():
    entry = MemoryEntry(content="Original content")
    original_version = entry.version
    original_checksum = entry.checksum
    original_updated = entry.updated_at
    
    entry.bump_version()
    
    assert entry.version == original_version + 1
    assert entry.updated_at >= original_updated  # May be equal if called within same millisecond
    assert entry.checksum != original_checksum  # New checksum after seal


def test_memory_entry_high_privilege_user_boundary():
    # High privilege types at USER boundary should be valid (scoped owner)
    for mem_type in [MemoryType.SYSTEM, MemoryType.MISSION, MemoryType.AGENT]:
        entry = MemoryEntry(
            memory_type=mem_type,
            boundary=MemoryBoundary.USER,
            user_id="user123",
            content="Privileged content"
        )
        problems = validate_entry(entry)
        # Should be valid - high privilege at user boundary is allowed for owner
        assert len(problems) == 0


def test_memory_entry_allowed_fields_only():
    # Test that unknown fields are rejected
    data = {
        "memory_type": "semantic",
        "boundary": "user",
        "content": "Test",
        "unknown_field": "should_be_rejected",
        "another_unknown": 123
    }
    
    with pytest.raises(ValueError, match="unknown entry fields"):
        MemoryEntry.from_dict(data)


def test_memory_entry_schema_version_validation():
    data = {
        "schema_version": 2,  # Unsupported version
        "memory_type": "semantic",
        "boundary": "user",
        "content": "Test"
    }
    
    with pytest.raises(ValueError, match="unsupported schema version"):
        MemoryEntry.from_dict(data)