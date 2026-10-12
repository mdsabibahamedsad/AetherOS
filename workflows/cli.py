"""CLI command handlers and parser builder for workflow management."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


def build_workflow_subparser(subparsers) -> None:
    """Build the workflow CLI subcommand tree."""
    parser = subparsers.add_parser("workflow", help="Visual workflow engine")
    subs = parser.add_subparsers(dest="workflow_command")

    p = subs.add_parser("create", help="Create a new workflow")
    p.add_argument("name", help="Workflow name")
    p.add_argument("--description", "-d", default="", help="Description")
    p.add_argument("--schedule", "-s", default="", help="Schedule (cron or interval)")
    p.add_argument("--tags", nargs="*", default=[], help="Tags")
    p.add_argument("--from-template", "-t", default="", help="Template name")

    p = subs.add_parser("list", help="List workflows")
    p.add_argument("--status", default="", choices=["active", "archived", "draft"])
    p.add_argument("--category", "-c", default="", help="Filter by category")
    p.add_argument("--json", action="store_true", help="JSON output")

    p = subs.add_parser("show", help="Show workflow details")
    p.add_argument("workflow_id", help="Workflow ID")
    p.add_argument("--json", action="store_true", help="JSON output")

    p = subs.add_parser("run", help="Execute a workflow")
    p.add_argument("workflow_id", help="Workflow ID")
    p.add_argument("--input", "-i", default="", help="Input data (JSON string)")
    p.add_argument("--background", action="store_true",
                    help="Run in background queue")
    p.add_argument("--wait", action="store_true", help="Wait for completion")

    p = subs.add_parser("edit", help="Edit workflow configuration")
    p.add_argument("workflow_id", help="Workflow ID")
    p.add_argument("--name", default="", help="New name")
    p.add_argument("--description", default="", help="New description")
    p.add_argument("--schedule", default="", help="New schedule")
    p.add_argument("--status", default="",
                    choices=["active", "archived", "draft"])

    p = subs.add_parser("delete", help="Delete a workflow")
    p.add_argument("workflow_id", help="Workflow ID")
    p.add_argument("--force", "-f", action="store_true", help="Force delete")

    p = subs.add_parser("export", help="Export workflow as JSON")
    p.add_argument("workflow_id", help="Workflow ID")
    p.add_argument("--output", "-o", default="", help="Output file path")

    p = subs.add_parser("import", help="Import workflow from JSON")
    p.add_argument("file", help="JSON file path")
    p.add_argument("--name", default="", help="Override name")

    p = subs.add_parser("duplicate", help="Duplicate a workflow")
    p.add_argument("workflow_id", help="Workflow ID")
    p.add_argument("--name", default="", help="New name")

    p = subs.add_parser("history", help="Show execution history")
    p.add_argument("workflow_id", help="Workflow ID")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--json", action="store_true", help="JSON output")

    p = subs.add_parser("logs", help="Show workflow logs")
    p.add_argument("workflow_id", help="Workflow ID")
    p.add_argument("--execution", default="", help="Execution ID")
    p.add_argument("--level", default="", choices=["INFO", "WARNING", "ERROR"])
    p.add_argument("--query", default="", help="Search query")
    p.add_argument("--follow", "-f", action="store_true", help="Follow new logs")
    p.add_argument("--limit", type=int, default=50)

    p = subs.add_parser("schedule", help="Schedule management")
    p.add_argument("action", choices=["sync", "status", "list"],
                    default="status", nargs="?")
    p.add_argument("--workflow-id", default="", help="Target workflow")

    p = subs.add_parser("marketplace", help="Workflow marketplace")
    msubs = p.add_subparsers(dest="marketplace_action")
    mp = msubs.add_parser("list", help="List marketplace workflows")
    mp.add_argument("--category", default="")
    mp = msubs.add_parser("install", help="Install a marketplace workflow")
    mp.add_argument("marketplace_id", help="Marketplace workflow ID")
    mp.add_argument("--name", default="", help="Override name")
    mp = msubs.add_parser("info", help="Show marketplace workflow details")
    mp.add_argument("marketplace_id", help="Marketplace workflow ID")
    mp = msubs.add_parser("categories", help="List marketplace categories")

    p = subs.add_parser("templates", help="List starter templates")
    p = subs.add_parser("nodes", help="List available node types")
    p.add_argument("--category", "-c", default="",
                    choices=["trigger", "ai", "logic", "action", "agent", "mcp"])

    p = subs.add_parser("daemon", help="Start/stop workflow executor daemon")
    p.add_argument("action", choices=["start", "stop", "status"])

    p = subs.add_parser("dashboard", help="Show workflow dashboard")


def handle_workflow_command(args: argparse.Namespace, **kwargs) -> None:
    """Dispatch to workflow command handler."""
    cmd = args.workflow_command
    if not cmd:
        show_workflow_help()
        return
    from workflows.store import WorkflowStore
    store = WorkflowStore()
    handlers = {
        "create": _cmd_create,
        "list": _cmd_list,
        "show": _cmd_show,
        "run": _cmd_run,
        "edit": _cmd_edit,
        "delete": _cmd_delete,
        "export": _cmd_export,
        "import": _cmd_import,
        "duplicate": _cmd_duplicate,
        "history": _cmd_history,
        "logs": _cmd_logs,
        "schedule": _cmd_schedule,
        "marketplace": _cmd_marketplace,
        "templates": _cmd_templates,
        "nodes": _cmd_nodes,
        "daemon": _cmd_daemon,
        "dashboard": _cmd_dashboard,
    }
    handler = handlers.get(cmd)
    if handler:
        handler(args, store)
    else:
        print(f"Unknown workflow command: {cmd}")


def _print_workflow(wf, detailed: bool = False):
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    console = Console()
    console.print(Panel(f"[bold]{wf.name}[/bold]",
                        subtitle=f"ID: {wf.id}"))
    console.print(f"  [dim]Description:[/dim] {wf.description or '(none)'}")
    console.print(f"  [dim]Status:[/dim] {wf.status.value if hasattr(wf.status, 'value') else wf.status}")
    console.print(f"  [dim]Version:[/dim] {wf.version}")
    console.print(f"  [dim]Schedule:[/dim] {wf.schedule or '(none)'}")
    console.print(f"  [dim]Nodes:[/dim] {len(wf.nodes)}")
    console.print(f"  [dim]Connections:[/dim] {len(wf.connections)}")
    if detailed and wf.nodes:
        console.print("\n[bold]Nodes:[/bold]")
        node_table = Table("ID", "Type", "Label")
        for n in wf.nodes:
            node_table.add_row(n.id[:12] + "...", n.type, n.label)
        console.print(node_table)


def _cmd_create(args, store):
    from workflows.models import WorkflowConfig, WorkflowNode, Connection
    kwargs = {"name": args.name, "description": args.description,
              "schedule": args.schedule, "tags": list(args.tags)}
    if args.from_template:
        from workflows.templates import get_template
        template = get_template(args.from_template)
        if template:
            kwargs["nodes"] = template.get("nodes", [])
            kwargs["connections"] = template.get("connections", [])
    wf = WorkflowConfig(**kwargs)
    saved = store.save_workflow(wf)
    print(f"Created workflow: [bold]{saved.name}[/bold] (id: {saved.id})")


def _cmd_list(args, store):
    from rich.console import Console
    from rich.table import Table
    workflows = store.list_workflows()
    if args.status:
        workflows = [w for w in workflows if w.status.value == args.status]
    if args.json:
        data = [{"id": w.id, "name": w.name, "status": w.status.value if hasattr(w.status, 'value') else w.status,
                 "nodes": len(w.nodes), "schedule": w.schedule} for w in workflows]
        print(json.dumps(data, indent=2))
        return
    console = Console()
    if not workflows:
        console.print("[yellow]No workflows found. Create one with 'aetheros workflow create <name>'[/yellow]")
        return
    table = Table("ID", "Name", "Status", "Nodes", "Schedule")
    for wf in workflows:
        table.add_row(wf.id[:16] + "...", wf.name,
                      wf.status.value if hasattr(wf.status, 'value') else str(wf.status),
                      str(len(wf.nodes)),
                      wf.schedule or "-")
    console.print(table)


def _cmd_show(args, store):
    wf = store.get_workflow(args.workflow_id)
    if not wf:
        print(f"Workflow not found: {args.workflow_id}")
        return
    if args.json:
        print(json.dumps(wf.to_dict(), indent=2))
        return
    _print_workflow(wf, detailed=True)


def _cmd_run(args, store):
    from workflows.engine import WorkflowEngine
    context = {}
    if args.input:
        try:
            context = json.loads(args.input)
        except json.JSONDecodeError:
            context = {"input": args.input}
    engine = WorkflowEngine(store)
    if args.background:
        engine.start_background(args.workflow_id, context)
        print(f"Started workflow {args.workflow_id} in background")
    else:
        record = engine.run(args.workflow_id, context)
        status = record.status.value if hasattr(record.status, 'value') else record.status
        steps = len(record.steps or [])
        duration = f"{record.duration:.2f}s" if record.duration else "N/A"
        print(f"Workflow completed: [{'green' if record.status.name == 'COMPLETED' else 'red'}]{status}[/]")
        print(f"  Duration: {duration}")
        print(f"  Steps: {steps}")
        if record.error:
            print(f"  Error: {record.error}")


def _cmd_edit(args, store):
    wf = store.get_workflow(args.workflow_id)
    if not wf:
        print(f"Workflow not found: {args.workflow_id}")
        return
    changed = False
    if args.name:
        wf.name = args.name; changed = True
    if args.description:
        wf.description = args.description; changed = True
    if args.schedule:
        wf.schedule = args.schedule; changed = True
    if args.status:
        from workflows.models import WorkflowStatus
        wf.status = WorkflowStatus(args.status); changed = True
    if changed:
        store.update_workflow(wf)
        print(f"Updated workflow: {wf.id}")
    else:
        print("No changes made")


def _cmd_delete(args, store):
    if args.force or input(f"Delete workflow {args.workflow_id}? [y/N] ").lower() == "y":
        store.delete_workflow(args.workflow_id)
        print(f"Deleted workflow: {args.workflow_id}")
    else:
        print("Cancelled")


def _cmd_export(args, store):
    from workflows.marketplace import WorkflowMarketplace
    mp = WorkflowMarketplace(store)
    output = args.output or f"{args.workflow_id}.json"
    mp.export_workflow(args.workflow_id, output)
    print(f"Exported to: {output}")


def _cmd_import(args, store):
    from workflows.marketplace import WorkflowMarketplace
    mp = WorkflowMarketplace(store)
    wf_id = mp.import_workflow(args.file)
    if wf_id:
        print(f"Imported workflow: {wf_id}")


def _cmd_duplicate(args, store):
    wf = store.get_workflow(args.workflow_id)
    if not wf:
        print(f"Workflow not found: {args.workflow_id}")
        return
    import copy
    new_wf = copy.deepcopy(wf)
    new_wf.id = None
    new_wf.name = args.name or f"{wf.name} (Copy)"
    saved = store.save_workflow(new_wf)
    print(f"Duplicated: {saved.id}")


def _cmd_history(args, store):
    from rich.console import Console
    from rich.table import Table
    records = store.list_executions(workflow_id=args.workflow_id,
                                     limit=args.limit)
    if args.json:
        print(json.dumps([r.to_dict() for r in records], indent=2))
        return
    console = Console()
    table = Table("ID", "Status", "Started", "Duration", "Steps")
    for rec in records:
        status = rec.status.value if hasattr(rec.status, 'value') else rec.status
        started = rec.started_at.isoformat()[:19] if rec.started_at else "-"
        duration = f"{rec.duration:.1f}s" if rec.duration else "-"
        steps = len(rec.steps or [])
        table.add_row(rec.id[:16] + "...", status, started, duration, str(steps))
    console.print(table)


def _cmd_logs(args, store):
    from workflows.logging import WorkflowLogStore
    log_store = WorkflowLogStore()
    if args.execution:
        logs = log_store.get_execution_logs(args.execution)
    else:
        logs = log_store.search(workflow_id=args.workflow_id,
                                 level=args.level or None,
                                 query=args.query or None,
                                 limit=args.limit)
    for entry in logs:
        ts = entry.get("timestamp", "")[:19]
        level = entry.get("level", "INFO").ljust(7)
        msg = entry.get("message", "")
        print(f"{ts} [{level}] {msg}")


def _cmd_schedule(args, store):
    from workflows.scheduler import WorkflowScheduler
    scheduler = WorkflowScheduler(store)
    if args.action == "sync":
        added, removed = scheduler.sync_schedules()
        print(f"Synced: {added} added, {removed} removed")
    elif args.action in ("status", "list"):
        jobs = scheduler.get_schedule_status()
        if not jobs:
            print("No scheduled workflows")
            return
        for j in jobs:
            print(f"  {j['workflow_id'][:16]}... | {j['schedule']} | {'ON' if j['enabled'] else 'OFF'}")


def _cmd_marketplace(args, store):
    from workflows.marketplace import WorkflowMarketplace
    from rich.console import Console
    from rich.table import Table
    mp = WorkflowMarketplace(store)
    action = args.marketplace_action or "list"
    console = Console()
    if action == "list":
        catalog = mp.get_catalog(args.category if hasattr(args, 'category') else None)
        table = Table("ID", "Name", "Category", "Author", "Version")
        for w in catalog:
            table.add_row(w["id"], w["name"], w.get("category", ""),
                          w.get("author", ""), w.get("version", ""))
        console.print(table)
    elif action == "install":
        wf_id = mp.install_from_marketplace(args.marketplace_id,
                                             getattr(args, 'name', None))
        if wf_id:
            print(f"Installed workflow: {wf_id}")
        else:
            print(f"Failed to install: {args.marketplace_id}")
    elif action == "info":
        info = mp.get_workflow_info(args.marketplace_id)
        if info:
            print(f"Name: {info['name']}")
            print(f"Description: {info.get('description', '')}")
            print(f"Category: {info.get('category', '')}")
            print(f"Author: {info.get('author', '')}")
            print(f"Version: {info.get('version', '')}")
            print(f"Tags: {', '.join(info.get('tags', []))}")
            print(f"Nodes: {len(info.get('nodes', []))}")
        else:
            print(f"Not found: {args.marketplace_id}")
    elif action == "categories":
        for c in mp.get_categories():
            print(f"  {c}")


def _cmd_templates(args, store):
    from workflows.templates import list_templates
    templates = list_templates()
    from rich.console import Console
    from rich.table import Table
    console = Console()
    table = Table("ID", "Name", "Description", "Nodes")
    for t in templates:
        table.add_row(t.get("id", ""), t.get("name", ""),
                      t.get("description", "")[:50],
                      str(len(t.get("nodes", []))))
    console.print(table)


def _cmd_nodes(args, store):
    from workflows.nodes.base import NodeRegistry
    NodeRegistry.discover()
    from rich.console import Console
    from rich.table import Table
    console = Console()
    if args.category:
        nodes = NodeRegistry.get_by_category(args.category)
    else:
        nodes = NodeRegistry.get_all().values()
    table = Table("Type", "Category", "Label", "Description")
    for nc in sorted(nodes, key=lambda x: f"{x.category}.{x.type}"):
        table.add_row(nc.type, nc.category, nc.label,
                      nc.description[:50] + "..." if len(nc.description) > 50 else nc.description)
    console.print(table)


def _cmd_daemon(args, store):
    from workflows.executor import WorkflowExecutor
    executor = WorkflowExecutor(store)
    if args.action == "start":
        import asyncio
        asyncio.create_task(executor.start())
        print("Executor daemon started")
    elif args.action == "stop":
        import asyncio
        asyncio.create_task(executor.stop())
        print("Executor daemon stopped")
    elif args.action == "status":
        print(f"Executor running: {executor.is_running()}")


def _cmd_dashboard(args, store):
    from workflows.engine import WorkflowEngine
    engine = WorkflowEngine(store)
    NodeRegistry.discover()
    workflows = store.list_workflows()
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    console = Console()
    console.print(Panel("[bold]Workflow Studio Dashboard[/bold]"))
    console.print(f"\n  Active workflows: {len([w for w in workflows if w.status and hasattr(w.status, 'value') and w.status.value == 'active'])}")
    console.print(f"  Total workflows: {len(workflows)}")
    console.print(f"  Available node types: {len(NodeRegistry.get_all())}")
    records = store.list_executions(limit=10)
    if records:
        console.print("\n[bold]Recent Executions:[/bold]")
        table = Table("ID", "Workflow", "Status", "Duration")
        for rec in records:
            wf = store.get_workflow(rec.workflow_id)
            wf_name = wf.name if wf else rec.workflow_id[:16]
            status = rec.status.value if hasattr(rec.status, 'value') else rec.status
            duration = f"{rec.duration:.1f}s" if rec.duration else "-"
            table.add_row(rec.id[:12] + "...", wf_name, status, duration)
        console.print(table)


def show_workflow_help():
    print("Usage: aetheros workflow <command> [options]")
    print("\nCommands:")
    for cmd, desc in [
        ("create", "Create a new workflow"),
        ("list", "List workflows"),
        ("show", "Show workflow details"),
        ("run", "Execute a workflow"),
        ("edit", "Edit workflow configuration"),
        ("delete", "Delete a workflow"),
        ("export", "Export workflow as JSON"),
        ("import", "Import workflow from JSON"),
        ("duplicate", "Duplicate a workflow"),
        ("history", "Show execution history"),
        ("logs", "Show workflow logs"),
        ("schedule", "Schedule management"),
        ("marketplace", "Workflow marketplace"),
        ("templates", "List starter templates"),
        ("nodes", "List available node types"),
        ("daemon", "Workflow executor daemon"),
        ("dashboard", "Show workflow dashboard"),
    ]:
        print(f"  {cmd:<15} {desc}")
