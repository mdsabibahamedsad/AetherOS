"""Tests for trust model and versioning."""
from aetheros_memory_intelligence.trust import TrustModel
from aetheros_memory_intelligence.versioning import VersionHistory, ConflictDetector, Conflict, EntryVersion
from aetheros_memory_intelligence.schema import MemoryEntry, MemoryEntryBuilder
from aetheros_memory_intelligence.types import TrustLevel, VerificationLevel, MemoryOrigin, MemoryType
import pytest
import time


def test_trust_model_init():
    model = TrustModel()
    assert model.decay_half_life_days == 90.0
    assert model.recency_weight == 0.2
    assert model.verification_bonus is not None
    assert model.verification_bonus[VerificationLevel.UNVERIFIED.value] == 0.0
    assert model.verification_bonus[VerificationLevel.SINGLE_SOURCE.value] == 0.05
    assert model.verification_bonus[VerificationLevel.CORROBORATED.value] == 0.15
    assert model.verification_bonus[VerificationLevel.CONTRADICTED.value] == -0.3


def test_trust_model_custom_params():
    model = TrustModel(
        decay_half_life_days=30.0,
        recency_weight=0.3
    )
    assert model.decay_half_life_days == 30.0
    assert model.recency_weight == 0.3


def test_trust_model_initial_trust():
    model = TrustModel()
    
    # Should clamp to [0,1] range
    assert model.initial_trust(-0.5) == 0.0
    assert model.initial_trust(0.0) == 0.0
    assert model.initial_trust(0.5) == 0.5
    assert model.initial_trust(1.0) == 1.0
    assert model.initial_trust(1.5) == 1.0


def test_trust_model_trust_for_basic():
    model = TrustModel()
    
    # Fresh entry with default trust (0.5) and no verification bonus
    entry = MemoryEntryBuilder()\
        .content("Test fact")\
        .scope(user_id="user123")\
        .provenance(trust=0.5, verification="unverified")\
        .build()
    
    trust = model.trust_for(entry)
    # Base 0.5 + bonus 0.0 = 0.5, no age decay yet
    assert abs(trust - 0.5) < 0.001


def test_trust_model_trust_with_verification_bonus():
    model = TrustModel()
    
    # Test each verification level
    base_trust = 0.5
    
    entry_unverified = MemoryEntryBuilder()\
        .content("Fact")\
        .scope(user_id="user123")\
        .provenance(trust=base_trust, verification="unverified")\
        .build()
    assert model.trust_for(entry_unverified) == base_trust + 0.0
    
    entry_single = MemoryEntryBuilder()\
        .content("Fact")\
        .scope(user_id="user123")\
        .provenance(trust=base_trust, verification="single_source")\
        .build()
    assert model.trust_for(entry_single) == base_trust + 0.05
    
    entry_corroborated = MemoryEntryBuilder()\
        .content("Fact")\
        .scope(user_id="user123")\
        .provenance(trust=base_trust, verification="corroborated")\
        .build()
    assert model.trust_for(entry_corroborated) == base_trust + 0.15
    
    entry_contradicted = MemoryEntryBuilder()\
        .content("Fact")\
        .scope(user_id="user123")\
        .provenance(trust=base_trust, verification="contradicted")\
        .build()
    assert model.trust_for(entry_contradicted) == base_trust - 0.3


def test_trust_model_trust_with_origin_trust():
    model = TrustModel()
    
    # Entry with explicit trust set (overrides base 0.5)
    entry = MemoryEntryBuilder()\
        .content("Fact")\
        .scope(user_id="user123")\
        .provenance(trust=0.8, verification="unverified")\
        .build()
    
    trust = model.trust_for(entry)
    # Should use the entry's trust value as base
    assert abs(trust - 0.8) < 0.001  # 0.8 base + 0.0 bonus


def test_trust_model_age_decay():
    model = TrustModel(decay_half_life_days=30.0)  # 30 day half-life for testing
    
    entry = MemoryEntryBuilder()\
        .content("Aging fact")\
        .scope(user_id="user123")\
        .provenance(trust=0.6, verification="unverified")\
        .build()
    
    # Fresh entry
    trust_fresh = model.trust_for(entry)
    assert abs(trust_fresh - 0.6) < 0.001
    
    # Simulate 30 days aging (one half-life)
    entry.updated_at = time.time() - (30 * 24 * 3600)
    trust_aged = model.trust_for(entry)
    # Should be half: 0.6 * 0.5 = 0.3
    assert abs(trust_aged - 0.3) < 0.001
    
    # Simulate 60 days aging (two half-lives)
    entry.updated_at = time.time() - (60 * 24 * 3600)
    trust_more_aged = model.trust_for(entry)
    # Should be quarter: 0.6 * 0.25 = 0.15
    assert abs(trust_more_aged - 0.15) < 0.001


