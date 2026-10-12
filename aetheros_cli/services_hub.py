"""
AetherOS Services Hub — manage all connected services and integrations.

Provides a unified interface for connecting, disconnecting, health-checking,
and managing permissions for every platform integration and service that
AetherOS supports.

Services:
  Communication: Telegram, Discord, Slack, Teams, WhatsApp
  Google: Gmail, Calendar, Drive, Docs, Sheets
  Development: GitHub, GitLab, Bitbucket, Docker, Kubernetes
  Productivity: Notion, Jira, Linear, ClickUp, Trello
  Cloud: Dropbox, OneDrive, Box
  Email: Gmail, Outlook, IMAP, SMTP
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from aetheros_cli.config import (
    get_env_value,
    save_env_value,
    remove_env_value,
    load_config,
    save_config,
)
from aetheros_cli.setup_renderer import (
    C_ACCENT,
    C_BORDER,
    C_CARD_BG,
    C_CYAN,
    C_DIM,
    C_ERROR,
    C_NAV_BG,
    C_PURPLE,
    C_SUCCESS,
    C_TEXT,
    C_WARN,
    clear,
    get_console,
    icon,
    make_card,
    make_keyboard_hints,
    make_nav_bar,
    make_step_progress,
    make_status_indicator,
    make_success_screen,
    make_error_screen,
)
from aetheros_cli.setup_wizard import _get_key

logger = logging.getLogger(__name__)


# =============================================================================
# Service Registry
# =============================================================================

_SERVICE_CATEGORIES = {
    "messaging": "Communication",
    "google": "Google",
    "dev": "Development",
    "productivity": "Productivity",
    "cloud": "Cloud Storage",
    "email": "Email",
}

_SERVICES = [
    # (id, name, category, icon, env_var, auth_type, description)
    # Communication
    ("telegram", "Telegram Bot", "messaging", "🤖", "TELEGRAM_BOT_TOKEN", "token", "Send and receive messages via Telegram bot"),
    ("telegram_personal", "Telegram Personal", "messaging", "📱", "TELEGRAM_API_ID", "oauth", "Login with your Telegram account"),
    ("discord", "Discord", "messaging", "💬", "DISCORD_BOT_TOKEN", "token", "Connect to Discord servers"),
    ("slack", "Slack", "messaging", "🔲", "SLACK_BOT_TOKEN", "oauth", "Integrate with Slack workspaces"),
    ("teams", "Microsoft Teams", "messaging", "🪟", "TEAMS_APP_ID", "oauth", "Microsoft Teams integration"),
    ("whatsapp", "WhatsApp Business", "messaging", "📞", "WHATSAPP_TOKEN", "token", "WhatsApp Business API"),

    # Google
    ("gmail", "Gmail", "google", "📧", "GMAIL_CREDENTIALS", "oauth", "Read and send emails"),
    ("calendar", "Google Calendar", "google", "📅", "GOOGLE_CALENDAR_CREDENTIALS", "oauth", "Manage calendar events"),
    ("drive", "Google Drive", "google", "📂", "GOOGLE_DRIVE_CREDENTIALS", "oauth", "Access Google Drive files"),
    ("docs", "Google Docs", "google", "📝", "GOOGLE_DOCS_CREDENTIALS", "oauth", "Create and edit documents"),
    ("sheets", "Google Sheets", "google", "📊", "GOOGLE_SHEETS_CREDENTIALS", "oauth", "Work with spreadsheets"),

    # Development
    ("github", "GitHub", "dev", "🐙", "GITHUB_TOKEN", "token", "Manage repositories and issues"),
    ("gitlab", "GitLab", "dev", "🦊", "GITLAB_TOKEN", "token", "GitLab integration"),
    ("bitbucket", "Bitbucket", "dev", "🔵", "BITBUCKET_APP_PASSWORD", "token", "Bitbucket repositories"),
    ("docker", "Docker", "dev", "🐳", "DOCKER_API_KEY", "token", "Container management"),
    ("kubernetes", "Kubernetes", "dev", "☸", "KUBE_CONFIG_PATH", "config", "Kubernetes cluster management"),

    # Productivity
    ("notion", "Notion", "productivity", "📘", "NOTION_API_KEY", "token", "Notion workspace integration"),
    ("jira", "Jira", "productivity", "🔶", "JIRA_API_TOKEN", "token", "Jira issue tracking"),
    ("linear", "Linear", "productivity", "⬛", "LINEAR_API_KEY", "token", "Linear project management"),
    ("clickup", "ClickUp", "productivity", "🟣", "CLICKUP_API_KEY", "token", "ClickUp workspace"),
    ("trello", "Trello", "productivity", "🔷", "TRELLO_API_KEY", "token", "Trello board management"),

    # Cloud
    ("dropbox", "Dropbox", "cloud", "📦", "DROPBOX_TOKEN", "oauth", "Dropbox file access"),
    ("onedrive", "OneDrive", "cloud", "☁", "ONEDRIVE_TOKEN", "oauth", "Microsoft OneDrive"),
    ("box", "Box", "cloud", "📦", "BOX_TOKEN", "oauth", "Box cloud storage"),

    # Email
    ("outlook", "Outlook", "email", "📧", "OUTLOOK_CREDENTIALS", "oauth", "Microsoft Outlook"),
    ("imap", "IMAP", "email", "📨", "IMAP_PASSWORD", "password", "IMAP email access"),
    ("smtp", "SMTP", "email", "📤", "SMTP_PASSWORD", "password", "SMTP email sending"),
]


def _get_service_health(name: str, env_var: str) -> tuple[str, str]:
    """Check if a service is configured and appears healthy."""
    value = get_env_value(env_var)
    if not value:
        return ("disconnected", "Not configured")
    if len(value) > 4:
        return ("connected", f"Configured ({'*' * 8}{value[-4:]})")
    return ("warning", "Configured but may be invalid")


# =============================================================================
# ServicesHub
# =============================================================================

class ServicesHub:
    """Unified interface for managing all connected services."""

    def __init__(self, config: dict | None = None):
        self.config = config or load_config()
        self._running = True
        self._cursor = 0
        self._filter_category: str | None = None
        self._filtered_services: list = list(_SERVICES)
        self._detail_mode = False
        self._detail_cursor = 0

    def run(self) -> None:
        """Run the services hub interface."""
        try:
            self._browser_loop()
        except KeyboardInterrupt:
            pass

    def _refresh_filtered(self) -> None:
        """Refresh the filtered service list based on category filter."""
        if self._filter_category:
            self._filtered_services = [
                s for s in _SERVICES if s[2] == self._filter_category
            ]
        else:
            self._filtered_services = list(_SERVICES)

    def _get_categories_with_counts(self) -> list[tuple[str, str, int, int]]:
        """Get categories with connected/total counts."""
        result = []
        for cat_id, cat_name in _SERVICE_CATEGORIES.items():
            services = [s for s in _SERVICES if s[2] == cat_id]
            total = len(services)
            connected = sum(
                1 for s in services if get_env_value(s[4])
            )
            result.append((cat_id, cat_name, connected, total))
        return result

    def _browser_loop(self) -> None:
        """Main browser loop for services hub."""
        while self._running:
            clear()
            self._render_browser()
            key = _get_key()
            self._handle_browser_input(key)

    def _render_browser(self) -> None:
        """Render the services browser."""
        progress = make_step_progress(1, 1, "Services Hub", "Manage your connected services")
        get_console().print(progress)
        get_console().print()

        # Category filter bar
        filter_bar = Table.grid(padding=(0, 1))
        filter_bar.add_column("Filter", width=80)

        parts = ["[bold]Filter:[/bold]  "]
        parts.append("[bold #58a6ff]All[/bold #58a6ff]" if not self._filter_category else "[dim]All[/dim]")
        parts.append("  ")

        for cat_id, cat_name in _SERVICE_CATEGORIES.items():
            is_active = self._filter_category == cat_id
            cat_style = f"bold {C_ACCENT}" if is_active else C_DIM
            parts.append(f"[{cat_style}]{cat_name}[/{cat_style}]")
            parts.append("  ")

        filter_bar.add_row("".join(parts))
        get_console().print(
            Panel(filter_bar, border_style=C_BORDER, padding=(0, 1), box=box.ROUNDED)
        )
        get_console().print()

        # Service list
        self._refresh_filtered()
        table = Table.grid(padding=(0, 2))
        table.add_column("Sel", width=4)
        table.add_column("Service", width=22)
        table.add_column("Category", width=14)
        table.add_column("Status", width=16)
        table.add_column("Auth", width=10)
        table.add_column("Action", width=16)

        for i, (sid, name, cat, serv_icon, env_var, auth_type, desc) in enumerate(self._filtered_services):
            status, status_detail = _get_service_health(sid, env_var)
            sel = "▸" if i == self._cursor else " "
            style = f"bold {C_TEXT}" if i == self._cursor else C_DIM

            status_colors = {
                "connected": C_SUCCESS,
                "disconnected": C_DIM,
                "warning": C_WARN,
            }
            status_color = status_colors.get(status, C_DIM)
            status_label = {
                "connected": "✓ Connected",
                "disconnected": "○ Disconnected",
                "warning": "⚠ Warning",
            }.get(status, "?")

            action_label = "Manage" if status == "connected" else "Connect"

            table.add_row(
                Text(f"{sel} {serv_icon}", style=style),
                Text(name, style=style),
                Text(_SERVICE_CATEGORIES.get(cat, cat), style=f"dim {C_DIM}"),
                Text(status_label, style=f"bold {status_color}"),
                Text(auth_type.upper(), style=f"dim {C_DIM}"),
                Text(action_label, style=f"bold {C_ACCENT}" if i == self._cursor else C_DIM),
            )

        get_console().print(
            Panel(
                Group(table, Text("")),
                border_style=C_ACCENT,
                padding=(1, 2),
                box=box.ROUNDED,
            )
        )
        get_console().print()

        # Category summary
        summary_parts = []
        for cat_id, cat_name, connected, total in self._get_categories_with_counts():
            summary_parts.append(f"  {cat_name}: {connected}/{total}")
        summary_text = "  |".join(summary_parts)

        get_console().print(
            Panel(
                Text(f"  {summary_text}", style=f"dim {C_DIM}"),
                border_style=C_BORDER,
                padding=(0, 1),
                box=box.ROUNDED,
            )
        )
        get_console().print()

        hints = [
            ("↑↓", "Navigate"),
            ("Enter", "Manage service"),
            ("1-5", "Filter category"),
            ("A", "All services"),
            ("Esc", "Back"),
        ]
        get_console().print(make_keyboard_hints(hints))

    def _handle_browser_input(self, key: str) -> None:
        """Handle keyboard input in browser mode."""
        if key == "cancel":
            self._running = False
        elif key == "up":
            self._cursor = max(0, self._cursor - 1)
        elif key == "down":
            self._cursor = min(len(self._filtered_services) - 1, self._cursor + 1)
        elif key == "confirm":
            if self._filtered_services:
                self._manage_service(self._cursor)
        elif key == "a" or key == "A":
            self._filter_category = None
            self._cursor = 0
        elif key in ("1", "2", "3", "4", "5"):
            cat_keys = list(_SERVICE_CATEGORIES.keys())
            idx = int(key) - 1
            if idx < len(cat_keys):
                self._filter_category = cat_keys[idx]
                self._cursor = 0

    def _manage_service(self, index: int) -> None:
        """Manage a specific service (connect/disconnect/health check)."""
        if index >= len(self._filtered_services):
            return
        sid, name, cat, serv_icon, env_var, auth_type, desc = self._filtered_services[index]
        status, status_detail = _get_service_health(sid, env_var)
        editing = True

        while editing:
            clear()
            progress = make_step_progress(1, 1, f"Manage {name}", desc)
            get_console().print(progress)
            get_console().print()

            # Service detail panel
            detail_table = Table.grid(padding=(0, 2))
            detail_table.add_column("Property", width=16)
            detail_table.add_column("Value", width=50)
            detail_table.add_row(
                Text("  Service", style=f"bold {C_ACCENT}"),
                Text(f"{serv_icon}  {name}", style=C_TEXT),
            )
            detail_table.add_row(
                Text("  Category", style=f"bold {C_ACCENT}"),
                Text(_SERVICE_CATEGORIES.get(cat, cat), style=C_DIM),
            )
            detail_table.add_row(
                Text("  Auth Type", style=f"bold {C_ACCENT}"),
                Text(auth_type.upper(), style=C_DIM),
            )
            detail_table.add_row(
                Text("  Status", style=f"bold {C_ACCENT}"),
                Text(
                    "✓ Connected" if status == "connected" else
                    "⚠ Warning" if status == "warning" else
                    "○ Disconnected",
                    style=f"bold {C_SUCCESS if status == 'connected' else C_WARN if status == 'warning' else C_DIM}",
                ),
            )
            if status_detail:
                detail_table.add_row(
                    Text("  Details", style=f"bold {C_ACCENT}"),
                    Text(status_detail, style=f"dim {C_DIM}"),
                )

            get_console().print(
                Panel(
                    Group(detail_table, Text("")),
                    border_style=C_ACCENT if status == "connected" else C_BORDER,
                    padding=(1, 2),
                    box=box.ROUNDED,
                )
            )
            get_console().print()

            # Action buttons
            action_table = Table.grid(padding=(0, 2))
            action_table.add_column("Action", width=60)

            actions = []
            if status == "connected":
                actions = [
                    ("1", "🔄  Reconnect", "Re-establish connection"),
                    ("2", "🔍  Health Check", "Verify service is operational"),
                    ("3", "🔑  View Permissions", "See granted permissions"),
                    ("4", "❌  Disconnect", "Remove access and configuration"),
                    ("5", "📋  View Config", "Inspect current configuration"),
                ]
            else:
                actions = [
                    ("1", "🔗  Connect", "Set up this service"),
                    ("2", "🔍  Health Check", "Verify service availability"),
                ]

            for num, act_label, act_desc in actions:
                action_table.add_row(
                    Text(f"  [{C_ACCENT}]{num}[/{C_ACCENT}]  {act_label}", style=C_TEXT)
                    + Text(f"  — {act_desc}", style=f"dim {C_DIM}")
                )

            get_console().print(
                Panel(
                    Group(action_table, Text("")),
                    title="[bold]Actions[/bold]",
                    border_style=C_BORDER,
                    padding=(1, 2),
                    box=box.ROUNDED,
                )
            )
            get_console().print()

            hints = [
                ("1-5", "Select action"),
                ("Esc", "Back to services"),
            ]
            get_console().print(make_keyboard_hints(hints))

            key = _get_key()
            if key == "cancel":
                editing = False
            elif key == "1":
                if status == "connected":
                    self._reconnect_service(sid, name, env_var, auth_type)
                else:
                    self._connect_service(sid, name, env_var, auth_type)
                status, status_detail = _get_service_health(sid, env_var)
            elif key == "2":
                self._health_check(sid, name, env_var)
            elif key == "3" and status == "connected":
                self._view_permissions(name)
            elif key == "4" and status == "connected":
                self._disconnect_service(sid, name, env_var)
                status, status_detail = _get_service_health(sid, env_var)
            elif key == "5" and status == "connected":
                self._view_config(sid, name, env_var)

    def _connect_service(self, sid: str, name: str, env_var: str, auth_type: str) -> None:
        """Connect a service by collecting credentials."""
        clear()
        get_console().print(
            Panel(
                Align.center(
                    Group(
                        Text(f"Connect {name}", style=f"bold {C_ACCENT}"),
                        Text(""),
                        Text(f"Authentication: {auth_type.upper()}", style=C_DIM),
                    ),
                    vertical="middle",
                ),
                border_style=C_ACCENT,
                padding=(2, 4),
                box=box.ROUNDED,
            )
        )

        from prompt_toolkit import PromptSession
        from prompt_toolkit.styles import Style as PtStyle
        pt_style = PtStyle.from_dict({"prompt": "#58a6ff bold", "": "#e6edf3"})
        session = PromptSession(style=pt_style)

        try:
            value = session.prompt(
                f"  {C_ACCENT}▸{C_DIM}  Enter credential/token: ",
                is_password=True,
            )
            if value:
                save_env_value(env_var, value)
                get_console().print(
                    Panel(
                        Align.center(Text(f"✓  {name} connected successfully", style=f"bold {C_SUCCESS}")),
                        border_style=C_SUCCESS,
                        padding=(1, 2),
                        box=box.ROUNDED,
                    )
                )
                time.sleep(1)
        except (EOFError, KeyboardInterrupt):
            pass

    def _reconnect_service(self, sid: str, name: str, env_var: str, auth_type: str) -> None:
        """Reconnect a service by updating credentials."""
        current = get_env_value(env_var) or ""
        clear()
        get_console().print(
            Panel(
                Align.center(
                    Group(
                        Text(f"Reconnect {name}", style=f"bold {C_ACCENT}"),
                        Text(""),
                        Text("Enter new credentials to replace existing ones.", style=C_DIM),
                    ),
                    vertical="middle",
                ),
                border_style=C_WARN,
                padding=(2, 4),
                box=box.ROUNDED,
            )
        )

        from prompt_toolkit import PromptSession
        from prompt_toolkit.styles import Style as PtStyle
        pt_style = PtStyle.from_dict({"prompt": "#58a6ff bold", "": "#e6edf3"})
        session = PromptSession(style=pt_style)

        try:
            value = session.prompt(
                f"  {C_ACCENT}▸{C_DIM}  New credential/token: ",
                default=current,
                is_password=True,
            )
            if value and value != current:
                save_env_value(env_var, value)
                get_console().print(
                    Panel(
                        Align.center(Text(f"✓  {name} reconnected", style=f"bold {C_SUCCESS}")),
                        border_style=C_SUCCESS,
                        padding=(1, 2),
                        box=box.ROUNDED,
                    )
                )
                time.sleep(1)
        except (EOFError, KeyboardInterrupt):
            pass

    def _disconnect_service(self, sid: str, name: str, env_var: str) -> None:
        """Disconnect a service by removing its credentials."""
        get_console().print(
            Panel(
                Align.center(
                    Group(
                        Text(f"Disconnect {name}?", style=C_WARN),
                        Text(""),
                        Text("This will remove all stored credentials.", style=C_DIM),
                    ),
                    vertical="middle",
                ),
                border_style=C_WARN,
                padding=(1, 2),
                box=box.ROUNDED,
            )
        )
        get_console().print(Text("  Press Y to confirm, any other key to cancel", style=f"dim {C_DIM}"))

        key = _get_key()
        if key in ("y", "Y"):
            remove_env_value(env_var)
            get_console().print(
                Panel(
                    Align.center(Text(f"✗  {name} disconnected", style=C_DIM)),
                    border_style=C_BORDER,
                    padding=(1, 2),
                    box=box.ROUNDED,
                )
            )
            time.sleep(1)

    def _health_check(self, sid: str, name: str, env_var: str) -> None:
        """Run a health check on a service."""
        value = get_env_value(env_var)
        clear()

        if not value:
            get_console().print(
                make_error_screen(
                    "Health Check Failed",
                    f"{name} is not configured.",
                    "Use Connect to set up this service.",
                )
            )
        else:
            get_console().print(
                Panel(
                    Align.center(
                        Group(
                            Text(f"Health Check: {name}", style=f"bold {C_ACCENT}"),
                            Text(""),
                            Text("✓  Credentials found", style=f"bold {C_SUCCESS}"),
                            Text("  Service appears configured", style=C_DIM),
                            Text(""),
                            Text("Full connectivity check requires service interaction.", style=f"dim {C_DIM}"),
                        ),
                        vertical="middle",
                    ),
                    border_style=C_SUCCESS,
                    padding=(2, 4),
                    box=box.ROUNDED,
                )
            )
        get_console().print(Text("  Press any key to continue", style=f"dim {C_DIM}"))
        _get_key()

    def _view_permissions(self, name: str) -> None:
        """View service permissions."""
        clear()
        get_console().print(
            Panel(
                Align.center(
                    Group(
                        Text(f"Permissions: {name}", style=f"bold {C_ACCENT}"),
                        Text(""),
                        Text("Permissions are managed through the service's own portal.", style=C_DIM),
                        Text(""),
                        Text("Open the service's settings page to review and manage", style=C_DIM),
                        Text("the specific permissions granted to this integration.", style=C_DIM),
                    ),
                    vertical="middle",
                ),
                border_style=C_BORDER,
                padding=(2, 4),
                box=box.ROUNDED,
            )
        )
        get_console().print(Text("  Press any key to continue", style=f"dim {C_DIM}"))
        _get_key()

    def _view_config(self, sid: str, name: str, env_var: str) -> None:
        """View service configuration."""
        value = get_env_value(env_var) or ""
        masked = f"{'*' * 20}{value[-4:]}" if len(value) > 8 else "(not configured)"
        clear()
        get_console().print(
            Panel(
                Align.center(
                    Group(
                        Text(f"Configuration: {name}", style=f"bold {C_ACCENT}"),
                        Text(""),
                        Text(f"  Environment Variable: {env_var}", style=C_DIM),
                        Text(f"  Current Value: {masked}", style=C_CYAN),
                        Text(""),
                        Text("Use Reconnect to update credentials.", style=f"dim {C_DIM}"),
                    ),
                    vertical="middle",
                ),
                border_style=C_BORDER,
                padding=(2, 4),
                box=box.ROUNDED,
            )
        )
        get_console().print(Text("  Press any key to continue", style=f"dim {C_DIM}"))
        _get_key()
