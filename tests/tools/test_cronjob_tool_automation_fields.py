"""Master-13 automation fields exposed via the cronjob model tool.

Behavior contracts (not snapshots): invalid values fail closed with a clean
tool error, valid values persist on the job record, and empty-object updates
clear the optional Master-13 fields.
"""

import json

import pytest

from tools.cronjob_tools import cronjob


def _payload(raw: str) -> dict:
    data = json.loads(raw)
    assert isinstance(data, dict)
    return data


class TestCreateWithAutomationFields:
    def test_create_accepts_all_master13_fields(self):
        raw = cronjob(
            action="create",
            prompt="daily digest",
            schedule="0 9 * * *",
            name="m13-fields",
            timezone="Asia/Kolkata",
            missed_policy="run_on_start",
            resource_limits={"max_runtime_seconds": 900, "max_turns": 30},
            breaker={"failure_threshold": 3, "cooldown_seconds": 600},
        )
        data = _payload(raw)
        assert data["success"] is True
        job = data["job"]
        assert job["timezone"] == "Asia/Kolkata"
        assert job["missed_policy"] == "run_on_start"
        assert job["resource_limits"] == {
            "max_runtime_seconds": 900,
            "max_turns": 30,
        }
        assert job["breaker"] == {"failure_threshold": 3, "cooldown_seconds": 600}

    def test_create_with_event_trigger(self):
        raw = cronjob(
            action="create",
            prompt="process inbox",
            schedule="every 1h",
            name="m13-triggered",
            trigger={
                "kind": "event",
                "event_types": ["file.created"],
                "allow_untrusted": True,
            },
        )
        data = _payload(raw)
        assert data["success"] is True
        trigger = data["job"]["trigger"]
        assert trigger["kind"] == "event"
        assert trigger["event_types"] == ["file.created"]
        assert trigger["allow_untrusted"] is True

    def test_create_invalid_timezone_fails_closed(self):
        raw = cronjob(
            action="create",
            prompt="x",
            schedule="every 1h",
            timezone="Mars/Olympus_Mons",
        )
        data = _payload(raw)
        assert data["success"] is False
        assert "IANA" in str(data.get("error", "")) or "timezone" in str(data.get("error", ""))

    def test_create_invalid_missed_policy_fails_closed(self):
        raw = cronjob(
            action="create",
            prompt="x",
            schedule="every 1h",
            missed_policy="whenever",
        )
        data = _payload(raw)
        assert data["success"] is False
        assert "missed_policy" in str(data.get("error", ""))

    def test_create_invalid_resource_limit_fails_closed(self):
        raw = cronjob(
            action="create",
            prompt="x",
            schedule="every 1h",
            resource_limits={"max_turns": -5},
        )
        data = _payload(raw)
        assert data["success"] is False


class TestUpdateWithAutomationFields:
    def _create(self) -> dict:
        return _payload(
            cronjob(
                action="create",
                prompt="base",
                schedule="every 2h",
                name="m13-update-target",
            )
        )["job"]

    def test_update_sets_and_clears_fields(self):
        job = self._create()
        jid = job["job_id"]

        updated = _payload(
            cronjob(
                action="update",
                job_id=jid,
                missed_policy="skip",
                resource_limits={"max_turns": 10},
            )
        )
        assert updated["success"] is True
        assert updated["job"]["missed_policy"] == "skip"
        assert updated["job"]["resource_limits"] == {"max_turns": 10}

        cleared = _payload(
            cronjob(
                action="update",
                job_id=jid,
                resource_limits={},
            )
        )
        assert cleared["success"] is True
        assert "resource_limits" not in cleared["job"]

    def test_update_trigger_attach_and_clear(self):
        job = self._create()
        jid = job["job_id"]

        attached = _payload(
            cronjob(
                action="update",
                job_id=jid,
                trigger={"kind": "event", "event_types": ["webhook.received"]},
            )
        )
        assert attached["success"] is True
        assert attached["job"]["trigger"]["event_types"] == ["webhook.received"]

        cleared = _payload(cronjob(action="update", job_id=jid, trigger={}))
        assert cleared["success"] is True
        assert "trigger" not in cleared["job"]

    def test_update_invalid_trigger_fails_closed(self):
        job = self._create()
        raw = cronjob(
            action="update",
            job_id=job["job_id"],
            trigger={"kind": "telepathy"},
        )
        data = _payload(raw)
        assert data["success"] is False
