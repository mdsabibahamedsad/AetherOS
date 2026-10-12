"""Tests for aetheros_security.response (emergency stop, lockdown,
incidents, health score)."""

import pytest

from aetheros_security.response import (
    IncidentSeverity,
    IncidentStatus,
    ResponseState,
    SecurityIncident,
    SecurityResponseManager,
)


@pytest.fixture
def resp():
    return SecurityResponseManager()


class TestEmergencyStop:
    def test_stop_and_recover(self, resp):
        assert resp.emergency_stop("compromise detected")
        assert resp.get_state() == ResponseState.EMERGENCY_STOP.value
        assert resp.is_emergency_stop()
        assert resp.recover_from_stop()
        assert resp.get_state() == ResponseState.RECOVERY.value

    def test_double_stop_noop(self, resp):
        assert resp.emergency_stop("first")
        assert not resp.emergency_stop("second")

    def test_double_recover_noop(self, resp):
        assert not resp.recover_from_stop()  # not stopped yet

    def test_emergency_stop_notifier(self, resp):
        events = []
        resp.register_notifier(lambda msg, details: events.append(msg))
        resp.emergency_stop("why")
        assert any("emergency stop" in e.lower() for e in events)

    def test_lockdown_gate(self, resp):
        assert resp.lockdown("maintenance")
        assert resp.get_state() == ResponseState.LOCKDOWN.value
        assert resp.is_locked_down()
        assert resp.release_lockdown()
        assert not resp.is_locked_down()

    def test_lockdown_propagates_to_authz(self, resp):
        from aetheros_security.authz import get_authorization_engine
        resp.lockdown("test")
        assert get_authorization_engine().emergency_stop_active
        resp.release_lockdown()
        assert not get_authorization_engine().emergency_stop_active


class TestIncidentLifecycle:
    def test_open_incident(self, resp):
        incident = resp.open_incident("anomalous outbound",
                                      severity="high")
        assert incident.incident_id
        assert incident.severity == IncidentSeverity.HIGH
        assert incident.status == IncidentStatus.DETECTED
        assert resp.get_incident(incident.incident_id) is incident

    def test_transition_to_close(self, resp):
        incident = resp.open_incident("x", severity="medium")
        assert resp.transition(incident.incident_id, IncidentStatus.CLOSED)
        assert incident.status == IncidentStatus.CLOSED
        assert incident.closed_at > 0

    def test_transition_sets_closed_at(self, resp):
        incident = resp.open_incident("x", severity="low")
        resp.transition(incident.incident_id, IncidentStatus.CLOSED)
        assert incident.closed_at > 0

    def test_unknown_incident_transition(self, resp):
        assert not resp.transition("missing", IncidentStatus.CLOSED)

    def test_list_incidents_filters_closed(self, resp):
        a = resp.open_incident("a", severity="high")
        resp.transition(a.incident_id, IncidentStatus.CLOSED)
        resp.open_incident("b", severity="low")
        assert len(resp.list_incidents(open_only=True)) == 1
        assert len(resp.list_incidents()) == 2

    def test_timeline_recorded(self, resp):
        incident = resp.open_incident("x", severity="medium")
        resp.transition(incident.incident_id, IncidentStatus.CONTAINED)
        events = [e["event"] for e in incident.timeline]
        assert "detected" in events
        assert "status:contained" in events


class TestHealth:
    def test_empty_health_score(self, resp):
        health = resp.run_health_checks()
        assert health["state"] == ResponseState.NORMAL.value
        assert health["score"] == 0
        assert health["total"] == 0

    def test_health_score_full(self, resp):
        resp.register_health_check("a", lambda: True)
        resp.register_health_check("b", lambda: True)
        health = resp.run_health_checks()
        assert health["score"] == 100
        assert health["passed"] == 2

    def test_health_check_failure_lowers_score(self, resp):
        resp.register_health_check("a", lambda: True)
        resp.register_health_check("b", lambda: False)
        health = resp.run_health_checks()
        assert health["score"] == 50

    def test_default_health_checks_registered(self, resp):
        resp.register_default_health_checks()
        health = resp.run_health_checks()
        assert health["total"] >= 7
        assert "encryption" in health["categories"]

    def test_emergency_stop_state_in_health(self, resp):
        resp.emergency_stop("x")
        health = resp.run_health_checks()
        assert health["state"] == ResponseState.EMERGENCY_STOP.value


class TestSecurityIncidentModel:
    def test_defaults(self):
        incident = SecurityIncident(incident_id="i1", title="t")
        assert incident.status == IncidentStatus.DETECTED
        assert incident.created_at > 0
        assert incident.closed_at == 0

    def test_incident_dict_roundtrip(self):
        incident = SecurityIncident(
            incident_id="i2", title="t", severity=IncidentSeverity.HIGH,
            affected_principals=["alice"], metadata={"host": "h1"})
        data = incident.to_dict()
        assert data["severity"] == "high"
        assert data["affected_principals"] == ["alice"]

    def test_add_event(self):
        incident = SecurityIncident(incident_id="i3", title="t")
        incident.add_event("investigating", {"note": "x"})
        assert incident.timeline[-1]["event"] == "investigating"
        assert incident.timeline[-1]["details"] == {"note": "x"}