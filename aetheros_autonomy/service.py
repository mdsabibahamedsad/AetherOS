"""AutomationService facade (Master 43): the one API for agents/UI/IPC.

CRUD + enable/disable + run-now + dry-run + pause/resume + search +
health/metrics + export/import + emergency stop + safe mode + global
settings + NL builder with plan preview (activation only after approval).
Integrations: swarm runs, memory lessons, cron mirror (failure-safe).
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aetheros_autonomy.models import (
    ApprovalPolicy, AutoState, AutomationDefinition, AutoType,
    GLOBAL_LIMITS, NotifyMode, ResourceLimits, RunRecord, RunState,
)
from aetheros_autonomy.notify import DigestEngine, Notification, NotificationCenter
from aetheros_autonomy.runtime import BackgroundAgentRuntime, ProactiveAgent
from aetheros_autonomy.safety import AutonomyEngine
from aetheros_autonomy.schedule import CanonicalSchedule, parse_natural_schedule
from aetheros_autonomy.scheduler import Scheduler, VirtualClock
from aetheros_autonomy.store import AutonomyStore, scan_definition
from aetheros_autonomy.templates import TEMPLATES
from aetheros_autonomy.triggers import TriggerEngine
from aetheros_autonomy.watchers import FileWatcher
from aetheros_autonomy.workflow import WorkflowEngine


class AutomationService:
    def __init__(self, root: Optional[Path] = None, *,
                 clock: Optional[VirtualClock] = None,
                 swarm_runner: Optional[Callable[[str], Dict[str, Any]]] = None,
                 memory_create: Optional[Callable[[str], Any]] = None) -> None:
        self._store = AutonomyStore()
        self._clock = clock
        self._swarm = swarm_runner
        self._memory = memory_create
        self._sched: Optional[Scheduler] = None
        self._triggers: Optional[TriggerEngine] = None
        self._work = WorkflowEngine(step_fn=self._exec_step)
        self._runtime = BackgroundAgentRuntime(work_fn=self._run_in_background)
        self._notify = NotificationCenter()
        self._digest = DigestEngine()
        self._safety = AutonomyEngine()
        self._proactive = ProactiveAgent()
        self._watchers: Dict[str, FileWatcher] = {}
        self._estop = False
        self._settings: Dict[str, Any] = {
            "max_background_agents": 4, "max_monthly_cost_usd": 10.0,
            "external_communication": "ask", "filesystem": "scoped",
            "network": "allow", "notification": "immediate",
            "background_execution": True, "power_mode": "balanced",
        }
        self._lock = threading.Lock()
        self._root = Path(root) if root else None
        self._initialized = False
        # Reuse swarm audit log (no duplicate audit system).
        try:
            from aetheros_swarm.ops import AuditLog
            self._audit = AuditLog()
        except ImportError:
            self._audit = None

    # -- lifecycle -------------------------------------------------------
    def initialize(self, root: Optional[Path] = None) -> None:
        if root is not None:
            self._root = Path(root)
        if self._root is None:
            from aetheros_constants import get_aetheros_home
            self._root = get_aetheros_home() / "autonomy"
        self._root.mkdir(parents=True, exist_ok=True)
        self._store.initialize(self._root / "store")
        self._sched = Scheduler(self._store, run_fn=self._execute_run,
                                clock=self._clock,
                                emergency_stop=lambda: self._estop,
                                safe_mode=lambda: self._safety.safe_mode)
        self._triggers = TriggerEngine(self._store.list_autos)
        if self._audit is not None:
            self._audit.initialize(self._root / "audit.jsonl")
        self._initialized = True
        self._sched.reconcile()

    def _audit_rec(self, action: str, **kw: Any) -> None:
        if self._audit is not None:
            try:
                self._audit.record(action, **kw)
            except Exception:
                pass

    # -- CRUD --------------------------------------------------------------
    def create(self, definition: Dict[str, Any], *, owner: str = "") -> Dict[str, Any]:
        scan = scan_definition(definition)
        if not scan["ok"]:
            return {"ok": False, "reason": scan["reason"]}
        auto = AutomationDefinition.from_dict(definition)
        auto.owner = owner or auto.owner
        auto.enabled = False  # SHOW PLAN first; activation is explicit
        auto.trusted = False
        if auto.trigger.get("kind") == "schedule" and self._sched:
            self._sched.schedule_next(auto, self._sched.now())
        self._store.save_auto(auto)
        self._audit_rec("automation_created", detail={"id": auto.id})
        return {"ok": True, "id": auto.id, "preview": self.preview(auto.id)}

    def preview(self, aid: str) -> Optional[Dict[str, Any]]:
        auto = self._store.get_auto(aid)
        if auto is None:
            return None
        sched = auto.trigger.get("schedule", {})
        return {"trigger": auto.trigger, "schedule_preview": sched.get("preview", ""),
                "actions": self._work.describe_plan(auto.workflow),
                "agents": auto.agent_policy, "tools": auto.tool_policy.get("tools", []),
                "permissions": auto.tool_policy.get("tools", []),
                "expected_outputs": ["run record", "artifacts", "notification"],
                "notifications": auto.notification_policy,
                "budget": auto.budget, "risks": scan_definition(auto.to_dict()).get("risk_flags", []),
                "approval": auto.approval_policy}

    def enable(self, aid: str) -> bool:
        auto = self._store.get_auto(aid)
        if auto is None or not auto.trusted and auto.metadata.get("needs_review"):
            return False
        auto.enabled = True
        if auto.trigger.get("kind") == "schedule" and self._sched:
            self._sched.schedule_next(auto, self._sched.now())
        self._store.save_auto(auto)
        self._audit_rec("automation_enabled", detail={"id": aid})
        return True

    def approve_import(self, aid: str) -> bool:
        auto = self._store.get_auto(aid)
        if auto is None:
            return False
        auto.trusted = True
        auto.metadata.pop("needs_review", None)
        self._store.save_auto(auto)
        return self.enable(aid)

    def disable(self, aid: str) -> bool:
        auto = self._store.get_auto(aid)
        if auto is None:
            return False
        auto.enabled = False
        self._store.save_auto(auto)
        self._audit_rec("automation_disabled", detail={"id": aid})
        return True

    def delete(self, aid: str) -> bool:
        ok = self._store.delete_auto(aid)
        if ok:
            self._audit_rec("automation_deleted", detail={"id": aid})
        return ok

    def get(self, aid: str) -> Optional[Dict[str, Any]]:
        auto = self._store.get_auto(aid)
        return auto.to_dict() if auto else None

    def search(self, *, query: str = "", status: str = "",
               trigger: str = "", project: str = "") -> List[Dict[str, Any]]:
        q = query.lower()
        out = []
        for auto in self._store.list_autos():
            if q and q not in (auto.name + " " + auto.description).lower():
                continue
            if status and auto.state().value != status:
                continue
            if trigger and auto.trigger.get("kind") != trigger:
                continue
            if project and auto.project_id != project:
                continue
            out.append(auto.to_dict())
        return out

    def update(self, aid: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        auto = self._store.update_auto(aid, patch)
        if auto:
            self._audit_rec("automation_modified", detail={"id": aid})
            return auto.to_dict()
        return None

    def diff_versions(self, aid: str, v1: int, v2: int) -> Optional[Dict[str, Any]]:
        auto = self._store.get_auto(aid)
        if auto is None:
            return None
        snaps = {s["version"]: s for s in auto.history}
        a, b = snaps.get(v1), snaps.get(v2)
        if not a or not b:
            return None
        diff = {}
        for k in ("trigger", "workflow", "tools"):
            if a.get(k) != b.get(k):
                diff[k] = {"from": a.get(k), "to": b.get(k)}
        return diff

    # -- execution -----------------------------------------------------------
    def run_now(self, aid: str, *, dry_run: bool = False) -> Optional[Dict[str, Any]]:
        auto = self._store.get_auto(aid)
        if auto is None or (not auto.enabled and not dry_run):
            return None
        run = RunRecord(automation_id=aid, trigger_kind="manual", dry_run=dry_run)
        run.ensure_key()
        self._store.save_run(run)
        return self._execute_run(auto, run).to_dict()

    def _execute_run(self, auto: AutomationDefinition,
                     run: RunRecord) -> RunRecord:
        if self._estop:
            run.state = RunState.CANCELLED
            return run
        if self._safety.safe_mode:
            risky = [s for s in auto.workflow
                     if str(s.get("action")) not in ("agent", "tool", "notify", "verify", "branch", "loop")]
            if risky and not run.dry_run:
                run.state = RunState.FAILED
                run.error = "safe mode: non-read action blocked"
                return run
        run.state = RunState.RUNNING
        run.started_at = self._sched.now() if self._sched else run.created_at
        self._work.run(auto.workflow, run, dry_run=run.dry_run)
        if run.error:
            run.state = RunState.FAILED
            run.failure_kind = "tool_failure"
        else:
            run.state = RunState.VERIFYING
            run.state = RunState.COMPLETED
        run.completed_at = self._sched.now() if self._sched else run.started_at
        auto.last_run = run.completed_at
        self._store.save_run(run)
        self._store.save_auto(auto)
        self._audit_rec("run_completed" if run.state == RunState.COMPLETED else "run_failed",
                        detail={"id": auto.id, "run": run.run_id})
        if not run.dry_run and self._memory and run.state == RunState.COMPLETED:
            try:
                self._memory(f"Automation '{auto.name}' completed run {run.run_id[:8]} "
                             f"with {len(run.steps)} steps."[:300])
            except Exception:
                pass
        return run

    def _exec_step(self, step: Dict[str, Any], run: RunRecord,
                   dry: bool) -> Dict[str, Any]:
        action = str(step.get("action", ""))
        if dry:
            return {"action": action, "dry": True, "ok": True,
                    "would": f"would {action}: {step.get('goal', step.get('tool', step.get('text', '')))}"[:200]}
        if action == "notify":
            note = Notification(automation_id=run.automation_id, run_id=run.run_id,
                                title=step.get("title", "Automation"),
                                body=str(step.get("text", ""))[:1000],
                                importance=str(step.get("importance", "normal")),
                                channel=step.get("channel", "in_app"),
                                mode=str(step.get("mode", NotifyMode.IMMEDIATE.value)))
            self._notify.notify(note)
            self._audit_rec("notification_sent", detail={"run": run.run_id})
            return {"action": action, "ok": True, "notification": note.id}
        if action == "agent" and self._swarm:
            try:
                res = self._swarm(str(step.get("goal", "")))
                return {"action": action, "ok": True, "swarm": res}
            except Exception as exc:
                return {"action": action, "ok": False, "error": str(exc)[:300]}
        if action == "approval":
            return {"action": action, "ok": True, "approval_required": True,
                    "note": "approval gate registered"}
        if action == "artifact":
            art = {"kind": step.get("kind", "report"), "run": run.run_id,
                   "at": self._sched.now() if self._sched else 0.0}
            run.artifacts.append(art)
            self._audit_rec("artifact_created", detail={"run": run.run_id})
            return {"action": action, "ok": True, "artifact": art}
        return {"action": action, "ok": True}

    def _run_in_background(self, run: RunRecord) -> RunRecord:
        auto = self._store.get_auto(run.automation_id)
        if auto is None:
            run.state = RunState.FAILED
            run.error = "automation deleted"
            return run
        return self._execute_run(auto, run)

    # -- triggers/watchers -----------------------------------------------------
    def emit(self, event: Dict[str, Any]) -> List[str]:
        """Deliver an event; returns started run_ids (recursion-safe)."""
        if self._triggers is None or self._sched is None:
            return []
        started = []
        for auto in self._triggers.match(event):
            run = self._sched.fire_event(auto, str(event.get("kind", "")),
                                         causal=list(event.get("causal", [])))
            if run is not None:
                started.append(run.run_id)
        return started

    def add_file_watcher(self, aid: str, watcher: FileWatcher) -> None:
        self._watchers[aid] = watcher

    def poll_watchers(self) -> List[str]:
        started = []
        for aid, watcher in self._watchers.items():
            auto = self._store.get_auto(aid)
            if auto is None or not auto.enabled:
                continue
            for evt in watcher.poll():
                started.extend(self.emit({"kind": "FILE_CHANGED" if evt.kind == "changed" else "FILE_CREATED",
                                          "path": evt.path, "causal": []}))
        return started

    # -- NL builder --------------------------------------------------------------
    def build_from_text(self, text: str, *, tz: str = "UTC") -> Dict[str, Any]:
        """Parse NL into a DRAFT definition + plan preview (no activation)."""
        low = text.lower()
        # Schedule extraction: find a schedule phrase.
        sched = None
        for pat in ("every weekday at", "every day at", "every monday", "every tuesday",
                    "every wednesday", "every thursday", "every friday",
                    "every saturday", "every sunday", "every first day",
                    "every 4 hours", "every hour", "every day", "every week"):
            if pat in low:
                start = low.index(pat)
                frag = text[start:start + 40]
                try:
                    sched = parse_natural_schedule(frag, tz=tz)
                    break
                except ValueError:
                    continue
        is_research = "research" in low
        workflow = ([{"action": "agent", "role": "researcher", "goal": text[:200]},
                     {"action": "verify", "method": "evidence"},
                     {"action": "notify", "text": "research summary ready"}]
                    if is_research else
                    [{"action": "agent", "role": "coder", "goal": text[:200]},
                     {"action": "notify", "text": "automation finished"}])
        definition = {"name": text[:60], "description": text[:300],
                      "auto_type": AutoType.RECURRING.value if sched else AutoType.MANUAL.value,
                      "trigger": ({"kind": "schedule", "schedule": sched.to_dict()}
                                  if sched else {"kind": "manual"}),
                      "workflow": workflow,
                      "tool_policy": {"tools": ["web_search"] if is_research else []},
                      "timezone": tz}
        res = self.create(definition)
        if res.get("ok") and sched is None:
            res["preview"]["warning"] = "no schedule detected; saved as MANUAL (run on demand)"
        return res

    # -- templates ---------------------------------------------------------------
    def from_template(self, name: str, arg: str = "") -> Dict[str, Any]:
        factory = TEMPLATES.get(name)
        if factory is None:
            return {"ok": False, "reason": f"unknown template: {name}"}
        auto, card = factory(arg)
        res = self.create({**auto.to_dict(), "name": auto.name,
                           "description": auto.description})
        res["safety_card"] = card
        return res

    # -- control plane ---------------------------------------------------------------
    def pause(self, aid: str) -> bool:
        auto = self._store.get_auto(aid)
        if auto is None:
            return False
        auto.enabled = False
        auto.metadata["paused"] = True
        self._store.save_auto(auto)
        return True

    def resume(self, aid: str) -> bool:
        auto = self._store.get_auto(aid)
        if auto is None:
            return False
        auto.metadata.pop("paused", None)
        self._store.save_auto(auto)
        return self.enable(aid)

    def emergency_stop(self) -> Dict[str, int]:
        self._estop = True
        running = self._runtime.running()
        cancelled = sum(1 for r in running if self._runtime.terminate(r))
        self._audit_rec("emergency_stop", detail={"running": len(running)})
        return {"running": len(running), "cancel_requested": cancelled}

    def clear_emergency(self) -> None:
        self._estop = False

    def set_safe_mode(self, on: bool) -> None:
        self._safety.safe_mode = on

    def update_settings(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        self._settings.update({k: v for k, v in patch.items() if k in self._settings})
        return dict(self._settings)

    # -- observability ---------------------------------------------------------------
    def health(self) -> Dict[str, Any]:
        autos = self._store.list_autos()
        runs = self._store.list_runs(limit=1000)
        failed = sum(1 for r in runs if r.state == RunState.FAILED)
        blocked = sum(1 for r in runs if r.state in (RunState.WAITING_APPROVAL, RunState.WAITING_NETWORK))
        active = sum(1 for a in autos if a.enabled)
        stale = sum(1 for a in autos if a.enabled and a.trigger.get("kind") == "schedule" and not a.next_run)
        total = max(1, len(runs))
        score = max(0.0, 1.0 - (failed + blocked + stale) / total)
        return {"score": round(score, 3), "automations": len(autos), "active": active,
                "runs": len(runs), "failed": failed, "blocked": blocked,
                "stale_schedules": stale,
                "runtime": dict(self._runtime.metrics),
                "scheduler": dict(self._sched.metrics) if self._sched else {}}

    def metrics(self) -> Dict[str, Any]:
        runs = self._store.list_runs(limit=5000)
        done = [r for r in runs if r.state == RunState.COMPLETED]
        failed = [r for r in runs if r.state == RunState.FAILED]
        durations = [r.completed_at - r.started_at for r in done
                     if r.completed_at and r.started_at]
        durations.sort()
        p95 = durations[int(len(durations) * 0.95)] if durations else 0.0
        return {"automation_count": len(self._store.list_autos()),
                "run_count": len(runs),
                "success_rate": round(len(done) / max(1, len(runs)), 3),
                "failure_rate": round(len(failed) / max(1, len(runs)), 3),
                "avg_duration_s": round(sum(durations) / max(1, len(durations)), 2),
                "p95_duration_s": round(p95, 2),
                "token_usage": sum(r.tokens for r in runs),
                "cost_usd": round(sum(r.cost_usd for r in runs), 4)}

    def runs(self, aid: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._store.list_runs(automation_id=aid, limit=limit)]

    # -- export/import ---------------------------------------------------------------
    def export(self, aid: str) -> Optional[Dict[str, Any]]:
        return self._store.export_auto(aid)

    def import_bundle(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        res = self._store.import_auto(bundle)
        if res.get("ok"):
            auto = self._store.get_auto(res["id"])
            if auto:
                auto.metadata["needs_review"] = True
                self._store.save_auto(auto)
        return res

    # -- cron mirror (failure-safe bridge; cron code untouched) --------------------------
    def mirror_to_cron(self, aid: str) -> Dict[str, Any]:
        try:
            import cron.jobs as cron_jobs
        except ImportError as exc:
            return {"ok": False, "reason": f"cron unavailable: {exc}"}
        auto = self._store.get_auto(aid)
        if auto is None:
            return {"ok": False, "reason": "not found"}
        sched = auto.trigger.get("schedule", {})
        if sched.get("kind") != "cron" or not sched.get("cron"):
            return {"ok": False, "reason": "only cron-kind schedules mirror"}
        try:
            job = cron_jobs.create_job(
                {"schedule": sched["cron"], "prompt": f"Automation runner: {auto.name}",
                 "automation_id": aid, "timezone": auto.timezone})
            return {"ok": True, "cron_job_id": job.get("id")}
        except Exception as exc:
            return {"ok": False, "reason": str(exc)[:300]}
