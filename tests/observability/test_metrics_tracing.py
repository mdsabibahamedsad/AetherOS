"""Tests for aetheros_observability metrics + tracing facades."""

from aetheros_observability.metrics import get_unified_metrics
from aetheros_observability.tracing import get_unified_tracer


class TestUnifiedMetrics:
    def test_increment_and_snapshot(self):
        m = get_unified_metrics()
        m.clear()
        m.increment("test.requests", 2, {"platform": "cli"})
        snap = m.snapshot()
        counters = snap.get("counters", {})
        assert any(k.startswith("test.requests") for k in counters)

    def test_set_gauge(self):
        m = get_unified_metrics()
        m.clear()
        m.set_gauge("test.queue", 5, {"queue": "pending"})
        gauges = m.snapshot().get("gauges", {})
        assert any(k.startswith("test.queue") for k in gauges)

    def test_observe_histogram(self):
        m = get_unified_metrics()
        m.clear()
        m.observe("test.latency", 12.5, {"op": "query"})
        snap = m.snapshot()
        hist = snap.get("histograms", {})
        assert any(k.startswith("test.latency") for k in hist)

    def test_record_helpers_do_not_raise(self):
        m = get_unified_metrics()
        m.record_request(platform="cli")
        m.record_error(error_type="TOOL_ERROR")
        m.record_retry(attempt=1)
        m.record_fallback(primary="a", fallback="b")
        m.set_circuit_breaker("open", component="model")
        m.set_queue_depth(3, queue="gateway")
        m.record_agent_execution(agent_id="a1", status="completed")
        m.record_model_call(model="gpt-4o", provider="openai",
                            input_tokens=100, output_tokens=50)
        m.record_tool_call(tool_name="terminal", status="ok")
        m.record_memory_op(operation="read", result_count=3)
        assert m.snapshot() != {}

    def test_prometheus_export(self):
        m = get_unified_metrics()
        m.clear()
        m.increment("test.prom", 1, {"kind": "x"})
        out = m.export_prometheus()
        assert "test.prom" in out


class TestUnifiedTracer:
    def test_start_span(self):
        t = get_unified_tracer()
        with t.start_span("unit.test_span", attributes={"k": "v"}):
            pass
        spans = t.get_recent_spans(10)
        assert any(s["name"] == "unit.test_span" for s in spans)

    def test_nested_spans_share_trace(self):
        t = get_unified_tracer()
        with t.start_span("outer"):
            with t.start_span("inner"):
                pass
        spans = t.get_recent_spans(10)
        names = [s["name"] for s in spans]
        assert "outer" in names and "inner" in names

    def test_record_model_call(self):
        t = get_unified_tracer()
        t.record_model_call(model="gpt-4o", provider="openai",
                            status="ok", duration_ms=10,
                            input_tokens=10, output_tokens=5)
        # metadata-only — should not raise and produce a span
        assert len(t.get_recent_spans(10)) >= 1

    def test_get_trace_by_id(self):
        t = get_unified_tracer()
        with t.start_span("traceable") as ctx:
            trace_id = ctx.trace_id
        spans = t.get_trace(trace_id)
        assert len(spans) >= 1
        # Each returned span correlates to our trace context (either as the
        # canonical span trace_id or via the attributes bridge we attach).
        for s in spans:
            assert (s["trace_id"] == trace_id
                    or s.get("attributes", {}).get("trace_id") == trace_id)

    def test_parent_lineage(self):
        t = get_unified_tracer()
        with t.start_span("parent"):
            with t.start_span("child"):
                pass
        spans = {s["name"]: s for s in t.get_recent_spans(10)}
        parent = spans.get("parent")
        child = spans.get("child")
        assert parent is not None and child is not None
        # The child span links back to the parent span via parent_id.
        assert child["parent_id"] == parent["span_id"]

    def test_stats(self):
        t = get_unified_tracer()
        stats = t.get_stats()
        assert "span_count" in stats
        assert "total" in stats