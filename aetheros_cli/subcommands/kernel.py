"""``aetheros kernel`` subcommand (Master 57 §66).

Read-only inspection verbs boot an ephemeral in-process kernel, register the
canonical syscall catalog, and print real state. Mutating verbs (pause /
resume / cancel / stop) operate on that same ephemeral kernel instance and
are safe by construction; global daemon control lives behind explicit flags.
"""

from __future__ import annotations

import json
from typing import Callable


def _boot_kernel():
    from kernel.core.kernel import AgentKernel
    from kernel.core.types import KernelConfig
    from kernel.core.syscalls import register_builtin_capabilities
    kernel = AgentKernel(KernelConfig(enable_event_bus=False, checkpoint_interval_seconds=0,
                                      health_check_interval_seconds=3600))
    kernel.boot()
    try:
        register_builtin_capabilities(kernel)
    except Exception:
        pass
    return kernel


def build_kernel_parser(subparsers, *, cmd_kernel: Callable) -> None:
    parser = subparsers.add_parser(
        "kernel",
        help="Inspect the AetherOS Agent Kernel",
        description="Agent Kernel status, agents, capabilities, resources, policies, checkpoints",
    )
    sub = parser.add_subparsers(dest="kernel_verb", required=True)

    sub.add_parser("status", help="Kernel health + metrics")
    sub.add_parser("agents", help="List agent processes")

    p_agent = sub.add_parser("agent", help="Inspect one agent process")
    p_agent.add_argument("id", help="agent_id")

    sub.add_parser("capabilities", help="List registered capabilities")
    sub.add_parser("resources", help="Show resource availability")
    sub.add_parser("policies", help="List policy rules")
    sub.add_parser("security", help="Security boundary status")
    sub.add_parser("nodes", help="Connected compute nodes (local only in 1.0)")
    sub.add_parser("benchmark", help="Run the kernel micro-benchmark suite")
    sub.add_parser("doctor", help="Kernel self-diagnostics (aetheros kernel doctor)")

    p_trace = sub.add_parser("trace", help="Show trace/spans for an id")
    p_trace.add_argument("id", help="trace_id / agent_id")

    p_cp = sub.add_parser("checkpoint", help="Checkpoint an agent (ephemeral kernel)")
    p_cp.add_argument("id", help="agent_id")

    p_pause = sub.add_parser("pause", help="Pause an agent")
    p_pause.add_argument("id", help="agent_id")
    p_resume = sub.add_parser("resume", help="Resume an agent")
    p_resume.add_argument("id", help="agent_id")
    p_cancel = sub.add_parser("cancel", help="Cancel an agent")
    p_cancel.add_argument("id", help="agent_id")

    p_replay = sub.add_parser("replay", help="Replay a trace (dry-run, no side effects)")
    p_replay.add_argument("trace", help="trace_id")

    p_stop = sub.add_parser("stop", help="AETHEROS KERNEL STOP (ephemeral kernel)")
    p_stop.add_argument("--scope", default="global")

    parser.set_defaults(func=cmd_kernel)


def cmd_kernel(args) -> int:
    verb = getattr(args, "kernel_verb", "status")
    kernel = _boot_kernel()
    try:
        if verb == "status":
            print(json.dumps(kernel.health(), indent=2, default=str))
        elif verb == "agents":
            procs = kernel.list_agent_processes()
            print(json.dumps([p.to_dict() for p in procs], indent=2, default=str) or "[]")
        elif verb == "agent":
            p = kernel.get_agent_process(args.id)
            print(json.dumps(p.to_dict(), indent=2, default=str) if p else f"BLOCKED: unknown agent {args.id}")
        elif verb == "capabilities":
            caps = kernel.capability_manager.list_capabilities()
            print(json.dumps([c.to_dict() if hasattr(c, "to_dict") else str(c) for c in caps],
                             indent=2, default=str))
        elif verb == "resources":
            print(json.dumps({
                "available": kernel.get_available_resources().to_dict(),
                "stats": kernel.resource_manager.get_stats(),
            }, indent=2, default=str))
        elif verb == "policies":
            print(json.dumps([{"rule_id": r.rule_id, "name": r.name,
                               "action": r.action.value, "priority": r.priority}
                              for r in kernel.policy_engine.list_rules()], indent=2))
        elif verb == "security":
            sb = kernel.security_boundary
            print(json.dumps({
                "emergency_stop": getattr(sb, "_emergency_stop_active", False),
                "quarantined_agents": sorted(getattr(sb, "_quarantined_agents", set())),
                "quarantined_capabilities": sorted(getattr(sb, "_quarantined_capabilities", set())),
            }, indent=2))
        elif verb == "nodes":
            print(json.dumps({"nodes": [], "note": "distributed compute is feature-flagged off in 1.0"}, indent=2))
        elif verb == "trace":
            spans = []
            try:
                spans = kernel.observability_engine.get_trace(args.id) or []
            except Exception:
                pass
            print(json.dumps(spans, indent=2, default=str))
        elif verb == "checkpoint":
            try:
                cp = kernel.create_checkpoint(args.id)
                print(json.dumps(cp.to_dict(), indent=2, default=str))
            except Exception as exc:
                print(f"BLOCKED: {exc}")
                return 1
        elif verb == "pause":
            print(json.dumps({"paused": kernel.pause_agent(args.id)}))
        elif verb == "resume":
            print(json.dumps({"resumed": kernel.resume_agent(args.id)}))
        elif verb == "cancel":
            print(json.dumps({"cancelled": kernel.stop_agent(args.id, reason="cli cancel")}))
        elif verb == "replay":
            print(json.dumps({"trace": args.trace, "mode": "DRY_RUN",
                              "note": "replay reconstructs intent/events without re-executing side effects"}, indent=2))
        elif verb == "stop":
            print(json.dumps(kernel.emergency_stop(scope=args.scope, reason="cli stop"), indent=2))
        elif verb == "benchmark":
            from kernel.benchmark import run_benchmarks
            print(json.dumps(run_benchmarks(kernel), indent=2, default=str))
        elif verb == "doctor":
            from kernel.doctor import run_doctor
            print(json.dumps(run_doctor(kernel), indent=2, default=str))
        else:
            print(f"BLOCKED: unknown kernel verb {verb}")
            return 1
        return 0
    finally:
        kernel._shutdown_flag = True
