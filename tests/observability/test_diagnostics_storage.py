"""Tests for aetheros_observability diagnostics + storage."""

import json
import os

import pytest

from aetheros_constants import get_aetheros_home
from aetheros_observability.diagnostics import get_diagnostics_service
from aetheros_observability.storage import TelemetryStore, get_telemetry_store


class TestDiagnosticsService:
    def test_bundle_has_core_keys(self):
        svc = get_diagnostics_service()
        bundle = svc.bundle(config={"model": "gpt-4o"})
        assert "diagnostic_id" in bundle
        assert "generated_at" in bundle
        assert "health" in bundle
        assert "metrics" in bundle

    def test_bundle_redacts_secrets_from_config(self):
        svc = get_diagnostics_service()
        bundle = svc.bundle(config={
            "model": "gpt-4o",
            "providers": {
                "openai": {"api_key": "sk-1234567890abcdef"},
            },
        })
        summary = bundle["config_summary"]
        text = json.dumps(summary)
        assert "sk-1234567890abcdef" not in text

    def test_validate(self):
        svc = get_diagnostics_service()
        bundle = svc.bundle(config={})
        result = svc.validate(bundle)
        assert result["valid"] is True
        assert "issues" in result

    def test_export_json(self, tmp_path):
        svc = get_diagnostics_service()
        bundle = svc.bundle(config={})
        path = str(tmp_path / "diag.json")
        assert svc.export(bundle, path, "json") is True
        assert os.path.exists(path)
        data = json.loads(open(path).read())
        assert "diagnostic_id" in data

    def test_export_csv(self, tmp_path):
        svc = get_diagnostics_service()
        bundle = svc.bundle(config={})
        path = str(tmp_path / "diag.csv")
        assert svc.export(bundle, path, "csv") is True
        assert os.path.exists(path)

    def test_summarize(self):
        svc = get_diagnostics_service()
        bundle = svc.bundle(config={})
        summary = svc.summarize(bundle)
        assert isinstance(summary, dict)
        assert "health_status" in summary or "status" in summary


class TestTelemetryStore:
    def test_uses_aetheros_home(self):
        store = TelemetryStore()
        assert "observability" in str(store._db_path)
        assert str(get_aetheros_home()) in str(store._db_path)

    def test_save_and_query_event(self):
        store = TelemetryStore()
        store.save_event({
            "event_type": "gateway.request",
            "component": "gateway",
            "severity": "INFO",
            "message": "hello",
            "payload": {},
            "trace_id": "abc123",
        })
        events = store.query_events(limit=10)
        assert len(events) >= 1
        assert events[-1]["event_type"] == "gateway.request"

    def test_save_and_query_span(self):
        store = TelemetryStore()
        store.save_span({
            "name": "unit.span",
            "trace_id": "tr1",
            "span_id": "sp1",
            "duration_ms": 5.0,
            "status": "ok",
        })
        spans = store.query_spans(limit=10)
        assert any(s["span_id"] == "sp1" for s in spans)

    def test_save_incident(self):
        store = TelemetryStore()
        store.save_incident({
            "incident_id": "inc1",
            "key": "error:TOOL_ERROR:terminal",
            "severity": "ERROR",
            "component": "terminal",
            "count": 3,
        })
        incidents = store.query_incidents(active_only=False)
        assert any(i["incident_id"] == "inc1" for i in incidents)

    def test_save_evaluation(self):
        store = TelemetryStore()
        store.save_evaluation({
            "task_id": "task-1",
            "outcome": "completed",
            "duration_ms": 100,
            "cost_usd": 0.01,
        })
        evals = store.query_evaluations(limit=10)
        assert any(e["task_id"] == "task-1" for e in evals)

    def test_stats(self):
        store = TelemetryStore()
        stats = store.stats()
        assert "events" in stats
        assert "spans" in stats
        assert "incidents" in stats
        assert "evaluations" in stats

    def test_failure_isolation(self):
        # A malformed row must not crash the store or poison queries.
        store = TelemetryStore()
        ok = store.save_event({"bogus": "row"})
        assert ok in (True, False)
        events = store.query_events(limit=10)
        assert isinstance(events, list)

    def test_singleton(self):
        assert get_telemetry_store() is get_telemetry_store()