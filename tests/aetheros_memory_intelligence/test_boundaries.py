"""Tests for memory boundaries and isolation."""
import pytest
from aetheros_memory_intelligence.boundaries import AccessContext, BoundaryPolicy, MemoryBoundaries
from aetheros_memory_intelligence.schema import MemoryEntry
from aetheros_memory_intelligence.types import MemoryType, MemoryBoundary, MemoryOrigin, MemoryState


def test_access_context():
    # Empty context
    ctx = AccessContext()
    assert ctx.scoped() == False
    assert ctx.user_id == ""
    assert ctx.workspace_id == ""
    assert ctx.session_id == ""
    assert ctx.agent_id == ""
    assert ctx.is_admin == False
    
    # Partial context
    ctx = AccessContext(user_id="alice", workspace_id="ws1")
    assert ctx.scoped() == True
    assert ctx.user_id == "alice"
    assert ctx.workspace_id == "ws1"
    
    # Full context with admin
    ctx = AccessContext(
        user_id="bob", 
        workspace_id="ws2", 
        session_id="sess3", 
        agent_id="agent4",
        is_admin=True
    )
    assert ctx.scoped() == True
    assert ctx.is_admin == True


def test_boundary_policy_defaults():
    policy = BoundaryPolicy()
    assert policy.cross_workspace_allowed == False
    assert policy.session_overlaps_workspace == True
    assert policy.admin_bypasses == True


def test_boundary_policy_custom():
    policy = BoundaryPolicy(
        cross_workspace_allowed=True,
        session_overlaps_workspace=False,
        admin_bypasses=False
    )
    assert policy.cross_workspace_allowed == True
    assert policy.session_overlaps_workspace == False
    assert policy.admin_bypasses == False


def test_memory_boundaries_init():
    boundaries = MemoryBoundaries()
    assert boundaries._policy is not None
    
    custom_policy = BoundaryPolicy(cross_workspace_allowed=True)
    boundaries = MemoryBoundaries(custom_policy)
    assert boundaries._policy.cross_workspace_allowed == True


def test_can_write_system_requires_admin():
    boundaries = MemoryBoundaries()
    
    # SYSTEM memory requires admin
    entry = MemoryEntry(
        memory_type=MemoryType.SYSTEM,
        boundary=MemoryBoundary.SYSTEM,
        content="System memory"
    )
    
    # Non-admin cannot write
    ctx = AccessContext(user_id="user", is_admin=False)
    assert boundaries.can_write(entry, ctx) == False
    
    # Admin can write
    ctx = AccessContext(user_id="admin", is_admin=True)
    assert boundaries.can_write(entry, ctx) == True


def test_can_write_agent_boundary():
    boundaries = MemoryBoundaries()
    
    entry = MemoryEntry(
        memory_type=MemoryType.AGENT,
        boundary=MemoryBoundary.AGENT,
        agent_id="agent123",
        content="Agent memory"
    )
    
    # No agent_id in actor
    ctx = AccessContext(user_id="user")
    assert boundaries.can_write(entry, ctx) == False
    
    # Wrong agent_id
    ctx = AccessContext(agent_id="agent456")
    assert boundaries.can_write(entry, ctx) == False
    
    # Correct agent_id
    ctx = AccessContext(agent_id="agent123")
    assert boundaries.can_write(entry, ctx) == True
    
    # Admin bypass
    ctx = AccessContext(agent_id="agent456", is_admin=True)
    assert boundaries.can_write(entry, ctx) == True


def test_can_write_user_boundary():
    boundaries = MemoryBoundaries()
    
    entry = MemoryEntry(
        memory_type=MemoryType.PREFERENCE,
        boundary=MemoryBoundary.USER,
        user_id="user123",
        content="User preference"
    )
    
    # No user_id
    ctx = AccessContext(workspace_id="ws1")
    assert boundaries.can_write(entry, ctx) == False
    
    # Wrong user_id
    ctx = AccessContext(user_id="user456")
    assert boundaries.can_write(entry, ctx) == False
    
    # Correct user_id
    ctx = AccessContext(user_id="user123")
    assert boundaries.can_write(entry, ctx) == True
    
    # Admin bypass
    ctx = AccessContext(user_id="user456", is_admin=True)
    assert boundaries.can_write(entry, ctx) == True