def test_trust_model_transient_no_decay():
    model = TrustModel(decay_half_life_days=1.0)  # Short half-life
    
    # SESSION type should not decay
    entry_session = MemoryEntryBuilder()\
        .content("Session fact")\
        .scope(user_id="user123", session_id="sess123")\
        .type(MemoryType.SESSION)\
        .provenance(trust=0.8, verification="unverified")\
        .build()
    
    trust_fresh = model.trust_for(entry_session)
    # Move to past
    entry_session.updated_at = time.time() - (30 * 24 * 3600)
    trust_aged = model.trust_for(entry_session)
    
    assert abs(trust_fresh - trust_aged) < 0.001  # No decay
    
    # TEMPORARY type should not decay
    entry_temp = MemoryEntryBuilder()\
        .content("Temporary fact")\
        .scope(user_id="user123")\
        .type(MemoryType.TEMPORARY)\
        .provenance(trust=0.8, verification="unverified")\
        .build()
    
    trust_fresh = model.trust_for(entry_temp)
    entry_temp.updated_at = time.time() - (30 * 24 * 3600)
    trust_aged = model.trust_for(entry_temp)
    
    assert abs(trust_fresh - trust_aged) < 0.001  # No decay


def test_trust_model_confidence_calculation():
    model = TrustModel()
    
    entry = MemoryEntryBuilder()\
        .content("Test fact")\
        .scope(user_id="user123")\
        .provenance(trust=0.7, verification="unverified")\
        .build()
    
    trust = model.trust_for(entry)
    confidence = model.confidence(entry)
    
    # Confidence = (1 - w) * trust + w * recency
    # With recency ~1.0 (fresh entry), w=0.2
    # Expected: 0.8 * 0.7 + 0.2 * 1.0 = 0.56 + 0.2 = 0.76
    assert abs(confidence - 0.76) < 0.001
    
    # Test with older entry (lower recency)
    entry.updated_at = time.time() - (7 * 24 * 3600)  # 1 week ago
    confidence_older = model.confidence(entry)
    # Recency = exp(-168 / (24*7)) = exp(-1) = 0.368
    # Expected: 0.8 * trust + 0.2 * 0.368
    # trust should be same as trust (no age decay for non-transient? Wait, trust does decay)
    # Actually both trust and confidence decay with age, but differently
    # Just verify it's different and reasonable
    assert confidence_older < confidence
    assert confidence_older >= 0.0


def test_trust_model_trust_levels():
    model = TrustModel()
    
    assert model.trust_level(0.95) == TrustLevel.VERIFIED
    assert model.trust_level(0.85) == TrustLevel.HIGH
    assert model.trust_level(0.65) == TrustLevel.MEDIUM
    assert model.trust_level(0.40) == TrustLevel.LOW
    assert model.trust_level(0.20) == TrustLevel.UNTRUSTED
    assert model.trust_level(0.0) == TrustLevel.UNTRUSTED


def test_version_history_init():
    history = VersionHistory()
    assert len(history._history) == 0


def test_version_history_record():
    history = VersionHistory()
    
    entry = MemoryEntryBuilder()\
        .content("Version 1")\
        .scope(user_id="user123")\
        .build()
    entry.seal()
    
    version = history.record(entry, actor="user123")
    
    assert isinstance(version, EntryVersion)
    assert version.entry_id == entry.id
    assert version.version == entry.version
    assert version.content == entry.content
    assert version.checksum == entry.checksum
    assert version.actor == "user123"
    assert version.created_at > 0
    
    # Should be stored in history
    hist = history.history(entry.id)
    assert len(hist) == 1
    assert hist[0] == version


def test_version_history_multiple_records():
    history = VersionHistory()
    
    entry = MemoryEntryBuilder()\
        .content("Initial")\
        .scope(user_id="user123")\
        .build()
    entry.seal()
    
    # Record first version
    v1 = history.record(entry, actor="user1")
    
    # Update entry
    entry.content = "Updated"
    entry.seal()
    entry.bump_version()  # This increments version
    
    # Record second version
    v2 = history.record(entry, actor="user2")
    
    # Should have both versions
    hist = history.history(entry.id)
    assert len(hist) == 2
    assert hist[0].version == 1
    assert hist[1].version == 2
    assert hist[0].content == "Initial"
    assert hist[1].content == "Updated"
    assert hist[0].actor == "user1"
    assert hist[1].actor == "user2"
    
    # Version count
    assert history.version_count(entry.id) == 2


def test_version_history_truncate():
    history = VersionHistory()
    
    entry = MemoryEntryBuilder()\
        .content("Test")\
        .scope(user_id="user123")\
        .build()
    entry.seal()
    
    # Record 5 versions
    for i in range(5):
        entry.content = f"Version {i+1}"
        entry.seal()
        entry.bump_version()
        history.record(entry, actor=f"user{i+1}")
    
    assert history.version_count(entry.id) == 5
    
    # Truncate to keep only last 2
    history.truncate(entry.id, keep=2)
    
    assert history.version_count(entry.id) == 2
    hist = history.history(entry.id)
    assert hist[0].content == "Version 4"  # Kept last 2: v4 and v5
    assert hist[1].content == "Version 5"


def test_conflict_detector_init():
    detector = ConflictDetector()
    assert detector.enabled == True
    assert detector.threshold == 0.6
    assert len(detector._conflicts) == 0


