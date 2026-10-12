from __future__ import annotations

import textwrap
from typing import Any

from aetheros_automation.models.models import ApprovalRequest


class ApprovalPrompts:
    """Format human-readable prompts and dialogs for approval workflows."""

    @staticmethod
    def format_approval_prompt(request: ApprovalRequest) -> str:
        """Build a printable approval summary for a pending request."""
        lines = [
            "=" * 60,
            f"APPROVAL REQUEST  [{request.id[:8]}]",
            "=" * 60,
            f"  Task ID:    {request.task_id}",
            f"  Action:     {request.action}",
            f"  Status:     {request.status}",
            "",
            "  Description:",
            _indent(request.description, 4),
        ]

        if request.details:
            lines.extend([
                "",
                "  Details:",
            ])
            for key, value in request.details.items():
                formatted = _format_value(value)
                lines.append(f"    {key}: {formatted}")

        lines.extend([
            "",
            f"  Requested:  {_format_timestamp(request.created_at)}",
            "",
            "  Respond with  /approve [reason]  or  /deny [reason]",
        ])
        return "\n".join(lines)

    @staticmethod
    def format_confirmation_dialog(action: str, details: dict[str, Any] | None) -> str:
        """Build a short inline confirmation dialog for low-complexity actions."""
        details = details or {}
        lines = [
            "┌─ Confirm Action ─────────────────────────────────────────────┐",
            f"│  Action:  {_truncate(action, 55):<55} │",
        ]

        for key, value in details.items():
            formatted = _format_value(value)
            wrapped = textwrap.wrap(
                formatted, width=50, subsequent_indent=" " * 6,
            )
            for i, part in enumerate(wrapped):
                label = key if i == 0 else ""
                lines.append(f"│  {label:<8} {part:<50} │")

        lines.append(
            "├──────────────────────────────────────────────────────────────┤"
        )
        lines.append("│  Type  y (yes)  or  n (no)                             │")
        lines.append(
            "└──────────────────────────────────────────────────────────────┘"
        )
        return "\n".join(lines)


def _indent(text: str, spaces: int) -> str:
    prefix = " " * spaces
    return textwrap.fill(
        text, width=56, initial_indent=prefix, subsequent_indent=prefix,
    )


def _format_timestamp(ts: float) -> str:
    import datetime
    dt = datetime.datetime.fromtimestamp(ts)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _format_value(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return "; ".join(f"{k}={v}" for k, v in value.items())
    return str(value)


def _truncate(text: str, max_len: int) -> str:
    return text if len(text) <= max_len else text[: max_len - 3] + "..."