def test_can_write_workspace_boundary():
    boundaries = MemoryBoundaries()  # cross_workspace_allowed=False by default
    
    entry = MemoryEntry(
        memory_type=MemoryType.WORKSPACE,
        boundary=MemoryBoundary.WORKSPACE,
        workspace_id="ws123",
        content="Workspace memory"
    )
    
    # No workspace_id
    ctx = AccessContext(user_id="user")
    assert boundaries.can_write(entry, ctx) == False
    
    # Wrong workspace_id
    ctx = AccessContext(workspace_id="ws456")
    assert boundaries.can_write(entry, ctx) == False
    
    # Correct workspace_id
    ctx = AccessContext(workspace_id="ws123")
    assert boundaries.can_write(entry, ctx) == True
    
    # Cross-workspace write denied by default
    ctx = AccessContext(workspace_id="ws789")
    assert boundaries.can_write(entry, ctx) == False
    
    # Admin can write cross-workspace
    ctx = AccessContext(workspace_id="ws789", is_admin=True)
    assert boundaries.can_write(entry, ctx) == True
    
    # With cross_workspace_allowed=True
    policy = BoundaryPolicy(cross_workspace_allowed=True)
    boundaries = MemoryBoundaries(policy)
    ctx = AccessContext(workspace_id="ws789")
    assert boundaries.can_write(entry, ctx) == True  # Non-admin can now write cross-workspace


def test_can_write_session_boundary():
    boundaries = MemoryBoundaries()  # session_overlaps_workspace=True by default
    
    entry = MemoryEntry(
        memory_type=MemoryType.EPISODIC,
        boundary=MemoryBoundary.SESSION,
        session_id="sess123",
        workspace_id="ws123",
        content="Session memory"
    )
    
    # Matching session_id
    ctx = AccessContext(session_id="sess123")
    assert boundaries.can_write(entry, ctx) == True
    
    # No session_id but matching workspace (due to session_overlaps_workspace=True)
    ctx = AccessContext(workspace_id="ws123")
    assert boundaries.can_write(entry, ctx) == True
    
    # No session_id, no workspace match
    ctx = AccessContext(workspace_id="ws456")
    assert boundaries.can_write(entry, ctx) == False
    
    # Admin bypass
    ctx = AccessContext(workspace_id="ws456", is_admin=True)
    assert boundaries.can_write(entry, ctx) == True
    
    # With session_overlaps_workspace=False
    policy = BoundaryPolicy(session_overlaps_workspace=False)
    boundaries = MemoryBoundaries(policy)
    ctx = AccessContext(workspace_id="ws123")  # Same workspace but no session overlap
    assert boundaries.can_write(entry, ctx) == False
    
    # Need exact session match
    ctx = AccessContext(session_id="sess123")
    assert boundaries.can_write(entry, ctx) == True


def test_enforce_write():
    boundaries = MemoryBoundaries()
    
    # Valid write
    entry = MemoryEntry(
        memory_type=MemoryType.SEMANTIC,
        boundary=MemoryBoundary.USER,
        user_id="user123",
        content="Valid memory"
    )
    ctx = AccessContext(user_id="user123")
    # Should not raise
    result = boundaries.enforce_write(entry, ctx)
    assert result == entry
    
    # Invalid write - should raise PermissionError
    entry = MemoryEntry(
        memory_type=MemoryType.SYSTEM,
        boundary=MemoryBoundary.SYSTEM,
        content="System memory"
    )
    ctx = AccessContext(user_id="user", is_admin=False)
    with pytest.raises(PermissionError, match="memory boundary denied"):
        boundaries.enforce_write(entry, ctx)