def test_conflict_detector_disabled():
    detector = ConflictDetector(enabled=False)
    
    entry1 = MemoryEntryBuilder()\
        .content("Content A")\
        .scope(user_id="user123")\
        .metadata({"semantic_key": "key1"})\
        .build()
    entry2 = MemoryEntryBuilder()\
        .content("Content B")\
        .scope(user_id="user123")\
        .metadata({"semantic_key": "key1"})\
        .build()
    
    conflicts = detector.find_conflicts([entry1, entry2])
    assert len(conflicts) == 0  # Disabled


def test_conflict_detector_need_at_least_two():
    detector = ConflictDetector()
    
    entry = MemoryEntryBuilder()\
        .content("Solo content")\
        .scope(user_id="user123")\
        .metadata({"semantic_key": "key1"})\
        .build()
    
    conflicts = detector.find_conflicts([entry])
    assert len(conflicts) == 0


def test_conflict_detector_find_conflicts():
    detector = ConflictDetector(threshold=0.5)  # 50% similarity threshold
    
    # Same semantic key, different content
    entry1 = MemoryEntryBuilder()\
        .content("Python is a programming language")\
        .scope(user_id="user123")\
        .metadata({"semantic_key": "python_def"})\
        .build()
    entry2 = MemoryEntryBuilder()\
        .content("Python is a type of snake")\
        .scope(user_id="user123")\
        .metadata({"semantic_key": "python_def"})\
        .build()
    
    conflicts = detector.find_conflicts([entry1, entry2])
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict.entry_a == entry1.id
    assert conflict.entry_b == entry2.id
    assert conflict.key == "python_def"  # From semantic_key
    assert "same semantic_key" in conflict.reason
    assert "similarity=" in conflict.reason
    
    # Should be stored in detector
    all_conflicts = detector.all_conflicts()
    assert len(all_conflicts) == 1


def test_conflict_detector_no_conflict_high_similarity():
    detector = ConflictDetector(threshold=0.3)  # Low threshold
    
    # Very similar content
    entry1 = MemoryEntryBuilder()\
        .content("The quick brown fox")\
        .scope(user_id="user123")\
        .metadata({"semantic_key": "phrase"})\
        .build()
    entry2 = MemoryEntryBuilder()\
        .content("The quick brown fox jumps")\
        .scope(user_id="user123")\
        .metadata({"semantic_key": "phrase"})\
        .build()
    
    conflicts = detector.find_conflicts([entry1, entry2])
    # Similarity should be high (>0.3), so no conflict
    assert len(conflicts) == 0


def test_conflict_detector_no_conflict_different_keys():
    detector = ConflictDetector()
    
    entry1 = MemoryEntryBuilder()\
        .content("Apple is a fruit")\
        .scope(user_id="user123")\
        .metadata({"semantic_key": "apple"})\
        .build()
    entry2 = MemoryEntryBuilder()\
        .content("Banana is a fruit")\
        .scope(user_id="user123")\
        .metadata({"semantic_key": "banana"})\
        .build()
    
    conflicts = detector.find_conflicts([entry1, entry2])
    assert len(conflicts) == 0  # Different semantic keys


def test_conflict_detector_resolve():
    detector = ConflictDetector()
    
    entry1 = MemoryEntryBuilder()\
        .content("Content A")\
        .scope(user_id="user123")\
        .metadata({"semantic_key": "key1"})\
        .build()
    entry2 = MemoryEntryBuilder()\
        .content("Content B")\
        .scope(user_id="user123")\
        .metadata({"semantic_key": "key1"})\
        .build()
    
    conflicts = detector.find_conflicts([entry1, entry2])
    assert len(conflicts) == 1
    conflict = conflicts[0]
    
    # Resolve by picking entry1 as winner
    detector.resolve(conflict, winner_id=entry1.id)
    
    # Conflict should be removed
    all_conflicts = detector.all_conflicts()
    assert len(all_conflicts) == 0


def test_conflict_dataclass():
    conflict = Conflict(
        key="test key",
        entry_a="id1",
        entry_b="id2",
        detected_at=1234567890.0,
        reason="test reason"
    )
    
    assert conflict.key == "test key"
    assert conflict.entry_a == "id1"
    assert conflict.entry_b == "id2"
    assert conflict.detected_at == 1234567890.0
    assert conflict.reason == "test reason"


def test_entry_version_dataclass():
    version = EntryVersion(
        entry_id="entry123",
        version=2,
        content="Test content",
        checksum="abcd1234",
        created_at=1234567890.0,
        actor="user456"
    )
    
    assert version.entry_id == "entry123"
    assert version.version == 2
    assert version.content == "Test content"
    assert version.checksum == "abcd1234"
    assert version.created_at == 1234567890.0
    assert version.actor == "user456"
    
    # Test to_dict
    d = version.to_dict()
    assert d["entry_id"] == "entry123"
    assert d["version"] == 2
    assert d["content"] == "Test content"
    assert d["checksum"] == "abcd1234"
    assert d["created_at"] == 1234567890.0
    assert d["actor"] == "user456"