"""Tests for aetheros_security.runtime module."""

from aetheros_security.runtime import (
    SecurityContext,
    clear_security_context,
    get_security_context,
    run_with_security_context,
    set_security_context,
)


def test_security_context_default():
    """Test that get_security_context returns a default empty context."""
    ctx = get_security_context()
    assert isinstance(ctx, SecurityContext)
    assert ctx.principal == ""
    assert ctx.user_id == ""
    assert ctx.agent_id == ""
    assert ctx.session_token == ""
    assert ctx.delegation_depth == 0
    assert ctx.mission == ""
    assert ctx.task == ""
    assert ctx.attributes == {}


def test_security_context_set_and_get():
    """Test setting and getting a security context."""
    ctx = SecurityContext(
        principal="user:alice",
        user_id="alice",
        agent_id="agent:123",
        session_token="token123",
        delegation_depth=2,
        mission="mission-1",
        task="task-456",
        attributes={"key": "value"},
    )
    set_security_context(ctx)
    
    retrieved = get_security_context()
    assert retrieved.principal == "user:alice"
    assert retrieved.user_id == "alice"
    assert retrieved.agent_id == "agent:123"
    assert retrieved.session_token == "token123"
    assert retrieved.delegation_depth == 2
    assert retrieved.mission == "mission-1"
    assert retrieved.task == "task-456"
    assert retrieved.attributes == {"key": "value"}


def test_security_context_clear():
    """Test clearing the security context."""
    ctx = SecurityContext(principal="user:alice")
    set_security_context(ctx)
    
    clear_security_context()
    
    retrieved = get_security_context()
    assert retrieved.principal == ""
    assert retrieved.user_id == ""
    assert retrieved.agent_id == ""
    assert retrieved.session_token == ""
    assert retrieved.delegation_depth == 0
    assert retrieved.mission == ""
    assert retrieved.task == ""
    assert retrieved.attributes == {}


def test_run_with_security_context():
    """Test running a function with a temporary security context."""
    def get_ctx():
        return get_security_context()
    
    # Default context should be empty
    assert get_ctx().principal == ""
    
    # Run with a custom context
    custom_ctx = SecurityContext(
        principal="user:test",
        user_id="test",
        agent_id="agent:test",
        session_token="test-token",
        delegation_depth=1,
        mission="test-mission",
        task="test-task",
        attributes={"test": "value"},
    )
    
    result_ctx = run_with_security_context(get_ctx, context=custom_ctx)
    assert result_ctx.principal == "user:test"
    assert result_ctx.user_id == "test"
    assert result_ctx.agent_id == "agent:test"
    assert result_ctx.session_token == "test-token"
    assert result_ctx.delegation_depth == 1
    assert result_ctx.mission == "test-mission"
    assert result_ctx.task == "test-task"
    assert result_ctx.attributes == {"test": "value"}
    
    # Context should be restored to default after the function
    assert get_ctx().principal == ""