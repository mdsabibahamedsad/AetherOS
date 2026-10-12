"""Long-running research via the existing cron scheduler (P58).

Creates real cron jobs whose prompt resumes a research task; monitoring
jobs re-run research on a schedule so findings stay current. No new
scheduler machinery is introduced — this composes ``cron.jobs.create_job``.
"""

from __future__ import annotations

from typing import Dict, Optional


def schedule_research(
    research_id: str,
    query: str,
    every: str = "1d",
    deliver: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict:
    """Create a recurring job that re-runs (and thus refreshes) research.

    Idempotent-ish: duplicate names for the same task are rejected by the
    job store's name handling; callers can pass a custom name.
    """
    from cron.jobs import create_job

    job_name = name or f"research-{research_id}"
    prompt = (
        f"Run `aetheros research resume {research_id}` in the terminal, then "
        f"print `aetheros research report {research_id}` and summarize any "
        f"changes versus the previous run. Original question: {query}"
    )
    kwargs: Dict = {
        "prompt": prompt,
        "schedule": f"every {every}",
        "name": job_name,
        "origin": "research",
        "repeat": True,
    }
    if deliver:
        kwargs["deliver"] = deliver
    return create_job(**kwargs)


def cancel_scheduled(research_id: str) -> bool:
    """Remove the monitor job for a research task, if present."""
    from cron import jobs as cron_jobs

    target = f"research-{research_id}"
    for job in cron_jobs.list_jobs(include_disabled=True):
        meta = job.get("meta") if isinstance(job, dict) else None
        name = (
            job.get("name") if isinstance(job, dict) else getattr(job, "name", "")
        ) or ""
        if name == target or (isinstance(meta, dict) and meta.get("name") == target):
            jid = job.get("id") if isinstance(job, dict) else getattr(job, "id", None)
            if jid:
                cron_jobs.remove_job(jid)
                return True
    return False
