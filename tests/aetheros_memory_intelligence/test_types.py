"""Tests for memory types and enums."""
from aetheros_memory_intelligence.types import (
    MemoryType, MemoryBoundary, MemoryOrigin, MemoryState,
    TrustLevel, VerificationLevel
)


def test_memory_type_enum():
    # Test all 11 memory types exist
    assert MemoryType.EPISODIC.value == "episodic"
    assert MemoryType.SEMANTIC.value == "semantic"
    assert MemoryType.PROCEDURAL.value == "procedural"
    assert MemoryType.PREFERENCE.value == "preference"
    assert MemoryType.WORKSPACE.value == "workspace"
    assert MemoryType.MISSION.value == "mission"
    assert MemoryType.AGENT.value == "agent"
    assert MemoryType.SESSION.value == "session"
    assert MemoryType.DOCUMENT.value == "document"
    assert MemoryType.SYSTEM.value == "system"
    assert MemoryType.TEMPORARY.value == "temporary"
    
    # Test is_transient
    assert MemoryType.SESSION.is_transient == True
    assert MemoryType.TEMPORARY.is_transient == True
    assert MemoryType.SEMANTIC.is_transient == False
    assert MemoryType.EPISODIC.is_transient == False
    
    # Test is_high_privilege
    assert MemoryType.SYSTEM.is_high_privilege == True
    assert MemoryType.MISSION.is_high_privilege == True
    assert MemoryType.AGENT.is_high_privilege == True
    assert MemoryType.SESSION.is_high_privilege == False
    # Note: there is no MemoryType.USER, it's PREFERENCE for user prefs
    assert MemoryType.PREFERENCE.is_high_privilege == False
    
    # Check that PREFERENCE is not high privilege (it's user preference)
    assert MemoryType.PREFERENCE.is_high_privilege == False


def test_memory_boundary_enum():
    assert MemoryBoundary.USER.value == "user"
    assert MemoryBoundary.WORKSPACE.value == "workspace"
    assert MemoryBoundary.SESSION.value == "session"
    assert MemoryBoundary.AGENT.value == "agent"
    assert MemoryBoundary.SYSTEM.value == "system"
    
    # Test allows() method
    assert MemoryBoundary.USER.allows(MemoryBoundary.USER) == True
    assert MemoryBoundary.USER.allows(MemoryBoundary.WORKSPACE) == False
    assert MemoryBoundary.WORKSPACE.allows(MemoryBoundary.USER) == True
    assert MemoryBoundary.WORKSPACE.allows(MemoryBoundary.WORKSPACE) == True
    assert MemoryBoundary.WORKSPACE.allows(MemoryBoundary.SESSION) == False
    assert MemoryBoundary.SESSION.allows(MemoryBoundary.WORKSPACE) == True
    assert MemoryBoundary.SESSION.allows(MemoryBoundary.AGENT) == False
    assert MemoryBoundary.AGENT.allows(MemoryBoundary.SESSION) == True
    assert MemoryBoundary.AGENT.allows(MemoryBoundary.SYSTEM) == False
    assert MemoryBoundary.SYSTEM.allows(MemoryBoundary.AGENT) == True
    assert MemoryBoundary.SYSTEM.allows(MemoryBoundary.SYSTEM) == True


def test_memory_origin_enum():
    assert MemoryOrigin.USER.value == "user"
    assert MemoryOrigin.CONVERSATION.value == "conversation"
    assert MemoryOrigin.TOOL.value == "tool"
    assert MemoryOrigin.WEB.value == "web"
    assert MemoryOrigin.EMAIL.value == "email"
    assert MemoryOrigin.FILE.value == "file"
    assert MemoryOrigin.AGENT.value == "agent"
    assert MemoryOrigin.SYSTEM.value == "system"
    assert MemoryOrigin.UNKNOWN.value == "unknown"
    
    # Test default_trust
    assert MemoryOrigin.USER.default_trust == 0.9
    assert MemoryOrigin.SYSTEM.default_trust == 0.9
    assert MemoryOrigin.AGENT.default_trust == 0.7
    assert MemoryOrigin.CONVERSATION.default_trust == 0.6
    assert MemoryOrigin.TOOL.default_trust == 0.6
    assert MemoryOrigin.FILE.default_trust == 0.5
    assert MemoryOrigin.EMAIL.default_trust == 0.4
    assert MemoryOrigin.WEB.default_trust == 0.3
    assert MemoryOrigin.UNKNOWN.default_trust == 0.2


def test_memory_state_enum():
    assert MemoryState.ACTIVE.value == "active"
    assert MemoryState.ARCHIVED.value == "archived"
    assert MemoryState.FORGOTTEN.value == "forgotten"
    assert MemoryState.QUARANTINED.value == "quarantined"


def test_trust_level_enum():
    assert TrustLevel.UNTRUSTED.value == "untrusted"
    assert TrustLevel.LOW.value == "low"
    assert TrustLevel.MEDIUM.value == "medium"
    assert TrustLevel.HIGH.value == "high"
    assert TrustLevel.VERIFIED.value == "verified"


def test_verification_level_enum():
    assert VerificationLevel.UNVERIFIED.value == "unverified"
    assert VerificationLevel.SINGLE_SOURCE.value == "single_source"
    assert VerificationLevel.CORROBORATED.value == "corroborated"
    assert VerificationLevel.CONTRADICTED.value == "contradicted"