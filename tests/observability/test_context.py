"""Tests for aetheros_observability.context — trace-context propagation."""

from aetheros_observability.context import (
    HEADER_NAMES,
    TraceContext,
    begin_trace,
    clear_current_context,
    fork_context,
    get_current_context,
    get_or_create_context,
    new_trace_id,
    set_current_context,
)


class TestContextIds:
    def test_trace_id_uniqueness(self):
        assert new_trace_id() != new_trace_id()
        assert len(new_trace_id()) >= 8

    def test_begin_trace_creates_root(self):
        ctx = begin_trace()
        assert ctx.trace_id
        assert ctx.span_id
        assert ctx.parent_span_id is None
        assert ctx.correlation_id
        assert ctx.causation_id is None
        assert ctx.span_id != ctx.trace_id

    def test_begin_trace_with_metadata(self):
        ctx = begin_trace(session_id="s1", mission_id="m1", task_id="t1",
                          agent_id="a1", correlation_id="c1")
        assert ctx.session_id == "s1"
        assert ctx.mission_id == "m1"
        assert ctx.task_id == "t1"
        assert ctx.agent_id == "a1"
        assert ctx.correlation_id == "c1"


class TestContextPropagation:
    def test_set_and_get_current(self):
        clear_current_context()
        assert get_current_context() is None
        ctx = begin_trace()
        set_current_context(ctx)
        assert get_current_context() is ctx

    def test_get_or_create_creates(self):
        clear_current_context()
        ctx = get_or_create_context()
        assert ctx.trace_id
        assert get_current_context() is ctx

    def test_clear_removes(self):
        ctx = begin_trace()
        set_current_context(ctx)
        clear_current_context()
        assert get_current_context() is None


class TestHeaderRoundTrip:
    def test_inject_extract(self):
        ctx = begin_trace(session_id="sess")
        headers = ctx.inject_headers()
        assert HEADER_NAMES["trace_id"] in headers
        assert headers[HEADER_NAMES["trace_id"]] == ctx.trace_id
        parsed = TraceContext.extract_headers(headers)
        assert parsed.trace_id == ctx.trace_id
        assert parsed.span_id == ctx.span_id
        assert parsed.correlation_id == ctx.correlation_id
        assert parsed.session_id == ctx.session_id

    def test_extract_missing(self):
        parsed = TraceContext.extract_headers({})
        # No inbound headers → a fresh context is generated, never None.
        assert parsed is not None
        assert parsed.trace_id
        assert parsed.correlation_id is None


class TestFork:
    def test_fork_keeps_parent_lineage(self):
        parent = begin_trace()
        child = fork_context()
        assert child.correlation_id == parent.correlation_id
        assert child.trace_id == parent.trace_id
        assert child.span_id != parent.span_id
        assert child.parent_span_id == parent.span_id

    def test_child_keeps_lineage(self):
        parent = begin_trace()
        child = parent.child()
        assert child.trace_id == parent.trace_id
        assert child.parent_span_id == parent.span_id
        assert child.correlation_id == parent.correlation_id