"""CLI interface for the Universal Tool Runtime.

Integrates with AetherOS CLI to provide:
- Tool runtime status and health
- Tool listings with details
- Execution history and metrics
- Permission and safety rule management
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional

from tool_runtime.manager import ToolRuntimeManager, get_runtime_manager
from tool_runtime.register_all import quick_start


def print_header(text: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}")


def cmd_status() -> None:
    """Show runtime manager status."""
    manager = get_runtime_manager()
    if manager.state.value == "stopped":
        print("Tool Runtime is STOPPED")
        print("Run 'aetheros tool-runtime start' to initialize")
        return

    health = manager.health_check()
    print_header("TOOL RUNTIME STATUS")
    print(f"  State:              {health['state']}")
    print(f"  Runtimes:           {health['total_runtimes']} total, {health['healthy_runtimes']} healthy")
    print(f"  Running Executions: {health['running_executions']}")
    print(f"  Uptime:             {health['uptime_seconds']:.1f}s")
    print(f"  History:            {health['history_count']} entries")

    if health['unhealthy_runtimes']:
        print(f"\n  Unhealthy Runtimes:")
        for u in health['unhealthy_runtimes']:
            print(f"    - {u}")

    metrics = manager.get_metrics()
    print_header("EXECUTION METRICS")
    print(f"  Total:     {metrics['total_executions']}")
    print(f"  Success:   {metrics['successful']}")
    print(f"  Failed:    {metrics['failed']}")
    print(f"  Rate:      {metrics['success_rate']}%")
    print(f"  Avg Time:  {metrics['avg_duration_ms']}ms")


def cmd_list() -> None:
    """List all registered runtimes."""
    manager = get_runtime_manager()
    runtimes = manager.list_runtimes()

    if not runtimes:
        print("No runtimes registered")
        return

    print_header(f"REGISTERED RUNTIMES ({len(runtimes)})")
    print(f"  {'ID':<25} {'Name':<25} {'Category':<15} {'Risk':<10} {'Approval':<10}")
    print(f"  {'-'*25} {'-'*25} {'-'*15} {'-'*10} {'-'*10}")
    for r in sorted(runtimes, key=lambda x: x["id"]):
        approval = "YES" if r["requires_approval"] else "no"
        print(f"  {r['id']:<25} {r['name']:<25} {r['category']:<15} {r['risk_level']:<10} {approval:<10}")


def cmd_history(limit: int = 20) -> None:
    """Show execution history."""
    manager = get_runtime_manager()
    history = manager.get_history(limit=limit)

    print_header(f"EXECUTION HISTORY (last {limit})")
    if not history:
        print("  No history available")
        return

    for h in reversed(history[-20:]):
        status = "✓" if h["success"] else "✗"
        tool = h["tool_name"][:25]
        dur = f"{h['duration_ms']:.0f}ms" if h["duration_ms"] else "?"
        err = f" - {h['error'][:50]}" if h.get("error") else ""
        print(f"  {status} {tool:<25} {dur:<10} {err}")


def cmd_permissions() -> None:
    """Show permission system status."""
    from tool_runtime.permission import get_permission_system
    perm = get_permission_system()

    print_header("PERMISSION SYSTEM")
    status = perm.get_status()
    print(f"  Max Risk Level: {status['max_risk_default']}")
    print(f"  Rules:          {status['rules_count']}")

    rules = perm.get_rules()
    if rules:
        print(f"\n  {'Effect':<8} {'Pattern':<25} {'Risk Max':<12} {'Reason'}")
        print(f"  {'-'*8} {'-'*25} {'-'*12} {'-'*30}")
        for r in rules:
            risk = r["risk_level_max"] or "-"
            print(f"  {r['effect']:<8} {r['tool_pattern']:<25} {risk:<12} {(r['reason'] or '')[:30]}")


def cmd_safety() -> None:
    """Show safety engine rules."""
    from tool_runtime.safety import get_safety_engine
    safety = get_safety_engine()

    print_header("SAFETY ENGINE RULES")
    rules = safety.get_rules_summary()
    if rules:
        print(f"  {'Name':<25} {'Severity':<10} {'Block':<8} {'Description'}")
        print(f"  {'-'*25} {'-'*10} {'-'*8} {'-'*40}")
        for r in rules:
            block = "BLOCK" if r["block"] else "warn"
            print(f"  {r['name']:<25} {r['severity']:<10} {block:<8} {r['description'][:40]}")


def cmd_observability() -> None:
    """Show observability metrics."""
    from tool_runtime.observability import get_observability_collector
    obs = get_observability_collector()

    print_header("OBSERVABILITY")
    metrics = obs.get_metrics()
    print(f"  Total Executions:  {metrics['total_executions']}")
    print(f"  Success Rate:      {metrics['success_rate_pct']}%")
    print(f"  Total Retries:     {metrics['total_retries']}")
    print(f"  Approval Requests: {metrics['approval_requests']}")
    print(f"  Tools Tracked:     {metrics['tools_tracked']}")

    latency = metrics["latency"]
    print(f"\n  Latency (all tools):")
    print(f"    Avg: {latency['avg_ms']}ms  P95: {latency['p95_ms']}ms  P99: {latency['p99_ms']}ms")
    print(f"    Min: {latency['min_ms']}ms  Max: {latency['max_ms']}ms  Count: {latency['count']}")

    breakdown = obs.get_tool_breakdown()
    if breakdown:
        print(f"\n  {'Tool':<25} {'Rate':<10} {'Avg':<12} {'P95':<12} {'Calls'}")
        print(f"  {'-'*25} {'-'*10} {'-'*12} {'-'*12} {'-'*8}")
        for b in sorted(breakdown, key=lambda x: -x["total_calls"])[:10]:
            print(f"  {b['tool_name']:<25} {b['success_rate_pct']:<10} {b['avg_duration_ms']:<12} {b['p95_duration_ms']:<12} {b['total_calls']:<8}")


def cmd_planner() -> None:
    """Show execution planner status."""
    from tool_runtime.planner import get_execution_planner
    planner = get_execution_planner()

    print_header("EXECUTION PLANNER")
    status = planner.get_status()
    print(f"  Total Plans: {status['total_plans']}")
    print(f"  Active:      {status['active']}")
    print(f"  Completed:   {status['completed']}")
    print(f"  Failed:      {status['failed']}")

    plans = planner.list_plans()
    if plans:
        print(f"\n  Recent Plans:")
        for p in plans[-5:]:
            print(f"    [{p['status']}] {p['goal'][:60]}")


def cmd_start() -> None:
    """Initialize and start the tool runtime."""
    print("Starting Universal Tool Runtime...")
    try:
        manager = quick_start()
        print(f"[OK] Tool Runtime started with {manager.get_runtime_count()} runtimes")
    except Exception as e:
        print(f"[FAIL] Failed to start Tool Runtime: {e}")


def cmd_test() -> None:
    """Run all tool runtime tests."""
    from tool_runtime.testing.tests import ToolRuntimeTests
    results = ToolRuntimeTests.run_all()
    print_header("TEST RESULTS")
    print(f"  Total:  {results['total']}")
    print(f"  Passed: {results['total'] - results['failures'] - results['errors']}")
    print(f"  Failed: {results['failures']}")
    print(f"  Errors: {results['errors']}")
    print(f"  Success: {results['success']}")


def main(args: Optional[List[str]] = None) -> None:
    """CLI entry point for tool runtime management."""
    if args is None:
        args = sys.argv[1:]

    commands = {
        "status": cmd_status,
        "list": cmd_list,
        "history": cmd_history,
        "permissions": cmd_permissions,
        "safety": cmd_safety,
        "observability": cmd_observability,
        "planner": cmd_planner,
        "start": cmd_start,
        "test": cmd_test,
    }

    if not args or args[0] in ("--help", "-h", "help"):
        print("AetherOS Universal Tool Runtime CLI")
        print()
        print("Usage: python -m tool_runtime.cli <command>")
        print()
        print("Commands:")
        for cmd in commands:
            print(f"  {cmd:<20} {commands[cmd].__doc__ or ''}")
        return

    cmd = args[0]
    handler = commands.get(cmd)
    if not handler:
        print(f"Unknown command: {cmd}")
        print("Available: " + ", ".join(commands.keys()))
        return

    handler()


if __name__ == "__main__":
    main()
