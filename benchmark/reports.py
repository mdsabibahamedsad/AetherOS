"""Report generators (P64-70, P95) — markdown rendered ONLY from persisted
artifacts. With zero executed runs every section reports the empty state
honestly instead of inventing numbers."""

from __future__ import annotations

import time
from pathlib import Path
from typing import List, Optional

from benchmark.comparison import (
    HeadToHead,
    generate_claims,
    leaderboard,
    tradeoff_notes,
)
from benchmark.controller import BenchmarkController
from benchmark.dataset import verify_dataset


def _fmt(v) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:,.2f}".rstrip("0").rstrip(".")
    return str(v)


class ReportBuilder:
    def __init__(self, results_dir: Path):
        self.ctrl = BenchmarkController(Path(results_dir))
        self.results = self.ctrl.load_results()

    # ------------------------------------------------------------ P60

    def leaderboard_md(self) -> str:
        rows = leaderboard(self.results)
        if not rows:
            return ("| Rank | Agent | Overall | Verified Success | "
                    "P50 ms | Tokens | Cost | Reliability | Safety |\n"
                    "|---|---|---|---|---|---|---|---|---|\n"
                    "| - | no executed runs yet | - | - | - | - | - | - | - |\n")
        head = ("| Rank | Agent | Overall | Verified Success | P50 ms | "
                "Tokens/task | Cost/task | Reliability | Safety events |")
        sep = "|---|---|---|---|---|---|---|---|---|"
        lines = [head, sep]
        for r in rows:
            if r.get("rank") is None:
                lines.append(f"| – | {r['agent']} "
                             f"({r['unranked_reason']}) | – | – | – | – "
                             f"| – | – | – |")
                continue
            lines.append(
                f"| {r['rank']} | {r['agent']}{' 🔒capped' if r['security_capped'] else ''} "
                f"| {_fmt(r['overall'])} | {_fmt(r['success_verified'])} "
                f"| {_fmt(r['speed_p50_ms'])} | {_fmt(r['tokens_per_success'])} "
                f"| {_fmt(r['cost_per_task'])} | {_fmt(r['reliability'])} "
                f"| {r['safety_events']} |")
        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------ P48/49

    def head_to_head_md(self, aetheros: str = "aetheros",
                        baseline: str = "hermes") -> str:
        agents = {r.agent for r in self.results}
        if aetheros not in agents or baseline not in agents:
            return (f"No executed head-to-head between `{aetheros}` and "
                    f"`{baseline}` exists yet — INSUFFICIENT EVIDENCE.\n")
        try:
            t = HeadToHead(aetheros, baseline, self.results).table()
        except ValueError as exc:
            return f"INSUFFICIENT EVIDENCE ({exc})\n"
        lines = [f"Matched executed tasks: **{t['matched_tasks']}**",
                 ""]
        if t["fairness_flags"]:
            lines.append("**FAIRNESS WARNINGS**: " +
                         "; ".join(t["fairness_flags"]))
            lines.append("")
        for section, values in t.items():
            if section in ("agents", "matched_tasks", "fairness_flags"):
                continue
            lines.append(f"- **{section}**")
            for k, v in values.items():
                lines.append(f"  - {k}: {_fmt(v)}")
        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------ P62/63

    def claims_md(self, baselines=("hermes", "openclaw", "openhands",
                                   "claude-code", "codex")) -> str:
        out = []
        for b in baselines:
            out.append(f"### AetherOS vs {b}\n")
            for c in generate_claims("aetheros", b, self.results):
                out.append(f"- {c}")
            out.append("")
        return "\n".join(out)

    # ------------------------------------------------------------ P81

    def quality_control_md(self) -> str:
        report = verify_dataset()
        status = "OK" if report["ok"] else \
            f"PROBLEMS: {report['problems']}"
        trace_state = "no traces yet (no live runs)"
        if any(r.trace_reference for r in self.results):
            trace_state = "enabled"
        return (f"- dataset integrity: {report['version']}, "
                f"{report['tasks']} tasks, hash "
                f"`{report['content_hash']}` → {status}\n"
                f"- validator registry: 12 deterministic validators\n"
                f"- trace capture: {trace_state}\n")

    # ------------------------------------------------------------ P64-70

    def full_report(self) -> str:
        parts: List[str] = [
            "# AETHEROS BENCHMARK REPORT",
            "",
            f"_Generated from artifacts only · "
            f"{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}_",
            "",
            "## Methodology",
            "",
            "- Same task text for every agent (P5); same scoring validators "
            "(P44).",
            "- Same-model rule enforced via fairness fingerprint; violations "
            "emit FAIRNESS_WARNING (P4/P19-20).",
            "- BLOCKED executions are preserved with reasons (P9/P12).",
            "- Claims are generated exclusively from measured artifacts; "
            "missing data yields INSUFFICIENT EVIDENCE (P62/63).",
            "",
            "## Dataset quality control",
            "",
            self.quality_control_md(),
            "## Leaderboard",
            "",
            self.leaderboard_md(),
            "## Head-to-head: AetherOS vs Hermes",
            "",
            self.head_to_head_md("aetheros", "hermes"),
            "## Evidence-gated claims",
            "",
            self.claims_md(),
            "## Tradeoffs observed",
            "",
            "\n".join(f"- {n}" for n in tradeoff_notes(self.results)),
            "",
            "## Limitations",
            "",
            "- Agents without installed CLIs are NOT_TESTED, never scored.",
            "- Live runs cost tokens and execute only behind explicit "
            "`--allow-live`.",
            "- Cross-environment comparisons carry fairness warnings.",
            "",
        ]
        return "\n".join(parts)


__all__ = ["ReportBuilder"]