def test_can_read():
    boundaries = MemoryBoundaries()
    
    # SYSTEM readable only by admin
    entry = MemoryEntry(
        memory_type=MemoryType.SYSTEM,
        boundary=MemoryBoundary.SYSTEM,
        content="System mem"
    )
    assert boundaries.can_read(entry, AccessContext(is_admin=False)) == False
    assert boundaries.can_read(entry, AccessContext(is_admin=True)) == True
    
    # AGENT readable by same agent or admin
    entry = MemoryEntry(
        memory_type=MemoryType.AGENT,
        boundary=MemoryBoundary.AGENT,
        agent_id="agent123",
        content="Agent mem"
    )
    assert boundaries.can_read(entry, AccessContext(agent_id="agent456")) == False
    assert boundaries.can_read(entry, AccessContext(agent_id="agent123")) == True
    assert boundaries.can_read(entry, AccessContext(is_admin=True)) == True
    
    # USER readable only by same user (not even admin unless same user)
    entry = MemoryEntry(
        memory_type=MemoryType.PREFERENCE,
        boundary=MemoryBoundary.USER,
        user_id="user123",
        content="User pref"
    )
    assert boundaries.can_read(entry, AccessContext(user_id="user456")) == False
    assert boundaries.can_read(entry, AccessContext(user_id="user123")) == True
    assert boundaries.can_read(entry, AccessContext(user_id="user123", is_admin=True)) == True  # Admin who is same user can read
    
    # WORKSPACE readable by same workspace OR same user
    entry = MemoryEntry(
        memory_type=MemoryType.WORKSPACE,
        boundary=MemoryBoundary.WORKSPACE,
        workspace_id="ws123",
        user_id="user456",  # Different user wrote it
        content="Workspace mem"
    )
    assert boundaries.can_read(entry, AccessContext(workspace_id="ws123", user_id="user789")) == True  # Same workspace
    assert boundaries.can_read(entry, AccessContext(user_id="user456")) == True  # Same user (owner)
    assert boundaries.can_read(entry, AccessContext(workspace_id="ws456", user_id="user789")) == False  # Neither
    
    # SESSION readable by same session, OR same workspace (if overlap), OR same agent
    entry = MemoryEntry(
        memory_type=MemoryType.EPISODIC,
        boundary=MemoryBoundary.SESSION,
        session_id="sess123",
        workspace_id="ws123",
        agent_id="agent456",
        content="Session mem"
    )
    assert boundaries.can_read(entry, AccessContext(session_id="sess123")) == True
    assert boundaries.can_read(entry, AccessContext(workspace_id="ws123")) == True  # overlap
    assert boundaries.can_read(entry, AccessContext(agent_id="agent456")) == True  # same agent
    assert boundaries.can_read(entry, AccessContext(workspace_id="ws456")) == False
    assert boundaries.can_read(entry, AccessContext(agent_id="agent789")) == False


def test_filter_readable():
    boundaries = MemoryBoundaries()
    
    entries = [
        MemoryEntry(
            memory_type=MemoryType.SYSTEM,
            boundary=MemoryBoundary.SYSTEM,
            content="System 1"
        ),
        MemoryEntry(
            memory_type=MemoryType.SYSTEM,
            boundary=MemoryBoundary.SYSTEM,
            content="System 2"
        ),
        MemoryEntry(
            memory_type=MemoryType.PREFERENCE,
            boundary=MemoryBoundary.USER,
            user_id="alice",
            content="Alice's pref"
        ),
        MemoryEntry(
            memory_type=MemoryType.PREFERENCE,
            boundary=MemoryBoundary.USER,
            user_id="bob",
            content="Bob's pref"
        ),
        MemoryEntry(
            memory_type=MemoryType.WORKSPACE,
            boundary=MemoryBoundary.WORKSPACE,
            workspace_id="ws1",
            content="Workspace mem"
        )
    ]
    
    # Admin can read all
    ctx = AccessContext(is_admin=True)
    readable = boundaries.filter_readable(entries, ctx)
    assert len(readable) == 5
    
    # Regular user Alice can read:
    # - System entries? No (requires admin)
    # - Her own user pref
    # - Workspace mem (same workspace? need workspace_id)
    ctx = AccessContext(user_id="alice", workspace_id="ws1")
    readable = boundaries.filter_readable(entries, ctx)
    readable_ids = [e.content for e in readable]
    assert "Alice's pref" in readable_ids
    assert "Workspace mem" in readable_ids
    assert "System 1" not in readable_ids
    assert "System 2" not in readable_ids
    assert "Bob's pref" not in readable_ids
    
    # User Bob in different workspace
    ctx = AccessContext(user_id="bob", workspace_id="ws2")
    readable = boundaries.filter_readable(entries, ctx)
    readable_ids = [e.content for e in readable]
    assert "Bob's pref" in readable_ids
    assert "Workspace mem" not in readable_ids  # Different workspace
    assert "System 1" not in readable_ids
    assert "System 2" not in readable_ids
    assert "Alice's pref" not in readable_ids