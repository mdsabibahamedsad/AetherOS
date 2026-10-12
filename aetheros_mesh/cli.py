"""CLI commands for mesh management (Master 49 section 104)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from aetheros_cli.commands import CommandDef, COMMAND_REGISTRY

logger = logging.getLogger(__name__)


# Add mesh commands to registry
MESH_COMMANDS = [
    CommandDef("mesh", "Global Agent Mesh management", "Mesh",
               aliases=(), args_hint="<subcommand>"),
    CommandDef("mesh status", "Show mesh status", "Mesh",
               aliases=(), args_hint="", cli_only=True),
    CommandDef("mesh topology", "Show mesh topology graph", "Mesh",
               aliases=(), args_hint="", cli_only=True),
    CommandDef("mesh nodes", "List mesh nodes", "Mesh",
               aliases=(), args_hint="[state]", cli_only=True),
    CommandDef("mesh edges", "Show mesh edges", "Mesh",
               aliases=(), args_hint="", cli_only=True),
    CommandDef("mesh tasks", "List mesh tasks", "Mesh",
               aliases=(), args_hint="", cli_only=True),
    CommandDef("mesh teams", "List mesh teams", "Mesh",
               aliases=(), args_hint="", cli_only=True),
    CommandDef("mesh incidents", "List mesh incidents", "Mesh",
               aliases=(), args_hint="[status]", cli_only=True),
    CommandDef("mesh optimize", "Run optimization loop", "Mesh",
               aliases=(), args_hint="", cli_only=True),
    CommandDef("mesh verify", "Verify recent results", "Mesh",
               aliases=(), args_hint="", cli_only=True),
    CommandDef("mesh isolate", "Quarantine an agent", "Mesh",
               aliases=(), args_hint="<agent_id>", cli_only=True),
    CommandDef("mesh revoke", "Revoke an agent", "Mesh",
               aliases=(), args_hint="<agent_id>", cli_only=True),
    CommandDef("mesh benchmark", "Run mesh benchmarks", "Mesh",
               aliases=(), args_hint="", cli_only=True),
    CommandDef("mesh experiments", "List experiments", "Mesh",
               aliases=(), args_hint="", cli_only=True),
    CommandDef("mesh discover", "Run mesh discovery", "Mesh",
               aliases=(), args_hint="", cli_only=True),
    CommandDef("mesh trust", "Show trust assessments", "Mesh",
               aliases=(), args_hint="[agent_id]", cli_only=True),
    CommandDef("mesh governance", "Show governance status", "Mesh",
               aliases=(), args_hint="", cli_only=True),
    CommandDef("mesh emergency-stop", "Activate emergency stop", "Mesh",
               aliases=(), args_hint="[reason]", cli_only=True),
    CommandDef("mesh emergency-resume", "Resume from emergency stop", "Mesh",
               aliases=(), args_hint="[reason]", cli_only=True),
]

# Register commands
for cmd in MESH_COMMANDS:
    # Check if already registered
    if cmd.name not in [c.name for c in COMMAND_REGISTRY]:
        COMMAND_REGISTRY.append(cmd)


def _get_mesh(cli) -> Optional[Any]:
    """Get or create mesh instance from CLI."""
    if not hasattr(cli, '_mesh'):
        try:
            from aetheros_mesh import create_global_agent_mesh
            from aetheros_constants import get_aetheros_home
            
            home = get_aetheros_home()
            cli._mesh = create_global_agent_mesh(home)
            
            # Start mesh if not already started
            if cli._mesh._state == "starting":
                cli._mesh.start()
        except Exception as e:
            logger.error(f"Failed to create mesh: {e}")
            return None
    return cli._mesh


def _handle_mesh(cli, cmd_original: str) -> bool:
    """Handle mesh subcommands."""
    parts = cmd_original.split()
    if len(parts) < 2:
        cli.console.print("[red]Usage: /mesh <subcommand>[/red]")
        cli.console.print("Subcommands: status, topology, nodes, edges, tasks, teams, incidents, optimize, verify, isolate, revoke, benchmark, experiments, discover, trust, governance, emergency-stop, emergency-resume")
        return True
    
    subcommand = parts[1]
    args = parts[2:] if len(parts) > 2 else []
    
    mesh = _get_mesh(cli)
    if not mesh:
        cli.console.print("[red]Failed to initialize mesh[/red]")
        return True
    
    try:
        result = mesh.execute_cli_command(subcommand, args)
        _print_result(cli, result)
    except Exception as e:
        cli.console.print(f"[red]Error: {e}[/red]")
        logger.exception("Mesh command failed")
    
    return True


def _print_result(cli, result: Dict[str, Any]) -> None:
    """Print command result nicely."""
    if "error" in result:
        cli.console.print(f"[red]{result['error']}[/red]")
        return
    
    # Handle specific result types
    if "mesh_id" in result and "node_count" in result:
        # MeshStatus
        from rich.table import Table
        table = Table(title=f"Mesh Status: {result['mesh_id']}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        for key, value in result.items():
            table.add_row(key.replace("_", " ").title(), str(value))
        cli.console.print(table)
    
    elif "nodes" in result:
        # Node list
        from rich.table import Table
        table = Table(title=f"Mesh Nodes ({len(result['nodes'])})")
        table.add_column("Node ID", style="cyan")
        table.add_column("Agent ID", style="white")
        table.add_column("State", style="yellow")
        table.add_column("Capabilities", style="green")
        table.add_column("Trust", style="magenta")
        table.add_column("Location", style="blue")
        
        for node in result["nodes"]:
            caps = ", ".join(node.get("capabilities", [])[:3])
            if len(node.get("capabilities", [])) > 3:
                caps += f" +{len(node['capabilities']) - 3} more"
            trust = node.get("trust", {})
            avg_trust = sum(trust.values()) / len(trust) if trust else 0
            table.add_row(
                node.get("node_id", "")[:12] + "...",
                node.get("agent_id", "")[:12] + "...",
                node.get("state", "unknown"),
                caps,
                f"{avg_trust:.2f}",
                node.get("location", "unknown"),
            )
        cli.console.print(table)
    
    elif "edges" in result:
        # Edge list
        from rich.table import Table
        table = Table(title="Mesh Edges")
        table.add_column("Source", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Targets", style="white")
        
        for source, edge_types in result["edges"].items():
            for edge_type, targets in edge_types.items():
                table.add_row(source[:12] + "...", edge_type, ", ".join(t[:12] + "..." for t in targets))
        cli.console.print(table)
    
    elif "tasks" in result:
        # Task list
        from rich.table import Table
        table = Table(title=f"Mesh Tasks ({len(result['tasks'])})")
        table.add_column("Task ID", style="cyan")
        table.add_column("Goal", style="white")
        table.add_column("Status", style="yellow")
        table.add_column("Topology", style="green")
        table.add_column("Agents", style="magenta")
        table.add_column("Confidence", style="blue")
        
        for task in result["tasks"]:
            table.add_row(
                task.get("task_id", "")[:12] + "...",
                task.get("goal", "")[:50] + "..." if len(task.get("goal", "")) > 50 else task.get("goal", ""),
                task.get("status", "unknown"),
                task.get("metadata", {}).get("topology", "unknown"),
                str(len(task.get("assigned_nodes", []))),
                f"{task.get('result', {}).get('confidence', 0):.2f}" if task.get('result') else "N/A",
            )
        cli.console.print(table)
    
    elif "teams" in result:
        # Team list
        from rich.table import Table
        table = Table(title=f"Mesh Teams ({len(result['teams'])})")
        table.add_column("Team ID", style="cyan")
        table.add_column("Task ID", style="white")
        table.add_column("Topology", style="yellow")
        table.add_column("Members", style="green")
        table.add_column("Active", style="magenta")
        
        for team in result["teams"]:
            table.add_row(
                team.get("team_id", "")[:12] + "...",
                team.get("task_id", "")[:12] + "...",
                team.get("topology", "unknown"),
                str(len(team.get("members", []))),
                "Yes" if team.get("active") else "No",
            )
        cli.console.print(table)
    
    elif "incidents" in result:
        # Incident list
        from rich.table import Table
        table = Table(title=f"Mesh Incidents ({len(result['incidents'])})")
        table.add_column("Incident ID", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Severity", style="red")
        table.add_column("Status", style="magenta")
        table.add_column("Agents", style="white")
        table.add_column("Title", style="green")
        
        for inc in result["incidents"]:
            table.add_row(
                inc.get("incident_id", "")[:12] + "...",
                inc.get("type", "unknown"),
                str(inc.get("severity", "unknown")),
                inc.get("status", "unknown"),
                str(len(inc.get("affected_agents", []))),
                inc.get("title", "")[:40] + "..." if len(inc.get("title", "")) > 40 else inc.get("title", ""),
            )
        cli.console.print(table)
    
    elif "optimization_loop" in result:
        loop = result["optimization_loop"]
        from rich.table import Table
        table = Table(title=f"Optimization Loop: {loop.get('loop_id', 'unknown')}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        for key, value in loop.items():
            if key not in ("proposals", "observations"):
                table.add_row(key, str(value))
        cli.console.print(table)
        
        if loop.get("proposals"):
            cli.console.print(f"\n[cyan]Proposals: {len(loop['proposals'])}[/cyan]")
            for p in loop["proposals"]:
                cli.console.print(f"  - {p.get('target', 'unknown')}: {p.get('status', 'unknown')} (confidence: {p.get('confidence', 0):.2f})")
    
    elif "experiments" in result:
        from rich.table import Table
        table = Table(title=f"Experiments ({len(result['experiments'])})")
        table.add_column("Experiment ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Metric", style="yellow")
        table.add_column("Status", style="green")
        table.add_column("Confidence", style="magenta")
        
        for exp in result["experiments"]:
            table.add_row(
                exp.get("experiment_id", "")[:12] + "...",
                exp.get("name", "unknown"),
                exp.get("metric", "unknown"),
                exp.get("status", "unknown"),
                f"{exp.get('confidence', 0):.2f}",
            )
        cli.console.print(table)
    
    elif "trust" in result:
        # Trust assessment
        from rich.table import Table
        table = Table(title=f"Trust Assessment: {result.get('agent_id', 'unknown')}")
        table.add_column("Dimension", style="cyan")
        table.add_column("Score", style="white")
        table.add_column("Confidence", style="yellow")
        table.add_column("Samples", style="green")
        
        for dim, data in result.get("dimensions", {}).items():
            table.add_row(
                dim,
                f"{data.get('score', 0):.4f}",
                f"{data.get('confidence', 0):.4f}",
                str(data.get('samples', 0)),
            )
        cli.console.print(table)
        
        cli.console.print(f"\nOverall: {result.get('overall_score', 0):.4f} (confidence: {result.get('overall_confidence', 0):.4f})")
        if result.get("flags"):
            cli.console.print(f"Flags: {', '.join(result['flags'])}")
    
    elif "governance" in result:
        gov = result["governance"]
        from rich.table import Table
        table = Table(title="Governance Status")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        for key, value in gov.items():
            if key != "policies_by_level":
                table.add_row(key.replace("_", " ").title(), str(value))
        cli.console.print(table)
        
        if "policies_by_level" in gov:
            cli.console.print("\n[cyan]Policies by Level:[/cyan]")
            for level, count in gov["policies_by_level"].items():
                cli.console.print(f"  {level}: {count}")
    
    elif "benchmark" in result:
        bench = result["benchmark"]
        from rich.table import Table
        table = Table(title="Mesh Benchmark")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        for key, value in bench.items():
            table.add_row(key.replace("_", " ").title(), str(value))
        cli.console.print(table)
    
    else:
        # Generic JSON output
        cli.console.print(json.dumps(result, indent=2, default=str))


# Register the handler with CLI
def register_mesh_commands(cli_class):
    """Register mesh commands with CLI class."""
    # This would be called from cli.py to add the mesh command handler
    original_process = cli_class.process_command
    
    def process_command(self, cmd_original: str):
        if cmd_original.strip().startswith("/mesh") or cmd_original.strip().startswith("mesh "):
            return _handle_mesh(self, cmd_original)
        return original_process(self, cmd_original)
    
    cli_class.process_command = process_command


# Export for integration
__all__ = [
    "register_mesh_commands",
    "MESH_COMMANDS",
]