"""Terminal Runtime.

Multi-shell command execution:
- PowerShell, CMD (Windows)
- Bash, Zsh, Fish (Unix)
- Run commands with capture
- Stream output with cancellation
- Full exit code and history support
"""

from __future__ import annotations

from tool_runtime.terminal.runtime import TerminalRuntime

__all__ = ["TerminalRuntime"]
