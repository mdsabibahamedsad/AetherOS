from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import rich
    from rich.box import ROUNDED
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
    from rich.table import Table
    from rich.text import Text
    from rich.tree import Tree
    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False


class LiveDisplay:
    """Real-time terminal dashboard with multi-agent workflow visualization."""

    def __init__(self, refresh_interval: float = 0.5) -> None:
        self._refresh_interval = refresh_interval
        self._running = False
        self._task: dict[str, Any] | None = None
        self._current_tool: tuple[str, dict[str, Any]] | None = None
        self._logs: list[tuple[str, str]] = []
        self._progress: dict[str, tuple[float, float]] = {}
        self._agent_activities: list[tuple[str, str, str]] = []  # (agent, action, task_id)
        self._workflow_graph: dict[str, list[str]] = {}  # task_id -> list of dependent task_ids
        self._workflow_steps: dict[str, list[dict]] = {}  # task_id -> list of step dicts
        self._engine_status: dict[str, Any] = {}

        self._rich_live: Live | None = None
        self._console = Console() if _RICH_AVAILABLE else None

    async def show_current_task(self, task: Any) -> None:
        if hasattr(task, "id"):
            self._task = {
                "id": getattr(task, "id", ""),
                "goal": getattr(task, "goal", getattr(task, "name", "")),
                "status": getattr(task, "status", ""),
                "mode": str(getattr(task, "mode", "")),
            }
        elif isinstance(task, dict):
            self._task = task
        else:
            self._task = {"name": str(task)}

    async def show_running_tool(self, tool_name: str, args: dict[str, Any]) -> None:
        self._current_tool = (tool_name, args)

    async def show_log(self, level: str, message: str) -> None:
        self._logs.append((level, message))
        if len(self._logs) > 200:
            self._logs = self._logs[-200:]

    async def show_progress(self, task_id: str, progress: float, elapsed: float) -> None:
        self._progress[task_id] = (progress, elapsed)

    async def show_agent_activity(self, agent: str, action: str, task_id: str = "") -> None:
        self._agent_activities.append((agent, action, task_id))
        if len(self._agent_activities) > 100:
            self._agent_activities = self._agent_activities[-100:]

    async def set_workflow_graph(self, graph: dict[str, list[str]]) -> None:
        self._workflow_graph = graph

    async def set_workflow_steps(self, task_id: str, steps: list[dict]) -> None:
        self._workflow_steps[task_id] = steps

    async def set_engine_status(self, status: dict[str, Any]) -> None:
        self._engine_status = status

    async def render(self) -> str:
        lines: list[str] = []

        if self._engine_status:
            lines.append(f" Engine: {'RUNNING' if self._engine_status.get('running') else 'STOPPED'}"
                         f" | Mode: {self._engine_status.get('current_mode', 'N/A')}"
                         f" | Tasks: {self._engine_status.get('task_count', 0)}"
                         f" | Agents: {self._engine_status.get('agent_count', 0)}")

        if self._task:
            t = self._task
            lines.append(f" Task: {t.get('goal', '?')}  [{t.get('status', '?')}]")

        if self._current_tool:
            name, args = self._current_tool
            args_str = ", ".join(f"{k}={v}" for k, v in args.items())
            lines.append(f" Tool: {name}({args_str})")

        if self._progress:
            for task_id, (progress, elapsed) in sorted(self._progress.items()):
                bar_len = 15
                filled = int(bar_len * progress / 100) if isinstance(progress, (int, float)) else 0
                bar = "█" * filled + "░" * (bar_len - filled)
                lines.append(f"  [{task_id[:8]}] {bar}  {progress:.0f}%  ({elapsed:.1f}s)")

        if self._workflow_graph:
            lines.append(" Workflow DAG:")
            for parent, children in self._workflow_graph.items():
                for child in children:
                    lines.append(f"  {parent[:8]} → {child[:8]}")

        if self._agent_activities:
            lines.append(" Agent Activity:")
            for agent, action, tid in self._agent_activities[-5:]:
                tag = f"[{tid[:8]}]" if tid else ""
                lines.append(f"  [{agent}] {action} {tag}")

        if self._logs:
            for level, msg in self._logs[-6:]:
                lines.append(f"  {level.upper():<7} {msg}")

        return "\n".join(lines)

    async def start_display_loop(self) -> None:
        if self._running:
            return
        self._running = True
        if _RICH_AVAILABLE and self._console:
            self._loop_task = asyncio.create_task(self._rich_loop())
        else:
            self._loop_task = asyncio.create_task(self._plain_loop())
        logger.info("LiveDisplay: display loop started")

    async def stop_display_loop(self) -> None:
        self._running = False
        if hasattr(self, "_loop_task"):
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        logger.info("LiveDisplay: display loop stopped")

    async def _plain_loop(self) -> None:
        while self._running:
            output = await self.render()
            print("\033[2J\033[H", end="")
            print(f"╔══ Aether Automation Engine {'═' * 40}")
            print(output)
            print(f"╚{'═' * 60}")
            await asyncio.sleep(self._refresh_interval)

    async def _rich_loop(self) -> None:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )

        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
        )
        task_progress_ids: dict[str, int] = {}

        with Live(layout, console=self._console, refresh_per_second=2) as live:
            while self._running:
                header_text = Text("Aether Automation Engine", style="bold cyan")
                if self._task:
                    t = self._task
                    header_text.append(f"  |  {t.get('goal', '?')} [{t.get('status', '?')}]", style="yellow")

                layout["header"].update(Panel(header_text, box=ROUNDED))

                body_panels: list[Panel] = []

                if self._current_tool:
                    name, args = self._current_tool
                    args_str = ", ".join(f"{k}={v}" for k, v in args.items())
                    body_panels.append(
                        Panel(Text(f"▸ {name}({args_str})", style="green"), title="Running Tool", box=ROUNDED)
                    )

                for tid, (p, elapsed) in self._progress.items():
                    if tid not in task_progress_ids:
                        task_progress_ids[tid] = progress.add_task(f"[cyan]{tid[:8]}[/]", total=100.0)
                    pid = task_progress_ids[tid]
                    progress.update(pid, completed=p)
                    progress.tasks[pid].description = f"[cyan]{tid[:8]}[/] ({elapsed:.1f}s)"
                body_panels.append(Panel(progress, title="Progress", box=ROUNDED))

                if self._workflow_graph:
                    tree = Tree("Workflow DAG")
                    seen = set()
                    def add_tasks(parent_id: str, parent_node: Tree):
                        if parent_id in seen:
                            return
                        seen.add(parent_id)
                        for child_id in self._workflow_graph.get(parent_id, []):
                            branch = parent_node.add(f"[cyan]{child_id[:8]}[/]")
                            add_tasks(child_id, branch)
                    roots = set(self._workflow_graph.keys()) - set().union(*self._workflow_graph.values())
                    for root in sorted(roots):
                        node = tree.add(f"[yellow]{root[:8]}[/]")
                        add_tasks(root, node)
                    body_panels.append(Panel(tree, title="Workflow DAG", box=ROUNDED))

                if self._agent_activities:
                    act_table = Table.grid(padding=(0, 1))
                    act_table.add_column()
                    for agent, action, tid in self._agent_activities[-8:]:
                        tag = f" [{tid[:6]}]" if tid else ""
                        act_table.add_row(
                            Text(f"[{agent}]", style="magenta"),
                            Text(f"{action}{tag}", style="white"),
                        )
                    body_panels.append(Panel(act_table, title="Agent Activity", box=ROUNDED))

                if self._logs:
                    log_table = Table.grid(padding=(0, 1))
                    log_table.add_column()
                    for level, msg in self._logs[-10:]:
                        style = {"error": "red", "warning": "yellow", "info": "green", "debug": "dim white"}.get(level.lower(), "white")
                        log_table.add_row(Text(f"{level.upper():<7}", style=style), Text(msg, style=style))
                    body_panels.append(Panel(log_table, title="Log", box=ROUNDED))

                if not body_panels:
                    body_panels.append(Panel(Text("Awaiting tasks...", style="dim"), box=ROUNDED))

                body_layout = Layout()
                if len(body_panels) == 1:
                    body_layout.update(body_panels[0])
                else:
                    body_layout.split_column(*[Layout(p) for p in body_panels])

                layout["body"].update(body_layout)

                footer_text = Text(
                    f"Ctrl+C to stop  |  agents: {len([a for a in self._agent_activities[-50:] if a])}  |  refresh: {self._refresh_interval:.1f}s",
                    style="dim",
                )
                layout["footer"].update(Panel(footer_text, box=ROUNDED))

                await asyncio.sleep(self._refresh_interval)

    def terminal_ui(self) -> str:
        if not _RICH_AVAILABLE:
            return "[Rich not available – install with 'pip install rich']\n"
        from rich.console import Console as RichConsole
        from rich.table import Table as RichTable

        console = RichConsole(width=80, force_terminal=True)
        with console.capture() as capture:
            if self._task:
                t = self._task
                table = RichTable(title="Current Task", box=ROUNDED)
                table.add_column("Key", style="cyan")
                table.add_column("Value", style="white")
                for k, v in t.items():
                    table.add_row(str(k), str(v))
                console.print(table)
            if self._current_tool:
                name, args = self._current_tool
                console.print(f"[green]▸[/] {name}({args})")
            if self._progress:
                prog = Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TextColumn("[progress.percentage]{task.percentage:>3.0f}%"), TimeElapsedColumn())
                for tid, (p, _elapsed) in self._progress.items():
                    prog.add_task(f"[cyan]{tid[:8]}[/]", total=100.0, completed=p)
                console.print(prog)
            if self._agent_activities:
                lt = RichTable.grid(padding=(0, 1))
                lt.add_column()
                for agent, action, tid in self._agent_activities[-5:]:
                    lt.add_row(Text(f"[{agent}]", style="magenta"), Text(action, style="white"))
                console.print(Panel(lt, title="Agent Activity", box=ROUNDED))
            if self._logs:
                lt = RichTable.grid(padding=(0, 1))
                lt.add_column()
                for level, msg in self._logs[-10:]:
                    style = {"error": "red", "warning": "yellow", "info": "green", "debug": "dim white"}.get(level.lower(), "white")
                    lt.add_row(Text(f"{level.upper():<7}", style=style), Text(msg, style=style))
                console.print(Panel(lt, title="Log", box=ROUNDED))
        return capture.get()
