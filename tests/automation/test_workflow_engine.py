"""Master-13 slice 3: workflow engine end-to-end (no LLM — run_job is faked),
approval gates, durable runs."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def cron_env(tmp_path, monkeypatch):
    aetheros_home = tmp_path / ".aetheros"
    aetheros_home.mkdir(parents=True)
    monkeypatch.setenv("AETHEROS_HOME", str(aetheros_home))

    import cron.jobs as jobs_mod

    monkeypatch.setattr(jobs_mod, "HERMES_DIR", aetheros_home)
    monkeypatch.setattr(jobs_mod, "CRON_DIR", aetheros_home / "cron")
    monkeypatch.setattr(jobs_mod, "JOBS_FILE", aetheros_home / "cron" / "jobs.json")
    monkeypatch.setattr(jobs_mod, "OUTPUT_DIR", aetheros_home / "cron" / "output")

    from automation.events import reset_bus

    reset_bus()
    yield aetheros_home
    reset_bus()


class FakeRunner:
    """Stands in for cron.scheduler.run_job; records prompts per step id.

    The synthetic step job's first line of prompt identifies the step via the
    step's own prompt text.
    """

    def __init__(self):
        self.calls = []

    def __call__(self, job):
        self.calls.append(job.get("prompt") or "")
        if not self.script:
            first_line = (job.get("prompt") or "").splitlines()[0] if (job.get("prompt") or "").strip() else ""
            return True, "# ok", "ok:" + first_line[:20], None
        return self.script(job)

    script = None


@pytest.fixture
def fake_runner(monkeypatch):
    runner = FakeRunner()
    monkeypatch.setattr("cron.scheduler.run_job", runner)
    return runner


def _wf_job(steps=None, **kw):
    from cron.jobs import create_job

    workflow = {
        "steps": steps or [
            {"id": "a", "prompt": "STEP-A"},
            {"id": "b", "prompt": "STEP-B", "depends_on": ["a"]},
        ]
    }
    return create_job(prompt="ignored", schedule="every 1h", **kw) | {"workflow": workflow}


class TestEngineExecution:
    def test_sequential_chain_with_context(self, cron_env, fake_runner):
        from automation.workflow_engine import run_workflow

        job = _wf_job()
        success, doc, final_response, error = run_workflow(job)
        assert success and error is None
        assert len(fake_runner.calls) == 2
        # Step B receives A's output as context.
        assert "Output from step 'a'" in fake_runner.calls[1]
        assert final_response.startswith("ok:STEP-B")

    def test_failure_stop_blocks_downstream(self, cron_env, fake_runner):
        from automation import runs as run_store
        from automation.workflow_engine import run_workflow

        def boom(job):
            if "STEP-A" in (job.get("prompt") or ""):
                return False, "", "", "401 invalid api key"   # non-retryable
            raise AssertionError("step B must never run")

        fake_runner.script = boom
        job = _wf_job()
        success, doc, _, error = run_workflow(job)
        assert not success
        assert "auth" or "401" in str(error)
        run = run_store.active_run_for(job["id"])
        assert run is None          # terminal → no longer active
        history = run_store.list_runs(automation_id=job["id"])
        assert history[0]["steps"]["b"]["status"] == "pending"

    def test_retry_transient_then_success(self, cron_env, fake_runner):
        from automation import runs as run_store
        from automation.workflow_engine import run_workflow

        state = {"n": 0}

        def flaky(job):
            if "STEP-A" in (job.get("prompt") or ""):
                state["n"] += 1
                if state["n"] < 3:
                    return False, "", "", "connection timed out"   # transient+retryable
            return True, "fine", "fine", None

        fake_runner.script = flaky
        job = _wf_job(steps=[
            {"id": "a", "prompt": "STEP-A", "attempts": 5},
            {"id": "b", "prompt": "STEP-B", "depends_on": ["a"]},
        ])
        success, doc, _, error = run_workflow(job)
        assert success
        assert state["n"] == 3
        runs_seen = run_store.list_runs(automation_id=job["id"])
        assert runs_seen[0]["steps"]["a"]["attempts"] == 3

    def test_condition_false_skips_branch_and_completes(self, cron_env, fake_runner):
        from automation.workflow_engine import run_workflow

        job = _wf_job(steps=[
            {"id": "a", "prompt": "STEP-A"},
            {"id": "opt", "prompt": "STEP-OPT", "depends_on": ["a"],
             "condition": [{"path": "steps.a.status", "op": "eq", "value": "failed"}]},
        ])
        success, doc, _, error = run_workflow(job)
        assert success
        assert "| opt | skipped |" in doc
        assert "condition not met" in doc

    def test_cancel_between_steps(self, cron_env, fake_runner):
        from automation import runs as run_store
        from automation.workflow_engine import run_workflow

        def spy(job):
            prompt = job.get("prompt") or ""
            if "STEP-A" in prompt:
                run = run_store.active_run_for(job["id"])
                run_store.request_cancel(run)
            return True, "# ok", "ok:" + prompt[:20], None

        fake_runner.script = spy
        job = _wf_job()
        success, doc, _, error = run_workflow(job)
        assert not success
        assert error == "workflow cancelled"


class TestApprovalGate:
    def _gated_job(self):
        return _wf_job(steps=[
            {"id": "a", "prompt": "STEP-A"},
            {"id": "ship", "prompt": "STEP-SHIP", "depends_on": ["a"],
             "approval_required": True},
        ])

    def test_gate_pauses_then_approval_resumes(self, cron_env, fake_runner):
        from automation import approvals
        from automation.workflow_engine import run_workflow

        job = self._gated_job()
        notices = []
        # First invocation: A runs, then the gate pauses before 'ship'.
        success, doc, final_response, error = run_workflow(job, notify_fn=notices.append)
        assert success and final_response == "[SILENT]"   # silent wait, no delivery
        assert any("WAITING APPROVAL" in n for n in notices)
        prompts = "\n".join(fake_runner.calls)
        assert "STEP-A" in prompts and "STEP-SHIP" not in prompts

        pending = approvals.pending_request(job["id"])
        assert pending and pending["step_id"] == "ship"

        approvals.resolve(job["id"], approve=True)
        success, doc, final_response, error = run_workflow(job)
        assert success and final_response.startswith("ok:STEP-SHIP")

    def test_deny_fails_run_without_executing(self, cron_env, fake_runner):
        from automation import approvals, runs as run_store
        from automation.workflow_engine import run_workflow

        job = self._gated_job()
        run_workflow(job, notify_fn=lambda m: None)
        approvals.resolve(job["id"], approve=False)

        # Engine sees denial on next invocation.
        success, doc, _, error = run_workflow(job)
        assert not success
        prompts = "\n".join(fake_runner.calls)
        assert "STEP-SHIP" not in prompts
        runs_seen = run_store.list_runs(automation_id=job["id"])
        assert runs_seen[0]["status"] in ("failed", "cancelled")

    def test_expired_approval_never_executes(self, cron_env, fake_runner, monkeypatch):
        from datetime import datetime, timedelta, timezone

        from automation import approvals, workflow_engine
        from automation.workflow_engine import run_workflow

        job = self._gated_job()
        run_workflow(job, notify_fn=lambda m: None)
        request = approvals.load(job["id"])
        assert request and request["status"] == "pending"

        # Force expiry, then sweep like the dispatcher pump does.
        past = datetime.now(timezone.utc) - timedelta(seconds=1)
        stale = dict(request)
        stale["expires_at"] = past.isoformat()
        approvals._write(stale)
        expired = approvals.sweep_expired()
        assert len(expired) == 1
        workflow_engine.expire_pending_run(expired[0])

        run = None
        from automation import runs as run_store
        for candidate in run_store.list_runs(automation_id=job["id"], limit=10):
            if candidate["run_id"] == request["run_id"]:
                run = candidate
        assert run is not None
        assert run["status"] == "expired"
        assert "STEP-SHIP" not in "\n".join(fake_runner.calls)


class TestVersioning:
    def test_resume_uses_snapshotted_spec(self, cron_env, fake_runner):
        """Phase 19: an in-flight run continues on its starting version even
        after the automation's definition_version moved on."""
        import automation.runs as run_store
        from automation.workflow_engine import run_workflow
        from cron.jobs import apply_job_field_updates, create_job

        job = create_job(prompt="p", schedule="every 1h") | {"workflow": {"steps": [
            {"id": "a", "prompt": "STEP-A"},
            {"id": "b", "prompt": "STEP-B", "depends_on": ["a"]},
        ]}}
        spec_snapshot = {
            "steps": [
                {"id": "a", "prompt": "STEP-A", "depends_on": [], "condition": [],
                 "approval_required": False, "max_turns": None, "attempts": 1,
                 "on_failure": "stop", "script": None},
                {"id": "b", "prompt": "STEP-B", "depends_on": ["a"], "condition": [],
                 "approval_required": False, "max_turns": None, "attempts": 1,
                 "on_failure": "stop", "script": None},
            ],
            "order": ["a", "b"], "concurrency": 1, "on_failure": "stop",
        }
        run = run_store.new_run(job["id"], "snap-test", 7, spec_snapshot)
        run["spec"] = spec_snapshot
        run_store.mark_step(run, "a", "done", output="A-CONTEXT")
        # Simulate a restart mid-run: A done, B still pending.
        run["status"] = "running"
        run_store.save_run(run)

        # Meanwhile the definition moved to version 99.
        apply_job_field_updates(job["id"], {"definition_version": 99})

        success, doc, final_response, error = run_workflow(job)
        assert success
        stored = run_store.load_run(run["run_id"])
        assert stored["definition_version"] == 7          # pinned at start
        assert stored["steps"]["b"]["status"] == "done"
        # Context from the pre-restart A output reached step B.
        assert "Output from step 'a'" in fake_runner.calls[0]
        assert "A-CONTEXT" in fake_runner.calls[0]
